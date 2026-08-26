"""Dimensionality reduction, unsupervised clustering algorithms, and evaluation metrics."""

from .dimensionality import perform_pca, perform_tsne, compute_pca_loadings
from .clustering import (
    fit_kmeans,
    fit_agglomerative,
    fit_gmm,
    fit_dbscan,
    fit_clustering_model,
)
from .evaluation import evaluate_clustering, find_optimal_k, ClusteringMetrics

__all__ = [
    "perform_pca",
    "perform_tsne",
    "compute_pca_loadings",
    "fit_kmeans",
    "fit_agglomerative",
    "fit_gmm",
    "fit_dbscan",
    "fit_clustering_model",
    "evaluate_clustering",
    "find_optimal_k",
    "ClusteringMetrics",
]

