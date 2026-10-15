"""Rules for the experimental clustering grid. The default K-means stays put."""

import inspect

import numpy as np
import pandas as pd

import f1_style_clustering.pipeline as pipeline_mod
from f1_style_clustering.analysis.model_grid import (
    DOMINANCE_SHARE,
    HDBSCAN_MIN_FIXED,
    HDBSCAN_MIN_FRACTION,
    IQR_EPS,
    K_MAX,
    K_MIN,
    LOW_MEMBERSHIP,
    METHODS,
    N_BOOT,
    N_REPLICATES,
    SEED,
    STRUCTURE_STATISTIC,
    GridSettings,
    _pack,
    beats_all_three,
    choose_gmm_candidate,
    class_floor,
    dominant_classes,
    fit_model,
    has_consensus,
    hdbscan_min_cluster_size,
    null_statistic_summary,
    permutation_scaled_draw,
    render_report,
    run_matrix,
)
from f1_style_clustering.analysis.triple_null import N_REPLICATES as TRIPLE_N
from f1_style_clustering.config import load_config
from f1_style_clustering.season import season_exclude_columns


def _settings(**overrides) -> GridSettings:
    base = dict(
        k_max=3,
        kmeans_n_init=2,
        kmedians_n_init=2,
        kmedoids_n_init=2,
        gmm_n_init=1,
        fuzzy_n_init=2,
        fuzzy_max_iter=30,
        n_bootstrap=2,
        n_replicates=2,
        methods=("kmeans", "gmm", "hdbscan"),
        hdbscan_min_fixed=8,
    )
    base.update(overrides)
    return GridSettings(**base)


def _blobs(seed: int = 0, n: int = 40):
    rng = np.random.default_rng(seed)
    left = rng.normal(loc=-8.0, size=(n, 2))
    right = rng.normal(loc=8.0, size=(n, 2))
    return np.vstack([left, right])


def test_rules_are_fixed_and_the_yaml_matches_them():
    assert (K_MIN, K_MAX) == (2, 10)
    assert SEED == 42
    assert N_REPLICATES == 50
    assert N_REPLICATES == TRIPLE_N
    assert N_BOOT == 20
    assert LOW_MEMBERSHIP == 0.8
    assert HDBSCAN_MIN_FIXED == 15
    assert HDBSCAN_MIN_FRACTION == 0.05
    assert DOMINANCE_SHARE == 0.5
    assert IQR_EPS == 1e-8
    assert STRUCTURE_STATISTIC["hdbscan"] == "dbcv"
    assert STRUCTURE_STATISTIC["kmeans"] == "silhouette"
    assert "fuzzy_cmeans" in METHODS
    cfg = load_config()
    assert GridSettings.from_config(cfg) == GridSettings()
    assert cfg["clustering"]["kmeans"]["k_range"] == [2, 7]
    assert cfg["clustering"]["kmeans"]["n_init"] == 20
    assert season_exclude_columns(cfg) == ["fast__brake_point_rel"]


def test_hdbscan_size_is_the_fixed_floor_and_the_lap_fraction():
    settings = GridSettings()
    assert hdbscan_min_cluster_size(104, settings) == 15
    assert hdbscan_min_cluster_size(1000, settings) == 50
    assert hdbscan_min_cluster_size(1275, settings) == 64
    assert class_floor(1000, settings) == 50
    assert class_floor(1000, settings, relaxed=True) == 3


def test_silhouette_tie_keeps_the_smaller_k_and_the_floor_drops_a_singleton():
    from f1_style_clustering.analysis.model_grid import _choose_silhouette

    settings = GridSettings()
    tied = [
        {"k": 4, "silhouette": 0.2, "min_size": 10},
        {"k": 2, "silhouette": 0.2, "min_size": 10},
        {"k": 3, "silhouette": 0.1, "min_size": 10},
    ]
    assert _choose_silhouette(tied, 100, settings)["k"] == 2
    tiny = [
        {"k": 2, "silhouette": 0.9, "min_size": 1},
        {"k": 3, "silhouette": 0.2, "min_size": 10},
    ]
    assert _choose_silhouette(tiny, 100, settings)["k"] == 3
    relaxed = [{"k": 2, "silhouette": 0.4, "min_size": 3}]
    assert _choose_silhouette(relaxed, 1000, settings)["k"] == 2


def test_gmm_tie_breaks_toward_smaller_k_then_full():
    rows = [
        {"k": 4, "covariance_type": "diag", "bic": 1.0, "min_size": 10},
        {"k": 3, "covariance_type": "diag", "bic": 1.0, "min_size": 10},
        {"k": 3, "covariance_type": "full", "bic": 1.0, "min_size": 10},
        {"k": 2, "covariance_type": "full", "bic": -5.0, "min_size": 1},
    ]
    chosen = choose_gmm_candidate(rows, 100, GridSettings())
    assert chosen["k"] == 3
    assert chosen["covariance_type"] == "full"


def test_two_blobs_select_two_classes_and_hdbscan_can_mark_noise():
    values = _blobs()
    settings = _settings()
    kmeans = fit_model(values, "kmeans", settings)
    assert kmeans["k"] == 2
    assert kmeans["silhouette"] > 0.5
    assert kmeans["fraction"] == 0.0
    assert kmeans["fraction_kind"] == "ninguna"
    fuzzy = fit_model(values, "fuzzy_cmeans", settings)
    assert fuzzy["k"] == 2
    assert fuzzy["fraction_kind"] == "baja pertenencia"
    hdb = fit_model(values, "hdbscan", settings)
    assert hdb["k"] == 2
    assert hdb["min_cluster_size"] == 8
    assert hdb["structure_name"] == "dbcv"
    assert hdb["dbcv"] is not None
    packed = _pack(
        "gmm",
        np.array([0, 0, 1]),
        np.zeros((3, 1)),
        GridSettings(),
        membership=np.array([[0.79, 0.21], [0.8, 0.2], [0.81, 0.19]]),
    )
    assert packed["fraction"] == 1.0 / 3.0
    assert packed["fraction_kind"] == "baja pertenencia"
    noise = _pack(
        "hdbscan",
        np.array([0, 0, 0, -1, 1, 1]),
        _blobs(n=3),
        GridSettings(),
        min_cluster_size=2,
    )
    assert noise["fraction"] == 1.0 / 6.0
    assert noise["fraction_kind"] == "ruido"


def test_a_stacked_feature_marks_the_class_and_only_that_class():
    values = np.array(
        [
            [0.0, 0.1],
            [0.0, -0.1],
            [0.0, 0.0],
            [5.0, 0.2],
            [5.0, -0.2],
            [6.0, 0.0],
        ]
    )
    labels = np.array([0, 0, 0, 1, 1, 1])
    rows = dominant_classes(values, labels, ["slow__a", "fast__b"])
    marked = [row for row in rows if row["marked"]]
    assert len(marked) == 1
    assert marked[0]["component"] == 0
    assert marked[0]["feature"] == "slow__a"
    assert "Driver" not in marked[0]


def test_structure_needs_every_null_and_consensus_needs_half_the_models():
    assert beats_all_three(
        {
            "permutation": {"beats_p95": True},
            "gaussian": {"beats_p95": True},
            "gaussian_copula": {"beats_p95": True},
        }
    )
    assert not beats_all_three(
        {
            "permutation": {"beats_p95": True},
            "gaussian": {"beats_p95": True},
            "gaussian_copula": {"beats_p95": False},
        }
    )
    assert has_consensus([True, True, True, True, False, False, False, False])
    assert not has_consensus([True, True, True, False, False, False, False, False])
    assert not has_consensus([True, True, True, True, False, False, False, False, False])
    tied = null_statistic_summary(1.0, [1.0, 1.0, 1.0, 1.0])
    assert tied["beats_p95"] is False
    above = null_statistic_summary(4.0, [0.0, 0.2, 0.4, 3.0])
    assert above["beats_p95"] is True


def test_permutation_keeps_a_stacked_column_constant_after_scaling():
    frame = pd.DataFrame({"slow__a": np.linspace(-1.0, 1.0, 30), "fast__coast_frac": np.ones(30)})
    drawn = permutation_scaled_draw(frame, np.random.default_rng(0))
    assert list(drawn.columns) == ["slow__a", "fast__coast_frac"]
    assert drawn["fast__coast_frac"].nunique() == 1


def test_run_matrix_reports_the_three_nulls_and_ari_against_kmeans():
    frame = pd.DataFrame(_blobs(), columns=["slow__a", "fast__b"])
    measured = run_matrix(frame, _settings(), workers=1, with_nulls=True, with_bootstrap=True)
    by_method = {row["method"]: row for row in measured["models"]}
    assert set(by_method) == {"kmeans", "gmm", "hdbscan"}
    assert by_method["kmeans"]["ari_kmeans"] == 1.0
    for name in ("permutation", "gaussian", "gaussian_copula"):
        assert by_method["kmeans"]["nulls"][name]["n"] == 2
    assert by_method["kmeans"]["bootstrap_ari"] is not None


def test_report_splits_declared_rules_from_measured_numbers():
    payload = {
        "races": [
            {
                "name": "Italia",
                "n_laps": 10,
                "n_features": 2,
                "features": ["slow__a"],
                "zero_iqr": [],
                "models": [
                    {
                        "method": "kmeans",
                        "k": 2,
                        "covariance_type": None,
                        "min_cluster_size": None,
                        "silhouette": 0.2,
                        "dbcv": None,
                        "fraction": 0.0,
                        "fraction_kind": "ninguna",
                        "min_size": 4,
                        "bootstrap_ari": 0.5,
                        "ari_kmeans": 1.0,
                        "beats_all": False,
                        "nulls": {
                            "permutation": {"n": 50, "p95": 0.1, "percentile": 80.0, "beats_p95": False},
                            "gaussian": {"n": 50, "p95": 0.1, "percentile": 90.0, "beats_p95": False},
                            "gaussian_copula": {"n": 50, "p95": 0.3, "percentile": 40.0, "beats_p95": False},
                        },
                        "classes": [],
                    }
                ],
            }
        ]
    }
    text = render_report(payload)
    assert "## Declarado" in text
    assert "## Medido" in text
    assert "2 a 10" in text or "2 a 10" in text
    assert "HDBSCAN" in text
    assert "0.8" in text or "0,8" in text
    assert "Italia" in text
    assert "supera los tres" in text
    assert "consenso" in text.lower() or "Consenso" in text or "consenso" in text
    measured = text.split("## Medido", 1)[1].lower()
    assert "reputación" not in measured
    assert "agresiv" not in text.lower()


def test_the_default_pipeline_does_not_import_the_grid():
    source = inspect.getsource(pipeline_mod)
    assert "model_grid" not in source
    assert "fit_kmeans" in source
