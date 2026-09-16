"""Unit tests for Pipeline B (typology×session median → driver aggregation).

These tests use synthetic telemetry only — no FastF1 network downloads.
"""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.features.zoi import (
    clip_and_merge_zones,
    disjoint_zone_bounds,
    extract_circuit_zones,
    in_distance_window,
    get_corner_fragments,
    map_typology_to_bucket,
    classify_speed_typology,
    resolve_selected_corners,
)
from f1_style_clustering.features.metrics import (
    is_brake_on,
    spatial_fraction,
    get_kinematic_apex_distance,
    get_brake_point_relative,
    get_trail_brake_frac,
    get_apex_speed,
    get_throttle_attack,
    get_coast_frac,
    get_full_throttle_frac,
    get_throttle_onset_relative,
)
from f1_style_clustering.features.preprocessor import (
    normalize_typology_session_median,
    standardize_features,
)
from f1_style_clustering.features.aggregators import (
    CORE_STYLE_FEATURES,
    extract_style_features_from_telemetry,
    aggregate_driver_style_features,
    collapse_to_driver_lap_typology,
)
from f1_style_clustering.data.filters import (
    MissingCanonicalPickError,
    filter_canonical_laps,
    apply_min_valid_laps,
)
from f1_style_clustering.models.evaluation import (
    InvalidKPoolError,
    mean_median_kmeans_ari,
    select_k_rule_based,
)
from f1_style_clustering.models.dimensionality import pca_for_clustering
from f1_style_clustering.models.clustering import (
    dbscan_prefilter_outliers,
    kmeans_driver_bootstrap_stability,
    kmeans_seed_stability,
)
from f1_style_clustering.features.preprocessor import (
    confounding_declaration,
    residualize_team_tyre_features,
    separate_metadata,
)
from f1_style_clustering.analysis.archetypes import assign_archetype_names
from f1_style_clustering.analysis.pipeline_c import cluster_laps_pipeline_c
from f1_style_clustering.config import load_config, load_circuit_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _synthetic_corner_telemetry(
    apex_m=300.0,
    n=80,
    brake_on_from=180.0,
    brake_off_at=295.0,
    min_speed_at=300.0,
    throttle_on_at=320.0,
    full_throttle_at=380.0,
):
    """Build a braking → apex → exit telemetry fragment along Distance."""
    distances = np.linspace(100.0, 500.0, n)
    speed = np.where(
        distances <= min_speed_at,
        np.interp(distances, [100.0, min_speed_at], [280.0, 90.0]),
        np.interp(distances, [min_speed_at, 500.0], [90.0, 250.0]),
    )
    brake = (distances >= brake_on_from) & (distances <= brake_off_at)
    throttle = np.zeros(n)
    throttle[distances >= throttle_on_at] = np.interp(
        distances[distances >= throttle_on_at],
        [throttle_on_at, full_throttle_at, 500.0],
        [20.0, 100.0, 100.0],
    )
    dt = np.full(n, 0.05)
    throttle_rate = np.concatenate([[0.0], np.diff(throttle) / dt[1:]])
    df = pd.DataFrame(
        {
            "Distance": distances,
            "Speed": speed,
            "Brake": brake,
            "Throttle": throttle,
            "TimeDelta": dt,
            "ThrottleRate": throttle_rate,
        }
    )
    return df


class _FakeLaps:
    """Minimal Laps stand-in exposing FastF1-style pick_* methods."""

    def __init__(self, df: pd.DataFrame):
        self._df = df.reset_index(drop=True)
        self.empty = self._df.empty
        self.columns = self._df.columns

    def __len__(self):
        return len(self._df)

    def __getitem__(self, key):
        return self._df[key]

    def pick_drivers(self, driver):
        return _FakeLaps(self._df[self._df["Driver"] == driver])

    def pick_accurate(self):
        return _FakeLaps(self._df[self._df["IsAccurate"]])

    def pick_wo_box(self):
        return _FakeLaps(self._df[~self._df["IsBox"]])

    def pick_not_deleted(self):
        return _FakeLaps(self._df[~self._df["Deleted"]])

    def pick_track_status(self, status: str, how: str = "equals"):
        col = self._df["TrackStatus"].astype(str)
        if how == "equals":
            return _FakeLaps(self._df[col == str(status)])
        return _FakeLaps(self._df[col.str.contains(str(status))])

    def pick_quicklaps(self):
        return _FakeLaps(self._df[self._df["IsQuick"]])


class _FakeSession:
    def __init__(self, laps: _FakeLaps):
        self.laps = laps


def _fake_laps_table():
    rows = [
        # VER: 3 canonical green accurate non-box non-deleted, 2 of them quick
        ("VER", True, False, False, "1", True, 1),
        ("VER", True, False, False, "1", True, 2),
        ("VER", True, False, False, "1", False, 3),
        ("VER", True, True, False, "1", False, 4),  # box
        ("VER", True, False, True, "1", False, 5),  # deleted
        ("VER", False, False, False, "1", False, 6),  # inaccurate
        ("VER", True, False, False, "4", False, 7),  # SC
        # HAM: only 1 canonical lap
        ("HAM", True, False, False, "1", True, 1),
        ("HAM", True, True, False, "1", False, 2),
    ]
    df = pd.DataFrame(
        rows,
        columns=["Driver", "IsAccurate", "IsBox", "Deleted", "TrackStatus", "IsQuick", "LapNumber"],
    )
    return _FakeLaps(df)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_pipeline_config_is_pipeline_b():
    cfg = load_config()
    assert cfg["pipeline"]["name"] == "B"
    assert cfg["features"]["aggregation"] == "median"
    assert cfg["features"]["normalization_unit"] == "typology_session_median"
    assert cfg["data_filtering"]["push_mode"] is False
    assert cfg["clustering"]["use_rule_based_k"] is True
    assert cfg["clustering"].get("default_k") in (None, "auto", "rule")


def test_circuits_yaml_has_typology_buckets_and_zoi_offsets():
    circuits = load_circuit_config()
    assert "default_zoi_offsets" in circuits
    assert "typology_buckets" in circuits
    assert circuits["typology_buckets"]["extreme_slow_hairpin"] == "slow"
    assert circuits["typology_buckets"]["ultra_high_speed"] == "fast"


# ---------------------------------------------------------------------------
# ZOI: disjoint windows + wrap-around
# ---------------------------------------------------------------------------

def test_disjoint_zone_bounds_do_not_overlap():
    bounds = disjoint_zone_bounds(
        apex_distance=1000.0,
        braking_pre_m=350.0,
        apex_pre_m=60.0,
        apex_post_m=60.0,
        exit_post_m=250.0,
        track_length=5000.0,
    )
    braking, apex, exit_z = bounds["braking"], bounds["apex"], bounds["exit"]
    assert braking[1] == apex[0]
    assert apex[1] == exit_z[0]
    assert braking[0] < braking[1] <= apex[0] < apex[1] <= exit_z[0] < exit_z[1]


def test_t1_wrap_around_puts_braking_near_track_end():
    bounds = disjoint_zone_bounds(
        apex_distance=40.0,
        braking_pre_m=350.0,
        apex_pre_m=60.0,
        apex_post_m=60.0,
        exit_post_m=250.0,
        track_length=5000.0,
    )
    braking = bounds["braking"]
    # Apex - 350 wraps: (40 - 350) % 5000 = 4690
    assert braking[0] == pytest.approx(4690.0)
    assert in_distance_window(4700.0, braking[0], braking[1], track_length=5000.0)
    assert not in_distance_window(200.0, braking[0], braking[1], track_length=5000.0)


def test_get_corner_fragments_wraps_t1_braking_samples():
    track_length = 1000.0
    distances = np.concatenate([np.linspace(0, 120, 25), np.linspace(850, 999, 25)])
    tel = pd.DataFrame(
        {
            "Distance": distances,
            "Speed": np.linspace(200, 80, len(distances)),
            "Brake": True,
            "Throttle": 0.0,
        }
    )
    zone = {
        **disjoint_zone_bounds(
            apex_distance=30.0,
            braking_pre_m=200.0,
            apex_pre_m=20.0,
            apex_post_m=20.0,
            exit_post_m=80.0,
            track_length=track_length,
        ),
        "apex_distance": 30.0,
        "track_length": track_length,
    }
    frags = get_corner_fragments(tel, zone)
    assert not frags["braking"].empty
    assert (frags["braking"]["Distance"] >= 850.0).any()


def test_map_and_classify_typology():
    circuits = {
        "typology_buckets": {"extreme_slow_hairpin": "slow", "ultra_high_speed": "fast"},
        "corner_speed_classification": {
            "slow": {"speed_threshold_max_kmh": 125},
            "medium": {"speed_threshold_min_kmh": 125, "speed_threshold_max_kmh": 205},
            "fast": {"speed_threshold_min_kmh": 205},
        },
    }
    assert map_typology_to_bucket("extreme_slow_hairpin", circuits) == "slow"
    assert classify_speed_typology(90.0, circuits) == "slow"
    assert classify_speed_typology(160.0, circuits) == "medium"
    assert classify_speed_typology(240.0, circuits) == "fast"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def test_brake_bool_and_spatial_trail_fraction():
    tel = _synthetic_corner_telemetry()
    assert is_brake_on(tel["Brake"]).dtype == bool
    frac = get_trail_brake_frac(tel)
    assert 0.0 < frac < 1.0
    # Spatial, not merely sample count: denser sampling in a region should not dominate
    dense = pd.DataFrame(
        {
            "Distance": np.concatenate([np.linspace(0, 10, 100), np.linspace(10, 100, 10)]),
            "Brake": np.concatenate([np.ones(100, dtype=bool), np.zeros(10, dtype=bool)]),
        }
    )
    spatial = spatial_fraction(dense, dense["Brake"])
    assert spatial == pytest.approx(10.0 / 100.0, abs=0.08)


def test_kinematic_apex_is_argmin_speed():
    tel = _synthetic_corner_telemetry(min_speed_at=310.0)
    apex_d = get_kinematic_apex_distance(tel)
    assert apex_d == pytest.approx(tel.loc[tel["Speed"].idxmin(), "Distance"])


def test_brake_point_relative_positive_when_braking_before_apex():
    tel = _synthetic_corner_telemetry(brake_on_from=180.0, min_speed_at=300.0)
    apex = get_kinematic_apex_distance(tel)
    bp = get_brake_point_relative(tel, apex_distance=apex)
    assert bp > 0


def test_throttle_attack_is_p95_not_raw_max_spike():
    tel = _synthetic_corner_telemetry()
    tel = tel.copy()
    tel.loc[tel.index[-1], "ThrottleRate"] = 1e6  # sensor spike
    attack = get_throttle_attack(tel, smooth_window=5)
    assert attack < 1e5
    assert attack > 0


def test_coast_and_full_throttle_fractions():
    tel = _synthetic_corner_telemetry()
    coast = get_coast_frac(tel)
    full = get_full_throttle_frac(tel)
    assert 0.0 <= coast <= 1.0
    assert 0.0 <= full <= 1.0
    assert coast > 0
    assert full > 0


def test_throttle_onset_can_be_pre_apex():
    tel = _synthetic_corner_telemetry(throttle_on_at=280.0, min_speed_at=300.0)
    apex = get_kinematic_apex_distance(tel)
    onset = get_throttle_onset_relative(tel, apex_distance=apex)
    assert onset < 0


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def test_canonical_filters_exclude_box_deleted_sc_inaccurate():
    laps = filter_canonical_laps(_fake_laps_table(), push_mode=False)
    assert len(laps) == 4  # VER 1,2,3 + HAM 1
    assert set(laps["LapNumber"].tolist()) == {1, 2, 3}


def test_push_mode_is_not_default_and_applies_quicklaps():
    default_laps = filter_canonical_laps(_fake_laps_table(), push_mode=False)
    push_laps = filter_canonical_laps(_fake_laps_table(), push_mode=True)
    assert len(push_laps) < len(default_laps)
    assert set(push_laps["IsQuick"].tolist()) == {True}


def test_min_valid_laps_drops_short_drivers():
    laps = filter_canonical_laps(_fake_laps_table(), push_mode=False)
    kept = apply_min_valid_laps(laps, min_laps=3, driver_col="Driver")
    assert set(kept["Driver"].unique()) == {"VER"}
    assert "HAM" not in set(kept["Driver"].unique())


# ---------------------------------------------------------------------------
# Normalisation + aggregation
# ---------------------------------------------------------------------------

def test_typology_session_median_centres_each_typology():
    df = pd.DataFrame(
        {
            "Driver": ["A", "A", "B", "B"],
            "typology": ["slow", "fast", "slow", "fast"],
            "brake_point_rel": [10.0, 100.0, 20.0, 80.0],
            "apex_speed_rel": [1.0, 10.0, 3.0, 12.0],
        }
    )
    out = normalize_typology_session_median(
        df, feature_cols=["brake_point_rel", "apex_speed_rel"]
    )
    for typ in ("slow", "fast"):
        sub = out[out["typology"] == typ]
        assert sub["brake_point_rel"].median() == pytest.approx(0.0)
        assert sub["apex_speed_rel"].median() == pytest.approx(0.0)


def test_median_vs_mean_aggregation_robustness_switch():
    long_df = pd.DataFrame(
        {
            "Driver": ["VER"] * 5 + ["HAM"] * 5,
            "LapNumber": list(range(5)) * 2,
            "typology": ["slow"] * 10,
            "brake_point_rel": [10, 11, 12, 13, 100, 20, 21, 22, 23, 24],
            "trail_brake_frac": [0.2] * 10,
            "apex_speed_rel": [1.0] * 10,
            "throttle_attack": [5.0] * 10,
            "coast_frac": [0.1] * 10,
            "full_throttle_frac": [0.4] * 10,
        }
    )
    med = aggregate_driver_style_features(long_df, method="median")
    mean = aggregate_driver_style_features(long_df, method="mean")
    assert med.loc["VER", "n_laps"] == 5
    assert mean.loc["VER", "n_laps"] == 5
    assert med.loc["VER", "brake_point_rel"] < mean.loc["VER", "brake_point_rel"]
    assert "brake_point_iqr" in med.columns


def test_extract_style_features_returns_six_to_eight_named_columns():
    tel = _synthetic_corner_telemetry()
    zones = {
        "Turn_1": {
            **disjoint_zone_bounds(300.0, 200.0, 40.0, 40.0, 150.0, track_length=None),
            "apex_distance": 300.0,
            "typology": "slow",
            "track_length": None,
            "corner_number": 1,
        }
    }
    rows = extract_style_features_from_telemetry(tel, zones)
    assert len(rows) == 1
    row = rows[0]
    for feat in CORE_STYLE_FEATURES:
        assert feat in row
        assert pd.notna(row[feat])
    assert row["typology"] == "slow"
    # Must not explode into one column per numbered corner
    assert not any(k.startswith("Turn_1_") for k in row)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

def test_rule_based_k_uses_silhouette_when_above_threshold():
    rng = np.random.default_rng(0)
    # Three well-separated blobs, 6 points each (>= 3)
    blobs = [
        rng.normal(loc=[0, 0], scale=0.1, size=(6, 2)),
        rng.normal(loc=[6, 0], scale=0.1, size=(6, 2)),
        rng.normal(loc=[0, 6], scale=0.1, size=(6, 2)),
    ]
    X = pd.DataFrame(np.vstack(blobs), columns=["f1", "f2"])
    k_star, eval_df, rule = select_k_rule_based(
        X, k_min=2, k_max=5, silhouette_threshold=0.25, min_cluster_size=3, n_seeds=3
    )
    assert k_star == 3
    assert rule == "silhouette"
    assert eval_df.loc[eval_df["k"] == 3, "min_cluster_size"].iloc[0] >= 3


def test_rule_based_k_falls_back_to_min_davies_bouldin():
    rng = np.random.default_rng(1)
    # Mildly overlapping blobs so silhouette stays below 0.95 but sizes stay ≥ 3.
    blobs = [
        rng.normal(loc=[0, 0], scale=1.1, size=(9, 2)),
        rng.normal(loc=[1.4, 0], scale=1.1, size=(9, 2)),
    ]
    X = pd.DataFrame(np.vstack(blobs), columns=["f1", "f2"])
    k_star, eval_df, rule = select_k_rule_based(
        X,
        k_min=2,
        k_max=4,
        silhouette_threshold=0.95,  # force DB fallback
        min_cluster_size=3,
        n_seeds=3,
    )
    assert rule == "davies_bouldin"
    assert k_star in set(eval_df["k"])
    pool = eval_df[eval_df["valid"]]
    assert not pool.empty
    min_db = pool["davies_bouldin"].min()
    tied = pool[np.isclose(pool["davies_bouldin"].astype(float), float(min_db))]
    assert k_star in set(tied["k"].astype(int))


def test_pca_for_clustering_skipped_when_few_features():
    df = pd.DataFrame(np.random.default_rng(0).normal(size=(12, 6)), columns=list("abcdef"))
    fit_space, model, info = pca_for_clustering(df, variance_threshold=0.85)
    assert info["used"] is False
    assert fit_space.shape[1] == 6
    assert model is None


def test_pca_for_clustering_used_as_fit_space_when_forced():
    rng = np.random.default_rng(2)
    cols = [f"f{i}" for i in range(12)]
    df = pd.DataFrame(rng.normal(size=(20, 12)), columns=cols)
    fit_space, model, info = pca_for_clustering(
        df, variance_threshold=0.80, force=True
    )
    assert info["used"] is True
    assert fit_space.shape[1] < 12
    assert info["cumulative_variance"] >= 0.80 - 1e-9
    assert model is not None


def test_seed_stability_helper_returns_mean_ari():
    rng = np.random.default_rng(3)
    X = pd.DataFrame(
        np.vstack(
            [
                rng.normal(0, 0.2, size=(8, 2)),
                rng.normal(5, 0.2, size=(8, 2)),
            ]
        ),
        columns=["a", "b"],
    )
    mean_ari, std_ari = kmeans_seed_stability(X, n_clusters=2, n_seeds=5)
    assert mean_ari > 0.7
    assert std_ari >= 0.0


def test_dbscan_is_prefilter_not_main_partition():
    rng = np.random.default_rng(4)
    core = rng.normal(size=(15, 2))
    outliers = np.array([[20.0, 20.0], [-20.0, -20.0]])
    X = pd.DataFrame(np.vstack([core, outliers]), columns=["a", "b"])
    inliers, mask = dbscan_prefilter_outliers(X, eps=2.0, min_samples=3)
    assert mask.sum() < len(X)
    assert len(inliers) == int(mask.sum())


# ---------------------------------------------------------------------------
# Archetype namer
# ---------------------------------------------------------------------------

def test_archetype_namer_unique_on_pipeline_b_features():
    profiles = pd.DataFrame(
        {
            "brake_point_rel": [-1.2, 1.1, 0.0],
            "trail_brake_frac": [0.8, -0.4, 0.0],
            "apex_speed_rel": [-0.5, 1.3, 0.1],
            "throttle_attack": [0.2, -0.3, 1.4],
            "coast_frac": [0.1, -0.2, -0.4],
            "full_throttle_frac": [0.0, -0.1, 1.1],
        },
        index=[0, 1, 2],
    )
    names = assign_archetype_names(profiles)
    assert len(names) == 3
    assert len(set(names.values())) == 3
    # Must not be "top-2 of ~60 columns" style names only
    joined = " ".join(names.values()).lower()
    assert "late" in joined or "momentum" in joined or "exit" in joined or "v-shape" in joined
    assert names[0] == "Late Braker (V-Shape)"
    assert names[1] == "Early Conservative Braker"


def test_namer_elif_exclusive_on_fit_space_includes_iqr():
    """if/elif on the 6–8 fit features including brake_point_iqr; uniqueness enforced."""
    profiles = pd.DataFrame(
        {
            "brake_point_rel": [-1.5, 1.2, 0.0, 0.0],
            "trail_brake_frac": [0.9, -0.5, 0.0, 0.0],
            "apex_speed_rel": [-0.4, -0.2, 1.4, 0.0],
            "throttle_attack": [0.1, 0.0, -0.2, 0.0],
            "coast_frac": [0.0, 0.0, -0.3, 0.0],
            "full_throttle_frac": [0.0, 0.2, -0.1, 0.0],
            "brake_point_iqr": [0.1, 0.2, 0.2, 1.8],
        },
        index=[0, 1, 2, 3],
    )
    names = assign_archetype_names(profiles)
    assert names[0] == "Late Braker (V-Shape)"
    assert names[1] == "Early Conservative Braker"
    assert names[2] == "Momentum Keeper (U-Shape)"
    assert names[3] == "Adaptive / Balanced"
    assert len(set(names.values())) == 4


def test_namer_elif_on_pca_fit_space():
    profiles = pd.DataFrame(
        {"PC1": [-1.0, 1.2, 0.4], "PC2": [-0.2, -0.3, 1.1]},
        index=[0, 1, 2],
    )
    names = assign_archetype_names(profiles)
    assert names[0] == "Late Braker (V-Shape)"
    assert names[1] == "Early Conservative Braker"
    assert names[2] == "Momentum Keeper (U-Shape)"
    assert len(set(names.values())) == 3


def test_pipeline_c_stub_is_not_main_path():
    with pytest.raises(NotImplementedError, match="appendix"):
        cluster_laps_pipeline_c(pd.DataFrame())


# ---------------------------------------------------------------------------
# key_corners grouping / YAML ownership / overlap clip
# ---------------------------------------------------------------------------

class _Event:
    def __init__(self, name):
        self.EventName = name
        self._name = name

    def __getitem__(self, key):
        if key == "EventName":
            return self._name
        raise KeyError(key)


class _FakeCircuitSession:
    def __init__(self, event_name, corners_df):
        self.event = _Event(event_name)
        self._corners = corners_df
        self.laps = None

    def get_circuit_info(self):
        return type("CI", (), {"corners": self._corners})()


def test_key_corners_groups_one_zone_per_yaml_entry():
    corners = pd.DataFrame(
        {
            "Number": [1, 2, 4, 5, 8, 9, 10, 11],
            "Distance": [200.0, 280.0, 800.0, 880.0, 1600.0, 1680.0, 1760.0, 2400.0],
        }
    )
    session = _FakeCircuitSession("Italian Grand Prix", corners)
    circuits = load_circuit_config()
    selected, source = resolve_selected_corners(session, circuits)
    assert source == "key_corners"
    assert set(selected) == {1, 2, 4, 5, 8, 9, 10, 11}

    zones = extract_circuit_zones(
        session, circuit_config=circuits, selected_corners=selected, track_length=5800.0
    )
    assert len(zones) == 4
    assert "T1_Variante_del_Rettifilo" in zones
    assert "Turn_1" not in zones
    t1 = zones["T1_Variante_del_Rettifilo"]
    assert t1["corner_numbers"] == [1, 2]
    assert t1["typology"] == "slow"
    assert t1["zone_source"] == "key_corners"
    assert t1["apex_distance"] == pytest.approx(200.0)
    assert t1["apex_distance_last"] == pytest.approx(280.0)
    # One zone covers the chicane group, not one per FastF1 Number.
    assert "T8_Variante_Ascari" in zones
    assert zones["T8_Variante_Ascari"]["corner_numbers"] == [8, 9, 10]


def test_unknown_circuit_uses_speed_threshold_fallback_not_key_corners():
    corners = pd.DataFrame({"Number": [1, 2, 3], "Distance": [100.0, 400.0, 900.0]})
    session = _FakeCircuitSession("Japanese Grand Prix", corners)
    circuits = load_circuit_config()
    selected, source = resolve_selected_corners(session, circuits)
    assert source == "speed_threshold_fallback"
    assert selected is None

    zones = extract_circuit_zones(
        session, circuit_config=circuits, selected_corners=selected, track_length=5000.0
    )
    assert len(zones) == 3
    assert all(z["zone_source"] == "speed_threshold_fallback" for z in zones.values())
    assert all(z.get("typology") is None for z in zones.values())
    assert "Turn_1" in zones
    assert "T1_Variante_del_Rettifilo" not in zones


def test_clip_and_merge_overlapping_apex_windows():
    zones = {
        "Turn_1": {
            **disjoint_zone_bounds(100.0, 80.0, 60.0, 60.0, 100.0, track_length=None),
            "apex_distance": 100.0,
            "corner_number": 1,
            "corner_numbers": [1],
            "yaml_zone_name": "Turn_1",
        },
        "Turn_2": {
            **disjoint_zone_bounds(150.0, 80.0, 60.0, 60.0, 100.0, track_length=None),
            "apex_distance": 150.0,
            "corner_number": 2,
            "corner_numbers": [2],
            "yaml_zone_name": "Turn_2",
        },
    }
    # Apex windows 40–160 and 90–210 overlap → merge along Distance.
    merged = clip_and_merge_zones(zones, track_length=None)
    assert len(merged) == 1
    only = next(iter(merged.values()))
    assert set(only["corner_numbers"]) == {1, 2}


def test_collapse_driver_lap_typology_does_not_inflate_by_corner_number():
    long_df = pd.DataFrame(
        {
            "Driver": ["VER"] * 3,
            "LapNumber": [1, 1, 1],
            "typology": ["slow", "slow", "fast"],
            "corner": ["Turn_1", "Turn_2", "Turn_8"],
            "corner_number": [1, 2, 8],
            "brake_point_rel": [10.0, 20.0, 100.0],
            "trail_brake_frac": [0.1, 0.3, 0.5],
            "apex_speed_rel": [1.0, 3.0, 9.0],
            "throttle_attack": [1.0, 1.0, 1.0],
            "coast_frac": [0.0, 0.0, 0.0],
            "full_throttle_frac": [0.4, 0.4, 0.4],
        }
    )
    collapsed = collapse_to_driver_lap_typology(long_df)
    assert len(collapsed) == 2
    by_typ = collapsed.set_index("typology")
    assert by_typ.loc["slow", "brake_point_rel"] == pytest.approx(15.0)
    assert by_typ.loc["fast", "brake_point_rel"] == pytest.approx(100.0)
    assert int(by_typ.loc["slow", "n_zones"]) == 2

    agg = aggregate_driver_style_features(collapsed, method="median")
    # Median of {15, 100} = 57.5, not median of {10, 20, 100} = 20 (Number inflation).
    assert agg.loc["VER", "brake_point_rel"] == pytest.approx(57.5)


def test_trail_brake_frac_apex_only_early_braker_neq_late_trail():
    """Early braker who releases before the apex is not a late trailer."""
    distances = np.linspace(100.0, 500.0, 81)
    speed = 200.0 - np.abs(distances - 300.0) * 0.4
    throttle = np.where(distances >= 340.0, 80.0, 0.0)

    def _tel(brake_from, brake_to):
        brake = (distances >= brake_from) & (distances <= brake_to)
        return pd.DataFrame(
            {
                "Distance": distances,
                "Speed": speed,
                "Brake": brake,
                "Throttle": throttle,
                "TimeDelta": np.full(len(distances), 0.05),
                "ThrottleRate": 0.0,
            }
        )

    zones = {
        "T1": {
            **disjoint_zone_bounds(300.0, 200.0, 60.0, 60.0, 150.0, track_length=None),
            "apex_distance": 300.0,
            "typology": "slow",
            "track_length": None,
            "corner_number": 1,
        }
    }
    early = extract_style_features_from_telemetry(_tel(150.0, 230.0), zones)[0]
    late = extract_style_features_from_telemetry(_tel(180.0, 330.0), zones)[0]

    assert early["trail_brake_frac"] == pytest.approx(0.0, abs=0.05)
    assert late["trail_brake_frac"] > 0.25
    assert early["trail_brake_frac"] < late["trail_brake_frac"] - 0.2
    assert early["brake_point_rel"] > late["brake_point_rel"]


def test_select_k_aborts_when_valid_pool_empty():
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(5, 2)), columns=["a", "b"])
    with pytest.raises(InvalidKPoolError, match="min_cluster_size"):
        select_k_rule_based(
            X, k_min=2, k_max=4, min_cluster_size=3, n_seeds=2
        )


def test_missing_canonical_pick_fails_closed():
    class _LapsWithoutAccurate:
        def __init__(self, df):
            self._df = df
            self.empty = False
            self.columns = df.columns

        def pick_wo_box(self):
            return self

        def pick_not_deleted(self):
            return self

        def pick_track_status(self, *args, **kwargs):
            return self

    df = _fake_laps_table()._df
    with pytest.raises(MissingCanonicalPickError, match="pick_accurate"):
        filter_canonical_laps(_LapsWithoutAccurate(df), require_accurate=True)


# ---------------------------------------------------------------------------
# Sigma statistical validation (driver bootstrap, ΔARI, residualization)
# ---------------------------------------------------------------------------

def _two_blob_driver_features(n_per_blob=8, seed=11):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame(
        np.vstack(
            [
                rng.normal(0, 0.2, size=(n_per_blob, 3)),
                rng.normal(5, 0.2, size=(n_per_blob, 3)),
            ]
        ),
        columns=["brake_point_rel", "apex_speed_rel", "throttle_attack"],
        index=[f"D{i:02d}" for i in range(2 * n_per_blob)],
    )
    return X


def test_driver_bootstrap_returns_finite_ari():
    """Leave-one-out / resample *drivers* (n_eff ≈ n_drivers), not seeds only."""
    X = _two_blob_driver_features()
    result = kmeans_driver_bootstrap_stability(X, n_clusters=2, n_boot=None, random_state=0)
    assert np.isfinite(result["mean_ari"])
    assert np.isfinite(result["std_ari"])
    assert result["std_ari"] >= 0.0
    assert result["n_eff"] == len(X)
    assert result["n_eff"] == result.get("n_drivers", result["n_eff"])
    assert -1.0 <= result["mean_ari"] <= 1.0
    seed_mean, seed_std = kmeans_seed_stability(X, n_clusters=2, n_seeds=4)
    assert np.isfinite(seed_mean)
    assert seed_std >= 0.0


def test_driver_loo_stability_returns_finite_ari():
    X = _two_blob_driver_features(n_per_blob=6)
    result = kmeans_driver_bootstrap_stability(
        X, n_clusters=2, method="loo", random_state=1
    )
    assert np.isfinite(result["mean_ari"])
    assert result["n_eff"] == len(X)
    assert result["method"] == "loo"


def test_mean_vs_median_kmeans_ari_is_numeric():
    """Same session/filters; median vs mean aggregation; ARI with aligned k."""
    rng = np.random.default_rng(7)
    rows = []
    for i in range(12):
        driver = f"D{i:02d}"
        centre = 0.0 if i < 6 else 8.0
        vals = rng.normal(centre, 0.4, size=5)
        if i % 2 == 0:
            vals = np.array([*vals[:4], vals[3] + 25.0])
        for lap, v in enumerate(vals):
            rows.append(
                {
                    "Driver": driver,
                    "LapNumber": lap,
                    "typology": "slow",
                    "brake_point_rel": float(v),
                    "trail_brake_frac": 0.2 + 0.01 * i,
                    "apex_speed_rel": centre + 0.1 * lap,
                    "throttle_attack": 5.0,
                    "coast_frac": 0.1,
                    "full_throttle_frac": 0.4,
                }
            )
    long_df = pd.DataFrame(rows)
    med = aggregate_driver_style_features(long_df, method="median")
    mean = aggregate_driver_style_features(long_df, method="mean")
    numeric = [
        c
        for c in med.columns
        if c not in ("Team", "n_laps", "LapsCount", "aggregator", "Compound", "TyreLife")
    ]
    result = mean_median_kmeans_ari(med[numeric], mean[numeric], n_clusters=2)
    assert "ari" in result
    assert np.isfinite(result["ari"])
    assert -1.0 <= result["ari"] <= 1.0
    assert result["k"] == 2


def test_residualize_or_declaration_does_not_crash():
    """Team FE when present; declaration always lists residual confounders."""
    df = pd.DataFrame(
        {
            "brake_point_rel": [10.0, 14.0, 0.0, 4.0, 1.0],
            "apex_speed_rel": [1.0, 3.0, 2.0, 4.0, 0.5],
        },
        index=["A", "B", "C", "D", "E"],
    )
    meta = pd.DataFrame(
        {
            "Team": ["T1", "T1", "T2", "T2", "T3"],
            "Compound": ["SOFT", "SOFT", "MEDIUM", "HARD", "SOFT"],
            "TyreLife": [5.0, 8.0, 12.0, 4.0, 6.0],
        },
        index=df.index,
    )
    out = residualize_team_tyre_features(df, meta)
    assert out.shape == df.shape
    assert list(out.columns) == list(df.columns)
    assert not out.isna().any().any()
    decl = out.attrs.get("confounding_declaration") or confounding_declaration()
    assert "fuel" in str(decl).lower()
    assert "setup" in str(decl).lower()
    # Singleton T3 is not absorbed; T1 teammate-relative around team mean.
    assert out.loc["A", "brake_point_rel"] == pytest.approx(-2.0, abs=1.5)

    empty_meta = residualize_team_tyre_features(df, None)
    assert empty_meta.shape == df.shape
    decl2 = empty_meta.attrs.get("confounding_declaration") or confounding_declaration()
    assert decl2 is not None

    numeric, meta_sep = separate_metadata(
        pd.concat([df, meta], axis=1)
    )
    residualize_team_tyre_features(numeric, meta_sep)
    _ = confounding_declaration()
