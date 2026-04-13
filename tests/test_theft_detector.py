from __future__ import annotations

import numpy as np
import pandas as pd

from src.theft_detector import _calibrate_theft_probability


def test_calibrated_theft_probability_pushes_strong_cases_above_point_nine() -> None:
    frame = pd.DataFrame(
        [
            {
                "seeded_theft_probability": 0.94,
                "anomaly_score": 0.62,
                "wastage_score": 0.28,
            },
            {
                "seeded_theft_probability": 0.08,
                "anomaly_score": 0.12,
                "wastage_score": 0.05,
            },
        ]
    )

    calibrated = _calibrate_theft_probability(
        frame,
        rf_probability=np.array([0.84, 0.18]),
        boost_probability=np.array([0.92, 0.22]),
    )

    assert calibrated[0] >= 0.91
    assert calibrated[1] < 0.9
