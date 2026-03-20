from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.weather_api import WeatherService
from utils.helpers import AREA_COORDINATES, ensure_project_dirs, generation_config, jitter_coordinate, save_json, seed_everything


USAGE_PROFILES = {
    "residential": 1.6,
    "night_usage": 1.7,
    "industrial": 3.4,
    "ac_heavy": 2.3,
    "commercial": 2.8,
}

THEFT_TYPES = [
    "meter_bypass",
    "abnormal_spikes",
    "constant_low_consumption",
    "illegal_connection",
    "tampered_meter",
]


@dataclass
class MeterProfile:
    meter_id: str
    region: str
    area: str
    latitude: float
    longitude: float
    usage_profile: str


def build_meter_catalog(num_meters: int, seed: int = 42) -> pd.DataFrame:
    seed_everything(seed)
    rng = np.random.default_rng(seed)
    areas = list(AREA_COORDINATES.keys())
    area_weights = np.array([0.09, 0.1, 0.06, 0.08, 0.08, 0.05, 0.05, 0.05, 0.05, 0.04, 0.05, 0.1, 0.07, 0.06, 0.07])
    area_weights = area_weights / area_weights.sum()
    profiles = list(USAGE_PROFILES.keys())
    profile_weights = np.array([0.38, 0.14, 0.18, 0.16, 0.14])

    meters: list[dict[str, Any]] = []
    for index in range(1, num_meters + 1):
        area = str(rng.choice(areas, p=area_weights))
        latitude, longitude = jitter_coordinate(*AREA_COORDINATES[area])
        profile = str(rng.choice(profiles, p=profile_weights))
        meters.append(
            {
                "meter_id": f"M{index:04d}",
                "region": "Bengaluru",
                "area": area,
                "latitude": latitude,
                "longitude": longitude,
                "usage_profile": profile,
            }
        )
    return pd.DataFrame(meters)


def _base_load_curve(profile: str, hour: np.ndarray, day_of_week: np.ndarray, temperature: np.ndarray) -> np.ndarray:
    weekend = (day_of_week >= 5).astype(float)
    if profile == "residential":
        curve = 0.55 + 0.35 * ((hour >= 6) & (hour <= 9)) + 0.75 * ((hour >= 18) & (hour <= 23)) + 0.12 * weekend
    elif profile == "night_usage":
        curve = 0.45 + 0.85 * ((hour >= 20) | (hour <= 4)) + 0.08 * weekend
    elif profile == "industrial":
        curve = 0.7 + 0.55 * ((hour >= 8) & (hour <= 18)) - 0.18 * weekend
    elif profile == "commercial":
        curve = 0.55 + 0.75 * ((hour >= 10) & (hour <= 21)) - 0.1 * weekend
    else:  # ac_heavy
        curve = 0.5 + 0.5 * ((hour >= 11) & (hour <= 19)) + 0.035 * np.maximum(temperature - 28, 0)
    return np.maximum(curve, 0.2)


def _seasonal_factor(timestamps: pd.DatetimeIndex) -> np.ndarray:
    day_of_year = timestamps.dayofyear.to_numpy()
    month = timestamps.month.to_numpy()
    monsoon = np.where(np.isin(month, [6, 7, 8, 9]), 0.08, 0.0)
    festive = np.where(np.isin(month, [10, 11, 12]), 0.05, 0.0)
    return 1.0 + 0.08 * np.sin((day_of_year / 365.0) * 2 * np.pi) + monsoon + festive


def _theft_mask(rng: np.random.Generator, size: int, hour: np.ndarray, theft_type: str) -> np.ndarray:
    start = int(rng.integers(max(24, size // 8), max(48, size // 2)))
    length = int(rng.integers(max(24, size // 20), max(96, size // 4)))
    stop = min(size, start + length)
    window = np.zeros(size, dtype=bool)
    window[start:stop] = True

    if theft_type in {"meter_bypass", "illegal_connection"}:
        window &= (hour >= 19) | (hour <= 5)
    elif theft_type == "abnormal_spikes":
        spike_mask = rng.random(size) < 0.08
        window |= spike_mask
    return window


def simulate_meter_series(
    meter: MeterProfile,
    timestamps: pd.DatetimeIndex,
    weather: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    hour = timestamps.hour.to_numpy()
    day_of_week = timestamps.dayofweek.to_numpy()

    temperature = weather["temperature"].to_numpy(dtype=float)
    humidity = weather["humidity"].to_numpy(dtype=float)
    rainfall = weather["rainfall"].to_numpy(dtype=float)
    wind_speed = weather["wind_speed"].to_numpy(dtype=float)
    weather_condition = weather["weather_condition"].to_numpy(dtype=str)

    base_kw = USAGE_PROFILES[meter.usage_profile]
    curve = _base_load_curve(meter.usage_profile, hour, day_of_week, temperature)
    weather_effect = 1.0 + 0.03 * np.maximum(temperature - 28, 0) + 0.015 * rainfall + 0.005 * np.maximum(humidity - 75, 0)
    expected_consumption = base_kw * curve * _seasonal_factor(timestamps) * weather_effect
    expected_consumption *= 1.0 + np.random.normal(0, 0.05, len(timestamps))
    expected_consumption = np.clip(expected_consumption, 0.12, None)

    actual_load = expected_consumption * (1.0 + np.random.normal(0, 0.08, len(timestamps)))
    actual_load = np.clip(actual_load, 0.1, None)
    reported_consumption = actual_load.copy()

    theft_type = "none"
    theft_probability = 0.0
    theft_mask = np.zeros(len(timestamps), dtype=bool)
    if rng.random() < 0.13:
        theft_type = str(rng.choice(THEFT_TYPES))
        theft_mask = _theft_mask(rng, len(timestamps), hour, theft_type)
        theft_probability = float(rng.uniform(0.68, 0.98))
        if theft_type == "meter_bypass":
            reported_consumption[theft_mask] = actual_load[theft_mask] * rng.uniform(0.18, 0.45)
        elif theft_type == "abnormal_spikes":
            actual_load[theft_mask] = actual_load[theft_mask] * rng.uniform(1.8, 3.1)
            reported_consumption[theft_mask] = actual_load[theft_mask] * rng.uniform(0.45, 0.7)
        elif theft_type == "constant_low_consumption":
            baseline = np.quantile(actual_load, 0.1)
            reported_consumption[theft_mask] = np.minimum(actual_load[theft_mask] * 0.22, baseline)
        elif theft_type == "illegal_connection":
            hidden_load = rng.uniform(0.4, 1.2, theft_mask.sum())
            actual_load[theft_mask] = actual_load[theft_mask] + hidden_load
            reported_consumption[theft_mask] = np.maximum(actual_load[theft_mask] - hidden_load * 1.2, 0.12)
        else:  # tampered_meter
            reported_consumption[theft_mask] = actual_load[theft_mask] * rng.uniform(0.35, 0.58)

    power_factor = np.clip(0.94 + np.random.normal(0, 0.025, len(timestamps)), 0.72, 0.99)
    power_factor[theft_mask] = np.clip(power_factor[theft_mask] - rng.uniform(0.08, 0.18), 0.55, 0.9)

    voltage = np.clip(230 + np.random.normal(0, 5.2, len(timestamps)), 205, 252)
    voltage[theft_mask] = np.clip(voltage[theft_mask] - rng.uniform(4, 13), 190, 252)

    power = np.round(actual_load, 3)
    current = np.clip((power * 1000) / np.maximum(voltage * power_factor, 1.0), 0.4, None)

    wastage_score = np.clip((reported_consumption - expected_consumption) / np.maximum(expected_consumption, 0.1), 0.0, 2.5)
    wastage_score += np.where((meter.usage_profile == "ac_heavy") & (temperature < 24) & (reported_consumption > expected_consumption * 1.15), 0.18, 0.0)
    wastage_score += np.where((power_factor < 0.82) & (~theft_mask), 0.12, 0.0)
    wastage_score = np.round(np.clip(wastage_score, 0.0, 2.5), 3)

    frame = pd.DataFrame(
        {
            "meter_id": meter.meter_id,
            "timestamp": timestamps,
            "region": meter.region,
            "area": meter.area,
            "latitude": meter.latitude,
            "longitude": meter.longitude,
            "voltage": np.round(voltage, 2),
            "current": np.round(current, 3),
            "power": power,
            "consumption_kwh": np.round(reported_consumption, 3),
            "power_factor": np.round(power_factor, 3),
            "temperature": np.round(temperature, 2),
            "humidity": np.round(humidity, 2),
            "rainfall": np.round(rainfall, 2),
            "wind_speed": np.round(wind_speed, 2),
            "weather_condition": weather_condition,
            "is_theft": theft_mask.astype(int),
            "expected_consumption_kwh": np.round(expected_consumption, 3),
            "wastage_score": wastage_score,
            "usage_profile": meter.usage_profile,
            "theft_type": theft_type,
            "seeded_theft_probability": theft_probability,
        }
    )
    return frame


def generate_smart_meter_data(
    num_meters: int | None = None,
    days: int | None = None,
    output_path: str | Path | None = None,
    overwrite: bool = True,
    chunk_size: int | None = None,
    sample_rows: int | None = None,
    simulation_days: int | None = None,
    simulation_meter_limit: int | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    paths = ensure_project_dirs()
    config = generation_config(full_scale=False)
    num_meters = num_meters or config["num_meters"]
    days = days or config["days"]
    chunk_size = chunk_size or config["chunk_size"]
    sample_rows = sample_rows or config["sample_rows"]
    simulation_days = simulation_days or config["simulation_days"]
    simulation_meter_limit = simulation_meter_limit or config["simulation_meter_limit"]
    output_path = Path(output_path) if output_path else paths.dataset

    seed_everything(seed)
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range(
        end=pd.Timestamp.utcnow().tz_localize(None).floor("h"),
        periods=days * 24,
        freq="h",
    )

    meter_catalog = build_meter_catalog(num_meters=num_meters, seed=seed)
    meter_catalog.to_csv(paths.meter_catalog, index=False)

    weather_service = WeatherService()
    weather_lookup = weather_service.area_weather_frame(timestamps)

    if overwrite and output_path.exists():
        output_path.unlink()
    if overwrite and paths.live_dataset.exists():
        paths.live_dataset.unlink()

    sampled_frames: list[pd.DataFrame] = []
    live_frames: list[pd.DataFrame] = []
    live_meter_ids = set(meter_catalog["meter_id"].head(simulation_meter_limit).tolist())
    live_start = timestamps.max() - pd.Timedelta(days=simulation_days)

    catalog_records = [MeterProfile(**row) for row in meter_catalog.to_dict(orient="records")]
    for chunk_index, start in enumerate(range(0, len(catalog_records), chunk_size)):
        stop = start + chunk_size
        chunk_records = catalog_records[start:stop]
        chunk_frames: list[pd.DataFrame] = []
        for meter in chunk_records:
            weather = weather_lookup[meter.area]
            meter_frame = simulate_meter_series(meter, timestamps, weather, rng)
            chunk_frames.append(meter_frame)
            if meter.meter_id in live_meter_ids:
                live_frames.append(meter_frame.loc[meter_frame["timestamp"] >= live_start].copy())

        chunk_df = pd.concat(chunk_frames, ignore_index=True)
        chunk_df.to_csv(output_path, mode="a", header=chunk_index == 0, index=False)

        if sample_rows:
            take = min(max(1500, sample_rows // max(1, num_meters // chunk_size + 1)), len(chunk_df))
            sampled_frames.append(chunk_df.sample(n=take, random_state=seed + chunk_index))

    sample_df = pd.concat(sampled_frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    sample_df.to_csv(paths.data_processed / "smart_meter_sample.csv", index=False)

    live_df = pd.concat(live_frames, ignore_index=True).sort_values(["timestamp", "meter_id"]).reset_index(drop=True)
    live_df.to_csv(paths.live_dataset, index=False)

    summary = {
        "config": {
            "num_meters": num_meters,
            "days": days,
            "sample_rows": sample_rows,
            "simulation_days": simulation_days,
        },
        "dataset_path": str(output_path),
        "sample_path": str(paths.data_processed / "smart_meter_sample.csv"),
        "live_path": str(paths.live_dataset),
        "records_written": int(num_meters * days * 24),
        "theft_rate_in_sample": float(sample_df["is_theft"].mean()),
        "areas": sorted(meter_catalog["area"].unique().tolist()),
    }
    save_json(summary, paths.data_processed / "generation_summary.json")
    return sample_df


if __name__ == "__main__":
    generate_smart_meter_data(**generation_config(full_scale=True))

