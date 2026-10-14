"""Three nulls, exact 0/1 shares, and the baseline interval rule."""

import numpy as np
import pandas as pd

from f1_style_clustering.analysis.baseline_predictions import (
    bootstrap_median_interval,
    clean_air_before_onset,
    interval_verdict,
    last_brake_release_distance,
    release_distance_to_apex,
)
from f1_style_clustering.analysis.triple_null import (
    N_REPLICATES,
    _null_record,
    column_value_shares,
    gaussian_copula_draw,
    gaussian_draw,
    run_triple_null,
    run_without_zero_iqr,
    shares_before_session_median,
)


def _tiny_config():
    return {
        "general": {"random_state": 0},
        "features": {"standardization": "robust"},
        "dimensionality_reduction": {"pca": {"variance_threshold": 0.85}},
        "clustering": {
            "kmeans": {"k_range": [2, 3], "n_init": 2},
            "seed_stability_n": 2,
            "silhouette_threshold": 0.25,
        },
    }


def test_replicate_count_is_fixed_at_50():
    assert N_REPLICATES == 50


def test_equal_null_does_not_beat_p95():
    record = _null_record([1.0, 1.0, 1.0, 1.0], 1.0)
    assert record["beats_p95"] is False
    assert record["p95"] == 1.0


def test_column_shares_count_exact_zero_and_one():
    frame = pd.DataFrame(
        {
            "Driver": ["A", "A", "A", "A"],
            "slow__brake_point_rel": [0.0, 0.0, 0.0, 2.0],
            "fast__coast_frac": [1.0, 1.0, 1.0, 1.0],
        }
    )
    shares = column_value_shares(frame).set_index("column")
    assert shares.loc["slow__brake_point_rel", "frac_0"] == 0.75
    assert shares.loc["slow__brake_point_rel", "frac_1"] == 0.0
    assert bool(shares.loc["fast__coast_frac", "zero_iqr"]) is True
    assert shares.loc["fast__coast_frac", "frac_1"] == 1.0


def test_copula_keeps_observed_values_and_identical_columns():
    rng = np.random.default_rng(0)
    base = rng.normal(size=40)
    other = rng.choice([0.0, 1.0, 3.0], size=40)
    frame = pd.DataFrame(
        {
            "slow__a": base,
            "fast__a": base.copy(),
            "medium__b": other,
            "slow__c": np.ones(40),
        }
    )
    drawn = gaussian_copula_draw(frame, np.random.default_rng(1))
    assert np.array_equal(drawn["slow__a"].to_numpy(), drawn["fast__a"].to_numpy())
    assert set(np.unique(drawn["medium__b"])).issubset(set(np.unique(other)))
    assert set(np.unique(drawn["slow__a"])).issubset(set(np.unique(base)))
    assert (drawn["slow__c"] == 1.0).all()


def test_gaussian_draw_matches_the_fit_shape():
    fit = pd.DataFrame(
        np.random.default_rng(0).normal(size=(25, 3)),
        columns=["PC1", "PC2", "PC3"],
    )
    drawn = gaussian_draw(fit, np.random.default_rng(1))
    assert drawn.shape == fit.shape
    assert np.isfinite(drawn.to_numpy()).all()


def test_shares_before_session_median_use_the_typology_name():
    long_df = pd.DataFrame(
        {
            "Driver": ["A", "A"],
            "LapNumber": [1, 1],
            "typology": ["fast", "fast"],
            "coast_frac": [0.0, 0.0],
            "full_throttle_frac": [0.0, 1.0],
        }
    )
    shares = shares_before_session_median(long_df).set_index("column")
    assert shares.loc["fast__coast_frac", "frac_0"] == 1.0
    assert shares.loc["fast__full_throttle_frac", "n"] == 1


def test_interval_rule_is_strict():
    assert interval_verdict(1, 2, 3, 4, predicted_a_below_b=True) == "confirmed"
    assert interval_verdict(3, 4, 1, 2, predicted_a_below_b=True) == "contradicted"
    assert interval_verdict(1, 3, 3, 5, predicted_a_below_b=True) == "no_evidence"
    assert interval_verdict(1, 2.5, 2, 4, predicted_a_below_b=True) == "no_evidence"
    assert interval_verdict(None, 1, 2, 3, predicted_a_below_b=True) == "no_evidence"


def test_bootstrap_interval_uses_the_median():
    interval = bootstrap_median_interval([1.0, 2.0, 100.0], n_boot=200, seed=42)
    assert interval["n"] == 3
    assert interval["median"] == 2.0
    assert interval["low"] <= interval["median"] <= interval["high"]


def test_release_is_the_last_on_to_off_sample():
    fragment = pd.DataFrame(
        {
            "Distance": [0.0, 10.0, 20.0, 30.0, 40.0],
            "Brake": [True, True, False, True, False],
        }
    )
    assert last_brake_release_distance(fragment) == 40.0
    assert release_distance_to_apex(fragment, 100.0, 1000.0) == 60.0
    never = fragment.copy()
    never["Brake"] = True
    assert np.isnan(last_brake_release_distance(never))


def test_clean_air_uses_the_150m_before_onset():
    telemetry = pd.DataFrame(
        {
            "Distance": [100.0, 150.0, 190.0, 200.0],
            "DistanceToDriverAhead": [80.0, 40.0, 10.0, 5.0],
        }
    )
    assert clean_air_before_onset(telemetry, 200.0, 1000.0) is False
    clear = telemetry.copy()
    clear["DistanceToDriverAhead"] = [np.nan, np.nan, np.nan, 1.0]
    assert clean_air_before_onset(clear, 200.0, 1000.0) is True
    far = telemetry.copy()
    far["DistanceToDriverAhead"] = [80.0, 60.0, 50.0, 1.0]
    assert clean_air_before_onset(far, 200.0, 1000.0) is True


def test_triple_null_reports_three_percentiles():
    rng = np.random.default_rng(0)
    block = np.vstack([rng.normal(0, 0.2, size=(30, 4)), rng.normal(4, 0.2, size=(30, 4))])
    frame = pd.DataFrame(
        block,
        columns=[
            "slow__brake_point_rel",
            "fast__coast_frac",
            "medium__apex_speed_rel",
            "slow__trail_brake_frac",
        ],
    )
    result = run_triple_null(frame, _tiny_config(), n_replicates=2, seed=0)
    assert result["error"] is None
    assert result["n_replicates"] == 2
    for name in ("column_permutation", "gaussian", "gaussian_copula"):
        assert "percentile" in result["nulls"][name]
        assert "p95" in result["nulls"][name]
        assert "beats_p95" in result["nulls"][name]
    assert "structure" in result


def test_zero_iqr_sensitivity_skips_when_every_column_varies():
    frame = pd.DataFrame(
        {
            "slow__a": [0.0, 1.0, 2.0, 3.0],
            "fast__b": [1.0, 0.0, 1.0, 0.0],
        }
    )
    skipped = run_without_zero_iqr(frame, _tiny_config(), n_replicates=1, seed=0)
    assert skipped["skipped"] == "no IQR-0 columns"
