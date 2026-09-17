"""Dimensionality reduction and clustering models."""

import numpy as np
import pandas as pd
import pytest

from f1_style_clustering.analysis.archetypes import assign_archetype_names, characterize_clusters
from f1_style_clustering.analysis.teammates import compare_teammates
from f1_style_clustering.models.clustering import fit_kmeans
from f1_style_clustering.models.dimensionality import compute_pca_loadings, perform_pca
from f1_style_clustering.models.evaluation import evaluate_clustering, find_optimal_k


@pytest.fixture
def sample_standardized_features():
    np.random.seed(42)
    drivers = ["VER", "NOR", "LEC", "HAM", "PIA", "RUS", "SAI", "PER", "ALO", "COL"]
    features = [
        "brake_point_rel",
        "trail_brake_frac",
        "apex_speed_rel",
        "throttle_attack",
        "coast_frac",
        "full_throttle_frac",
    ]
    data = np.random.randn(len(drivers), len(features))
    return pd.DataFrame(data, index=drivers, columns=features)


def test_perform_pca(sample_standardized_features):
    df_pca, pca_model, summary = perform_pca(sample_standardized_features, n_components=2)
    assert df_pca.shape == (10, 2)
    assert len(summary["explained_variance_ratio"]) == 2
    assert summary["cumulative_variance"] <= 1.0

    loadings = compute_pca_loadings(pca_model, sample_standardized_features.columns.tolist())
    assert loadings.shape == (6, 2)


def test_clustering_models(sample_standardized_features):
    labels_km, km_model = fit_kmeans(sample_standardized_features, n_clusters=3)
    assert len(labels_km) == 10
    assert labels_km.nunique() == 3


def test_cluster_evaluation(sample_standardized_features):
    labels, model = fit_kmeans(sample_standardized_features, n_clusters=3)
    metrics = evaluate_clustering(sample_standardized_features, labels, model)

    assert not np.isnan(metrics.silhouette)
    assert not np.isnan(metrics.davies_bouldin)
    assert metrics.inertia is not None

    df_eval = find_optimal_k(sample_standardized_features, k_min=2, k_max=4)
    assert len(df_eval) == 3
    assert "silhouette" in df_eval.columns


def test_archetype_characterization(sample_standardized_features):
    labels, _ = fit_kmeans(sample_standardized_features, n_clusters=3)
    profiles = characterize_clusters(sample_standardized_features, labels)
    assert profiles.shape[0] == 3

    names = assign_archetype_names(profiles)
    assert len(names) == 3


def test_teammates_comparison(sample_standardized_features):
    df_meta = pd.DataFrame(
        {
            "Team": [
                "Red Bull",
                "McLaren",
                "Ferrari",
                "Mercedes",
                "McLaren",
                "Mercedes",
                "Ferrari",
                "Red Bull",
                "Aston Martin",
                "Williams",
            ]
        },
        index=sample_standardized_features.index,
    )

    pairs = compare_teammates(sample_standardized_features, df_meta)
    assert len(pairs) >= 4
    assert "Style_Euclidean_Distance" in pairs.columns
