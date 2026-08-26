"""Unit tests for dimensionality reduction and clustering models."""

import pytest
import pandas as pd
import numpy as np

from f1_style_clustering.models.dimensionality import perform_pca, compute_pca_loadings, perform_tsne
from f1_style_clustering.models.clustering import fit_kmeans, fit_agglomerative, fit_gmm, fit_clustering_model
from f1_style_clustering.models.evaluation import evaluate_clustering, find_optimal_k
from f1_style_clustering.analysis.archetypes import characterize_clusters, assign_archetype_names
from f1_style_clustering.analysis.teammates import compare_teammates


@pytest.fixture
def sample_standardized_features():
    """Create synthetic standardized driver features matrix."""
    np.random.seed(42)
    drivers = ["VER", "NOR", "LEC", "HAM", "PIA", "RUS", "SAI", "PER", "ALO", "COL"]
    features = [
        "T1_ApexSpeed", "T1_MaxDecel", "T1_BrakingDistToApex", "T1_MaxThrottleRate",
        "T4_ApexSpeed", "T4_MaxDecel", "T4_BrakingDistToApex", "T4_MaxThrottleRate",
    ]
    data = np.random.randn(len(drivers), len(features))
    df = pd.DataFrame(data, index=drivers, columns=features)
    return df


def test_perform_pca(sample_standardized_features):
    df_pca, pca_model, summary = perform_pca(sample_standardized_features, n_components=2)
    assert df_pca.shape == (10, 2)
    assert len(summary["explained_variance_ratio"]) == 2
    assert summary["cumulative_variance"] <= 1.0

    loadings = compute_pca_loadings(pca_model, sample_standardized_features.columns.tolist())
    assert loadings.shape == (8, 2)


def test_perform_tsne(sample_standardized_features):
    df_tsne, tsne_model = perform_tsne(sample_standardized_features, n_components=2, perplexity=3.0)
    assert df_tsne.shape == (10, 2)


def test_clustering_models(sample_standardized_features):
    # K-Means
    labels_km, km_model = fit_kmeans(sample_standardized_features, n_clusters=3)
    assert len(labels_km) == 10
    assert labels_km.nunique() == 3

    # Agglomerative
    labels_agg, agg_model = fit_agglomerative(sample_standardized_features, n_clusters=3)
    assert len(labels_agg) == 10

    # GMM
    labels_gmm, probs, gmm_model = fit_gmm(sample_standardized_features, n_components=3)
    assert len(labels_gmm) == 10
    assert probs.shape == (10, 3)

    # Unified
    labels_uni, _ = fit_clustering_model(sample_standardized_features, algorithm="kmeans", n_clusters=2)
    assert len(labels_uni) == 10


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
    df_meta = pd.DataFrame({
        "Team": ["Red Bull", "McLaren", "Ferrari", "Mercedes", "McLaren", "Mercedes", "Ferrari", "Red Bull", "Aston Martin", "Williams"]
    }, index=sample_standardized_features.index)

    pairs = compare_teammates(sample_standardized_features, df_meta)
    assert len(pairs) >= 4  # Red Bull, McLaren, Ferrari, Mercedes pairs
    assert "Style_Euclidean_Distance" in pairs.columns

