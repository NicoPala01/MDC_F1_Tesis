"""CLI: one race (--smoke / --circuit) or a full season (--season YEAR)."""

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from f1_style_clustering.analysis.teammates import compare_teammates
from f1_style_clustering.config import load_circuit_config, load_config
from f1_style_clustering.data.loader import enable_cache, load_session
from f1_style_clustering.pipeline import run_pipeline
from f1_style_clustering.season import (
    print_pipeline_summary,
    resolve_event_name,
    run_season_pipeline,
    session_output_dir,
    write_session_outputs,
)


def run_single_session(
    year: int,
    grand_prix: str,
    session_type: str = "R",
    output_dir: str = "results",
    save_plots: bool = True,
    k_clusters=None,
    aggregation=None,
    push_mode=None,
    use_pca_fit=None,
    driver_bootstrap=True,
    compare_aggregators=True,
    residualize=True,
):
    cfg = load_config()
    circuits = load_circuit_config()
    event_name = resolve_event_name(grand_prix, circuits)
    print(f"[1] {year} {event_name} {session_type}")

    cache_dir = (cfg.get("general") or {}).get("cache_dir", "cache")
    enable_cache(cache_dir)
    session = load_session(year=year, grand_prix=event_name, session_type=session_type)

    print("[2] ZOIs → per-lap features → driver vectors → K-means")
    result = run_pipeline(
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
        return result

    dest = session_output_dir(output_dir, year, event_name)
    write_session_outputs(result, dest, save_plots=save_plots)
    print_pipeline_summary(result, str(dest))

    df_summary = result["df_summary"]
    cols = [c for c in ["Cluster", "Archetype", "Team", "n_laps"] if c in df_summary.columns]
    print(df_summary[cols] if cols else df_summary)

    df_scaled = result["df_scaled"]
    df_meta = result["df_meta"]
    if df_meta is not None and "Team" in df_meta.columns:
        teammates_df = compare_teammates(df_scaled, df_meta)
        if not teammates_df.empty:
            teammates_df.to_csv(dest / "teammates.csv", index=False)
            print_cols = [
                c
                for c in ["Team", "Driver_1", "Driver_2", "Style_Euclidean_Distance", "Status"]
                if c in teammates_df.columns
            ]
            print(teammates_df[print_cols])

    print(f"wrote {dest}")
    return result


def main():
    parser = argparse.ArgumentParser(description="F1 driving-style clustering")
    parser.add_argument("--smoke", action="store_true", help="Italian Grand Prix (Monza) only")
    parser.add_argument("--season", type=int, default=None, help="Run every race of this year")
    parser.add_argument("--year", type=int, default=2025, help="Year for --smoke / --circuit")
    parser.add_argument("--circuit", type=str, default=None, help="Single GP name or alias (monza)")
    parser.add_argument("--session", type=str, default="R", choices=["R", "Q", "FP1", "FP2", "FP3", "SQ", "S"])
    parser.add_argument("--k-clusters", type=int, default=None)
    parser.add_argument("--aggregator", type=str, default=None, choices=["median", "mean"])
    parser.add_argument("--push-mode", action="store_true")
    parser.add_argument("--pca-fit", action="store_true")
    parser.add_argument("--no-driver-bootstrap", action="store_true")
    parser.add_argument("--no-mean-median-ari", action="store_true")
    parser.add_argument("--no-residualize", action="store_true")
    parser.add_argument("--output-dir", type=str, default="results")
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()

    shared = dict(
        k_clusters=args.k_clusters,
        aggregation=args.aggregator,
        push_mode=True if args.push_mode else None,
        use_pca_fit=args.pca_fit,
        driver_bootstrap=not args.no_driver_bootstrap,
        compare_aggregators=not args.no_mean_median_ari,
        residualize=not args.no_residualize,
        save_plots=not args.no_plots,
        output_dir=args.output_dir,
    )

    if args.season is not None and not args.smoke:
        run_season_pipeline(year=args.season, session_type=args.session, **shared)
        return

    circuit = args.circuit
    if args.smoke or circuit is None:
        circuit = "Italian Grand Prix"
    run_single_session(
        year=args.year,
        grand_prix=circuit,
        session_type=args.session,
        **shared,
    )


if __name__ == "__main__":
    main()
