"""Unit tests for Pipeline B (typology×session median → driver aggregation).

These tests use synthetic telemetry only — no FastF1 network downloads.
"""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.features.zoi import (
    disjoint_zone_bounds,
    in_distance_window,
    get_corner_fragments,
    map_typology_to_bucket,
    classify_speed_typology,
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
)
from f1_style_clustering.data.filters import (
    filter_canonical_laps,
    apply_min_valid_laps,
)
from f1_style_clustering.models.evaluation import select_k_rule_based
from f1_style_clustering.models.dimensionality import pca_for_clustering
from f1_style_clustering.models.clustering import kmeans_seed_stability, dbscan_prefilter_outliers
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
        X, k_min=2, k_max=5, silhouette_threshold=0.25, min_cluster_size=3
    )
    assert k_star == 3
    assert rule == "silhouette"
    assert eval_df.loc[eval_df["k"] == 3, "min_cluster_size"].iloc[0] >= 3


def test_rule_based_k_falls_back_to_min_davies_bouldin():
    rng = np.random.default_rng(1)
    # Overlapping cloud: silhouette will be weak
    X = pd.DataFrame(rng.normal(size=(18, 2)), columns=["f1", "f2"])
    k_star, eval_df, rule = select_k_rule_based(
        X,
        k_min=2,
        k_max=4,
        silhouette_threshold=0.95,  # force DB fallback
        min_cluster_size=3,
    )
    assert rule == "davies_bouldin"
    assert k_star in set(eval_df["k"])
    pool = eval_df[eval_df["valid"]]
    if pool.empty:
        pool = eval_df.dropna(subset=["davies_bouldin"])
    chosen = pool.nsmallest(1, "davies_bouldin")["k"].iloc[0]
    assert k_star == int(chosen)


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


def test_pipeline_c_stub_is_not_main_path():
    with pytest.raises(NotImplementedError, match="appendix"):
        cluster_laps_pipeline_c(pd.DataFrame())
