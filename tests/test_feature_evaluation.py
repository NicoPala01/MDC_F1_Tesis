"""Candidate feature scoring: team / teammate / lap shares, reliability, confounders."""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.analysis.feature_evaluation import (
    clustering_gain,
    confounder_association,
    nested_variance_shares,
    phase_leakage,
    redundancy,
    score_features,
    split_half_reliability,
    teammate_split_rate,
)


@pytest.fixture
def laps():
    """Six drivers in three teams, 30 laps each.

    ``car_only``: team level, teammates equal. ``teammate``: each driver its own level.
    ``noise``: lap noise. ``tyre``: rises with tyre life only.
    """
    rng = np.random.default_rng(0)
    rows = []
    teams = {"VER": "RB", "TSU": "RB", "NOR": "MCL", "PIA": "MCL", "LEC": "FER", "HAM": "FER"}
    driver_level = {"VER": 2.0, "TSU": -2.0, "NOR": 1.0, "PIA": -1.0, "LEC": 0.5, "HAM": -0.5}
    team_level = {"RB": 3.0, "MCL": 0.0, "FER": -3.0}
    for d, t in teams.items():
        for lap in range(1, 31):
            life = lap if lap <= 15 else lap - 15
            rows.append({
                "Driver": d, "Team": t, "LapNumber": lap,
                "Compound": "MEDIUM" if lap <= 15 else "HARD", "TyreLife": life,
                "car_only": team_level[t] + rng.normal(0, 0.3),
                "teammate": driver_level[d] + rng.normal(0, 0.3),
                "noise": rng.normal(0, 1.0),
                "tyre": 0.2 * life + rng.normal(0, 0.1),
            })
    return pd.DataFrame(rows)


def test_nested_shares_separate_car_from_driver(laps):
    car = nested_variance_shares(laps["car_only"].to_numpy(), laps["Driver"].to_numpy(), laps["Team"].to_numpy())
    drv = nested_variance_shares(laps["teammate"].to_numpy(), laps["Driver"].to_numpy(), laps["Team"].to_numpy())
    noise = nested_variance_shares(laps["noise"].to_numpy(), laps["Driver"].to_numpy(), laps["Team"].to_numpy())
    assert car["share_team"] > 0.9 and car["omega2_driver_in_team"] < 0.02
    assert drv["omega2_driver_in_team"] > 0.8 and drv["p_driver_in_team"] < 1e-6
    assert abs(noise["omega2_driver_in_team"]) < 0.05 and abs(noise["omega2_team"]) < 0.05
    for res in (car, drv, noise):
        assert abs(res["share_team"] + res["share_driver_in_team"] + res["share_lap"] - 1.0) < 1e-9


def test_nested_shares_degenerate():
    res = nested_variance_shares(np.ones(10), np.array(list("aabbccddee")), np.array(list("xxxxxyyyyy")))
    assert np.isnan(res["share_team"])


def test_split_half_reliability(laps):
    keys = (laps["Driver"].to_numpy(), laps["LapNumber"].to_numpy(), laps["Team"].to_numpy())
    good = split_half_reliability(laps["teammate"].to_numpy(), *keys)
    bad = split_half_reliability(laps["noise"].to_numpy(), *keys)
    assert good["spearman_brown"] > 0.95
    assert good["teammate_sign_agreement"] == 1.0 and good["n_teams_compared"] == 3
    assert bad["spearman_brown"] < good["spearman_brown"]


def test_confounder_association_flags_tyre(laps):
    keys = (laps["Driver"].to_numpy(), laps["Compound"].to_numpy(), laps["TyreLife"].to_numpy(), laps["LapNumber"].to_numpy())
    tyre = confounder_association(laps["tyre"].to_numpy(), *keys)
    clean = confounder_association(laps["teammate"].to_numpy(), *keys)
    assert tyre["rho_tyre_life_within"] > 0.9
    assert abs(clean["rho_tyre_life_within"]) < 0.3
    assert clean["omega2_compound_within"] < 0.05
    assert clean["omega2_compound_within"] < clean["eta2_compound_within"]


def test_redundancy_finds_copy(laps):
    res = redundancy(laps["teammate"] * 2 + 1, laps[["car_only", "teammate", "noise"]])
    assert res["most_similar_existing"] == "teammate" and res["max_abs_rho_existing"] > 0.99


def test_score_features_recommends_teammate_signal_only(laps):
    laps = laps.copy()
    laps["mostly_zero"] = 0.0
    laps.loc[laps.index[:3], "mostly_zero"] = 1.0
    scores = score_features(laps, ["car_only", "teammate", "noise", "tyre", "mostly_zero"], reference_cols=["car_only"])
    rec = set(scores.loc[scores["recommended"], "feature"])
    assert rec == {"teammate"}
    assert {"share_team", "omega2_driver_in_team", "spearman_brown", "max_abs_rho_existing"} <= set(scores.columns)


def test_phase_leakage_flags_race_phase_classes():
    frame = pd.DataFrame({"LapNumber": np.arange(1, 41), "TyreLife": np.tile(np.arange(1, 21), 2)})
    phase = phase_leakage(frame, (frame["LapNumber"] > 20).astype(int).to_numpy())
    mixed = phase_leakage(frame, (frame["LapNumber"] % 2).to_numpy())
    assert phase["lap_span"] == 20.0 and mixed["lap_span"] == 1.0
    assert phase["tyre_life_span"] == 0.0


def test_car_fingerprint_is_not_recommended(laps):
    laps = laps.copy()
    laps["mostly_car"] = laps["car_only"] + 0.6 * laps["teammate"]
    scores = score_features(laps, ["mostly_car", "teammate"]).set_index("feature")
    assert scores.loc["mostly_car", "share_team"] > 0.5
    assert scores.loc["mostly_car", "omega2_driver_in_team"] >= 0.03
    assert not scores.loc["mostly_car", "recommended"]


def test_teammate_split_rate():
    labels = np.array([0, 0, 1, 1, 0, 0])
    drivers = np.array(["A", "A", "B", "B", "C", "C"])
    teams = np.array(["T1", "T1", "T1", "T1", "T2", "T2"])
    assert teammate_split_rate(labels, drivers, teams) == 1.0


def test_clustering_gain_runs(laps):
    gain = clustering_gain(laps, ["car_only", "noise"], ["teammate"], k_range=(2, 3), n_perm=2, n_boot=2)
    assert set(gain["set"]) == {"base", "base+extra"}
    assert {"silhouette_gap", "prediction_strength", "ami_driver", "teammate_split_rate", "lap_span"} <= set(gain.columns)
    with_extra = gain[gain["set"] == "base+extra"]["ami_driver"].max()
    base = gain[gain["set"] == "base"]["ami_driver"].max()
    assert with_extra > base
