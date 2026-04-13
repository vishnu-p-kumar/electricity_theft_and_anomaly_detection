from __future__ import annotations

import pandas as pd

import numpy as np

from src.data_generator import LiveTheftProfile, MeterProfile, build_meter_catalog, simulate_meter_series
from src.feature_engineering import build_feature_matrix
from src.preprocess import preprocess_frame


def test_meter_catalog_stays_within_bengaluru_bounds() -> None:
    catalog = build_meter_catalog(num_meters=40, seed=42)
    assert len(catalog) == 40
    assert catalog["latitude"].between(12.80, 13.20).all()
    assert catalog["longitude"].between(77.45, 77.80).all()
    assert catalog["area"].nunique() >= 5


def test_preprocess_handles_existing_numeric_subset() -> None:
    frame = pd.DataFrame(
        [
            {
                "meter_id": "M0001",
                "timestamp": "2026-03-12 10:00:00",
                "power": 2.4,
                "consumption_kwh": 1.8,
                "power_factor": 0.78,
                "temperature": 29.4,
                "humidity": 70.0,
                "rainfall": 0.0,
                "wind_speed": 2.1,
                "wastage_score": 0.31,
            }
        ]
    )
    processed = preprocess_frame(frame)
    assert processed.loc[0, "wastage_flag"] == 1
    assert processed.loc[0, "temperature_band"] in {"warm", "hot"}


def test_feature_engineering_creates_expected_columns(sample_meter_frame: pd.DataFrame) -> None:
    enriched, features = build_feature_matrix(sample_meter_frame)
    assert "hour_of_day" in enriched.columns
    assert "rolling_average_consumption" in enriched.columns
    assert "night_usage_ratio" in enriched.columns
    assert "area_Whitefield" in features.columns
    assert "usage_profile_residential" in features.columns
    assert not features.empty


def test_live_theft_generation_stays_consistent_for_selected_meter() -> None:
    timestamps = pd.date_range("2026-03-10 00:00:00", periods=12, freq="h")
    weather = pd.DataFrame(
        {
            "temperature": [28.0] * len(timestamps),
            "humidity": [68.0] * len(timestamps),
            "rainfall": [0.0] * len(timestamps),
            "wind_speed": [2.0] * len(timestamps),
            "weather_condition": ["clear"] * len(timestamps),
        }
    )
    meter = MeterProfile(
        meter_id="M0001",
        region="Bengaluru",
        area="Whitefield",
        latitude=12.97,
        longitude=77.75,
        usage_profile="residential",
    )

    frame = simulate_meter_series(
        meter,
        timestamps,
        weather,
        np.random.default_rng(42),
        live_theft_profile=LiveTheftProfile(theft_type="meter_bypass", theft_probability=0.93),
        live_start=timestamps[4],
        disable_random_theft=True,
    )

    assert (frame.loc[frame["timestamp"] < timestamps[4], "is_theft"] == 0).all()
    assert (frame.loc[frame["timestamp"] >= timestamps[4], "is_theft"] == 1).all()
    assert frame.loc[frame["timestamp"] >= timestamps[4], "theft_type"].eq("meter_bypass").all()
    assert frame["seeded_theft_probability"].eq(0.93).all()


def test_live_generation_can_disable_random_theft_for_non_selected_meters() -> None:
    timestamps = pd.date_range("2026-03-10 00:00:00", periods=12, freq="h")
    weather = pd.DataFrame(
        {
            "temperature": [28.0] * len(timestamps),
            "humidity": [68.0] * len(timestamps),
            "rainfall": [0.0] * len(timestamps),
            "wind_speed": [2.0] * len(timestamps),
            "weather_condition": ["clear"] * len(timestamps),
        }
    )
    meter = MeterProfile(
        meter_id="M0002",
        region="Bengaluru",
        area="Koramangala",
        latitude=12.93,
        longitude=77.62,
        usage_profile="commercial",
    )

    frame = simulate_meter_series(
        meter,
        timestamps,
        weather,
        np.random.default_rng(42),
        disable_random_theft=True,
    )

    assert frame["is_theft"].eq(0).all()
    assert frame["theft_type"].eq("none").all()
    assert frame["seeded_theft_probability"].eq(0.0).all()
