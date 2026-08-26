"""Dimensionality reduction techniques: PCA and t-SNE."""

from typing import Tuple, Optional, Dict, Any
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE


def perform_pca(
    df_standardized: pd.DataFrame,
    n_components: int = 2,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, PCA, Dict[str, Any]]:
    """
    Perform Principal Component Analysis (PCA) on standardized telemetry features.

    Args:
        df_standardized: DataFrame of standardized feature values (drivers as rows).
        n_components: Number of principal components (default: 2).
        random_state: Random seed for reproducibility.

    Returns:
        Tuple containing:
        - df_pca: DataFrame with projected coordinates (PC1, PC2, ...) indexed by driver.
        - pca_model: Fitted sklearn PCA object.
        - pca_summary: Dict with explained variance ratio and cumulative variance.
    """
    pca = PCA(n_components=n_components, random_state=random_state)
    pca_results = pca.fit_transform(df_standardized)

    col_names = [f"PC{i+1}" for i in range(n_components)]
    df_pca = pd.DataFrame(
        data=pca_results,
        columns=col_names,
        index=df_standardized.index,
    )

    summary = {
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "cumulative_variance": float(np.sum(pca.explained_variance_ratio_)),
        "n_components": n_components,
    }

    return df_pca, pca, summary


def compute_pca_loadings(
    pca_model: PCA,
    feature_names: list,
    n_components: int = 2,
) -> pd.DataFrame:
    """
    Extract the feature loadings (eigenvector coefficients) for each principal component.

    Args:
        pca_model: Fitted PCA model.
        feature_names: Original list of feature column names.
        n_components: Number of components to extract loadings for.

    Returns:
        DataFrame of feature loadings (features as rows, PC1, PC2 as columns).
    """
    loadings = pca_model.components_[:n_components].T
    col_names = [f"PC{i+1}" for i in range(n_components)]
    df_loadings = pd.DataFrame(
        data=loadings,
        index=feature_names,
        columns=col_names,
    )
    return df_loadings


def perform_tsne(
    df_standardized: pd.DataFrame,
    n_components: int = 2,
    perplexity: float = 5.0,
    n_iter: int = 1000,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, TSNE]:
    """
    Perform t-Distributed Stochastic Neighbor Embedding (t-SNE) for non-linear manifold projection.

    Args:
        df_standardized: Standardized telemetry feature DataFrame.
        n_components: Dimensions of embedded space (2 for 2D plot).
        perplexity: Balance between local and global data topology.
        n_iter: Maximum number of iterations.
        random_state: Random state seed.

    Returns:
        Tuple of (df_tsne, tsne_model).
    """
    # Adjust perplexity if sample size is very small
    n_samples = len(df_standardized)
    effective_perplexity = min(perplexity, max(1.0, (n_samples - 1) / 3.0))

    tsne = TSNE(
        n_components=n_components,
        perplexity=effective_perplexity,
        max_iter=n_iter,
        random_state=random_state,
    )
    tsne_results = tsne.fit_transform(df_standardized)

    col_names = [f"TSNE{i+1}" for i in range(n_components)]
    df_tsne = pd.DataFrame(
        data=tsne_results,
        columns=col_names,
        index=df_standardized.index,
    )

    return df_tsne, tsne

