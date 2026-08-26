"""Unit tests for telemetry signal processing and feature calculation."""

import pytest
import pandas as pd
import numpy as np

from f1_style_clustering.features.metrics import (
    get_braking_point,
    get_braking_distance_to_apex,
    get_max_deceleration,
    get_min_apex_speed,
    get_max_throttle_rate,
    get_throttle_application_point,
    get_trail_braking_score,
)
from f1_style_clustering.features.preprocessor import (
    normalize_relative_to_mean,
    standardize_features,
)


@pytest.fixture
def sample_telemetry_fragment():
    """Create synthetic telemetry dataframe mimicking a braking-apex-exit sequence."""
    distances = np.linspace(100, 500, 40)
    time_sec = np.linspace(0, 4.0, 40)
    speeds = np.concatenate([np.linspace(300, 100, 20), np.linspace(100, 260, 20)])
    brakes = np.concatenate([np.zeros(5), np.ones(15), np.zeros(20)])
    throttles = np.concatenate([np.zeros(20), np.linspace(0, 100, 20)])
    accels = np.concatenate([np.linspace(0, -35, 10), np.linspace(-35, 0, 10), np.linspace(0, 15, 20)])

    df = pd.DataFrame({
        "Distance": distances,
        "Time": pd.to_timedelta(time_sec, unit="s"),
        "TimeDelta": np.diff(time_sec, prepend=0.1),
        "Speed": speeds,
        "Brake": brakes,
        "Throttle": throttles,
        "Acceleration": accels,
        "ThrottleRate": np.concatenate([[0], np.diff(throttles) / 0.1]),
    })
    return df


def test_get_braking_point(sample_telemetry_fragment):
    frag = sample_telemetry_fragment.iloc[:20]
    bp = get_braking_point(frag)
    assert pd.notna(bp)
    assert bp >= 100.0


def test_get_braking_distance_to_apex(sample_telemetry_fragment):
    frag = sample_telemetry_fragment.iloc[:20]
    dist_to_apex = get_braking_distance_to_apex(frag, apex_distance=300.0)
    assert pd.notna(dist_to_apex)
    assert dist_to_apex > 0


def test_get_max_deceleration(sample_telemetry_fragment):
    frag = sample_telemetry_fragment.iloc[:20]
    max_decel = get_max_deceleration(frag)
    assert pd.notna(max_decel)
    assert max_decel >= 30.0  # magnitude


def test_get_min_apex_speed(sample_telemetry_fragment):
    frag = sample_telemetry_fragment.iloc[15:25]
    min_speed = get_min_apex_speed(frag)
    assert pd.notna(min_speed)
    assert min_speed <= 150.0


def test_get_max_throttle_rate(sample_telemetry_fragment):
    frag = sample_telemetry_fragment.iloc[20:]
    max_rate = get_max_throttle_rate(frag)
    assert pd.notna(max_rate)
    assert max_rate > 0


def test_get_trail_braking_score(sample_telemetry_fragment):
    frag = sample_telemetry_fragment.iloc[15:25]
    tb = get_trail_braking_score(frag)
    assert 0.0 <= tb <= 1.0


def test_preprocessor_normalization_and_scaling():
    df_raw = pd.DataFrame({
        "Turn1_ApexSpeed": [120.0, 125.0, 130.0, 115.0],
        "Turn1_MaxDecel": [30.0, 32.0, 28.0, 35.0],
        "Team": ["Red Bull", "McLaren", "Ferrari", "Mercedes"],
    }, index=["VER", "NOR", "LEC", "HAM"])

    df_norm, df_meta = normalize_relative_to_mean(df_raw)
    assert len(df_norm) == 4
    assert np.isclose(df_norm["Turn1_ApexSpeed"].mean(), 0.0, atol=1e-6)

    df_scaled, _, scaler = standardize_features(df_norm)
    assert np.isclose(df_scaled["Turn1_ApexSpeed"].mean(), 0.0, atol=1e-6)
    assert np.isclose(df_scaled["Turn1_ApexSpeed"].std(ddof=0), 1.0, atol=1e-6)

