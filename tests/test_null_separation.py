"""Silueta real contra un nulo de columnas permutadas, y diagnóstico por columna."""

import numpy as np
import pandas as pd
import pytest
from sklearn.decomposition import PCA

from f1_style_clustering.analysis.null_separation import (
    column_diagnostics,
    driver_variance_split,
    identical_value_fraction,
    pc_feature_weights,
    percentile_of_observed,
    sensitivity_column_sets,
    separates_from_null,
    silhouette_against_column_null,
    zero_iqr_columns,
)


def test_percentile_of_observed_is_the_share_of_nulls_at_or_below():
    assert percentile_of_observed([0.0, 1.0, 2.0, 3.0], 2.0) == pytest.approx(75.0)
    assert percentile_of_observed([0.0, 1.0, 2.0, 3.0], 4.0) == pytest.approx(100.0)
    assert percentile_of_observed([0.0, 1.0, 2.0, 3.0], -1.0) == pytest.approx(0.0)
    assert np.isnan(percentile_of_observed([], 1.0))
    assert np.isnan(percentile_of_observed([1.0, np.nan], np.nan))


def test_separates_from_null_uses_a_declared_percentile_cutoff():
    assert separates_from_null(95.1) is True
    assert separates_from_null(95.0) is False
    assert separates_from_null(np.nan) is False
    assert separates_from_null(90.0, threshold=80.0) is True


def test_zero_iqr_and_identical_fraction():
    df = pd.DataFrame(
        {
            "flat": [0.0, 0.0, 0.0, 0.0, 1.0],
            "spread": [0.0, 1.0, 2.0, 3.0, 4.0],
        }
    )
    assert zero_iqr_columns(df, ["flat", "spread"]) == ["flat"]
    assert identical_value_fraction([1, 1, 1, 2]) == pytest.approx(0.75)
    assert identical_value_fraction([1, 2, 3, 4]) == pytest.approx(0.25)
    assert np.isnan(identical_value_fraction([np.nan, np.nan]))


def test_driver_variance_split_between_exceeds_within():
    values = np.array([0.0, 0.1, -0.1, 10.0, 10.1, 9.9])
    groups = np.array(["A", "A", "A", "B", "B", "B"])
    res = driver_variance_split(values, groups)
    assert res["n_drivers"] == 2
    assert res["var_between"] > 10 * res["var_within"]
    assert res["ratio_between_within"] == pytest.approx(res["var_between"] / res["var_within"])


def test_sensitivity_column_sets_drop_zero_iqr_and_near_constant():
    df = pd.DataFrame(
        {
            "Driver": ["A"] * 10,
            "keep__x": np.linspace(0, 1, 10),
            "flat__z": [0.0] * 9 + [5.0],
            "ties__y": [0.0] * 6 + [1.0, 2.0, 3.0, 4.0],
        }
    )
    sets = sensitivity_column_sets(df, ["keep__x", "flat__z", "ties__y"])
    assert "flat__z" in sets["zero_iqr"]
    assert "flat__z" in sets["dropped"]
    assert "keep__x" in sets["kept"]
    assert "keep__x" not in sets["dropped"]


def test_pc_feature_weights_follow_the_signal_axis():
    rng = np.random.default_rng(0)
    signal = rng.normal(size=120)
    frame = pd.DataFrame(
        {
            "a": signal,
            "b": signal + rng.normal(scale=0.05, size=120),
            "c": rng.normal(size=120),
        }
    )
    centered = (frame - frame.mean()) / frame.std(ddof=0)
    pca = PCA(n_components=1, random_state=0).fit(centered)
    weights = pc_feature_weights(pca, list(centered.columns)).set_index("feature")
    assert weights.loc["a", "peso_pc_share"] > weights.loc["c", "peso_pc_share"]
    assert weights.loc["a", "peso_pc_share"] + weights.loc["b", "peso_pc_share"] > 0.85
    assert weights["peso_pc_share"].sum() == pytest.approx(1.0)
    unused = pc_feature_weights(None, ["a", "b"]).set_index("feature")
    assert unused.loc["a", "comunalidad"] == pytest.approx(1.0)
    assert unused["peso_pc_share"].sum() == pytest.approx(1.0)


def test_column_diagnostics_joins_variance_ties_and_weights():
    df = pd.DataFrame(
        {
            "Driver": ["A", "A", "A", "B", "B", "B"],
            "slow__x": [0.0, 0.1, -0.1, 5.0, 5.1, 4.9],
        }
    )
    table = column_diagnostics(df, feature_cols=["slow__x"], pca_model=None)
    row = table.iloc[0]
    assert row["feature"] == "slow__x"
    assert row["identical_frac"] == pytest.approx(1.0 / 6.0)
    assert row["var_between"] > row["var_within"]
    assert row["peso_pc_share"] == pytest.approx(1.0)
    assert bool(row["zero_iqr"]) is False


def test_silhouette_null_percentile_is_high_for_separated_blobs():
    rng = np.random.default_rng(1)
    centers = np.array(
        [
            [0.0, 0.0, 0.0, 0.0, 0.0],
            [6.0, 6.0, 6.0, 6.0, 6.0],
            [0.0, 6.0, 0.0, 6.0, 0.0],
        ]
    )
    parts = [c + rng.normal(scale=0.25, size=(30, 5)) for c in centers]
    X = pd.DataFrame(np.vstack(parts), columns=["a", "b", "c", "d", "e"])
    summary, scores = silhouette_against_column_null(
        X,
        k_range=range(2, 4),
        n_perm=12,
        random_state=0,
        n_init=5,
        max_features_direct=8,
    )
    at3 = summary.set_index("k").loc[3]
    assert at3["silhouette"] > 0.7
    assert at3["percentile"] >= 90.0
    assert at3["n_perm"] == 12
    assert len(scores[3]) == 12
    assert at3["percentile"] == pytest.approx(percentile_of_observed(scores[3], at3["silhouette"]))
    assert separates_from_null(at3["percentile"], threshold=90.0)


def test_silhouette_null_rejects_too_few_columns():
    X = pd.DataFrame({"only": np.arange(10, dtype=float)})
    with pytest.raises(ValueError):
        silhouette_against_column_null(X, k_range=range(2, 3), n_perm=1, n_init=1)
