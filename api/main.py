from __future__ import annotations

import asyncio
import os
from collections import deque
from contextlib import asynccontextmanager, suppress
from threading import Lock
from typing import Any

import pandas as pd
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.alert_engine import dispatch_alerts
from src.consumer_segmentation import cluster_consumers
from src.data_drift_monitor import generate_drift_report
from src.data_generator import generate_smart_meter_data
from src.demand_forecasting import forecast_horizons
from src.energy_efficiency import calculate_efficiency_metrics, summarise_efficiency
from src.explainable_ai import explain_prediction
from src.grid_network_model import build_grid_graph, compute_feeder_load, detect_cluster_anomalies, graph_to_payload
from src.grid_simulator import simulate_grid_state
from src.preprocess import (
    aggregate_region_consumption,
    aggregate_weather_impact,
    build_overview_snapshot,
    load_dataset,
    load_training_dataset,
    preprocess_frame,
)
from src.report_generator import generate_daily_report
from src.risk_scoring import risk_distribution_by_area, risk_payload, score_meter_risk
from src.spatial_analysis import build_theft_heatmap
from src.theft_detector import classify_meter_events
from src.train_models import train_all_models
from src.transformer_forecasting import forecast_transformer_horizons
from src.weather_api import WeatherService
from utils.helpers import dataframe_to_sqlite, ensure_project_dirs, generation_config, records_for_json


class MeterReading(BaseModel):
    meter_id: str = Field(..., examples=["M0512"])
    timestamp: str | None = None
    region: str = "Bengaluru"
    area: str
    latitude: float
    longitude: float
    voltage: float
    current: float
    power: float
    consumption_kwh: float
    power_factor: float
    temperature: float
    humidity: float
    rainfall: float
    wind_speed: float
    weather_condition: str
    is_theft: int = 0
    expected_consumption_kwh: float | None = None
    wastage_score: float | None = None
    usage_profile: str = "residential"
    theft_type: str = "unknown"
    seeded_theft_probability: float = 0.0


def _prepare_request_frame(payload: MeterReading | list[MeterReading]) -> pd.DataFrame:
    records = payload if isinstance(payload, list) else [payload]
    rows: list[dict[str, Any]] = []
    for record in records:
        data = record.model_dump()
        if not data.get("timestamp"):
            data["timestamp"] = pd.Timestamp.utcnow().tz_localize(None).floor("h")
        data["expected_consumption_kwh"] = data.get("expected_consumption_kwh") or data["consumption_kwh"]
        if data.get("wastage_score") is None:
            expected = max(float(data["expected_consumption_kwh"]), 0.1)
            data["wastage_score"] = max((float(data["consumption_kwh"]) - expected) / expected, 0.0)
        rows.append(data)
    return preprocess_frame(pd.DataFrame(rows))


def _empty_forecast() -> dict[str, Any]:
    return {
        "next_hour": 0.0,
        "next_day": 0.0,
        "next_week": 0.0,
        "series": [],
        "lstm": {"next_hour": 0.0, "next_day": 0.0, "next_week": 0.0, "series": [], "model_type": "baseline"},
        "transformer": {"next_hour": 0.0, "next_day": 0.0, "next_week": 0.0, "series": [], "model_type": "baseline"},
        "ensemble": {"next_hour": 0.0, "next_day": 0.0, "next_week": 0.0},
        "comparison_series": {"lstm": [], "transformer": []},
    }


def _flatten_drift_report(report: dict[str, Any]) -> pd.DataFrame:
    quality = report.get("data_quality", {})
    concept = report.get("concept_drift", {})
    return pd.DataFrame(
        [
            {
                "generated_at": report.get("generated_at"),
                "method": report.get("method"),
                "drift_detected": int(bool(report.get("drift_detected"))),
                "current_missing_pct": quality.get("current_missing_pct", 0.0),
                "reference_missing_pct": quality.get("reference_missing_pct", 0.0),
                "issue_count": len(quality.get("issues", [])),
                "theft_rate_shift": concept.get("theft_rate_shift", 0.0),
                "prediction_rate_shift": concept.get("prediction_rate_shift", 0.0),
                "concept_drift_detected": int(bool(concept.get("detected"))),
            }
        ]
    )


class SmartGridRuntime:
    def __init__(self) -> None:
        self.paths = ensure_project_dirs()
        self.weather_service = WeatherService()
        self.lock = Lock()
        self.update_interval = int(os.getenv("SMARTGRID_UPDATE_INTERVAL", "4"))
        self.simulation_source = pd.DataFrame()
        self.historical_frame = pd.DataFrame()
        self.latest_predictions = pd.DataFrame()
        self.prediction_buffer: deque[pd.DataFrame] = deque(maxlen=36)
        self.timeline: list[pd.Timestamp] = []
        self.cursor = 0
        self.current_timestamp: pd.Timestamp | None = None
        self.ws_clients: list[WebSocket] = []
        self.cached_forecast: dict[str, Any] = _empty_forecast()
        self.cached_segments = pd.DataFrame()
        self.cached_grid_status: dict[str, Any] = {"feeders": [], "summary": {}, "network": {"nodes": [], "edges": []}, "clusters": []}
        self.cached_drift_report: dict[str, Any] = {
            "generated_at": None,
            "method": "fallback",
            "drift_detected": False,
            "feature_drift": [],
            "concept_drift": {"detected": False},
            "data_quality": {"issues": []},
        }
        self.cached_alert_results: list[dict[str, Any]] = []

    def _build_forecast_payload(self) -> dict[str, Any]:
        lstm_forecast = forecast_horizons(metadata_path=self.paths.demand_metadata, model_path=self.paths.lstm_model)
        transformer_forecast = forecast_transformer_horizons(
            metadata_path=self.paths.transformer_metadata,
            model_path=self.paths.transformer_model,
        )
        return {
            **lstm_forecast,
            "lstm": lstm_forecast,
            "transformer": transformer_forecast,
            "ensemble": {
                "next_hour": round((lstm_forecast.get("next_hour", 0.0) + transformer_forecast.get("next_hour", 0.0)) / 2.0, 2),
                "next_day": round((lstm_forecast.get("next_day", 0.0) + transformer_forecast.get("next_day", 0.0)) / 2.0, 2),
                "next_week": round((lstm_forecast.get("next_week", 0.0) + transformer_forecast.get("next_week", 0.0)) / 2.0, 2),
            },
            "comparison_series": {
                "lstm": lstm_forecast.get("series", []),
                "transformer": transformer_forecast.get("series", []),
            },
        }

    def bootstrap(self) -> None:
        full_scale = os.getenv("SMARTGRID_FULL_SCALE", "0") == "1"
        config = generation_config(full_scale=full_scale)
        sample_path = self.paths.data_processed / "smart_meter_sample.csv"

        if not self.paths.dataset.exists() or not self.paths.live_dataset.exists() or not sample_path.exists():
            generate_smart_meter_data(**config)

        if not all(
            [
                self.paths.isolation_forest.exists(),
                self.paths.random_forest.exists(),
                self.paths.xgboost_model.exists(),
                self.paths.model_metadata.exists(),
                self.paths.demand_metadata.exists(),
                self.paths.transformer_metadata.exists(),
            ]
        ):
            train_all_models(dataset_path=sample_path, max_rows=config["sample_rows"], forecast_epochs=4)

        self.historical_frame = load_training_dataset(max_rows=config["sample_rows"])
        if self.historical_frame.empty:
            self.historical_frame = load_dataset(self.paths.dataset, nrows=20000)
        dataframe_to_sqlite(self.historical_frame, "meter_readings")

        self.simulation_source = load_dataset(self.paths.live_dataset)
        if self.simulation_source.empty:
            self.simulation_source = self.historical_frame.sort_values("timestamp").reset_index(drop=True)

        self.timeline = sorted(self.simulation_source["timestamp"].drop_duplicates().tolist())
        self.cursor = 0
        self.prediction_buffer.clear()
        self.cached_forecast = self._build_forecast_payload()
        self.advance_tick()

    def recent_predictions(self) -> pd.DataFrame:
        if not self.prediction_buffer:
            return self.latest_predictions.copy()
        return pd.concat(list(self.prediction_buffer), ignore_index=True)

    def _clustering_source(self, recent_frame: pd.DataFrame) -> pd.DataFrame:
        history_slice = self.historical_frame.sort_values("timestamp").tail(3200).copy()
        if recent_frame.empty:
            return history_slice
        common_columns = sorted(set(history_slice.columns).union(recent_frame.columns))
        history_slice = history_slice.reindex(columns=common_columns)
        recent_slice = recent_frame.reindex(columns=common_columns)
        return pd.concat([history_slice, recent_slice], ignore_index=True)

    def advance_tick(self) -> None:
        if not self.timeline:
            return

        timestamp = self.timeline[self.cursor]
        current_frame = self.simulation_source.loc[self.simulation_source["timestamp"] == timestamp].copy()
        predictions = classify_meter_events(current_frame).sort_values(
            ["theft_probability", "anomaly_score"],
            ascending=False,
        )
        predictions = calculate_efficiency_metrics(score_meter_risk(predictions)).reset_index(drop=True)

        previous_recent = self.recent_predictions()
        recent = pd.concat([previous_recent, predictions], ignore_index=True) if not previous_recent.empty else predictions.copy()
        recent = recent.tail(5000).reset_index(drop=True)

        forecast_payload = self._build_forecast_payload()
        segments = cluster_consumers(self._clustering_source(recent))
        graph = build_grid_graph(predictions)
        feeder_load = compute_feeder_load(predictions, graph=graph)
        grid_status = simulate_grid_state(predictions)
        grid_status["network"] = graph_to_payload(graph)
        grid_status["clusters"] = detect_cluster_anomalies(predictions, graph=graph)
        grid_status["feeder_load"] = records_for_json(feeder_load)

        reference_frame = self.historical_frame.sort_values("timestamp").tail(3500)
        drift_report = generate_drift_report(reference_frame=reference_frame, current_frame=recent.tail(1200))

        alert_results: list[dict[str, Any]] = []
        if os.getenv("SMARTGRID_ENABLE_ALERTS", "0") == "1":
            alert_results = dispatch_alerts(predictions.loc[predictions["risk_level"].isin(["High", "Critical"])], limit=5)

        with self.lock:
            self.current_timestamp = pd.Timestamp(timestamp)
            self.latest_predictions = predictions
            self.prediction_buffer.append(predictions.copy())
            self.cached_forecast = forecast_payload
            self.cached_segments = segments
            self.cached_grid_status = grid_status
            self.cached_drift_report = drift_report
            self.cached_alert_results = alert_results

            dataframe_to_sqlite(self.latest_predictions, "live_predictions")
            dataframe_to_sqlite(recent, "recent_predictions")
            dataframe_to_sqlite(self.latest_predictions, "risk_scores")
            dataframe_to_sqlite(self.cached_segments, "consumer_segments")
            dataframe_to_sqlite(self.latest_predictions, "efficiency_metrics")
            dataframe_to_sqlite(_flatten_drift_report(self.cached_drift_report), "drift_reports")
            grid_table = pd.DataFrame(self.cached_grid_status.get("feeders", []))
            if not grid_table.empty:
                dataframe_to_sqlite(grid_table, "grid_status")

            forecast_frames: list[pd.DataFrame] = []
            for model_name in ["lstm", "transformer"]:
                model_series = pd.DataFrame(self.cached_forecast.get(model_name, {}).get("series", []))
                if not model_series.empty:
                    model_series["model_name"] = model_name
                    forecast_frames.append(model_series)
            if forecast_frames:
                dataframe_to_sqlite(pd.concat(forecast_frames, ignore_index=True), "forecast_snapshots")
            if self.cursor % 3 == 0:
                build_theft_heatmap(recent)
            if self.cursor % 6 == 0:
                generate_daily_report(recent, forecast=self.cached_forecast)

        self.cursor = (self.cursor + 1) % len(self.timeline)

    async def simulation_loop(self) -> None:
        while True:
            await asyncio.sleep(self.update_interval)
            self.advance_tick()
            await self.broadcast_snapshot()

    async def register_client(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self.lock:
            self.ws_clients.append(websocket)
        await websocket.send_json(self.snapshot_message())

    def unregister_client(self, websocket: WebSocket) -> None:
        with self.lock:
            self.ws_clients = [client for client in self.ws_clients if client is not websocket]

    def snapshot_message(self) -> dict[str, Any]:
        return {
            "type": "live_tick",
            "overview": self.overview_payload(),
            "theft": self.theft_payload(limit=8),
            "weather": self.weather_payload(),
            "meters": self.meter_payload(limit=16),
            "risk": self.risk_scores_payload(limit=12),
            "segments": self.consumer_segments_payload(),
            "efficiency": self.efficiency_payload(limit=10),
            "grid": self.grid_status_payload(),
            "drift": self.drift_payload(),
            "forecast": self.forecast_payload(),
        }

    async def broadcast_snapshot(self) -> None:
        payload = self.snapshot_message()
        disconnected: list[WebSocket] = []
        for client in list(self.ws_clients):
            try:
                await client.send_json(payload)
            except Exception:
                disconnected.append(client)
        for client in disconnected:
            self.unregister_client(client)

    def overview_payload(self) -> dict[str, Any]:
        with self.lock:
            latest = self.latest_predictions.copy()
            recent = self.recent_predictions().copy()
            forecast = dict(self.cached_forecast)
            drift = dict(self.cached_drift_report)
            grid_summary = dict(self.cached_grid_status.get("summary", {}))

        summary = build_overview_snapshot(latest)
        if not self.historical_frame.empty:
            summary["total_meters"] = int(self.historical_frame["meter_id"].nunique())
        live_consumption = (
            recent.groupby("timestamp", as_index=False)
            .agg(
                total_consumption=("consumption_kwh", "sum"),
                anomalies=("is_anomaly", "sum"),
                theft=("status", lambda values: int((values == "Electricity Theft").sum())),
            )
            .sort_values("timestamp")
            .tail(24)
        )
        region_consumption = aggregate_region_consumption(latest)
        risk_distribution = risk_distribution_by_area(latest)

        return {
            "timestamp": self.current_timestamp.isoformat() if self.current_timestamp is not None else None,
            "summary": summary,
            "live_consumption": records_for_json(live_consumption),
            "region_consumption": records_for_json(region_consumption),
            "risk_distribution": records_for_json(risk_distribution),
            "forecast": forecast,
            "grid_summary": grid_summary,
            "drift_detected": bool(drift.get("drift_detected", False)),
            "alert_results": self.cached_alert_results,
        }

    def meter_payload(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.lock:
            latest = self.latest_predictions.copy()
        preferred_columns = [
            "meter_id",
            "timestamp",
            "area",
            "consumption_kwh",
            "power",
            "voltage",
            "power_factor",
            "anomaly_score",
            "theft_probability",
            "risk_score",
            "risk_level",
            "efficiency_score",
            "status",
        ]
        columns = [column for column in preferred_columns if column in latest.columns]
        return records_for_json(latest[columns].head(limit))

    def anomaly_payload(self, limit: int = 25) -> dict[str, Any]:
        with self.lock:
            recent = self.recent_predictions().copy()
        anomalies = (
            recent.loc[(recent["is_anomaly"] == 1) | (recent["status"] == "Anomaly")]
            .sort_values(["anomaly_score", "risk_score"], ascending=False)
            .head(limit)
        )
        return {"records": records_for_json(anomalies), "count": int(len(anomalies))}

    def theft_payload(self, limit: int = 20) -> dict[str, Any]:
        with self.lock:
            recent = self.recent_predictions().copy()
        theft_records = (
            recent.loc[recent["status"] == "Electricity Theft"]
            .sort_values(["risk_score", "theft_probability"], ascending=False)
            .head(limit)
            .copy()
        )
        reasons: list[str] = []
        for _, row in theft_records.iterrows():
            explanation = explain_prediction(pd.DataFrame([row]))
            reasons.append(explanation.get("summary", ""))
        theft_records["reason"] = reasons

        return {
            "records": records_for_json(theft_records),
            "count": int(len(theft_records)),
            "heatmap_path": "./theft_heatmap.html",
        }

    def weather_payload(self) -> dict[str, Any]:
        with self.lock:
            recent = self.recent_predictions().copy()
        combined = pd.concat([self.historical_frame.tail(4000), recent], ignore_index=True)
        impact = aggregate_weather_impact(combined)
        scatter = combined[["temperature", "consumption_kwh", "wastage_score", "area"]].tail(240)
        return {
            "bands": records_for_json(impact),
            "scatter": records_for_json(scatter),
            "live_weather": self.weather_service.current_area_weather(),
        }

    def forecast_payload(self) -> dict[str, Any]:
        return self.cached_forecast

    def risk_scores_payload(self, limit: int = 25) -> dict[str, Any]:
        with self.lock:
            latest = self.latest_predictions.copy()
        return risk_payload(latest, limit=limit)

    def consumer_segments_payload(self) -> dict[str, Any]:
        with self.lock:
            segments = self.cached_segments.copy()
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
            "summary": records_for_json(summary),
            "records": records_for_json(segments),
        }

    def efficiency_payload(self, limit: int = 20) -> dict[str, Any]:
        with self.lock:
            latest = self.latest_predictions.copy()
        return summarise_efficiency(latest, limit=limit)

    def grid_status_payload(self) -> dict[str, Any]:
        return self.cached_grid_status

    def drift_payload(self) -> dict[str, Any]:
        return self.cached_drift_report

    def health_payload(self) -> dict[str, Any]:
        artifacts = {
            "dataset": self.paths.dataset.exists(),
            "live_dataset": self.paths.live_dataset.exists(),
            "meter_catalog": self.paths.meter_catalog.exists(),
            "isolation_forest": self.paths.isolation_forest.exists(),
            "random_forest": self.paths.random_forest.exists(),
            "boost_model": self.paths.xgboost_model.exists(),
            "model_metadata": self.paths.model_metadata.exists(),
            "forecast_metadata": self.paths.demand_metadata.exists(),
            "transformer_metadata": self.paths.transformer_metadata.exists(),
            "heatmap": self.paths.map_path.exists(),
            "daily_report": self.paths.daily_report.exists(),
            "drift_report": self.paths.drift_report.exists(),
        }
        healthy = all(
            [
                artifacts["live_dataset"],
                artifacts["isolation_forest"],
                artifacts["random_forest"],
                artifacts["boost_model"],
                artifacts["model_metadata"],
            ]
        )
        return {
            "status": "ok" if healthy else "degraded",
            "timestamp": pd.Timestamp.utcnow().tz_localize(None).isoformat(),
            "current_tick": self.current_timestamp.isoformat() if self.current_timestamp is not None else None,
            "websocket_clients": len(self.ws_clients),
            "artifacts": artifacts,
        }

    def predict_payload(self, payload: MeterReading | list[MeterReading]) -> list[dict[str, Any]]:
        request_frame = _prepare_request_frame(payload)
        predictions = calculate_efficiency_metrics(score_meter_risk(classify_meter_events(request_frame)))
        responses: list[dict[str, Any]] = []
        for _, row in predictions.iterrows():
            explanation = explain_prediction(pd.DataFrame([row]))
            responses.append(
                {
                    "meter_id": row["meter_id"],
                    "region": row["region"],
                    "area": row["area"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "status": row["status"],
                    "theft_probability": round(float(row["theft_probability"]), 4),
                    "anomaly_score": round(float(row["anomaly_score"]), 4),
                    "risk_score": round(float(row["risk_score"]), 2),
                    "risk_level": row["risk_level"],
                    "efficiency_score": round(float(row["efficiency_score"]), 2),
                    "reason": explanation.get("reason", []),
                }
            )
        return responses


runtime = SmartGridRuntime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime.bootstrap()
    task = asyncio.create_task(runtime.simulation_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Smart Grid Electricity Theft Detection API",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> dict[str, Any]:
    return {
        "project": "SMART GRID ELECTRICITY THEFT, ANOMALY, AND WASTAGE DETECTION SYSTEM",
        "city": "Bengaluru",
        "timestamp": runtime.current_timestamp.isoformat() if runtime.current_timestamp is not None else None,
        "version": "2.0.0",
    }


@app.get("/health")
def get_health() -> dict[str, Any]:
    return runtime.health_payload()


@app.get("/overview")
def get_overview() -> dict[str, Any]:
    return runtime.overview_payload()


@app.get("/meters")
def get_meters(limit: int = 50) -> list[dict[str, Any]]:
    return runtime.meter_payload(limit=limit)


@app.get("/anomalies")
def get_anomalies(limit: int = 25) -> dict[str, Any]:
    return runtime.anomaly_payload(limit=limit)


@app.get("/theft")
def get_theft(limit: int = 20) -> dict[str, Any]:
    return runtime.theft_payload(limit=limit)


@app.get("/weather-impact")
def get_weather_impact() -> dict[str, Any]:
    return runtime.weather_payload()


@app.get("/forecast")
def get_forecast() -> dict[str, Any]:
    return runtime.forecast_payload()


@app.get("/risk-scores")
def get_risk_scores(limit: int = 25) -> dict[str, Any]:
    return runtime.risk_scores_payload(limit=limit)


@app.get("/consumer-segments")
def get_consumer_segments() -> dict[str, Any]:
    return runtime.consumer_segments_payload()


@app.get("/efficiency")
def get_efficiency(limit: int = 20) -> dict[str, Any]:
    return runtime.efficiency_payload(limit=limit)


@app.get("/grid-status")
def get_grid_status() -> dict[str, Any]:
    return runtime.grid_status_payload()


@app.get("/drift-report")
def get_drift_report() -> dict[str, Any]:
    return runtime.drift_payload()


@app.post("/predict")
def predict_meter_status(payload: MeterReading | list[MeterReading]) -> list[dict[str, Any]]:
    return runtime.predict_payload(payload)


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    await runtime.register_client(websocket)
    try:
        while websocket in runtime.ws_clients:
            await asyncio.sleep(60)
    finally:
        runtime.unregister_client(websocket)
