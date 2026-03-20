from __future__ import annotations

import pandas as pd

from src.data_generator import build_meter_catalog
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

