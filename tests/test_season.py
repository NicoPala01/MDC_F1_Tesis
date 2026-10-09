"""Season-level median profiles, global clustering, and stability."""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.pipeline import cluster_driver_matrix
from f1_style_clustering.season import (
    archetype_by_race_table,
    build_season_driver_matrix,
    event_slug,
    resolve_event_name,
    run_season_pipeline,
    season_stability,
    session_output_dir,
    write_session_outputs,
)


CORE = [
    "brake_point_rel",
    "trail_brake_frac",
    "apex_speed_rel",
    "throttle_attack",
    "coast_frac",
    "full_throttle_frac",
]


def _driver_frame(values_by_driver, team="TeamA"):
    df = pd.DataFrame.from_dict(values_by_driver, orient="index", columns=CORE)
    df["Team"] = team
    df["n_laps"] = 10
    return df


def test_event_slug_and_monza_alias():
    assert event_slug("Italian Grand Prix") == "italian_grand_prix"
    assert resolve_event_name("monza") == "Italian Grand Prix"
    assert resolve_event_name("Italian Grand Prix") == "Italian Grand Prix"
    assert session_output_dir("results", 2025, "Italian Grand Prix").as_posix().endswith(
        "results/2025/italian_grand_prix"
    )


def test_build_season_driver_matrix_median_and_min_races():
    r1 = _driver_frame(
        {
            "VER": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "HAM": [2.0, 0.0, 1.0, 0.0, 0.0, 0.0],
        }
    )
    r2 = _driver_frame(
        {
            "VER": [3.0, 0.0, 2.0, 0.0, 0.0, 0.0],
            "HAM": [4.0, 0.0, 3.0, 0.0, 0.0, 0.0],
        }
    )
    r3 = _driver_frame({"VER": [5.0, 0.0, 4.0, 0.0, 0.0, 0.0]})
    out = build_season_driver_matrix(
        {"Italian Grand Prix": r1, "British Grand Prix": r2, "Belgian Grand Prix": r3},
        min_races=3,
    )
    assert list(out.index) == ["VER"]
    assert out.loc["VER", "brake_point_rel"] == pytest.approx(3.0)
    assert int(out.loc["VER", "n_races"]) == 3


def test_season_stability_agreement():
    by_race = pd.DataFrame(
        {
            "Italian Grand Prix": ["Late Braker (V-Shape)", "Momentum Keeper (U-Shape)"],
            "British Grand Prix": ["Late Braker (V-Shape)", "Late Braker (V-Shape)"],
        },
        index=["VER", "HAM"],
    )
    season_summary = pd.DataFrame(
        {"Archetype": ["Late Braker (V-Shape)", "Momentum Keeper (U-Shape)"]},
        index=["VER", "HAM"],
    )
    stab = season_stability(by_race, season_summary)
    assert stab.loc["VER", "agreement"] == pytest.approx(1.0)
    assert stab.loc["HAM", "agreement"] == pytest.approx(0.5)


def test_archetype_by_race_table_aligns_drivers():
    s1 = pd.DataFrame({"Archetype": ["A", "B"]}, index=["VER", "HAM"])
    s2 = pd.DataFrame({"Archetype": ["A"]}, index=["VER"])
    table = archetype_by_race_table({"Italian Grand Prix": s1, "British Grand Prix": s2})
    assert table.loc["VER", "Italian Grand Prix"] == "A"
    assert pd.isna(table.loc["HAM", "British Grand Prix"])


def test_cluster_driver_matrix_on_season_like_vectors():
    rng = np.random.default_rng(0)
    rows = []
    index = []
    for i, drv in enumerate(["A", "B", "C", "D", "E", "F", "G", "H", "I"]):
        center = np.array([-1.5, 1.0, 0.0, 0.0, 0.0, 0.0]) if i < 5 else np.array([1.5, -1.0, 0.0, 0.0, 0.0, 0.0])
        rows.append(center + rng.normal(0, 0.05, size=6))
        index.append(drv)
    df = pd.DataFrame(rows, index=index, columns=CORE)
    df["Team"] = ["T1", "T1", "T2", "T2", "T3", "T3", "T4", "T4", "T5"]
    cfg = {
        "features": {"standardization": "robust", "residualize_team_tyre": False, "aggregation": "median"},
        "clustering": {
            "use_rule_based_k": True,
            "min_cluster_size": 3,
            "silhouette_threshold": 0.25,
            "kmeans": {"k_range": [2, 3], "n_init": 10},
            "seed_stability_n": 3,
            "driver_bootstrap": False,
            "compare_aggregators": False,
            "dbscan_prefilter": False,
        },
        "dimensionality_reduction": {"pca": {"use_as_clustering_input": "auto", "variance_threshold": 0.85}},
        "general": {"random_state": 0},
    }
    result = cluster_driver_matrix(
        df,
        config=cfg,
        k_clusters=2,
        residualize=False,
        driver_bootstrap=False,
        compare_aggregators=False,
    )
    assert "error" not in result or not result.get("error")
    assert result["k_used"] >= 2
    assert len(result["cluster_labels"]) == 9
    assert "Archetype" in result["df_summary"].columns


def test_run_season_pipeline_with_injected_session_results(tmp_path):
    race_data = {
        "Italian Grand Prix": _driver_frame(
            {d: [1.0 if d in {"VER", "NOR", "LEC"} else -1.0, 0.2, 0.0, 0.0, 0.0, 0.0] for d in ["VER", "NOR", "LEC", "HAM", "RUS", "PIA"]}
        ),
        "British Grand Prix": _driver_frame(
            {d: [1.1 if d in {"VER", "NOR", "LEC"} else -0.9, 0.1, 0.0, 0.0, 0.0, 0.0] for d in ["VER", "NOR", "LEC", "HAM", "RUS", "PIA"]}
        ),
        "Belgian Grand Prix": _driver_frame(
            {d: [0.9 if d in {"VER", "NOR", "LEC"} else -1.1, 0.0, 0.0, 0.0, 0.0, 0.0] for d in ["VER", "NOR", "LEC", "HAM", "RUS"]}
        ),
    }
    summaries = {}
    for name, df in race_data.items():
        labels = pd.Series([0 if v > 0 else 1 for v in df["brake_point_rel"]], index=df.index, name="Cluster")
        summaries[name] = pd.DataFrame(
            {
                "Cluster": labels,
                "Archetype": ["Late Braker (V-Shape)" if v == 0 else "Early Conservative Braker" for v in labels],
            },
            index=df.index,
        )

    calls = {"n": 0}
    events = list(race_data.keys())

    def load_fn(**kwargs):
        return {"grand_prix": kwargs["grand_prix"]}

    def run_fn(session, **kwargs):
        name = session["grand_prix"]
        calls["n"] += 1
        df = race_data[name]
        return {
            "df_raw": df,
            "df_summary": summaries[name],
            "df_scaled": df[CORE],
            "cluster_labels": summaries[name]["Cluster"],
            "k_used": 2,
            "k_rule": "user_override",
            "metrics": type("M", (), {"silhouette": 0.4, "davies_bouldin": 0.8})(),
            "zone_source": "key_corners",
            "profiles": None,
            "radar_features": [],
            "df_pca_vis": None,
            "eval_df": None,
            "archetype_names": {0: "Late Braker (V-Shape)", 1: "Early Conservative Braker"},
        }

    cfg = {
        "general": {"cache_dir": str(tmp_path / "cache"), "min_races_season": 2, "random_state": 0},
        "features": {"standardization": "robust", "residualize_team_tyre": False, "aggregation": "median"},
        "clustering": {
            "use_rule_based_k": True,
            "min_cluster_size": 2,
            "silhouette_threshold": 0.1,
            "kmeans": {"k_range": [2, 3], "n_init": 5},
            "seed_stability_n": 2,
            "driver_bootstrap": False,
            "compare_aggregators": False,
            "dbscan_prefilter": False,
        },
        "dimensionality_reduction": {"pca": {"use_as_clustering_input": "auto", "variance_threshold": 0.85}},
        "data_filtering": {},
    }

    out = run_season_pipeline(
        year=2025,
        output_dir=str(tmp_path / "results"),
        config=cfg,
        circuit_config={"benchmark_circuits": {}},
        min_races=2,
        events=events,
        driver_bootstrap=False,
        compare_aggregators=False,
        residualize=False,
        save_plots=False,
        load_session_fn=load_fn,
        run_pipeline_fn=run_fn,
    )
    assert calls["n"] == 3
    assert "VER" in out["season_matrix"].index
    assert "PIA" in out["season_matrix"].index
    assert int(out["season_matrix"].loc["PIA", "n_races"]) == 2
    assert not out["season_result"].get("error")
    assert (tmp_path / "results" / "2025" / "italian_grand_prix" / "features_raw.csv").exists()
    assert (tmp_path / "results" / "2025" / "season" / "stability.csv").exists()
    assert "agreement" in out["stability"].columns


def test_radar_uses_style_profiles_when_fit_space_is_pca(tmp_path):
    """PCA centroids do not carry typology columns; the radar must still save."""
    style = pd.DataFrame(
        {
            "slow__brake_point_rel": [-1.0, -0.8, 1.1, 0.9],
            "slow__apex_speed_rel": [0.4, 0.2, -0.5, -0.3],
            "fast__full_throttle_frac": [0.1, 0.0, -0.2, -0.1],
        },
        index=["L1", "L2", "L3", "L4"],
    )
    labels = pd.Series([0, 0, 1, 1], index=style.index, name="Cluster")
    result = {
        "df_summary": pd.DataFrame(
            {"Cluster": [0, 1], "Archetype": ["Late Braker (V-Shape)", "Early Conservative Braker"]},
            index=["VER", "HAM"],
        ),
        "profiles": pd.DataFrame({"PC1": [-0.6, 0.7], "PC2": [0.2, -0.1]}, index=[0, 1]),
        "style_profiles": style.groupby(labels).mean(numeric_only=True),
        "radar_features": list(style.columns),
        "archetype_names": {0: "Late Braker (V-Shape)", 1: "Early Conservative Braker"},
        "eval_df": pd.DataFrame(),
    }
    dest = write_session_outputs(result, tmp_path / "monza", save_plots=True)
    assert (dest / "figures" / "radar_archetypes.png").exists()

    mismatched = dict(result)
    mismatched["style_profiles"] = None
    mismatched["radar_features"] = ["slow__brake_point_rel"]
    dest_pc = write_session_outputs(mismatched, tmp_path / "pca_only", save_plots=True)
    assert (dest_pc / "figures" / "radar_archetypes.png").exists()


def _synthetic_lap_matrix(event_seed: int) -> pd.DataFrame:
    """Six drivers, 30 laps. Every car gains apex speed and brakes later as fuel burns;
    drivers differ in coasting and trail braking."""
    rng = np.random.default_rng(event_seed)
    teams = {"VER": "RB", "TSU": "RB", "NOR": "MCL", "PIA": "MCL", "LEC": "FER", "HAM": "FER"}
    coaster = {"VER": -1.0, "TSU": 1.0, "NOR": -1.0, "PIA": 1.0, "LEC": -1.0, "HAM": 1.0}
    rows = []
    for driver, team in teams.items():
        for lap in range(1, 31):
            row = {"Driver": driver, "FullName": driver, "Team": team, "LapNumber": lap,
                   "Compound": "MEDIUM" if lap <= 15 else "HARD", "TyreLife": float(lap if lap <= 15 else lap - 15)}
            for typ in ("slow", "medium", "fast"):
                row[f"{typ}__apex_speed_rel"] = 0.6 * lap + rng.normal(0, 1.0)
                row[f"{typ}__brake_point_rel"] = -0.8 * lap + rng.normal(0, 1.5)
                row[f"{typ}__coast_frac"] = 0.02 * coaster[driver] + rng.normal(0, 0.008)
                row[f"{typ}__trail_brake_frac"] = -0.03 * coaster[driver] + rng.normal(0, 0.012)
            rows.append(row)
    frame = pd.DataFrame(rows)
    frame.index = frame["Driver"] + " L" + frame["LapNumber"].astype(str)
    frame.attrs["feature_cols"] = ["apex_speed_rel", "brake_point_rel", "coast_frac", "trail_brake_frac"]
    return frame


def _run_synthetic_season(monkeypatch, tmp_path, features_override=None):
    from f1_style_clustering import pipeline as pipeline_mod
    from f1_style_clustering.config import load_config

    events = {"Italian Grand Prix": 1, "Dutch Grand Prix": 2, "British Grand Prix": 3}
    monkeypatch.setattr(pipeline_mod, "resolve_selected_corners", lambda session, circuits: (None, "synthetic"))
    monkeypatch.setattr(pipeline_mod, "extract_circuit_zones", lambda session, **kw: {})
    monkeypatch.setattr(pipeline_mod, "build_lap_style_matrix", lambda session, **kw: _synthetic_lap_matrix(session["seed"]))
    cfg = load_config()
    cfg["general"]["cache_dir"] = str(tmp_path / "cache")
    cfg["clustering"]["seed_stability_n"] = 2
    cfg["features"].update(features_override or {})
    return run_season_pipeline(
        year=2025,
        events=list(events),
        output_dir=str(tmp_path / "results"),
        config=cfg,
        min_races=2,
        save_plots=False,
        load_session_fn=lambda year, grand_prix, session_type, cache_dir: {"seed": events[grand_prix]},
    )


def _class_lap_span(result):
    frame = result["df_raw"].reindex(result["cluster_labels"].index)
    medians = frame.groupby(result["cluster_labels"])["LapNumber"].median()
    return float(medians.max() - medians.min())


def test_season_runs_with_default_lap_synchronous_config(monkeypatch, tmp_path):
    out = _run_synthetic_season(monkeypatch, tmp_path)
    assert out["failures"] == []
    assert set(out["per_race"]) == {"Italian Grand Prix", "Dutch Grand Prix", "British Grand Prix"}
    for result in out["per_race"].values():
        assert result["normalization"]["lap_synchronous"] is True
        assert result["normalization"]["within_driver_tyre_effects"] is True
        assert "extended_lap_metrics" not in result
        assert _class_lap_span(result) <= 3.0
        assert not any("late braking" in n.lower() or "early braking" in n.lower() for n in result["archetype_names"].values())
    season = out["season_matrix"]
    assert not season.empty and set(season.index) == {"VER", "TSU", "NOR", "PIA", "LEC", "HAM"}
    assert season.loc["VER", "Archetype"] != season.loc["TSU", "Archetype"]
    assert (out["stability"]["agreement"] == 1.0).all()
    season_dir = tmp_path / "results" / "2025" / "season"
    for name in ("driver_summary.csv", "archetype_by_race.csv", "stability.csv"):
        assert (season_dir / name).exists()
    assert (tmp_path / "results" / "2025" / "italian_grand_prix" / "driver_laps_by_class.csv").exists()


def test_season_classes_split_race_phase_without_lap_synchronous(monkeypatch, tmp_path):
    out = _run_synthetic_season(
        monkeypatch, tmp_path, {"lap_synchronous": False, "within_driver_tyre_effects": False}
    )
    spans = [_class_lap_span(r) for r in out["per_race"].values()]
    assert min(spans) >= 10.0


def test_config_without_normalization_keys_uses_the_lap_synchronous_default(monkeypatch):
    from f1_style_clustering import pipeline as pipeline_mod
    from f1_style_clustering.config import load_config

    monkeypatch.setattr(pipeline_mod, "resolve_selected_corners", lambda session, circuits: (None, "synthetic"))
    monkeypatch.setattr(pipeline_mod, "extract_circuit_zones", lambda session, **kw: {})
    monkeypatch.setattr(pipeline_mod, "build_lap_style_matrix", lambda session, **kw: _synthetic_lap_matrix(1))
    cfg = load_config()
    cfg["clustering"]["seed_stability_n"] = 2
    for key in ("lap_synchronous", "within_driver_tyre_effects", "extended_metrics", "feature_screening"):
        cfg["features"].pop(key)
    result = pipeline_mod.run_pipeline({"seed": 1}, config=cfg, circuit_config={})
    assert result["normalization"]["lap_synchronous"] is True
    assert result["normalization"]["within_driver_tyre_effects"] is True
    assert _class_lap_span(result) <= 3.0
