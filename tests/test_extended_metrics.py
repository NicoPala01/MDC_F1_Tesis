"""Time-domain throttle / lift metrics, lap-synchronous centring and within-driver tyre effects."""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.features.aggregators import (
    EXTENDED_STYLE_FEATURES,
    extract_style_features_from_telemetry,
)
from f1_style_clustering.features.metrics import (
    get_apex_to_full_throttle_time,
    get_lift_before_brake_time,
    get_min_gear,
    get_release_to_full_throttle_time,
    get_throttle_excess_variation,
    order_along_track,
    zone_is_active,
)
from f1_style_clustering.features.preprocessor import normalize_lap_synchronous, remove_within_driver_effects
from f1_style_clustering.features.zoi import disjoint_zone_bounds


def _corner(n=161, speed_kmh=None, brake=None, throttle=None, gear=None, start=0.0):
    """Samples every 5 m from ``start``; constant 36 km/h (10 m/s) unless given."""
    d = start + np.arange(n) * 5.0
    return pd.DataFrame({
        "Distance": d,
        "Speed": np.full(n, 36.0) if speed_kmh is None else speed_kmh,
        "Brake": np.zeros(n, dtype=bool) if brake is None else brake,
        "Throttle": np.full(n, 100.0) if throttle is None else throttle,
        "nGear": np.full(n, 6) if gear is None else gear,
    })


def test_order_along_track_wraps_and_integrates_time():
    frame = _corner(n=4, start=0.0)
    frame["Distance"] = [990.0, 995.0, 0.0, 5.0]
    ordered = order_along_track(frame.iloc[[2, 3, 0, 1]], start=990.0, track_length=1000.0)
    assert ordered["pos"].tolist() == [0.0, 5.0, 10.0, 15.0]
    assert np.allclose(ordered["t"], [0.0, 0.5, 1.0, 1.5])


def test_release_and_apex_to_full_throttle():
    n = 41
    brake = np.zeros(n, dtype=bool)
    brake[5:15] = True  # last brake sample at 70 m
    throttle = np.zeros(n)
    throttle[20:] = np.linspace(20, 100, n - 20)  # crosses 95 between samples
    w = order_along_track(_corner(n=n, brake=brake, throttle=throttle), start=0.0)
    apex_pos = 90.0
    t_full = get_apex_to_full_throttle_time(w, apex_pos)
    t_release = get_release_to_full_throttle_time(w, apex_pos)
    full_i = int(np.flatnonzero(throttle >= 95)[0])
    assert full_i * 0.5 - 1.0 < t_full + 9.0 <= full_i * 0.5 + 1e-9
    assert t_release == pytest.approx(t_full + (90.0 - 70.0) / 10.0)
    no_brake = order_along_track(_corner(n=n, throttle=throttle), start=0.0)
    assert np.isnan(get_release_to_full_throttle_time(no_brake, apex_pos))
    never_full = order_along_track(_corner(n=n, throttle=np.full(n, 50.0)), start=0.0)
    assert np.isnan(get_apex_to_full_throttle_time(never_full, apex_pos))


def test_throttle_excess_variation_counts_only_corrections():
    monotone = _corner(n=5, throttle=np.array([0.0, 25.0, 50.0, 75.0, 100.0]))
    wobbly = _corner(n=5, throttle=np.array([0.0, 60.0, 40.0, 80.0, 100.0]))
    assert get_throttle_excess_variation(monotone) == 0.0
    # |Δ| sum 140, net 100 → 40 over 20 m
    assert get_throttle_excess_variation(wobbly) == pytest.approx(2.0)
    assert np.isnan(get_throttle_excess_variation(monotone.iloc[:1]))


def test_lift_before_brake_time():
    n = 41
    throttle = np.full(n, 100.0)
    throttle[20:30] = 0.0  # coast from 100 m
    brake = np.zeros(n, dtype=bool)
    brake[30:] = True  # onset at 150 m
    w = order_along_track(_corner(n=n, throttle=throttle, brake=brake), start=0.0)
    assert get_lift_before_brake_time(w, braking_start_pos=100.0) == pytest.approx(5.0)
    straight_to_brake = throttle.copy()
    straight_to_brake[20:30] = 100.0
    w2 = order_along_track(_corner(n=n, throttle=straight_to_brake, brake=brake), start=0.0)
    assert get_lift_before_brake_time(w2, braking_start_pos=100.0) == 0.0
    w3 = order_along_track(_corner(n=n, throttle=throttle), start=0.0)
    assert np.isnan(get_lift_before_brake_time(w3, braking_start_pos=100.0))


def test_zone_activity_and_min_gear():
    flat = _corner(n=10)
    braked = _corner(n=10, brake=np.r_[np.zeros(5, bool), np.ones(5, bool)], gear=np.array([7, 7, 6, 5, 4, 3, 3, 4, 5, 6]))
    assert not zone_is_active(flat)
    assert zone_is_active(braked)
    assert get_min_gear(braked) == 3.0


def _lap_with_corner_and_flat_zone():
    n = 401
    d = np.arange(n) * 5.0
    speed = np.where(d < 600, 300.0, np.where(d < 800, np.interp(d, [600, 800], [300, 90]), np.interp(d, [800, 2000], [90, 300])))
    brake = (d >= 600) & (d < 780)
    throttle = np.where(d < 560, 100.0, np.where(d < 840, 0.0, np.clip((d - 840) * 0.8, 0, 100)))
    return pd.DataFrame({"Distance": d, "Speed": speed, "Brake": brake, "Throttle": throttle, "nGear": 5, "ThrottleRate": 0.0})


def test_extract_style_features_extended_columns_and_flat_zone_nan():
    tel = _lap_with_corner_and_flat_zone()
    zones = {
        "Corner": {**disjoint_zone_bounds(800.0, 300.0, 60.0, 60.0, 250.0), "apex_distance": 800.0, "typology": "slow", "track_length": None},
        "Flat": {**disjoint_zone_bounds(1800.0, 150.0, 60.0, 60.0, 150.0), "apex_distance": 1800.0, "typology": "fast", "track_length": None},
    }
    rows = {r["corner"]: r for r in extract_style_features_from_telemetry(tel, zones, include_throttle_onset=False, include_extended=True)}
    for feat in EXTENDED_STYLE_FEATURES:
        assert feat in rows["Corner"] and np.isnan(rows["Flat"][feat])
    assert rows["Corner"]["lift_coast_s"] > 0
    assert rows["Corner"]["release_to_full_s"] > rows["Corner"]["apex_to_full_s"] > 0
    default = extract_style_features_from_telemetry(tel, zones, include_throttle_onset=False)
    assert not any(feat in default[0] for feat in EXTENDED_STYLE_FEATURES)


@pytest.fixture
def race_laps():
    """Three drivers; every car gains 0.5 per lap (fuel); MEDIUM is +2 for everyone."""
    rows = []
    level = {"A": 3.0, "B": 0.0, "C": -3.0}
    for d, lvl in level.items():
        for lap in range(1, 31):
            medium = (lap <= 15) if d != "C" else (lap > 15)
            rows.append({"Driver": d, "LapNumber": lap, "Compound": "MEDIUM" if medium else "HARD",
                         "TyreLife": lap if lap <= 15 else lap - 15,
                         "medium__apex_speed_rel": lvl + 0.5 * lap + (2.0 if medium else 0.0)})
    return pd.DataFrame(rows)


def test_lap_synchronous_removes_common_trend_and_keeps_driver_gaps(race_laps):
    before = abs(np.corrcoef(race_laps["LapNumber"], race_laps["medium__apex_speed_rel"])[0, 1])
    out = normalize_lap_synchronous(race_laps, ["medium__apex_speed_rel"], min_count=3)
    by_driver = out.groupby("Driver")["medium__apex_speed_rel"]
    after = abs(np.corrcoef(out["LapNumber"], out["medium__apex_speed_rel"])[0, 1])
    # What is left is C's compound switch against a field that is mostly on MEDIUM early.
    assert before > 0.6 and after < 0.3
    assert by_driver.mean()["A"] > by_driver.mean()["B"] > by_driver.mean()["C"]
    assert set(out.attrs["lap_sync_window"].values()) == {0}


def test_lap_synchronous_widens_window_for_sparse_laps(race_laps):
    sparse = race_laps[~((race_laps["LapNumber"] == 10) & (race_laps["Driver"] != "A"))]
    out = normalize_lap_synchronous(sparse, ["medium__apex_speed_rel"], min_count=3)
    assert out.attrs["lap_sync_window"][10] == 1
    assert out["medium__apex_speed_rel"].notna().all()


def test_within_driver_effects_remove_compound_offset_only(race_laps):
    out = remove_within_driver_effects(race_laps, ["medium__apex_speed_rel"], numeric=("LapNumber",))
    coefs = out.attrs["within_driver_coefs"]["medium__apex_speed_rel"]
    assert coefs["Compound_MEDIUM"] == pytest.approx(2.0)
    assert coefs["LapNumber"] == pytest.approx(0.5)
    within = out.groupby(["Driver", "Compound"])["medium__apex_speed_rel"].mean().unstack()
    assert (within["MEDIUM"] - within["HARD"]).abs().max() < 1e-9
    means = out.groupby("Driver")["medium__apex_speed_rel"].mean()
    assert means["A"] - means["C"] == pytest.approx(6.0)
    untouched = remove_within_driver_effects(race_laps.drop(columns=["Compound", "TyreLife"]), ["medium__apex_speed_rel"])
    assert untouched["medium__apex_speed_rel"].equals(race_laps["medium__apex_speed_rel"])


def _long_table():
    rows = []
    for d, shift in (("A", 0.0), ("B", 5.0)):
        for lap in range(1, 6):
            for zone, typ in (("Z1", "slow"), ("Z2", "medium")):
                rows.append({
                    "Driver": d, "LapNumber": lap, "Team": "T", "FullName": d, "corner": zone, "typology": typ,
                    "brake_point_rel": 50.0 + shift + lap, "trail_brake_frac": 0.2, "apex_speed_rel": 100.0,
                    "throttle_attack": 30.0, "coast_frac": 0.05, "full_throttle_frac": 0.4,
                    "release_to_full_s": 1.0 + 0.1 * lap, "apex_to_full_s": 0.5, "throttle_excess_tv": 0.01,
                    "lift_coast_s": 0.0,
                })
    return pd.DataFrame(rows)


def test_builders_carry_extended_columns_only_in_the_lap_matrix(monkeypatch):
    from f1_style_clustering.features import aggregators

    seen = {}

    def fake_long(session, **kwargs):
        seen.update(kwargs)
        return _long_table()

    monkeypatch.setattr(aggregators, "build_long_style_table", fake_long)
    zones = {"Z1": {}, "Z2": {}}
    laps = aggregators.build_lap_style_matrix(None, analysis_zones=zones, include_extended=True, min_valid_laps=1)
    assert seen["include_extended"] is True
    assert {"slow__release_to_full_s", "medium__lift_coast_s"} <= set(laps.columns)
    seen.clear()
    drivers = aggregators.build_feature_matrix(None, analysis_zones=zones, min_valid_laps=1)
    assert "include_extended" not in seen
    assert not drivers.empty
    assert not any("release_to_full" in str(c) for c in drivers.columns)


def test_within_driver_effects_leave_zero_iqr_columns(race_laps):
    laps = race_laps.copy()
    laps["fast__full_throttle_frac"] = 0.0
    laps.loc[laps.index[:3], "fast__full_throttle_frac"] = -0.4
    out = remove_within_driver_effects(laps, ["fast__full_throttle_frac"], numeric=("LapNumber",))
    assert out["fast__full_throttle_frac"].equals(laps["fast__full_throttle_frac"])
    assert "fast__full_throttle_frac" not in out.attrs["within_driver_coefs"]


def test_pipeline_helpers_split_extended_and_screen(race_laps):
    from f1_style_clustering.pipeline import _normalize_lap_matrix, _screen_lap_matrix

    laps = race_laps.copy()
    laps["Team"] = laps["Driver"]
    laps["slow__coast_frac"] = laps["Driver"].map({"A": 0.1, "B": 0.0, "C": -0.1}) + 0.001 * laps["LapNumber"] % 3
    laps["fast__full_throttle_frac"] = 0.0
    laps["medium__release_to_full_s"] = 1.0 + 0.01 * laps["LapNumber"]
    out, extended, info = _normalize_lap_matrix(laps, lap_sync=True, tyre_fe=False)
    assert info["lap_synchronous"] and not info["within_driver_tyre_effects"]
    assert "medium__release_to_full_s" not in out.columns
    assert list(extended.columns[-1:]) == ["medium__release_to_full_s"]
    screened, sinfo = _screen_lap_matrix(out, {"drop_near_constant": True, "min_icc": 0.25})
    assert "fast__full_throttle_frac" in sinfo["dropped_near_constant"]
    assert "fast__full_throttle_frac" not in screened.columns
    assert "slow__coast_frac" in sinfo["kept"]
    untouched, uinfo = _screen_lap_matrix(out, {})
    assert untouched.shape == out.shape and uinfo["min_icc"] is None


def test_default_config_centres_laps_and_keeps_all_clustered_columns(race_laps):
    from f1_style_clustering.config import load_config
    from f1_style_clustering.pipeline import _normalize_lap_matrix, _screen_lap_matrix

    feat = load_config()["features"]
    laps = race_laps.copy()
    laps["Team"] = laps["Driver"]
    laps["fast__full_throttle_frac"] = 0.0
    out, extended, info = _normalize_lap_matrix(laps, feat["lap_synchronous"], feat["within_driver_tyre_effects"])
    assert info["lap_synchronous"] and info["within_driver_tyre_effects"]
    assert info["unit"] == "typology_session_median+lap_synchronous"
    assert extended is None
    assert abs(np.corrcoef(out["LapNumber"], out["medium__apex_speed_rel"])[0, 1]) < 0.3
    screened, sinfo = _screen_lap_matrix(out, feat["feature_screening"])
    assert screened.shape == out.shape
    assert sinfo["dropped_near_constant"] == [] and sinfo["min_icc"] is None
    assert "fast__full_throttle_frac" in sinfo["kept"]
