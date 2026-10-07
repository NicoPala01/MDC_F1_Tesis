"""Lap vectors, modal driver profiles, and the dashboard session index."""

from pathlib import Path

import pandas as pd
import pytest

from f1_style_clustering.analysis.dashboard_data import discover_sessions, metric_table
from f1_style_clustering.analysis.lap_distribution import (
    build_lap_distribution_reports,
    driver_laps_by_class,
    teammates_from_distribution,
)
from f1_style_clustering.features.aggregators import lap_vectors_from_typology
from f1_style_clustering.season import season_modal_summary, write_session_outputs


def _lap_typology_rows():
    rows = []
    specs = [
        ("VER", 1, "slow", 10.0),
        ("VER", 1, "fast", 2.0),
        ("VER", 2, "slow", 12.0),
        ("HAM", 1, "slow", 1.0),
        ("HAM", 1, "fast", 8.0),
        ("HAM", 3, "slow", 4.0),
    ]
    for driver, lap, typ, brake in specs:
        rows.append(
            {
                "Driver": driver,
                "FullName": "Max Verstappen" if driver == "VER" else "Lewis Hamilton",
                "Team": "Red Bull" if driver == "VER" else "Ferrari",
                "LapNumber": lap,
                "typology": typ,
                "brake_point_rel": brake,
                "trail_brake_frac": 0.2,
                "apex_speed_rel": 1.0,
                "throttle_attack": 3.0,
                "coast_frac": 0.1,
                "full_throttle_frac": 0.4,
            }
        )
    return pd.DataFrame(rows)


def test_lap_vectors_drop_incomplete_laps_and_name_typology_blocks():
    wide = lap_vectors_from_typology(_lap_typology_rows())
    assert set(wide["Driver"]) == {"VER", "HAM"}
    assert set(wide["LapNumber"]) == {1}
    assert "slow__brake_point_rel" in wide.columns
    assert "fast__brake_point_rel" in wide.columns
    assert "fast__trail_brake_frac" in wide.columns
    assert "slow__throttle_attack" in wide.columns
    assert "fast__throttle_attack" not in wide.columns
    ver = wide.set_index("Driver").loc["VER"]
    assert ver["slow__brake_point_rel"] == pytest.approx(10.0)
    assert ver["fast__brake_point_rel"] == pytest.approx(2.0)
    assert "HAM L3" not in wide.index


def test_fast_throttle_attack_dropped_slow_and_medium_kept():
    rows = []
    for typ, attack in (("slow", 1.0), ("medium", 2.0), ("fast", 9.0)):
        rows.append(
            {
                "Driver": "VER",
                "LapNumber": 1,
                "typology": typ,
                "brake_point_rel": 4.0,
                "trail_brake_frac": 0.3,
                "apex_speed_rel": 1.0,
                "throttle_attack": attack,
                "coast_frac": 0.1,
                "full_throttle_frac": 0.2,
            }
        )
    wide = lap_vectors_from_typology(pd.DataFrame(rows))
    assert "fast__throttle_attack" not in wide.columns
    assert wide.loc[wide.index[0], "slow__throttle_attack"] == pytest.approx(1.0)
    assert wide.loc[wide.index[0], "medium__throttle_attack"] == pytest.approx(2.0)
    assert "fast__brake_point_rel" in wide.columns
    assert "fast__trail_brake_frac" in wide.columns


def test_driver_profile_is_the_modal_lap_class():
    labels = pd.Series(
        [0, 0, 0, 1],
        index=["VER L1", "VER L2", "VER L3", "VER L4"],
        name="Cluster",
    )
    meta = pd.DataFrame(
        {
            "Driver": ["VER"] * 4,
            "FullName": ["Max Verstappen"] * 4,
            "Team": ["Red Bull"] * 4,
            "LapNumber": [1, 2, 3, 4],
        },
        index=labels.index,
    )
    lap_typ = pd.DataFrame(
        {
            "Driver": ["VER"] * 4,
            "LapNumber": [1, 2, 3, 4],
            "typology": ["slow"] * 4,
            "brake_point_rel": [1.0, 3.0, 5.0, 100.0],
            "trail_brake_frac": [0.1, 0.1, 0.1, 0.9],
            "apex_speed_rel": [0.0, 0.0, 0.0, 0.0],
            "throttle_attack": [1.0, 1.0, 1.0, 1.0],
            "coast_frac": [0.0, 0.0, 0.0, 0.0],
            "full_throttle_frac": [0.5, 0.5, 0.5, 0.5],
        }
    )
    names = {0: "Late Braker (V-Shape)", 1: "Early Conservative Braker"}
    classifications, distribution, profiles = build_lap_distribution_reports(
        labels,
        names,
        meta,
        lap_typ=lap_typ,
        feature_cols=["brake_point_rel", "trail_brake_frac", "apex_speed_rel", "throttle_attack", "coast_frac", "full_throttle_frac"],
    )
    assert list(classifications["Archetype"]).count("Late Braker (V-Shape)") == 3
    assert profiles.loc["VER", "Archetype"] == "Late Braker (V-Shape)"
    assert profiles.loc["VER", "modal_fraction"] == pytest.approx(0.75)
    assert profiles.loc["VER", "FullName"] == "Max Verstappen"
    assert profiles.loc["VER", "brake_point_rel"] == pytest.approx(4.0)
    assert distribution["fraction"].sum() == pytest.approx(1.0)
    assert bool(distribution.loc[distribution["is_modal"], "is_modal"].iloc[0])


def _class_table(cluster_ids, drivers):
    labels = pd.Series(cluster_ids, index=[f"L{i}" for i in range(len(cluster_ids))], name="Cluster")
    meta = pd.DataFrame(
        {
            "Driver": drivers,
            "FullName": drivers,
            "Team": ["Team"] * len(drivers),
            "LapNumber": list(range(1, len(drivers) + 1)),
        },
        index=labels.index,
    )
    classifications, _, _ = build_lap_distribution_reports(labels, {}, meta)
    return driver_laps_by_class(classifications)


def test_laps_by_class_columns_follow_fit_k():
    """Class columns are the ids of that fit. k=4 is four columns, not a fixed pair."""
    two = _class_table([0, 0, 1], ["VER", "VER", "HAM"])
    two_cols = [c for c in two.columns if str(c).startswith("clase ")]
    assert two_cols == ["clase 0", "clase 1"]
    assert list(two["piloto"]) == ["HAM", "VER", "total"]
    assert int(two.loc[two["piloto"] == "HAM", "clase 0"].iloc[0]) == 0
    assert int(two.loc[two["piloto"] == "total", "total"].iloc[0]) == 3

    four = _class_table([0, 1, 2, 3, 3], ["VER", "HAM", "LEC", "NOR", "NOR"])
    four_cols = [c for c in four.columns if str(c).startswith("clase ")]
    assert four_cols == ["clase 0", "clase 1", "clase 2", "clase 3"]
    assert len(four_cols) == 4
    assert int(four.loc[four["piloto"] == "total", "clase 3"].iloc[0]) == 2
    assert int(four.loc[four["piloto"] == "total", "total"].iloc[0]) == 5

    other = _class_table([5, 5, 8], ["VER", "HAM", "HAM"])
    other_cols = [c for c in other.columns if str(c).startswith("clase ")]
    assert other_cols == ["clase 5", "clase 8"]
    assert "clase 0" not in other.columns
    assert int(other.loc[other["piloto"] == "VER", "clase 8"].iloc[0]) == 0


def test_session_output_writes_laps_by_class(tmp_path: Path):
    table = _class_table([0, 1, 2, 2], ["VER", "HAM", "LEC", "LEC"])
    write_session_outputs(
        {"driver_laps_by_class": table},
        tmp_path,
        save_plots=False,
    )
    saved = pd.read_csv(tmp_path / "driver_laps_by_class.csv")
    class_cols = [c for c in saved.columns if str(c).startswith("clase ")]
    assert class_cols == ["clase 0", "clase 1", "clase 2"]
    assert saved.iloc[-1]["piloto"] == "total"
    assert int(saved.iloc[-1]["total"]) == 4


def test_teammate_distance_uses_lap_fractions():
    distribution = pd.DataFrame(
        {
            "Driver": ["VER", "PER", "VER", "PER"],
            "Team": ["Red Bull"] * 4,
            "Archetype": ["A", "A", "B", "B"],
            "fraction": [0.8, 0.2, 0.2, 0.8],
        }
    )
    pairs = teammates_from_distribution(distribution)
    assert len(pairs) == 1
    assert pairs.iloc[0]["Style_Euclidean_Distance"] > 0


def test_season_tendency_is_the_modal_race_archetype():
    by_race = pd.DataFrame(
        {
            "Italian Grand Prix": ["Late Braker (V-Shape)", "Momentum Keeper (U-Shape)"],
            "British Grand Prix": ["Late Braker (V-Shape)", "Late Braker (V-Shape)"],
            "Belgian Grand Prix": ["Late Braker (V-Shape)", None],
        },
        index=["VER", "HAM"],
    )
    summaries = {
        "Italian Grand Prix": pd.DataFrame(
            {"Archetype": ["Late Braker (V-Shape)", "Momentum Keeper (U-Shape)"], "Team": ["Red Bull", "Ferrari"], "FullName": ["Max Verstappen", "Lewis Hamilton"]},
            index=["VER", "HAM"],
        )
    }
    summary = season_modal_summary(by_race, summaries, min_races=2)
    assert summary.loc["VER", "Archetype"] == "Late Braker (V-Shape)"
    assert int(summary.loc["VER", "n_races"]) == 3
    assert summary.loc["VER", "FullName"] == "Max Verstappen"
    assert "HAM" in summary.index
    assert int(summary.loc["HAM", "n_races"]) == 2


def test_session_outputs_keep_driver_column(tmp_path: Path):
    profiles = pd.DataFrame(
        {"Archetype": ["Late Braker (V-Shape)"], "modal_fraction": [0.8], "n_laps": [10]},
        index=pd.Index(["VER"], name="Driver"),
    )
    distribution = pd.DataFrame(
        {
            "Driver": ["VER"],
            "Archetype": ["Late Braker (V-Shape)"],
            "n_laps_in_class": [8],
            "fraction": [0.8],
            "is_modal": [True],
            "n_laps": [10],
        }
    )
    write_session_outputs(
        {
            "df_summary": profiles,
            "driver_profiles": profiles,
            "driver_lap_distribution": distribution,
            "lap_classifications": distribution,
        },
        tmp_path,
        save_plots=False,
    )
    saved = pd.read_csv(tmp_path / "driver_profiles.csv")
    assert "Driver" in saved.columns
    assert saved.loc[0, "Driver"] == "VER"


def test_discover_sessions_skips_season_folder(tmp_path: Path):
    event = tmp_path / "2025" / "italian_grand_prix"
    event.mkdir(parents=True)
    pd.DataFrame({"Driver": ["VER"]}).to_csv(event / "driver_profiles.csv", index=False)
    pd.DataFrame({"Driver": ["VER"], "Archetype": ["A"], "fraction": [1.0]}).to_csv(
        event / "driver_lap_distribution.csv", index=False
    )
    season = tmp_path / "2025" / "season"
    season.mkdir()
    pd.DataFrame({"Driver": ["VER"]}).to_csv(season / "driver_profiles.csv", index=False)
    pd.DataFrame({"Driver": ["VER"]}).to_csv(season / "driver_lap_distribution.csv", index=False)

    found = discover_sessions(tmp_path)
    assert len(found) == 1
    assert found[0]["event"] == "italian_grand_prix"
    metrics = metric_table(pd.Series({"brake_point_rel": 1.5, "Driver": "VER"}))
    assert metrics.iloc[0]["Métrica"] == "Punto de frenado (relativo)"
    assert metrics.iloc[0]["Mediana de las vueltas"] == pytest.approx(1.5)
