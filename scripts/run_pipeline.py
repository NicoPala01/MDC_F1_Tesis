"""
End-to-end CLI runner for F1 Driver Driving Style Clustering — Pipeline B.
Master's Thesis Project - Universidad Austral
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from f1_style_clustering.analysis.teammates import compare_teammates
from f1_style_clustering.config import load_circuit_config, load_config
from f1_style_clustering.data.loader import enable_cache, load_session
from f1_style_clustering.models.dimensionality import compute_pca_loadings
from f1_style_clustering.pipeline import run_pipeline_b
from f1_style_clustering.visualization.cluster_plots import (
    plot_optimal_k_evaluation,
    plot_pca_biplot,
    plot_pca_clusters,
)
from f1_style_clustering.visualization.radar_charts import plot_cluster_radar_chart


def run_single_session_pipeline(
    season: int = 2025,
    grand_prix: str = "Italian Grand Prix",
    session_type: str = "R",
    k_clusters: int = None,
    output_dir: str = "results",
    save_plots: bool = True,
    aggregation: str = None,
    push_mode: bool = None,
    use_pca_fit: bool = False,
    driver_bootstrap: bool = True,
    compare_aggregators: bool = True,
    residualize: bool = True,
):
    print(f"\n{'='*70}")
    print("F1 DRIVING STYLE CLUSTERING — PIPELINE B")
    print("per-lap → typology×session median → driver median → K-means++ (rule-based k)")
    print(f"Season: {season} | Grand Prix: {grand_prix} | Session: {session_type}")
    print(f"{'='*70}\n")

    cfg = load_config()
    circuits = load_circuit_config()

    out_path = Path(output_dir)
    data_dir = out_path / "data"
    fig_dir = out_path / "figures"
    data_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    print("[1/7] Loading FastF1 session data...")
    cache_dir = (cfg.get("general") or {}).get("cache_dir", "cache")
    enable_cache(cache_dir)
    session = load_session(year=season, grand_prix=grand_prix, session_type=session_type)
    print(f"      Loaded: {session.event.EventName} - {session.name} ({len(session.drivers)} drivers)")

    print("[2/7] Extracting disjoint ZOIs from circuits.yaml (wrap-aware)...")
    print("[3/7] Per-lap style features, typology×session median, driver aggregation...")
    print("[4/7] Robust scaling and optional PCA fit space...")
    print("[5/7] Rule-based K-means++ (silhouette ≥ 0.25 else min Davies-Bouldin)...")

    result = run_pipeline_b(
        session,
        config=cfg,
        circuit_config=circuits,
        k_clusters=k_clusters,
        aggregation=aggregation,
        push_mode=push_mode,
        use_pca_fit=use_pca_fit if use_pca_fit else None,
        driver_bootstrap=driver_bootstrap,
        compare_aggregators=compare_aggregators,
        residualize=residualize,
    )
    if result.get("error"):
        print(f"ERROR: {result['error']}")
        return

    df_raw = result["df_raw"]
    df_scaled = result["df_scaled"]
    df_meta = result["df_meta"]
    df_pca = result["df_pca_vis"]
    pca_summary = result["pca_vis_summary"]
    cluster_labels = result["cluster_labels"]
    metrics = result["metrics"]
    profiles = result["profiles"]
    archetype_names = result["archetype_names"]
    df_summary = result["df_summary"]
    df_eval = result["eval_df"]
    radar_features = result["radar_features"]
    k_used = result["k_used"]
    k_rule = result["k_rule"]
    pca_info = result["pca_fit_info"]
    event_slug = session.event.EventName.replace(" ", "_")

    print(f"      Drivers × features: {df_raw.shape[0]} × {df_raw.shape[1]}")
    print(f"      Aggregator: {result['aggregation']} | n_laps reported in metadata")
    print(f"      ZOI corners: {len(result['analysis_zones'])}")
    print(f"      PCA as fit space: {pca_info.get('used')} (n={pca_info.get('n_components')})")
    print(f"      k={k_used} via rule '{k_rule}' | silhouette={metrics.silhouette:.3f} | DB={metrics.davies_bouldin:.3f}")
    ari = result["seed_stability"]
    print(f"      Seed stability mean ARI: {ari['mean_ari']:.3f} (±{ari['std_ari']:.3f})")
    boot = result.get("driver_bootstrap") or {}
    if boot:
        n_eff = boot.get("n_eff", boot.get("n_drivers"))
        method = boot.get("method", "bootstrap")
        print(
            f"      Driver {method} (n_eff={n_eff}) mean ARI: "
            f"{boot.get('mean_ari', float('nan')):.3f} (±{boot.get('std_ari', float('nan')):.3f})"
        )
        conc = boot.get("mean_profile_concordance")
        if conc is not None and conc == conc:
            print(f"      Driver {method} profile concordance: {conc:.3f}")
    mm = result.get("mean_median_ari")
    if mm is not None and mm == mm:
        mm_k = (result.get("mean_median") or {}).get("k", k_used)
        print(f"      Mean vs median ΔARI (aligned k={mm_k}): {float(mm):.3f}")
    decl = result.get("confounding_declaration") or {}
    resid = decl.get("residualized_when_present") or decl.get("residualized_covariates") or []
    print(
        "      Confounding: residualized="
        f"{resid if resid else '[]'}; fuel load and car setup are not in FastF1. "
        "Clusters are perfiles/patrones observables, not causal styles."
    )

    raw_csv = data_dir / f"features_raw_{season}_{event_slug}_{session_type}.csv"
    df_raw.to_csv(raw_csv)
    scaled_csv = data_dir / f"features_standardized_{season}_{event_slug}_{session_type}.csv"
    df_scaled.to_csv(scaled_csv)
    summary_csv = data_dir / f"driver_clusters_summary_{season}_{event_slug}_{session_type}.csv"
    df_summary.to_csv(summary_csv)
    print(f"      Saved: {raw_csv}")

    print("\n--- Driver Archetype Summary (Pipeline B 6–8 features) ---")
    cols = [c for c in ["Cluster", "Archetype", "Team", "n_laps"] if c in df_summary.columns]
    print(df_summary[cols] if cols else df_summary)

    if df_meta is not None and "Team" in df_meta.columns:
        teammates_df = compare_teammates(df_scaled, df_meta)
        if not teammates_df.empty:
            print("\n--- Teammate Style Distance ---")
            print(teammates_df[["Team", "Driver_1", "Driver_2", "Style_Euclidean_Distance"]])
            tm_csv = data_dir / f"teammates_comparison_{season}_{event_slug}_{session_type}.csv"
            teammates_df.to_csv(tm_csv, index=False)

    if save_plots:
        print("\n[7/7] Generating visualization figures (radar = same 6–8 fit features)...")
        fig_pca = plot_pca_clusters(df_pca, cluster_labels, pca_summary, archetype_names=archetype_names)
        fig_pca.savefig(fig_dir / f"pca_clusters_{season}_{event_slug}.png", dpi=300)
        plt.close(fig_pca)

        loadings = compute_pca_loadings(result["pca_vis"], df_scaled.columns.tolist())
        fig_biplot = plot_pca_biplot(df_pca, loadings, cluster_labels=cluster_labels)
        fig_biplot.savefig(fig_dir / f"pca_biplot_{season}_{event_slug}.png", dpi=300)
        plt.close(fig_biplot)

        fig_k = plot_optimal_k_evaluation(df_eval)
        fig_k.savefig(fig_dir / f"optimal_k_eval_{season}_{event_slug}.png", dpi=300)
        plt.close(fig_k)

        if radar_features:
            fig_radar = plot_cluster_radar_chart(
                profiles, features=radar_features, archetype_names=archetype_names
            )
            fig_radar.savefig(fig_dir / f"radar_archetypes_{season}_{event_slug}.png", dpi=300)
            plt.close(fig_radar)

        print(f"      All figures saved to {fig_dir}/")

    print(f"\nPipeline B finished. Outputs stored in '{output_dir}/'\n")


def main():
    parser = argparse.ArgumentParser(description="F1 Driver Driving Style Clustering — Pipeline B")
    parser.add_argument("--season", type=int, default=2025, help="Championship season year (default: 2025)")
    parser.add_argument("--circuit", type=str, default="Italian Grand Prix", help="Grand Prix name or round number")
    parser.add_argument("--session", type=str, default="R", choices=["R", "Q", "FP1", "FP2", "FP3", "SQ", "S"], help="Session type")
    parser.add_argument(
        "--k-clusters",
        type=int,
        default=None,
        help="Override K-means k. Default: rule-based selection (silhouette ≥ 0.25 else min Davies-Bouldin).",
    )
    parser.add_argument(
        "--aggregator",
        type=str,
        default=None,
        choices=["median", "mean"],
        help="Driver aggregation after typology×session median (default from YAML: median).",
    )
    parser.add_argument(
        "--push-mode",
        action="store_true",
        help="Also apply FastF1 pick_quicklaps (explicit push mode, not default clean).",
    )
    parser.add_argument(
        "--pca-fit",
        action="store_true",
        help="Force PCA (variance_threshold from YAML) as the clustering fit space.",
    )
    parser.add_argument(
        "--no-driver-bootstrap",
        action="store_true",
        help="Skip driver-level bootstrap/LOO stability (n_eff ≈ n_drivers).",
    )
    parser.add_argument(
        "--mean-median-ari",
        action="store_true",
        default=None,
        help="Force mean-vs-median ΔARI (already on by default).",
    )
    parser.add_argument(
        "--no-mean-median-ari",
        action="store_true",
        help="Skip dual-run mean vs median aggregation ARI.",
    )
    parser.add_argument(
        "--no-residualize",
        action="store_true",
        help="Skip Team/Compound/TyreLife residualization (declaration still printed).",
    )
    parser.add_argument("--output-dir", type=str, default="results", help="Directory to store results and figures")
    parser.add_argument("--no-plots", action="store_true", help="Disable figure rendering and export")

    args = parser.parse_args()

    compare_aggregators = False if args.no_mean_median_ari else True
    run_single_session_pipeline(
        season=args.season,
        grand_prix=args.circuit,
        session_type=args.session,
        k_clusters=args.k_clusters,
        output_dir=args.output_dir,
        save_plots=not args.no_plots,
        aggregation=args.aggregator,
        push_mode=True if args.push_mode else None,
        use_pca_fit=args.pca_fit,
        driver_bootstrap=not args.no_driver_bootstrap,
        compare_aggregators=compare_aggregators,
        residualize=not args.no_residualize,
    )


if __name__ == "__main__":
    main()
