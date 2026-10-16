"""Continuous lap profile. K-means stays the default path."""

import inspect

import numpy as np
import pandas as pd

import f1_style_clustering.pipeline as pipeline_mod

from f1_style_clustering.analysis.continuous_profile import (
    INTERVAL_QUANTILES,
    LOADING_SEED,
    MIN_SHARED_FEATURES,
    N_LOADING_BOOT,
    N_PARALLEL,
    N_PROFILE_BOOT,
    N_TEAM_PERM,
    PARALLEL_QUANTILE,
    PARALLEL_SEED,
    PROFILE_SEED,
    TEAM_SEED,
    align_component_signs,
    bootstrap_loadings,
    bootstrap_stratified_median,
    describe_axis,
    distance_is_closer,
    driver_score_profiles,
    match_and_align,
    n_components_parallel,
    pairwise_congruence,
    parallel_analysis,
    render_report,
    resample_stratified,
    run_race_profile,
    scale_lap_matrix,
    shared_feature_congruence,
    teammate_distance_against_random,
    teammate_mean_distance,
    tucker_congruence,
)
from f1_style_clustering.config import load_config
from f1_style_clustering.season import season_exclude_columns


def test_counts_are_the_ones_already_used_in_the_repo():
    """50 is the season null. 200 is column_null_bundle. 2000 is the baseline interval."""
    assert N_PARALLEL == 50
    assert PARALLEL_SEED == 42
    assert PARALLEL_QUANTILE == 0.95
    assert N_LOADING_BOOT == 200
    assert LOADING_SEED == 42
    assert N_PROFILE_BOOT == 2000
    assert PROFILE_SEED == 42
    assert INTERVAL_QUANTILES == (0.025, 0.975)
    assert N_TEAM_PERM == 50
    assert TEAM_SEED == 42
    assert MIN_SHARED_FEATURES == 2


def test_sequential_rule_stops_at_the_first_component_inside_the_null():
    observed = np.array([5.0, 1.0, 4.0])
    null = np.tile(np.array([2.0, 2.0, 2.0]), (10, 1))
    assert n_components_parallel(observed, null) == 1
    assert n_components_parallel(np.array([5.0, 4.0, 3.0]), null) == 3
    assert n_components_parallel(np.array([1.0, 5.0]), null[:, :2]) == 0
    tied = np.tile(np.array([5.0, 5.0]), (8, 1))
    assert n_components_parallel(np.array([5.0, 9.0]), tied) == 0


def test_parallel_analysis_keeps_only_the_duplicated_axis():
    rng = np.random.default_rng(0)
    base = rng.normal(size=180)
    frame = pd.DataFrame(
        {
            "slow__a": base,
            "medium__a": base.copy(),
            "fast__b": rng.normal(scale=0.05, size=180),
        }
    )
    result = parallel_analysis(frame, n_perm=40, seed=0)
    assert result["n_components"] == 1
    assert result["n_components"] == n_components_parallel(result["eigenvalues"], result["null_eigenvalues"])
    assert list(result["loadings"].index) == ["slow__a", "medium__a", "fast__b"]
    assert result["loadings"].shape[1] == 1
    lead = describe_axis(result["loadings"].iloc[:, 0])
    assert lead["feature"] in {"slow__a", "medium__a"}
    assert lead["sign"] == 1
    ratios = result["explained_variance_ratio"]
    assert len(ratios) == 1
    assert 0.0 < ratios[0] <= 1.0


def test_scale_keeps_a_zero_iqr_column():
    frame = pd.DataFrame(
        {
            "Driver": ["A", "A", "B", "B"],
            "LapNumber": [1, 2, 1, 2],
            "Compound": ["SOFT", "HARD", "SOFT", "HARD"],
            "slow__brake_point_rel": [1.0, 2.0, 3.0, 4.0],
            "fast__coast_frac": [0.2, 0.2, 0.2, 0.2],
        }
    )
    scaled, meta = scale_lap_matrix(frame, scaler_type="robust")
    assert list(scaled.columns) == ["slow__brake_point_rel", "fast__coast_frac"]
    assert "fast__brake_point_rel" not in scaled.columns
    assert meta["Driver"].tolist() == ["A", "A", "B", "B"]
    assert (scaled["fast__coast_frac"] == 0.0).all()


def test_sign_alignment_and_component_match():
    reference = np.array([[1.0, 0.0], [0.0, 1.0]])
    flipped = np.array([[-1.0, 0.0], [0.0, -0.5]])
    aligned = align_component_signs(reference, flipped)
    assert np.allclose(aligned, [[1.0, 0.0], [0.0, 0.5]])
    swapped = np.array([[0.0, -1.0], [-1.0, 0.0]])
    matched = match_and_align(reference, swapped)
    assert np.allclose(matched, reference)


def test_tucker_congruence_on_shared_features_only():
    assert tucker_congruence([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert tucker_congruence([1.0, 0.0], [-1.0, 0.0]) == -1.0
    assert tucker_congruence([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert np.isnan(tucker_congruence([1.0, 0.0], [1.0]))
    assert np.isnan(tucker_congruence([0.0, 0.0], [1.0, 0.0]))
    left = pd.Series({"slow__a": 1.0, "medium__b": 0.0, "fast__c": 0.5})
    right = pd.Series({"medium__b": 0.0, "fast__c": -0.5, "slow__d": 3.0})
    shared = shared_feature_congruence(left, right)
    assert shared["defined"] is True
    assert shared["n_shared"] == 2
    assert shared["features"] == ["fast__c", "medium__b"]
    assert shared["congruence"] == 1.0
    only_one = shared_feature_congruence(pd.Series({"slow__a": 1.0}), pd.Series({"slow__a": 1.0, "fast__b": 2.0}))
    assert only_one["defined"] is False
    assert np.isnan(only_one["congruence"])


def test_stratified_resample_keeps_each_compound_count():
    compounds = np.array(["SOFT", "SOFT", "HARD", "HARD", "HARD"])
    rng = np.random.default_rng(1)
    drawn = resample_stratified(compounds, rng)
    assert len(drawn) == 5
    assert sorted(compounds[drawn].tolist()) == ["HARD", "HARD", "HARD", "SOFT", "SOFT"]


def test_stratified_median_interval_uses_the_declared_percentiles():
    values = np.array([1.0, 2.0, 100.0, 3.0])
    compounds = np.array(["SOFT", "SOFT", "HARD", "HARD"])
    interval = bootstrap_stratified_median(values, compounds, n_boot=300, seed=42)
    assert interval["n"] == 4
    assert interval["median"] == 2.5
    assert interval["low"] <= interval["median"] <= interval["high"]
    assert interval["n_by_compound"] == {"HARD": 2, "SOFT": 2}
    empty = bootstrap_stratified_median([], [], n_boot=10, seed=42)
    assert empty["n"] == 0
    assert empty["median"] is None


def test_driver_profile_is_the_median_of_lap_scores():
    scores = pd.DataFrame({"PC1": [1.0, 3.0, 10.0, 0.0], "PC2": [5.0, 5.0, 1.0, 1.0]})
    drivers = ["HAM", "HAM", "LEC", "LEC"]
    compounds = ["SOFT", "HARD", "SOFT", "SOFT"]
    profiles = driver_score_profiles(scores, drivers, compounds, n_boot=100, seed=42)
    ham = profiles[(profiles["Driver"] == "HAM") & (profiles["component"] == "PC1")].iloc[0]
    assert ham["n"] == 2
    assert ham["median"] == 2.0
    assert ham["low"] <= ham["median"] <= ham["high"]
    assert ham["n_by_compound"] == {"HARD": 1, "SOFT": 1}
    lec = profiles[(profiles["Driver"] == "LEC") & (profiles["component"] == "PC2")].iloc[0]
    assert lec["median"] == 1.0


def test_loading_bootstrap_aligns_signs():
    rng = np.random.default_rng(0)
    base = rng.normal(size=80)
    frame = pd.DataFrame({"slow__a": base, "medium__a": base + rng.normal(scale=0.01, size=80)})
    fitted = parallel_analysis(frame, n_perm=20, seed=1)
    intervals = bootstrap_loadings(frame, fitted["loadings"], n_boot=25, seed=2)
    assert set(intervals["component"]) == {"PC1"}
    assert set(intervals["feature"]) == {"slow__a", "medium__a"}
    assert (intervals["low"] <= intervals["loading"]).all()
    assert (intervals["loading"] <= intervals["high"]).all()
    assert (intervals["loading"] >= 0).all()


def test_teammate_distance_uses_team_name_and_the_strict_lower_tail():
    profile = pd.DataFrame(
        {
            "Driver": ["HAM", "LEC", "NOR", "PIA"],
            "PC1": [0.0, 0.0, 10.0, 10.0],
            "PC2": [0.0, 0.0, 0.0, 0.0],
        }
    )
    teams = pd.Series({"HAM": "Ferrari", "LEC": "Ferrari", "NOR": "McLaren", "PIA": "McLaren"})
    measured = teammate_mean_distance(profile, teams)
    assert measured["n_pairs"] == 2
    assert measured["mean_distance"] == 0.0
    assert {row["TeamName"] for row in measured["pairs"]} == {"Ferrari", "McLaren"}
    assert distance_is_closer(0.1, np.array([1.0, 1.0, 1.0, 1.0])) is True
    assert distance_is_closer(1.0, np.array([1.0, 1.0, 1.0, 1.0])) is False


def test_same_index_congruence_aligns_the_sign_and_skips_a_missing_axis():
    left = pd.DataFrame({"PC1": [1.0, 0.0]}, index=["slow__a", "fast__b"])
    right = pd.DataFrame({"PC1": [-1.0, 0.0], "PC2": [0.0, 1.0]}, index=["slow__a", "fast__b"])
    table = pairwise_congruence({"Italia": left, "Bélgica": right})
    assert len(table) == 1
    assert table.iloc[0]["component"] == "PC1"
    assert table.iloc[0]["congruence"] == 1.0
    assert table.iloc[0]["n_shared"] == 2


def test_random_reassignment_uses_the_same_closer_rule():
    profile = pd.DataFrame(
        {
            "Driver": ["HAM", "LEC", "NOR", "PIA"],
            "PC1": [0.0, 0.0, 8.0, 8.0],
        }
    )
    teams = pd.Series({"HAM": "Ferrari", "LEC": "Ferrari", "NOR": "McLaren", "PIA": "McLaren"})
    result = teammate_distance_against_random(profile, teams, n_perm=30, seed=0)
    assert result["mean_distance"] == 0.0
    assert result["n_pairs"] == 2
    assert result["n_perm"] == 30
    assert result["closer"] is distance_is_closer(result["mean_distance"], result["null_distances"])


def test_race_profile_keeps_every_scaled_column():
    rng = np.random.default_rng(0)
    base = rng.normal(size=40)
    frame = pd.DataFrame(
        {
            "Driver": ["HAM"] * 40 + ["LEC"] * 40,
            "LapNumber": list(range(40)) * 2,
            "Compound": (["SOFT"] * 20 + ["HARD"] * 20) * 2,
            "slow__a": np.concatenate([base, base]),
            "medium__a": np.concatenate([base, base]),
            "fast__coast_frac": np.zeros(80),
        }
    )
    teams = pd.Series({"HAM": "Ferrari", "LEC": "Ferrari"})
    result = run_race_profile(
        frame,
        teams,
        n_perm=15,
        n_loading=8,
        n_profile=20,
        n_team=10,
        seed=0,
    )
    assert result["features"] == ["slow__a", "medium__a", "fast__coast_frac"]
    assert result["n_laps"] == 80
    assert result["n_components"] == 1
    assert {row["Driver"] for row in result["profiles"]} == {"HAM", "LEC"}


def test_axis_text_uses_the_loading_not_a_driver():
    axis = describe_axis(pd.Series({"slow__brake_point_rel": -0.8, "fast__coast_frac": 0.1}))
    assert axis["feature"] == "slow__brake_point_rel"
    assert axis["sign"] == -1
    assert axis["loading"] == -0.8
    assert "Driver" not in axis


def test_report_keeps_the_declared_rule_apart_from_measured_numbers():
    payload = {
        "races": [
            {
                "event": "Italian Grand Prix",
                "name": "Italia",
                "n_laps": 12,
                "n_features": 2,
                "features": ["slow__a", "fast__b"],
                "n_components": 1,
                "explained_variance_ratio": [0.42],
                "cumulative_variance": 0.42,
                "eigenvalues": [1.5],
                "null_p95": [0.9],
                "retained": [True],
                "loadings": [
                    {"feature": "slow__a", "PC1": 0.91},
                    {"feature": "fast__b", "PC1": -0.41},
                ],
                "axes": [{"component": "PC1", "feature": "slow__a", "loading": 0.91, "sign": 1}],
                "teammates": {
                    "n_pairs": 2,
                    "mean_distance": 0.33,
                    "null_p05": 0.8,
                    "percentile": 4.0,
                    "closer": True,
                },
            }
        ],
        "congruence_summary": {"n_pairs": 0, "median": None},
        "baseline": {
            "brake_point": {
                "compounds": [
                    {
                        "compound": "MEDIUM",
                        "HAM_LEC": {"reading": "no_evidence", "left": {"n": 3, "median": -0.5, "low": -1.0, "high": 0.2}, "right": {"n": 3, "median": -1.2, "low": -2.0, "high": -0.1}},
                    }
                ]
            },
            "release": {
                "HAM_LEC": {"reading": "no_evidence", "left": {"n": 4, "median": 79.0, "low": 74.0, "high": 81.0}, "right": {"n": 4, "median": 80.0, "low": 77.0, "high": 82.0}},
            },
        },
    }
    text = render_report(payload)
    assert "## Declarado" in text
    assert "## Medido" in text
    assert "percentil 95" in text
    assert "secuencial" in text
    assert "fast__brake_point_rel" in text
    assert "0.42" in text
    assert "Italia" in text
    assert "no hay evidencia" in text
    assert "agresiv" not in text.lower()
    assert "reputación" not in text.split("## Medido", 1)[1].lower()


def test_exploratory_pair_is_printed_when_the_baseline_pair_is_absent():
    payload = {
        "races": [],
        "congruence_summary": {"n_pairs": 0, "median": None},
        "baseline": {
            "clean_air": {"n_clean": 173, "n_not_clean": 16, "n_excluded_no_onset": 0},
            "brake_point": {
                "compounds": [
                    {
                        "compound": "SOFT",
                        "NOR_PIA": {
                            "reading": "exploratory",
                            "left": {"n": 4, "median": -17.3, "low": -20.0, "high": -3.4},
                            "right": {"n": 5, "median": 9.6, "low": 3.0, "high": 23.5},
                        },
                    }
                ]
            },
            "release": {
                "NOR_PIA": {
                    "reading": "exploratory",
                    "left": {"n": 48, "median": 82.0, "low": 78.1, "high": 85.5},
                    "right": {"n": 48, "median": 85.2, "low": 83.5, "high": 88.8},
                }
            },
        },
    }
    text = render_report(payload)
    assert "SOFT" in text
    assert "173" in text
    assert "Norris" in text
    assert "Piastri" in text
    assert "exploratorio" in text


def test_kmeans_stays_the_default_and_the_season_vector_is_unchanged():
    source = inspect.getsource(pipeline_mod)
    assert "continuous_profile" not in source
    assert "fit_kmeans" in source
    from f1_style_clustering.analysis import continuous_profile as continuous_mod

    continuous_source = inspect.getsource(continuous_mod)
    assert "KMeans" not in continuous_source
    assert "fit_kmeans" not in continuous_source
    cfg = load_config()
    assert season_exclude_columns(cfg) == ["fast__brake_point_rel"]
    metrics = (cfg.get("features") or {}).get("metrics") or []
    assert "brake_point_rel" in metrics
