"""Fracción de compuesto por clase y diferencia de medianas con bootstrap."""

import numpy as np
import pandas as pd

from f1_style_clustering.analysis.compound_report import (
    bootstrap_median_difference,
    compound_by_class,
    lap_size_floor,
    within_compound_median_contrasts,
)


def test_lap_size_floor_matches_the_pipeline_rule():
    assert lap_size_floor(0) == 3
    assert lap_size_floor(40) == 3
    assert lap_size_floor(842) == 43
    assert lap_size_floor(381) == 20
    assert lap_size_floor(439) == 22


def test_compound_shares_sum_to_one_inside_each_class():
    features = pd.DataFrame(
        {
            "Driver": ["A", "A", "B", "B", "C"],
            "LapNumber": [1, 2, 1, 2, 1],
            "Compound": ["HARD", "MEDIUM", "HARD", "HARD", "SOFT"],
        }
    )
    classes = pd.DataFrame(
        {
            "Driver": ["A", "A", "B", "B", "C"],
            "LapNumber": [1, 2, 1, 2, 1],
            "Cluster": [0, 0, 1, 1, 0],
            "Archetype": ["late", "late", "early", "early", "late"],
        }
    )
    table = compound_by_class(features, classes)
    assert table.attrs["n_matched"] == 5
    assert table.attrs["n_feature_only"] == 0
    shares = table.groupby("Cluster")["frac_of_class"].sum()
    assert np.allclose(shares.to_numpy(), 1.0)
    hard = table.loc[table["Compound"] == "HARD", "frac_of_compound"].sum()
    assert hard == 1.0
    late_hard = table.loc[(table["Cluster"] == 0) & (table["Compound"] == "HARD")].iloc[0]
    assert int(late_hard["n"]) == 1
    assert late_hard["frac_of_class"] == 1 / 3


def test_unmatched_laps_are_counted_and_left_out_of_the_shares():
    features = pd.DataFrame(
        {"Driver": ["A", "B"], "LapNumber": [1, 2], "Compound": ["HARD", "MEDIUM"]}
    )
    classes = pd.DataFrame(
        {
            "Driver": ["A", "C"],
            "LapNumber": [1, 9],
            "Cluster": [0, 1],
            "Archetype": ["late", "early"],
        }
    )
    table = compound_by_class(features, classes)
    assert table.attrs["n_matched"] == 1
    assert table.attrs["n_feature_only"] == 1
    assert table.attrs["n_class_only"] == 1
    assert len(table) == 1
    assert table.iloc[0]["frac_of_class"] == 1.0


def test_bootstrap_median_difference_is_zero_for_identical_samples():
    stats = bootstrap_median_difference([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0], n_boot=400, seed=1)
    assert stats["enough"] is True
    assert stats["difference"] == 0.0
    assert stats["ci_low"] <= 0.0 <= stats["ci_high"]
    assert stats["n_boot"] == 400


def test_bootstrap_interval_excludes_zero_when_the_shift_is_large():
    rng = np.random.default_rng(0)
    left = rng.normal(loc=10.0, scale=0.2, size=80)
    right = rng.normal(loc=0.0, scale=0.2, size=80)
    stats = bootstrap_median_difference(left, right, n_boot=500, seed=2)
    assert stats["difference"] > 9.0
    assert stats["ci_low"] > 0.0
    assert stats["ci_high"] > stats["ci_low"]


def test_bootstrap_stays_empty_below_the_sample_floor():
    stats = bootstrap_median_difference([1.0], [2.0, 3.0], n_boot=100, seed=0, min_n=2)
    assert stats["enough"] is False
    assert np.isnan(stats["difference"])
    assert stats["n_left"] == 1
    assert stats["n_boot"] == 0


def test_within_compound_contrasts_do_not_pool_compounds():
    features = pd.DataFrame(
        {
            "Driver": ["HAM", "HAM", "LEC", "LEC", "HAM", "LEC"],
            "LapNumber": [1, 2, 1, 2, 3, 3],
            "Compound": ["HARD", "HARD", "HARD", "HARD", "SOFT", "SOFT"],
            "slow__brake_point_rel": [1.0, 3.0, 0.0, 0.0, 100.0, -100.0],
        }
    )
    table = within_compound_median_contrasts(
        features,
        "slow__brake_point_rel",
        pairs=[("HAM", "LEC")],
        n_boot=300,
        seed=3,
    )
    hard = table.loc[table["Compound"] == "HARD"].iloc[0]
    soft = table.loc[table["Compound"] == "SOFT"].iloc[0]
    assert hard["difference"] == 2.0
    assert int(hard["n_left"]) == 2
    assert bool(hard["enough"]) is True
    assert int(soft["n_left"]) == 1
    assert bool(soft["enough"]) is False
    assert np.isnan(soft["difference"])
