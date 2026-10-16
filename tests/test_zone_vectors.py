"""Zone vectors and braking-window edges. The default vector stays by typology."""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.config import load_config
from f1_style_clustering.features.aggregators import lap_vectors_from_zones
from f1_style_clustering.features.brake_windows import (
    apply_scaled_braking,
    braking_pre_apex_m,
    classify_onset,
    scale_braking_distance,
    summarize_onsets,
)
from f1_style_clustering.features.zoi import disjoint_zone_bounds


def _long(rows):
    return pd.DataFrame(rows)


def test_config_keeps_typology_vectors_and_fixed_windows():
    cfg = load_config()
    assert cfg["features"]["vector_unit"] == "typology"
    assert cfg["features"]["speed_scaled_windows"] is False
    assert cfg["features"]["zone_brake_min_coverage"] == pytest.approx(0.95)
    assert cfg["features"]["speed_scaled_ref_kmh"] == pytest.approx(300)


def test_zone_vector_drops_brake_columns_where_nobody_brakes_and_keeps_laps():
    rows = []
    for lap in range(4):
        rows.append(
            {
                "Driver": "A",
                "LapNumber": lap,
                "corner": "T1",
                "brake_point_rel": 100.0 + lap,
                "trail_brake_frac": 0.2,
                "apex_speed_rel": 80.0,
            }
        )
        rows.append(
            {
                "Driver": "A",
                "LapNumber": lap,
                "corner": "T3",
                "brake_point_rel": np.nan,
                "trail_brake_frac": np.nan,
                "apex_speed_rel": 300.0,
            }
        )
    out = lap_vectors_from_zones(_long(rows), min_brake_coverage=0.95)
    report = out.attrs["zone_vector"]
    assert report["naive_complete_laps"] == 0
    assert report["n_laps"] == 4
    assert len(out) == 4
    assert "T1__brake_point_rel" in out.columns
    assert "T3__brake_point_rel" not in out.columns
    assert "T3__trail_brake_frac" not in out.columns
    assert "T3__braked" not in out.columns
    assert "T3__apex_speed_rel" in out.columns
    assert report["brake_coverage"]["T3"] == pytest.approx(0.0)


def test_partial_braking_is_an_explicit_indicator_not_a_fake_distance():
    rows = []
    for lap in range(10):
        rows.append(
            {
                "Driver": "A",
                "LapNumber": lap,
                "corner": "T7",
                "brake_point_rel": 40.0 if lap < 8 else np.nan,
                "trail_brake_frac": 0.1 if lap < 8 else np.nan,
                "apex_speed_rel": 150.0,
            }
        )
    out = lap_vectors_from_zones(_long(rows), min_brake_coverage=0.95)
    assert len(out) == 10
    assert "T7__brake_point_rel" not in out.columns
    assert "T7__braked" in out.columns
    assert out["T7__braked"].sum() == pytest.approx(8.0)
    assert set(out["T7__braked"].unique()) <= {0.0, 1.0}


def test_high_brake_coverage_keeps_the_distance_and_dropna_only_the_holes():
    rows = []
    for lap in range(25):
        rows.append(
            {
                "Driver": "A",
                "LapNumber": lap,
                "corner": "T1",
                "brake_point_rel": np.nan if lap == 0 else 90.0,
                "apex_speed_rel": 70.0,
            }
        )
    out = lap_vectors_from_zones(_long(rows), feature_cols=["brake_point_rel", "apex_speed_rel"], min_brake_coverage=0.95)
    assert "T1__brake_point_rel" in out.columns
    assert "T1__braked" not in out.columns
    assert len(out) == 24


def test_scale_braking_distance_follows_speed_squared():
    assert scale_braking_distance(350.0, 300.0, ref_kmh=300.0) == pytest.approx(350.0)
    assert scale_braking_distance(350.0, 150.0, ref_kmh=300.0) == pytest.approx(87.5)
    assert scale_braking_distance(350.0, None) == pytest.approx(350.0)
    assert scale_braking_distance(350.0, 0.0) == pytest.approx(350.0)
    assert scale_braking_distance(350.0, 50.0, min_m=80.0) == pytest.approx(80.0)


def test_rescale_moves_only_the_braking_start():
    zone = disjoint_zone_bounds(1000.0, braking_pre_m=350.0, track_length=5800.0)
    zone["apex_distance"] = 1000.0
    zone["track_length"] = 5800.0
    assert braking_pre_apex_m(zone) == pytest.approx(350.0)
    moved = apply_scaled_braking({"T1": zone}, {"T1": 300.0}, ref_kmh=300.0)
    assert moved["T1"]["braking"][1] == zone["apex"][0]
    assert braking_pre_apex_m(moved["T1"]) == pytest.approx(350.0, abs=1.0)
    shorter = apply_scaled_braking({"T1": zone}, {"T1": 150.0}, ref_kmh=300.0, min_m=80.0)
    assert braking_pre_apex_m(shorter["T1"]) < 350.0


def test_onset_on_the_first_sample_is_the_window_edge():
    on_edge = pd.DataFrame(
        {"Distance": [0.0, 10.0, 20.0], "Brake": [True, True, False], "Speed": [310.0, 280.0, 250.0]}
    )
    inside = pd.DataFrame(
        {"Distance": [0.0, 10.0, 80.0], "Brake": [False, False, True], "Speed": [300.0, 300.0, 220.0]}
    )
    edge = classify_onset(on_edge, window_start=0.0, track_length=None)
    later = classify_onset(inside, window_start=0.0, track_length=None)
    none = classify_onset(pd.DataFrame(), window_start=0.0, track_length=None)
    assert edge["edge"] is True and edge["within_5m"] is True
    assert edge["onset_from_start_m"] == pytest.approx(0.0)
    assert later["edge"] is False and later["has_onset"] is True
    assert later["onset_from_start_m"] == pytest.approx(80.0)
    assert later["within_5m"] is False
    assert none is None
    summary = summarize_onsets(
        pd.DataFrame(
            [
                {"window": "350m", "zone": "T1", "has_onset": True, "edge": True, "within_5m": True, "entry_speed": 300.0},
                {"window": "350m", "zone": "T1", "has_onset": True, "edge": False, "within_5m": False, "entry_speed": 290.0},
                {"window": "350m", "zone": "T3", "has_onset": False, "edge": False, "within_5m": False, "entry_speed": 320.0},
            ]
        )
    )
    total = summary[(summary["window"] == "350m") & (summary["zone"] == "TOTAL")].iloc[0]
    assert total["n_onsets"] == 2
    assert total["edge_frac_of_onsets"] == pytest.approx(0.5)


def test_default_run_does_not_build_zone_vectors(monkeypatch):
    from f1_style_clustering import pipeline as pipeline_mod

    calls = []
    matrix = _clusterable_matrix()

    def typology(*_args, **_kwargs):
        calls.append("typology")
        return matrix.copy()

    def zone(*_args, **_kwargs):
        calls.append("zone")
        return matrix.copy()

    def boom(*_args, **_kwargs):
        raise AssertionError("speed-scaled windows ran on the default path")

    monkeypatch.setattr(pipeline_mod, "resolve_selected_corners", lambda *_a, **_k: (None, "synthetic"))
    monkeypatch.setattr(pipeline_mod, "extract_circuit_zones", lambda *_a, **_k: {})
    monkeypatch.setattr(pipeline_mod, "build_lap_style_matrix", typology)
    monkeypatch.setattr(pipeline_mod, "build_zone_style_matrix", zone)
    monkeypatch.setattr(pipeline_mod, "apply_speed_scaled_windows", boom)
    cfg = load_config()
    cfg["clustering"]["seed_stability_n"] = 2
    cfg["clustering"]["kmeans"]["n_init"] = 2
    cfg["clustering"]["kmeans"]["k_range"] = [2, 3]
    result = pipeline_mod.run_pipeline({}, config=cfg, circuit_config={})
    assert calls == ["typology"]
    assert "zone_vector" not in result
    assert not result.get("error")


def _clusterable_matrix() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for driver, level in (("AAA", 0.0), ("BBB", 0.0), ("CCC", 6.0), ("DDD", 6.0)):
        for lap in range(1, 16):
            rows.append(
                {
                    "Driver": driver,
                    "FullName": driver,
                    "Team": "T",
                    "LapNumber": lap,
                    "Compound": "MEDIUM",
                    "TyreLife": float(lap),
                    "slow__apex_speed_rel": level + rng.normal(0, 0.2),
                    "slow__brake_point_rel": level + rng.normal(0, 0.2),
                    "medium__coast_frac": level / 10.0 + rng.normal(0, 0.01),
                    "fast__apex_speed_rel": level + rng.normal(0, 0.2),
                }
            )
    df = pd.DataFrame(rows)
    df.index = df["Driver"] + " L" + df["LapNumber"].astype(str)
    df.attrs["feature_cols"] = ["apex_speed_rel", "brake_point_rel", "coast_frac"]
    df.attrs["lap_typology"] = pd.DataFrame()
    return df
