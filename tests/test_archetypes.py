"""Class names follow the class medians of the style metrics, not PCA axes or driver identity."""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.analysis.archetypes import (
    UNNAMED,
    assign_archetype_names,
    class_trait_scores,
    name_classes_from_medians,
)
from f1_style_clustering.config import load_config
from f1_style_clustering.pipeline import cluster_driver_matrix

TYPOLOGIES = ("slow", "medium", "fast")


def _laps(levels, n=60, seed=0):
    """Laps of three classes; ``levels[cls][metric]`` is the class offset in IQR-ish units."""
    rng = np.random.default_rng(seed)
    scale = {"brake_point_rel": 20.0, "apex_speed_rel": 6.0, "coast_frac": 0.03, "trail_brake_frac": 0.08}
    rows, labels = [], []
    for cls, offsets in levels.items():
        for i in range(n):
            row = {"Driver": f"D{cls}{i % 3}", "LapNumber": i + 1}
            for metric, sd in scale.items():
                for typ in TYPOLOGIES:
                    row[f"{typ}__{metric}"] = offsets.get(metric, 0.0) * sd + rng.normal(0, 0.3 * sd)
            row["medium__full_throttle_frac"] = 0.0
            rows.append(row)
            labels.append(cls)
    df = pd.DataFrame(rows)
    return df, pd.Series(labels, index=df.index, name="Cluster")


MONZA_LIKE = {
    0: {"apex_speed_rel": 1.0, "brake_point_rel": -0.8},
    1: {"trail_brake_frac": 1.0, "coast_frac": -0.6},
    2: {"coast_frac": 1.2, "apex_speed_rel": -0.9, "brake_point_rel": 0.6},
}


def _style(df):
    return df[[c for c in df.columns if "__" in c]]


def _traits(name):
    return set(name.lower().split(" + "))


def test_class_that_brakes_earlier_is_never_called_late_braking():
    df, labels = _laps(MONZA_LIKE)
    names = name_classes_from_medians(_style(df), labels)
    scores = class_trait_scores(_style(df), labels)
    assert scores.loc[2, "brake_point_rel"] > 0 and scores.loc[0, "brake_point_rel"] < 0
    assert "late braking" not in names[2].lower()
    assert "more coasting" in _traits(names[2])
    assert _traits(names[0]) == {"high apex speed", "late braking"}
    assert _traits(names[1]) == {"more trail braking", "less coasting"}


def test_direction_words_follow_the_sign_of_each_median():
    df, labels = _laps({0: {"brake_point_rel": 1.5}, 1: {"brake_point_rel": -1.5}, 2: {}})
    names = name_classes_from_medians(_style(df), labels, max_traits=1)
    assert names[0] == "Early braking"
    assert names[1] == "Late braking"


def test_zero_iqr_columns_do_not_name_a_class_and_weak_classes_stay_unnamed():
    df, labels = _laps({0: {}, 1: {}, 2: {}}, seed=3)
    spike = labels[labels == 2].index[:5]
    df.loc[spike, "medium__full_throttle_frac"] = 0.5  # 5 of 180 laps: the column keeps IQR 0
    scores = class_trait_scores(_style(df), labels)
    assert "full_throttle_frac" not in scores.columns
    names = name_classes_from_medians(_style(df), labels)
    assert all(n.startswith(UNNAMED) for n in names.values())
    assert len(set(names.values())) == 3


def test_colliding_names_take_the_next_trait_then_the_class_id():
    df, labels = _laps({0: {"apex_speed_rel": 1.0, "coast_frac": 0.8, "trail_brake_frac": 0.5},
                        1: {"apex_speed_rel": 1.0, "coast_frac": 0.8, "trail_brake_frac": -0.5},
                        2: {"apex_speed_rel": -1.0}})
    names = name_classes_from_medians(_style(df), labels)
    assert names[0] != names[1]
    assert "trail braking" in names[0] and "trail braking" in names[1]
    twins, twin_labels = _laps({0: {"apex_speed_rel": 1.0}, 1: {"apex_speed_rel": 1.0}, 2: {"apex_speed_rel": -1.0}}, seed=5)
    twin_names = name_classes_from_medians(_style(twins)[[c for c in twins.columns if "apex" in c]], twin_labels)
    assert twin_names[0].endswith("(class 0)") and twin_names[1].endswith("(class 1)")


def test_pipeline_names_come_from_medians_even_when_fit_in_pca_space():
    df, truth = _laps(MONZA_LIKE, n=50)
    cfg = load_config()
    cfg["clustering"].update(min_cluster_size=10, driver_bootstrap=False, compare_aggregators=False, seed_stability_n=2)
    cfg["clustering"]["kmeans"]["k_range"] = [3, 3]
    result = cluster_driver_matrix(df, config=cfg, use_pca_fit=True, driver_bootstrap=False, compare_aggregators=False)
    assert result["pca_fit_info"]["used"]
    labels = result["cluster_labels"]
    names = result["archetype_names"]
    brake = result["class_trait_scores"]["brake_point_rel"]
    for cid, name in names.items():
        if "early braking" in name.lower():
            assert brake[cid] > 0
        if "late braking" in name.lower():
            assert brake[cid] < 0
    medians = df.groupby(labels)[[f"{t}__brake_point_rel" for t in TYPOLOGIES]].median().mean(axis=1)
    assert "late braking" not in names[int(medians.idxmax())].lower()
    assert any("late braking" in n.lower() for n in names.values())
    assert set(result["df_summary"]["Archetype"]) == set(names.values())


def test_legacy_namer_gives_no_name_on_pca_centroids():
    profiles = pd.DataFrame({"PC1": [-1.0, 1.2, 0.4], "PC2": [-0.2, -0.3, 1.1]}, index=[0, 1, 2])
    names = assign_archetype_names(profiles)
    assert names == {0: f"{UNNAMED} (class 0)", 1: f"{UNNAMED} (class 1)", 2: f"{UNNAMED} (class 2)"}


def test_same_traits_give_the_same_name_whatever_their_ranking():
    coast_first, labels_a = _laps({0: {"coast_frac": 1.4, "trail_brake_frac": -0.7}, 1: {}, 2: {"coast_frac": -1.0}})
    trail_first, labels_b = _laps({0: {"coast_frac": 0.7, "trail_brake_frac": -1.4}, 1: {}, 2: {"coast_frac": -1.0}})
    a = name_classes_from_medians(_style(coast_first), labels_a)[0]
    b = name_classes_from_medians(_style(trail_first), labels_b)[0]
    assert a == b == "Less trail braking + more coasting"


def test_names_use_no_driver_identity():
    df, labels = _laps(MONZA_LIKE)
    shuffled = df.copy()
    shuffled["Driver"] = np.random.default_rng(1).permutation(shuffled["Driver"].to_numpy())
    assert name_classes_from_medians(_style(df), labels) == name_classes_from_medians(_style(shuffled), labels)
