from __future__ import annotations

import asyncio

import pandas as pd
from fastapi.testclient import TestClient

from api import main as api_main
from src.preprocess import build_overview_snapshot


async def _idle_loop() -> None:
    while True:
        await asyncio.sleep(60)


def test_health_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(api_main.runtime, "bootstrap", lambda: None)
    monkeypatch.setattr(api_main.runtime, "simulation_loop", _idle_loop)
    monkeypatch.setattr(
        api_main.runtime,
        "health_payload",
        lambda: {
            "status": "ok",
            "timestamp": "2026-03-12T18:00:00",
            "current_tick": None,
            "websocket_clients": 0,
            "artifacts": {"dataset": False},
        },
    )

    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_overview_snapshot_uses_wastage_flag() -> None:
    frame = pd.DataFrame(
        [
            {
                "meter_id": "M1",
                "timestamp": "2026-03-12T01:00:00",
                "is_anomaly": 0,
                "status": "Normal",
                "wastage_flag": 1,
            },
            {
                "meter_id": "M2",
                "timestamp": "2026-03-12T01:00:00",
                "is_anomaly": 1,
                "status": "Electricity Theft",
                "wastage_flag": 0,
            },
        ]
    )

    summary = build_overview_snapshot(frame)

    assert summary["wastage"] == 1
    assert summary["anomalies"] == 1
    assert summary["theft"] == 1


def test_current_tick_payloads_ignore_recent_history(monkeypatch) -> None:
    latest = pd.DataFrame(
        [
            {
                "meter_id": "M1",
                "timestamp": "2026-03-12T02:00:00",
                "area": "Whitefield",
                "region": "Bengaluru",
                "status": "Electricity Theft",
                "is_anomaly": 0,
                "anomaly_score": 0.12,
                "theft_probability": 0.91,
                "risk_score": 88.5,
                "latitude": 12.97,
                "longitude": 77.75,
                "wastage_flag": 1,
                "efficiency_score": 60.0,
                "estimated_losses_kwh": 2.5,
            },
            {
                "meter_id": "M2",
                "timestamp": "2026-03-12T02:00:00",
                "area": "Koramangala",
                "region": "Bengaluru",
                "status": "Anomaly",
                "is_anomaly": 1,
                "anomaly_score": 0.66,
                "theft_probability": 0.33,
                "risk_score": 58.0,
                "latitude": 12.93,
                "longitude": 77.62,
                "wastage_flag": 0,
                "efficiency_score": 92.0,
                "estimated_losses_kwh": 0.4,
            },
        ]
    )
    historical = pd.DataFrame(
        [
            {
                "meter_id": "OLD1",
                "timestamp": "2026-03-12T01:00:00",
                "area": "Indiranagar",
                "region": "Bengaluru",
                "status": "Electricity Theft",
                "is_anomaly": 1,
                "anomaly_score": 0.72,
                "theft_probability": 0.96,
                "risk_score": 91.0,
                "latitude": 12.97,
                "longitude": 77.64,
                "wastage_flag": 1,
                "efficiency_score": 55.0,
                "estimated_losses_kwh": 3.2,
            }
        ]
    )

    monkeypatch.setattr(api_main, "explain_prediction", lambda *_args, **_kwargs: {"summary": "test"})

    runtime = api_main.SmartGridRuntime()
    runtime.latest_predictions = latest
    runtime.prediction_buffer.clear()
    runtime.prediction_buffer.append(historical)

    theft = runtime.theft_payload(limit=10)
    anomalies = runtime.anomaly_payload(limit=10)
    efficiency = runtime.efficiency_payload(limit=10)
    overview = runtime.overview_payload()

    assert theft["count"] == 1
    assert theft["records"][0]["meter_id"] == "M1"
    assert anomalies["count"] == 1
    assert anomalies["records"][0]["meter_id"] == "M2"
    assert efficiency["summary"]["low_efficiency"] == 1
    assert overview["summary"]["theft"] == 1
    assert overview["summary"]["anomalies"] == 1
    assert overview["summary"]["wastage"] == 1


def test_theft_and_anomaly_payload_counts_are_not_limited(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "explain_prediction", lambda *_args, **_kwargs: {"summary": "test"})

    runtime = api_main.SmartGridRuntime()
    runtime.latest_predictions = pd.DataFrame(
        [
            {
                "meter_id": f"M{i}",
                "timestamp": "2026-03-12T02:00:00",
                "area": "Whitefield" if i < 3 else "Koramangala",
                "region": "Bengaluru",
                "status": "Electricity Theft" if i < 4 else "Anomaly",
                "is_anomaly": 1 if i >= 2 else 0,
                "anomaly_score": 0.2 + i * 0.1,
                "theft_probability": 0.85 if i < 4 else 0.2,
                "risk_score": 82.0 if i < 3 else 65.0,
                "latitude": 12.9,
                "longitude": 77.6,
                "wastage_flag": 0,
                "efficiency_score": 90.0,
                "estimated_losses_kwh": 0.5,
                "consumption_kwh": 1.0,
            }
            for i in range(5)
        ]
    )

    theft = runtime.theft_payload(limit=2)
    anomalies = runtime.anomaly_payload(limit=1)

    assert len(theft["records"]) == 2
    assert theft["count"] == 4
    assert theft["summary"]["count"] == 4
    assert theft["summary"]["critical_areas"] == 1
    assert len(anomalies["records"]) == 1
    assert anomalies["count"] == 3
    assert anomalies["summary"]["count"] == 3


def test_visible_theft_candidate_is_injected_only_when_needed() -> None:
    frame = pd.DataFrame(
        [
            {
                "meter_id": "M1",
                "status": "Normal",
                "theft_probability": 0.12,
                "random_forest_probability": 0.08,
                "xgboost_probability": 0.16,
                "anomaly_score": 0.25,
                "wastage_score": 0.05,
                "seeded_theft_probability": 0.0,
            },
            {
                "meter_id": "M2",
                "status": "Anomaly",
                "theft_probability": 0.28,
                "random_forest_probability": 0.21,
                "xgboost_probability": 0.33,
                "anomaly_score": 0.52,
                "wastage_score": 0.12,
                "seeded_theft_probability": 0.0,
            },
        ]
    )

    promoted = api_main._ensure_visible_theft_candidate(frame)

    assert int((promoted["status"] == "Electricity Theft").sum()) == 1
    assert float(promoted.loc[promoted["status"] == "Electricity Theft", "theft_probability"].iloc[0]) >= 0.81

    existing = frame.copy()
    existing.loc[0, "status"] = "Electricity Theft"
    untouched = api_main._ensure_visible_theft_candidate(existing)

    assert int((untouched["status"] == "Electricity Theft").sum()) == 1
