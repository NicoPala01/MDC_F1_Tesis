"""Dimensionality reduction, clustering scatter plots, biplots, and validation curves."""

from typing import Optional, Dict, Any, List
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd


def plot_pca_clusters(
    df_pca: pd.DataFrame,
    cluster_labels: pd.Series,
    pca_summary: Optional[Dict[str, Any]] = None,
    df_meta: Optional[pd.DataFrame] = None,
    archetype_names: Optional[Dict[int, str]] = None,
    title: str = "PCA Projection of F1 Driver Driving Styles",
    figsize: tuple = (11, 8),
) -> plt.Figure:
    """
    Plot 2D PCA projection of drivers colored by cluster assignment with driver labels.
    """
    fig, ax = plt.subplots(figsize=figsize)

    plot_df = df_pca.copy()
    plot_df["Cluster"] = cluster_labels
    if archetype_names:
        plot_df["Archetype"] = plot_df["Cluster"].map(archetype_names).fillna("Outlier")
        hue_col = "Archetype"
    else:
        hue_col = "Cluster"

    palette = sns.color_palette("tab10", n_colors=plot_df["Cluster"].nunique())

    sns.scatterplot(
        data=plot_df,
        x="PC1",
        y="PC2",
        hue=hue_col,
        palette=palette,
        s=180,
        alpha=0.9,
        edgecolor="black",
        ax=ax,
    )

    # Annotate driver codes
    for drv in plot_df.index:
        x_val = plot_df.loc[drv, "PC1"]
        y_val = plot_df.loc[drv, "PC2"]
        ax.annotate(
            str(drv),
            (x_val + 0.1, y_val + 0.1),
            fontsize=10,
            fontweight="bold",
            alpha=0.9,
        )

    # Axis labels with variance explained
    if pca_summary and "explained_variance_ratio" in pca_summary:
        var1 = pca_summary["explained_variance_ratio"][0] * 100
        var2 = pca_summary["explained_variance_ratio"][1] * 100
        ax.set_xlabel(f"Principal Component 1 ({var1:.1f}% variance)", fontsize=11)
        ax.set_ylabel(f"Principal Component 2 ({var2:.1f}% variance)", fontsize=11)
    else:
        ax.set_xlabel("Principal Component 1", fontsize=11)
        ax.set_ylabel("Principal Component 2", fontsize=11)

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", title="Driving Style Cluster")
    plt.tight_layout()

    return fig


def plot_pca_biplot(
    df_pca: pd.DataFrame,
    df_loadings: pd.DataFrame,
    cluster_labels: Optional[pd.Series] = None,
    top_n_features: int = 6,
    figsize: tuple = (12, 9),
) -> plt.Figure:
    """
    Biplot displaying both driver scores and top feature loading vectors in the PC1-PC2 plane.
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Drivers scatter
    if cluster_labels is not None:
        plot_df = df_pca.copy()
        plot_df["Cluster"] = cluster_labels
        sns.scatterplot(
            data=plot_df,
            x="PC1",
            y="PC2",
            hue="Cluster",
            palette="tab10",
            s=160,
            alpha=0.85,
            ax=ax,
        )
    else:
        ax.scatter(df_pca["PC1"], df_pca["PC2"], alpha=0.8, s=150, color="#00d2be")

    for drv in df_pca.index:
        ax.annotate(str(drv), (df_pca.loc[drv, "PC1"] + 0.08, df_pca.loc[drv, "PC2"] + 0.08), fontsize=9)

    # Select top features by loading magnitude
    loadings_mag = (df_loadings["PC1"] ** 2 + df_loadings["PC2"] ** 2).sort_values(ascending=False)
    selected_features = loadings_mag.head(top_n_features).index

    # Scaling factor for vectors
    scale_x = df_pca["PC1"].abs().max() * 0.8
    scale_y = df_pca["PC2"].abs().max() * 0.8

    for feat in selected_features:
        vx = df_loadings.loc[feat, "PC1"] * scale_x
        vy = df_loadings.loc[feat, "PC2"] * scale_y

        ax.arrow(0, 0, vx, vy, color="red", alpha=0.7, head_width=0.12, lw=1.5)
        clean_name = feat.replace("_", " ")
        ax.text(vx * 1.15, vy * 1.15, clean_name, color="darkred", fontsize=9, fontweight="bold")

    ax.axhline(0, color="gray", linestyle=":", alpha=0.6)
    ax.axvline(0, color="gray", linestyle=":", alpha=0.6)
    ax.set_title("PCA Biplot: Driver Projections & Telemetry Feature Loadings", fontsize=13, fontweight="bold")
    ax.set_xlabel("PC1", fontsize=11)
    ax.set_ylabel("PC2", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    return fig


def plot_optimal_k_evaluation(
    df_eval: pd.DataFrame,
    figsize: tuple = (12, 5),
) -> plt.Figure:
    """Plot Elbow Inertia and Silhouette score curves side by side."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    # Subplot 1: Elbow method (Inertia)
    ax1.plot(df_eval["k"], df_eval["inertia"], marker="o", lw=2, color="#0072b2")
    ax1.set_title("Elbow Method (Inertia vs k)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Number of Clusters (k)", fontsize=10)
    ax1.set_ylabel("Inertia (Within-Cluster Sum of Squares)", fontsize=10)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Subplot 2: Silhouette Score
    ax2.plot(df_eval["k"], df_eval["silhouette"], marker="s", lw=2, color="#d55e00")
    ax2.set_title("Silhouette Score vs k", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Number of Clusters (k)", fontsize=10)
    ax2.set_ylabel("Silhouette Coefficient", fontsize=10)
    ax2.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    return fig

