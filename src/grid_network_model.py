from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

try:  # pragma: no cover - optional at runtime
    import networkx as nx
except Exception:  # pragma: no cover - optional at runtime
    nx = None


AREA_TO_SUBSTATION = {
    "Whitefield": "Bengaluru East Substation",
    "Marathahalli": "Bengaluru East Substation",
    "Bellandur": "Bengaluru East Substation",
    "Electronic City": "Bengaluru South Substation",
    "Koramangala": "Bengaluru South Substation",
    "BTM Layout": "Bengaluru South Substation",
    "HSR Layout": "Bengaluru South Substation",
    "Jayanagar": "Bengaluru South Substation",
    "Banashankari": "Bengaluru South Substation",
    "Indiranagar": "Bengaluru Central Substation",
    "Malleshwaram": "Bengaluru Central Substation",
    "Rajajinagar": "Bengaluru Central Substation",
    "Yelahanka": "Bengaluru North Substation",
    "Hebbal": "Bengaluru North Substation",
    "Peenya Industrial Area": "Bengaluru North Substation",
}


def _substation_for_area(area: str) -> str:
    return AREA_TO_SUBSTATION.get(area, "Bengaluru Central Substation")


def _feeder_for_area(area: str) -> str:
    area_token = str(area).upper().replace(" ", "_").replace("-", "_")
    return f"FDR_{area_token}"


def _node_for_meter(area: str, meter_id: str) -> str:
    suffix = meter_id[-2:] if meter_id else "00"
    return f"{area}_NODE_{suffix}"


def build_grid_graph(dataframe: pd.DataFrame) -> Any:
    frame = dataframe.copy()
    if frame.empty:
        if nx is not None:
            return nx.DiGraph()
        return {"nodes": {}, "edges": []}

    frame = frame.sort_values("timestamp").groupby("meter_id", as_index=False).tail(1).reset_index(drop=True)
    if nx is not None:
        graph = nx.DiGraph()
        for _, row in frame.iterrows():
            substation = _substation_for_area(row["area"])
            feeder = _feeder_for_area(row["area"])
            node = _node_for_meter(row["area"], row["meter_id"])
            graph.add_node(substation, kind="substation", area=row["area"])
            graph.add_node(feeder, kind="feeder", area=row["area"], substation=substation)
            graph.add_node(node, kind="distribution_node", area=row["area"], feeder=feeder)
            graph.add_node(
                row["meter_id"],
                kind="meter",
                area=row["area"],
                latitude=float(row.get("latitude", 0.0)),
                longitude=float(row.get("longitude", 0.0)),
                risk_score=float(row.get("risk_score", 0.0)),
            )
            graph.add_edge(substation, feeder)
            graph.add_edge(feeder, node)
            graph.add_edge(node, row["meter_id"])
        return graph

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[tuple[str, str]] = []
    for _, row in frame.iterrows():
        substation = _substation_for_area(row["area"])
        feeder = _feeder_for_area(row["area"])
        node = _node_for_meter(row["area"], row["meter_id"])
        nodes.setdefault(substation, {"kind": "substation", "area": row["area"]})
        nodes.setdefault(feeder, {"kind": "feeder", "area": row["area"], "substation": substation})
        nodes.setdefault(node, {"kind": "distribution_node", "area": row["area"], "feeder": feeder})
        nodes[row["meter_id"]] = {
            "kind": "meter",
            "area": row["area"],
            "latitude": float(row.get("latitude", 0.0)),
            "longitude": float(row.get("longitude", 0.0)),
            "risk_score": float(row.get("risk_score", 0.0)),
        }
        edges.extend([(substation, feeder), (feeder, node), (node, row["meter_id"])])
    return {"nodes": nodes, "edges": edges}


def graph_to_payload(graph: Any) -> dict[str, Any]:
    if nx is not None and hasattr(graph, "nodes"):
        nodes = [{"id": str(node), **attributes} for node, attributes in graph.nodes(data=True)]
        edges = [{"source": str(source), "target": str(target)} for source, target in graph.edges()]
        return {"nodes": nodes, "edges": edges}
    nodes = [{"id": node_id, **attributes} for node_id, attributes in graph.get("nodes", {}).items()]
    edges = [{"source": source, "target": target} for source, target in graph.get("edges", [])]
    return {"nodes": nodes, "edges": edges}


def compute_feeder_load(dataframe: pd.DataFrame, graph: Any | None = None) -> pd.DataFrame:
    if dataframe.empty:
        return pd.DataFrame(columns=["feeder_id", "substation", "meter_count", "total_load_kw", "capacity_kw", "load_ratio", "overload_flag"])
    frame = dataframe.sort_values("timestamp").groupby("meter_id", as_index=False).tail(1).copy()
    frame["feeder_id"] = frame["area"].map(_feeder_for_area)
    frame["substation"] = frame["area"].map(_substation_for_area)
    feeder = (
        frame.groupby(["substation", "feeder_id"], as_index=False)
        .agg(
            meter_count=("meter_id", "nunique"),
            total_load_kw=("power", "sum"),
            average_voltage=("voltage", "mean"),
            critical_meters=("risk_level", lambda values: int((values == "Critical").sum())) if "risk_level" in frame.columns else ("meter_id", "count"),
        )
    )
    feeder["capacity_kw"] = (feeder["meter_count"] * 3.6 + 60.0).round(2)
    feeder["load_ratio"] = (feeder["total_load_kw"] / feeder["capacity_kw"]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    feeder["overload_flag"] = (feeder["load_ratio"] >= 0.85).astype(int)
    return feeder.sort_values(["overload_flag", "load_ratio"], ascending=[False, False]).reset_index(drop=True)


def detect_cluster_anomalies(dataframe: pd.DataFrame, graph: Any | None = None) -> list[dict[str, Any]]:
    if dataframe.empty:
        return []
    frame = dataframe.sort_values("timestamp").groupby("meter_id", as_index=False).tail(1).copy()
    frame["feeder_id"] = frame["area"].map(_feeder_for_area)
    suspicious = frame.loc[
        (frame.get("risk_score", pd.Series(0.0, index=frame.index)) >= 70.0)
        | (frame.get("status", pd.Series("", index=frame.index)) == "Electricity Theft")
        | (frame.get("is_anomaly", pd.Series(0, index=frame.index)) == 1)
    ].copy()
    if suspicious.empty:
        return []

    grouped = defaultdict(list)
    for _, row in suspicious.iterrows():
        grouped[(row["feeder_id"], row["area"])].append(row)

    clusters: list[dict[str, Any]] = []
    for (feeder_id, area), rows in grouped.items():
        cluster_frame = pd.DataFrame(rows)
        if len(cluster_frame) < 2 and float(cluster_frame.get("risk_score", pd.Series([0.0])).max()) < 85.0:
            continue
        clusters.append(
            {
                "feeder_id": feeder_id,
                "area": area,
                "meter_count": int(cluster_frame["meter_id"].nunique()),
                "meters": cluster_frame["meter_id"].tolist(),
                "average_risk_score": round(float(cluster_frame.get("risk_score", pd.Series([0.0])).mean()), 2),
                "cluster_status": "Critical" if float(cluster_frame.get("risk_score", pd.Series([0.0])).max()) >= 85.0 else "High",
            }
        )
    clusters.sort(key=lambda item: (item["cluster_status"] == "Critical", item["average_risk_score"]), reverse=True)
    return clusters
