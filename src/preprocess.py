from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from utils.helpers import ensure_project_dirs


NUMERIC_COLUMNS = [
    "latitude",
    "longitude",
    "voltage",
    "current",
    "power",
    "consumption_kwh",
    "power_factor",
    "temperature",
    "humidity",
    "rainfall",
    "wind_speed",
    "is_theft",
    "expected_consumption_kwh",
    "wastage_score",
    "seeded_theft_probability",
]


def preprocess_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = dataframe.copy()
    if frame.empty:
        return frame

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame = frame.dropna(subset=["timestamp"]).sort_values(["meter_id", "timestamp"]).reset_index(drop=True)

    for column in NUMERIC_COLUMNS:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    existing_numeric = [column for column in NUMERIC_COLUMNS if column in frame.columns]
    frame[existing_numeric] = frame[existing_numeric].fillna(0.0)
    frame["power_factor"] = frame["power_factor"].clip(0.0, 1.0)
    frame["consumption_kwh"] = frame["consumption_kwh"].clip(lower=0.0)
    frame["wastage_score"] = frame["wastage_score"].clip(lower=0.0)
    frame["wastage_flag"] = ((frame["wastage_score"] >= 0.25) | (frame["power_factor"] < 0.8)).astype(int)
    frame["power_gap"] = (frame["power"] - frame["consumption_kwh"]).round(3)
    frame["temperature_band"] = pd.cut(
        frame["temperature"],
        bins=[-10, 20, 26, 32, 50],
        labels=["cool", "mild", "warm", "hot"],
    ).astype(str)
    return frame


def load_dataset(path: str | Path | None = None, nrows: int | None = None) -> pd.DataFrame:
    paths = ensure_project_dirs()
    target = Path(path) if path else paths.dataset
    if not target.exists():
        return pd.DataFrame()
    dataframe = pd.read_csv(target, nrows=nrows)
    return preprocess_frame(dataframe)


def load_training_dataset(max_rows: int = 50000) -> pd.DataFrame:
    paths = ensure_project_dirs()
    sample_path = paths.data_processed / "smart_meter_sample.csv"
    if sample_path.exists():
        frame = load_dataset(sample_path)
    else:
        frame = load_dataset(paths.dataset, nrows=max_rows)
    if frame.empty or len(frame) <= max_rows:
        return frame

    positives = frame[frame["is_theft"] == 1]
    negatives = frame[frame["is_theft"] == 0]
    positive_take = min(len(positives), max_rows // 3)
    negative_take = max_rows - positive_take
    sampled = pd.concat(
        [
            positives.sample(n=positive_take, random_state=42) if positive_take else positives.head(0),
            negatives.sample(n=min(len(negatives), negative_take), random_state=42),
        ],
        ignore_index=True,
    )
    return sampled.sample(frac=1.0, random_state=42).reset_index(drop=True)


def build_overview_snapshot(dataframe: pd.DataFrame) -> dict[str, float]:
    if dataframe.empty:
        return {"total_meters": 0, "active_meters": 0, "anomalies": 0, "theft": 0, "wastage": 0}
    latest = dataframe.sort_values("timestamp").groupby("meter_id", as_index=False).tail(1)
    return {
        "total_meters": int(dataframe["meter_id"].nunique()),
        "active_meters": int(latest["meter_id"].nunique()),
        "anomalies": int((latest.get("is_anomaly", pd.Series(dtype=int)) == 1).sum()),
        "theft": int((latest.get("status", pd.Series(dtype=object)) == "Electricity Theft").sum()),
        "wastage": int((latest.get("status", pd.Series(dtype=object)) == "Power Wastage").sum()),
    }


def aggregate_weather_impact(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        return pd.DataFrame(columns=["temperature_band", "avg_consumption", "avg_wastage", "avg_humidity"])
    grouped = (
        dataframe.groupby("temperature_band", dropna=False)
        .agg(
            avg_consumption=("consumption_kwh", "mean"),
            avg_wastage=("wastage_score", "mean"),
            avg_humidity=("humidity", "mean"),
        )
        .reset_index()
    )
    return grouped.sort_values("temperature_band").reset_index(drop=True)


def aggregate_region_consumption(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        return pd.DataFrame(columns=["area", "consumption_kwh"])
    return (
        dataframe.groupby("area", as_index=False)
        .agg(consumption_kwh=("consumption_kwh", "sum"))
        .sort_values("consumption_kwh", ascending=False)
        .reset_index(drop=True)
    )
