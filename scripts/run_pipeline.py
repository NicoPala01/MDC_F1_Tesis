"""
End-to-end CLI runner for F1 Driver Driving Style Clustering Pipeline.
Master's Thesis Project - Universidad Austral
"""

import argparse
import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from f1_style_clustering.config import load_config, load_circuit_config
from f1_style_clustering.data.loader import load_session, enable_cache
from f1_style_clustering.features.zoi import extract_circuit_zones
from f1_style_clustering.features.aggregators import build_session_feature_matrix
from f1_style_clustering.features.preprocessor import normalize_relative_to_mean, standardize_features
from f1_style_clustering.models.dimensionality import perform_pca, compute_pca_loadings, perform_tsne
from f1_style_clustering.models.clustering import fit_kmeans
from f1_style_clustering.models.evaluation import evaluate_clustering, find_optimal_k
from f1_style_clustering.analysis.archetypes import characterize_clusters, assign_archetype_names, get_driver_archetype_summary
from f1_style_clustering.analysis.teammates import compare_teammates
from f1_style_clustering.visualization.cluster_plots import plot_pca_clusters, plot_optimal_k_evaluation, plot_pca_biplot
from f1_style_clustering.visualization.radar_charts import plot_cluster_radar_chart


def run_single_session_pipeline(
    season: int = 2025,
    grand_prix: str = "Italian Grand Prix",
    session_type: str = "R",
    k_clusters: int = 3,
    output_dir: str = "results",
    save_plots: bool = True,
):
    print(f"\n{'='*70}")
    print(f"F1 DRIVING STYLE CLUSTERING PIPELINE")
    print(f"Season: {season} | Grand Prix: {grand_prix} | Session: {session_type}")
    print(f"{'='*70}\n")

    out_path = Path(output_dir)
    data_dir = out_path / "data"
    fig_dir = out_path / "figures"
    data_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Session
    print("[1/7] Loading FastF1 session data...")
    enable_cache("cache")
    session = load_session(year=season, grand_prix=grand_prix, session_type=session_type)
    print(f"      Loaded: {session.event.EventName} - {session.name} ({len(session.drivers)} drivers)")

    # 2. Extract Zones of Interest
    print("[2/7] Extracting circuit Zones of Interest (ZOIs)...")
    analysis_zones = extract_circuit_zones(session)
    print(f"      Identified {len(analysis_zones)} corner analysis zones.")

    # 3. Build Feature Matrix
    print("[3/7] Computing telemetry metrics and aggregating driver features...")
    df_raw = build_session_feature_matrix(session, analysis_zones=analysis_zones)
    if df_raw.empty:
        print("ERROR: No valid driver features could be extracted.")
        return

    print(f"      Extracted {df_raw.shape[0]} drivers x {df_raw.shape[1]} features.")
    raw_csv = data_dir / f"features_raw_{season}_{session.event.EventName.replace(' ', '_')}_{session_type}.csv"
    df_raw.to_csv(raw_csv)
    print(f"      Saved raw features: {raw_csv}")

    # 4. Normalization and Standardization
    print("[4/7] Normalizing and standardizing features (Z-scores)...")
    df_norm, df_meta = normalize_relative_to_mean(df_raw)
    df_scaled, _, scaler = standardize_features(df_norm)
    scaled_csv = data_dir / f"features_standardized_{season}_{session.event.EventName.replace(' ', '_')}_{session_type}.csv"
    df_scaled.to_csv(scaled_csv)

    # 5. Dimensionality Reduction (PCA)
    print("[5/7] Performing PCA dimensionality reduction...")
    df_pca, pca_model, pca_summary = perform_pca(df_scaled, n_components=2)
    loadings = compute_pca_loadings(pca_model, df_scaled.columns.tolist())
    var_exp = pca_summary['cumulative_variance'] * 100
    print(f"      PCA: 2 components explain {var_exp:.1f}% of total variance.")

    # 6. Unsupervised Clustering & Evaluation
    print(f"[6/7] Fitting K-Means (k={k_clusters}) and evaluating clustering...")
    df_eval = find_optimal_k(df_scaled, k_min=2, k_max=min(6, len(df_scaled) - 1))
    cluster_labels, km_model = fit_kmeans(df_scaled, n_clusters=k_clusters)
    metrics = evaluate_clustering(df_scaled, cluster_labels, km_model)
    print(f"      Silhouette Score: {metrics.silhouette:.3f} | Davies-Bouldin: {metrics.davies_bouldin:.3f}")

    # Archetype characterization
    profiles = characterize_clusters(df_scaled, cluster_labels)
    archetype_names = assign_archetype_names(profiles)
    df_summary = get_driver_archetype_summary(df_scaled, cluster_labels, df_meta)

    print("\n--- Driver Archetype Summary ---")
    print(df_summary[["Cluster", "Archetype", "Team"] if "Team" in df_summary.columns else ["Cluster", "Archetype"]])

    summary_csv = data_dir / f"driver_clusters_summary_{season}_{session.event.EventName.replace(' ', '_')}_{session_type}.csv"
    df_summary.to_csv(summary_csv)

    # Teammate comparison
    if df_meta is not None and "Team" in df_meta.columns:
        teammates_df = compare_teammates(df_scaled, df_meta)
        if not teammates_df.empty:
            print("\n--- Teammate Style Distance ---")
            print(teammates_df[["Team", "Driver_1", "Driver_2", "Style_Euclidean_Distance"]])
            tm_csv = data_dir / f"teammates_comparison_{season}_{session.event.EventName.replace(' ', '_')}_{session_type}.csv"
            teammates_df.to_csv(tm_csv, index=False)

    # 7. Visualization & Plots
    if save_plots:
        print("\n[7/7] Generating and saving visualization figures...")
        # PCA Clusters
        fig_pca = plot_pca_clusters(df_pca, cluster_labels, pca_summary, archetype_names=archetype_names)
        fig_pca.savefig(fig_dir / f"pca_clusters_{season}_{session.event.EventName.replace(' ', '_')}.png", dpi=300)
        plt.close(fig_pca)

        # Biplot
        fig_biplot = plot_pca_biplot(df_pca, loadings, cluster_labels=cluster_labels)
        fig_biplot.savefig(fig_dir / f"pca_biplot_{season}_{session.event.EventName.replace(' ', '_')}.png", dpi=300)
        plt.close(fig_biplot)

        # Optimal k
        fig_k = plot_optimal_k_evaluation(df_eval)
        fig_k.savefig(fig_dir / f"optimal_k_eval_{season}_{session.event.EventName.replace(' ', '_')}.png", dpi=300)
        plt.close(fig_k)

        # Radar
        if df_scaled.shape[1] >= 4:
            fig_radar = plot_cluster_radar_chart(profiles, features=df_scaled.columns[:6].tolist(), archetype_names=archetype_names)
            fig_radar.savefig(fig_dir / f"radar_archetypes_{season}_{session.event.EventName.replace(' ', '_')}.png", dpi=300)
            plt.close(fig_radar)

        print(f"      All figures saved to {fig_dir}/")

    print(f"\nPipeline finished successfully! Outputs stored in '{output_dir}/'\n")


def main():
    parser = argparse.ArgumentParser(description="F1 Driver Driving Style Clustering Pipeline")
    parser.add_argument("--season", type=int, default=2025, help="Championship season year (default: 2025)")
    parser.add_argument("--circuit", type=str, default="Italian Grand Prix", help="Grand Prix name or round number")
    parser.add_argument("--session", type=str, default="R", choices=["R", "Q", "FP1", "FP2", "FP3", "SQ", "S"], help="Session type")
    parser.add_argument("--k-clusters", type=int, default=3, help="Number of clusters for K-Means (default: 3)")
    parser.add_argument("--output-dir", type=str, default="results", help="Directory to store results and figures")
    parser.add_argument("--no-plots", action="store_true", help="Disable figure rendering and export")

    args = parser.parse_args()

    run_single_session_pipeline(
        season=args.season,
        grand_prix=args.circuit,
        session_type=args.session,
        k_clusters=args.k_clusters,
        output_dir=args.output_dir,
        save_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main()

