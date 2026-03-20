from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler

from src.feature_engineering import add_engineered_features


SEGMENT_LABELS = {
    "low": "Residential",
    "mid": "Commercial",
    "high": "Industrial",
    "suspicious": "Suspicious cluster",
}


def _aggregate_consumers(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        return pd.DataFrame()
    frame = add_engineered_features(dataframe)
    aggregations = {
        "region": ("region", "last"),
        "area": ("area", "last"),
        "usage_profile": ("usage_profile", "last"),
        "avg_consumption_kwh": ("consumption_kwh", "mean"),
        "peak_consumption_kwh": ("consumption_kwh", "max"),
        "consumption_std": ("consumption_kwh", "std"),
        "night_usage_ratio": ("night_usage_ratio", "mean"),
        "peak_usage_ratio": ("peak_usage_ratio", "mean"),
        "power_factor_loss": ("power_factor_loss", "mean"),
        "voltage_irregularity": ("voltage_irregularity", "mean"),
        "theft_probability": ("theft_probability", "max") if "theft_probability" in frame.columns else ("consumption_kwh", "mean"),
        "anomaly_score": ("anomaly_score", "max") if "anomaly_score" in frame.columns else ("consumption_kwh", "mean"),
    }
    aggregated = frame.groupby("meter_id", as_index=False).agg(**aggregations)
    aggregated["consumption_std"] = aggregated["consumption_std"].fillna(0.0)
    return aggregated


def _rank_based_labels(consumption: pd.Series, labels: np.ndarray) -> dict[int, str]:
    ranked = (
        pd.DataFrame({"cluster": labels, "consumption": consumption})
        .groupby("cluster", as_index=False)["consumption"]
        .mean()
        .sort_values("consumption")
        .reset_index(drop=True)
    )
    scale = ["low", "mid", "high"]
    mapping: dict[int, str] = {}
    for index, row in ranked.iterrows():
        label_index = min(index, len(scale) - 1)
        mapping[int(row["cluster"])] = SEGMENT_LABELS[scale[label_index]]
    return mapping


def cluster_consumers(dataframe: pd.DataFrame, n_clusters: int = 3) -> pd.DataFrame:
    aggregated = _aggregate_consumers(dataframe)
    if aggregated.empty:
        aggregated["kmeans_cluster"] = pd.Series(dtype=int)
        aggregated["dbscan_cluster"] = pd.Series(dtype=int)
        aggregated["segment"] = pd.Series(dtype=object)
        return aggregated

    feature_columns = [
        "avg_consumption_kwh",
        "peak_consumption_kwh",
        "consumption_std",
        "night_usage_ratio",
        "peak_usage_ratio",
        "power_factor_loss",
        "voltage_irregularity",
    ]
    scaled = StandardScaler().fit_transform(aggregated[feature_columns].fillna(0.0))

    effective_clusters = max(1, min(n_clusters, len(aggregated)))
    kmeans = KMeans(n_clusters=effective_clusters, random_state=42, n_init=10)
    aggregated["kmeans_cluster"] = kmeans.fit_predict(scaled)

    if len(aggregated) >= 3:
        dbscan = DBSCAN(eps=1.15, min_samples=max(2, min(4, len(aggregated) // 3)))
        aggregated["dbscan_cluster"] = dbscan.fit_predict(scaled)
    else:
        aggregated["dbscan_cluster"] = -1

    label_map = _rank_based_labels(aggregated["avg_consumption_kwh"], aggregated["kmeans_cluster"].to_numpy())
    aggregated["segment"] = aggregated["kmeans_cluster"].map(label_map).fillna("Residential")

    high_theft_mask = aggregated["theft_probability"].fillna(0.0) >= 0.75
    high_anomaly_mask = aggregated["anomaly_score"].fillna(0.0) >= aggregated["anomaly_score"].quantile(0.85)
    suspicious_mask = (
        ((aggregated["dbscan_cluster"] == -1) & (high_theft_mask | high_anomaly_mask))
        | high_theft_mask
        | high_anomaly_mask
    )
    aggregated.loc[suspicious_mask, "segment"] = SEGMENT_LABELS["suspicious"]
    return aggregated.sort_values(["segment", "avg_consumption_kwh"], ascending=[True, False]).reset_index(drop=True)


def segmentation_payload(dataframe: pd.DataFrame) -> dict[str, Any]:
    if {"segment", "avg_consumption_kwh"}.issubset(dataframe.columns):
        segments = dataframe.copy()
    else:
        segments = cluster_consumers(dataframe)
    if segments.empty:
        return {"summary": [], "records": []}
    summary = (
        segments.groupby("segment", as_index=False)
        .agg(
            meter_count=("meter_id", "nunique"),
            avg_consumption_kwh=("avg_consumption_kwh", "mean"),
        )
        .sort_values("meter_count", ascending=False)
        .reset_index(drop=True)
    )
    return {
        "summary": summary.replace({np.nan: None}).to_dict(orient="records"),
        "records": segments.replace({np.nan: None}).to_dict(orient="records"),
    }
