"""BIC selection for a Gaussian mixture. K-means stays the default."""

import inspect

import numpy as np
import pandas as pd

import f1_style_clustering.pipeline as pipeline_mod
from f1_style_clustering.analysis.gmm_select import (
    COVARIANCE_TYPES,
    K_MAX,
    K_MIN,
    N_INIT,
    N_REPLICATES,
    POSTERIOR_MAX_BELOW,
    REG_COVAR,
    SEED,
    adjusted_rand,
    bic_gain,
    choose_bic,
    copula_scaled_draw,
    describe_component,
    driver_posterior,
    fraction_max_posterior_below,
    null_gain_summary,
    posterior_entropy,
    render_report,
    select_gmm,
)
from f1_style_clustering.analysis.triple_null import N_REPLICATES as TRIPLE_N
from f1_style_clustering.config import load_config
from f1_style_clustering.season import season_exclude_columns


def test_rule_is_fixed_before_any_race():
    assert COVARIANCE_TYPES == ("full", "diag")
    assert K_MIN == 1
    assert K_MAX == 7
    assert N_INIT == 20
    assert SEED == 42
    assert REG_COVAR == 1e-6
    assert POSTERIOR_MAX_BELOW == 0.8
    assert N_REPLICATES == 50
    assert N_REPLICATES == TRIPLE_N


def test_choice_keeps_k1_and_breaks_ties_by_smaller_k_then_full():
    rows = [
        {"covariance_type": "diag", "k": 3, "bic": 1.0, "converged": True},
        {"covariance_type": "full", "k": 1, "bic": 1.0, "converged": True},
        {"covariance_type": "diag", "k": 1, "bic": 1.0, "converged": True},
        {"covariance_type": "full", "k": 4, "bic": -5.0, "converged": False},
    ]
    chosen = choose_bic(rows)
    assert chosen["k"] == 1
    assert chosen["covariance_type"] == "full"
    assert bic_gain(1.0, 1.0) == 0.0
    assert bic_gain(4.0, 7.0) == 3.0


def test_one_gaussian_keeps_k1_and_two_blobs_do_not():
    rng = np.random.default_rng(0)
    cloud = rng.normal(size=(240, 2))
    single = select_gmm(cloud, k_max=3, n_init=2, random_state=0)
    assert single["k"] == 1
    assert single["gain"] == 0.0
    assert single["entropy"] == 0.0
    assert single["frac_max_below"] == 0.0
    left = rng.normal(loc=-8.0, size=(120, 2))
    right = rng.normal(loc=8.0, size=(120, 2))
    mixed = np.vstack([left, right])
    two = select_gmm(mixed, k_max=3, n_init=2, random_state=0)
    assert two["k"] > 1
    assert two["gain"] > 0.0
    assert two["means"].shape == (two["k"], 2)
    assert two["covariance_type"] in COVARIANCE_TYPES


def test_zero_column_stays_in_the_component_mean():
    rng = np.random.default_rng(1)
    values = np.column_stack([rng.normal(size=50), np.zeros(50)])
    fitted = select_gmm(values, k_max=2, n_init=1, random_state=0)
    assert fitted["means"].shape[1] == 2
    axis = describe_component(fitted["means"][0], np.diag(fitted["covariances"][0]), ["slow__a", "fast__b"])
    assert axis["feature"] in {"slow__a", "fast__b"}
    assert "Driver" not in axis


def test_entropy_and_the_strict_posterior_cutoff():
    certain = np.array([[1.0, 0.0], [0.0, 1.0]])
    assert posterior_entropy(certain) == 0.0
    uniform = np.array([[0.5, 0.5]])
    assert posterior_entropy(uniform) == np.log(2.0)
    proba = np.array([[0.79, 0.21], [0.8, 0.2], [0.81, 0.19]])
    assert fraction_max_posterior_below(proba, POSTERIOR_MAX_BELOW) == 1.0 / 3.0


def test_driver_rows_use_the_posterior_mass():
    proba = np.array([[0.9, 0.1], [0.25, 0.75], [1.0, 0.0]])
    table = driver_posterior(["HAM", "HAM", "LEC"], proba)
    ham = table[table["Driver"] == "HAM"]
    assert float(ham.loc[ham["component"] == 0, "posterior"].iloc[0]) == 1.15
    assert float(ham["posterior"].sum()) == 2.0
    assert int(ham.loc[ham["component"] == 0, "n_argmax"].iloc[0]) == 1


def test_ari_is_one_for_the_same_partition_and_missing_without_kmeans():
    assert adjusted_rand([0, 0, 1, 1], [1, 1, 0, 0]) == 1.0
    assert adjusted_rand([0, 0, 1, 1], None) is None


def test_null_gain_uses_the_strict_percentile_and_counts_k_above_one():
    summary = null_gain_summary(1.5, [0.0, 0.2, 0.4, 3.0], [1, 1, 2, 2])
    assert summary["frac_k_above_1"] == 0.5
    assert summary["beats_p95"] is False
    above = null_gain_summary(4.0, [0.0, 0.2, 0.4, 3.0], [1, 1, 1, 1])
    assert above["beats_p95"] is True
    assert above["frac_k_above_1"] == 0.0
    tied = null_gain_summary(1.0, [1.0, 1.0, 1.0, 1.0], [1, 1, 1, 1])
    assert tied["beats_p95"] is False


def test_copula_draw_keeps_a_stacked_column_constant_after_scaling():
    frame = pd.DataFrame(
        {
            "slow__a": np.linspace(-1.0, 1.0, 30),
            "fast__coast_frac": np.ones(30),
        }
    )
    drawn = copula_scaled_draw(frame, np.random.default_rng(0))
    assert list(drawn.columns) == ["slow__a", "fast__coast_frac"]
    assert drawn["fast__coast_frac"].nunique() == 1


def test_report_splits_declared_rules_from_measured_numbers():
    payload = {
        "races": [
            {
                "name": "Italia",
                "n_laps": 10,
                "n_features": 2,
                "k": 1,
                "covariance_type": "diag",
                "bic": 12.5,
                "bic_k1": 12.5,
                "gain": 0.0,
                "entropy": 0.0,
                "frac_max_below": 0.0,
                "ari": 0.12,
                "kmeans_k": 3,
                "gaussian": {"frac_k_above_1": 0.0, "p95": 1.0, "percentile": 40.0, "beats_p95": False, "n": 50},
                "gaussian_copula": {"frac_k_above_1": 0.2, "p95": 2.0, "percentile": 10.0, "beats_p95": False, "n": 50},
                "components": [],
            }
        ]
    }
    text = render_report(payload)
    assert "## Declarado" in text
    assert "## Medido" in text
    assert "full" in text and "diag" in text
    assert "K=1" in text or "K = 1" in text
    assert "0,8" in text or "0.8" in text
    assert "Italia" in text
    assert "0.12" in text
    assert "agresiv" not in text.lower()
    measured = text.split("## Medido", 1)[1].lower()
    assert "reputación" not in measured


def test_kmeans_and_the_vector_stay_untouched():
    source = inspect.getsource(pipeline_mod)
    assert "gmm_select" not in source
    assert "fit_kmeans" in source
    cfg = load_config()
    assert season_exclude_columns(cfg) == ["fast__brake_point_rel"]
    assert "brake_point_rel" in (cfg.get("features") or {}).get("metrics", [])
