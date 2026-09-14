"""Dimensionality reduction, unsupervised clustering algorithms, and evaluation metrics."""

from .dimensionality import perform_pca, perform_tsne, compute_pca_loadings, pca_for_clustering
from .clustering import (
    fit_kmeans,
    fit_agglomerative,
    fit_gmm,
    fit_dbscan,
    fit_clustering_model,
    kmeans_seed_stability,
    dbscan_prefilter_outliers,
)
from .evaluation import evaluate_clustering, find_optimal_k, select_k_rule_based, ClusteringMetrics

__all__ = [
    "perform_pca",
    "perform_tsne",
    "compute_pca_loadings",
    "pca_for_clustering",
    "fit_kmeans",
    "fit_agglomerative",
    "fit_gmm",
    "fit_dbscan",
    "fit_clustering_model",
    "kmeans_seed_stability",
    "dbscan_prefilter_outliers",
    "evaluate_clustering",
    "find_optimal_k",
    "select_k_rule_based",
    "ClusteringMetrics",
]

