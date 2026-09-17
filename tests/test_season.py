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
