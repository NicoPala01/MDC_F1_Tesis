"""Season runner: per-race lap profiles, season tendency = modal GP archetype."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import matplotlib.pyplot as plt
import pandas as pd

from .config import load_circuit_config, load_config
from .data.loader import enable_cache, get_season_events, load_session
from .models.dimensionality import compute_pca_loadings
from .pipeline import run_pipeline
from .visualization.cluster_plots import (
    plot_optimal_k_evaluation,
    plot_pca_biplot,
    plot_pca_clusters,
)
from .visualization.radar_charts import plot_cluster_radar_chart

logger = logging.getLogger(__name__)

NUMERIC_SKIP = {
    "n_laps",
    "LapsCount",
    "n_races",
    "n_zones",
    "TyreLife",
    "Stint",
}


def event_slug(event_name: str) -> str:
    return (
        str(event_name)
        .strip()
        .lower()
        .replace("–", "-")
        .replace("—", "-")
        .replace(" ", "_")
        .replace("-", "_")
    )


def resolve_event_name(query: str, circuit_config: Optional[Dict[str, Any]] = None) -> str:
    """Map aliases such as 'monza' to the FastF1 event name."""
    circuits = circuit_config if circuit_config is not None else load_circuit_config()
    q = str(query).strip().lower()
    aliases = {
        "monza": "Italian Grand Prix",
        "italy": "Italian Grand Prix",
        "italian": "Italian Grand Prix",
    }
    if q in aliases:
        return aliases[q]
    for key, spec in (circuits.get("benchmark_circuits") or {}).items():
        event = str(spec.get("event_name") or "")
        if q == str(key).lower() or q == event.lower():
            return event
    return str(query)


def session_output_dir(output_dir: str | Path, year: int, event_name: str) -> Path:
    return Path(output_dir) / str(year) / event_slug(event_name)


def season_output_dir(output_dir: str | Path, year: int) -> Path:
    return Path(output_dir) / str(year) / "season"


def iter_race_event_names(year: int) -> List[str]:
    schedule = get_season_events(year)
    names: List[str] = []
    for _, row in schedule.iterrows():
        fmt = str(row.get("EventFormat") or "").lower()
        if fmt in {"testing", "test"}:
            continue
        name = row.get("EventName")
        if name and str(name).strip():
            names.append(str(name))
    return names


def write_session_outputs(
    result: Dict[str, Any],
    dest: Path,
    save_plots: bool = True,
) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    fig_dir = dest / "figures"
    df_raw = result.get("df_raw")
    df_summary = result.get("df_summary")
    if df_raw is not None and hasattr(df_raw, "to_csv"):
        df_raw.to_csv(dest / "features_raw.csv")
    if df_summary is not None and hasattr(df_summary, "to_csv"):
        df_summary.to_csv(dest / "driver_summary.csv")
    for key, filename in (
        ("lap_classifications", "lap_classifications.csv"),
        ("driver_lap_distribution", "driver_lap_distribution.csv"),
        ("driver_laps_by_class", "driver_laps_by_class.csv"),
        ("driver_profiles", "driver_profiles.csv"),
        ("teammates", "teammates.csv"),
    ):
        table = result.get(key)
        if table is None or not hasattr(table, "to_csv") or getattr(table, "empty", True):
            continue
        if key == "driver_profiles" and table.index.name == "Driver" and "Driver" not in table.columns:
            table = table.reset_index()
        table.to_csv(dest / filename, index=False)
    df_scaled = result.get("df_scaled")
    if df_scaled is not None and hasattr(df_scaled, "to_csv"):
        df_scaled.to_csv(dest / "features_scaled.csv")

    if save_plots and not result.get("error"):
        fig_dir.mkdir(parents=True, exist_ok=True)
        df_pca = result.get("df_pca_vis")
        labels = result.get("cluster_labels")
        pca_summary = result.get("pca_vis_summary")
        archetypes = result.get("archetype_names")
        if df_pca is not None and labels is not None:
            fig = plot_pca_clusters(df_pca, labels, pca_summary, archetype_names=archetypes)
            fig.savefig(fig_dir / "pca_clusters.png", dpi=160)
            plt.close(fig)
            pca_vis = result.get("pca_vis")
            df_scaled = result.get("df_scaled")
            if pca_vis is not None and df_scaled is not None:
                loadings = compute_pca_loadings(pca_vis, df_scaled.columns.tolist())
                fig = plot_pca_biplot(df_pca, loadings, cluster_labels=labels)
                fig.savefig(fig_dir / "pca_biplot.png", dpi=160)
                plt.close(fig)
        eval_df = result.get("eval_df")
        if eval_df is not None and not getattr(eval_df, "empty", True):
            fig = plot_optimal_k_evaluation(eval_df)
            fig.savefig(fig_dir / "optimal_k.png", dpi=160)
            plt.close(fig)
        profiles = result.get("profiles")
        radar_features = result.get("radar_features")
        if profiles is not None and radar_features:
            fig = plot_cluster_radar_chart(
                profiles, features=radar_features, archetype_names=archetypes
            )
            fig.savefig(fig_dir / "radar_archetypes.png", dpi=160)
            plt.close(fig)
    return dest


def _numeric_feature_cols(df: pd.DataFrame) -> List[str]:
    cols = []
    for c in df.select_dtypes(include="number").columns:
        if c in NUMERIC_SKIP:
            continue
        cols.append(c)
    return cols


def build_season_driver_matrix(
    per_race_raws: Dict[str, pd.DataFrame],
    min_races: int = 8,
) -> pd.DataFrame:
    """Median of per-race driver vectors. Drivers below ``min_races`` are dropped."""
    frames = []
    for event_name, df in per_race_raws.items():
        if df is None or df.empty:
            continue
        part = df.copy()
        if part.index.name != "Driver":
            if "Driver" in part.columns:
                part = part.set_index("Driver")
        part = part.copy()
        part["Event"] = event_name
        frames.append(part)
    if not frames:
        return pd.DataFrame()

    stacked = pd.concat(frames, axis=0)
    feature_cols = _numeric_feature_cols(stacked)
    n_races = stacked.groupby(level=0).size().rename("n_races")
    median = stacked.groupby(level=0)[feature_cols].median()
    out = median.join(n_races)
    if "Team" in stacked.columns:
        team = stacked.groupby(level=0)["Team"].agg(
            lambda s: s.dropna().mode().iloc[0] if not s.dropna().empty else pd.NA
        )
        out["Team"] = team
    out = out[out["n_races"] >= int(min_races)]
    out.index.name = "Driver"
    return out


def archetype_by_race_table(per_race_summaries: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    series_map = {}
    for event_name, summary in per_race_summaries.items():
        if summary is None or summary.empty or "Archetype" not in summary.columns:
            continue
        series_map[event_name] = summary["Archetype"]
    if not series_map:
        return pd.DataFrame()
    table = pd.DataFrame(series_map)
    table.index.name = "Driver"
    return table


def season_stability(
    archetype_by_race: pd.DataFrame,
    season_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Fraction of races whose per-GP archetype matches the season archetype."""
    if archetype_by_race.empty:
        return pd.DataFrame(columns=["n_races", "agreement", "season_archetype", "modal_race_archetype"])
    global_arch = season_summary["Archetype"] if "Archetype" in season_summary.columns else pd.Series(dtype=str)
    rows = []
    for driver in archetype_by_race.index:
        row = archetype_by_race.loc[driver]
        values = row.dropna()
        n = int(values.shape[0])
        season_name = global_arch.get(driver) if driver in global_arch.index else pd.NA
        if n == 0:
            agree = float("nan")
        else:
            agree = float((values == season_name).mean()) if pd.notna(season_name) else float("nan")
        mode = values.mode().iloc[0] if not values.empty else pd.NA
        rows.append(
            {
                "Driver": driver,
                "n_races": n,
                "agreement": agree,
                "season_archetype": season_name,
                "modal_race_archetype": mode,
            }
        )
    out = pd.DataFrame(rows).set_index("Driver")
    if "Team" in season_summary.columns:
        out["Team"] = season_summary.reindex(out.index)["Team"]
    return out


def season_modal_summary(
    archetype_by_race: pd.DataFrame,
    per_race_summaries: Dict[str, pd.DataFrame],
    min_races: int,
) -> pd.DataFrame:
    """Season profile = the archetype that shows up most often across Grands Prix."""
    if archetype_by_race is None or archetype_by_race.empty:
        return pd.DataFrame()
    rows = []
    for driver in archetype_by_race.index:
        values = archetype_by_race.loc[driver].dropna()
        n = int(values.shape[0])
        if n < int(min_races):
            continue
        mode = values.mode().iloc[0] if not values.empty else pd.NA
        team = pd.NA
        full_name = pd.NA
        for summary in per_race_summaries.values():
            if summary is None or getattr(summary, "empty", True) or driver not in summary.index:
                continue
            if "Team" in summary.columns and pd.notna(summary.loc[driver, "Team"]):
                team = summary.loc[driver, "Team"]
            if "FullName" in summary.columns and pd.notna(summary.loc[driver, "FullName"]):
                full_name = summary.loc[driver, "FullName"]
        rows.append(
            {
                "Driver": driver,
                "FullName": full_name,
                "Team": team,
                "n_races": n,
                "Archetype": mode,
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("Driver")


def print_pipeline_summary(result: Dict[str, Any], heading: str) -> None:
    if result.get("error"):
        print(f"{heading}: ERROR {result['error']}")
        return
    metrics = result.get("metrics")
    sil = getattr(metrics, "silhouette", float("nan")) if metrics is not None else float("nan")
    db = getattr(metrics, "davies_bouldin", float("nan")) if metrics is not None else float("nan")
    n_drivers = result.get("n_drivers_profiled")
    driver_bit = f" drivers={n_drivers}" if n_drivers is not None else ""
    print(
        f"{heading}: n={len(result.get('df_raw', []))}{driver_bit} k={result.get('k_used')} "
        f"rule={result.get('k_rule')} silhouette={sil:.3f} DB={db:.3f} "
        f"zones={result.get('zone_source')}"
    )


def run_season_pipeline(
    year: int = 2025,
    session_type: str = "R",
    output_dir: str = "results",
    config: Optional[Dict[str, Any]] = None,
    circuit_config: Optional[Dict[str, Any]] = None,
    min_races: Optional[int] = None,
    events: Optional[Sequence[str]] = None,
    k_clusters: Optional[int] = None,
    aggregation: Optional[str] = None,
    push_mode: Optional[bool] = None,
    use_pca_fit: Optional[bool] = None,
    driver_bootstrap: Optional[bool] = None,
    compare_aggregators: Optional[bool] = None,
    residualize: Optional[bool] = None,
    save_plots: bool = True,
    load_session_fn=None,
    run_pipeline_fn=None,
) -> Dict[str, Any]:
    """Run the session pipeline on every race. Season tendency is the modal GP archetype."""
    cfg = config if config is not None else load_config()
    circuits = circuit_config if circuit_config is not None else load_circuit_config()
    cache_dir = (cfg.get("general") or {}).get("cache_dir", "cache")
    enable_cache(cache_dir)

    if min_races is None:
        min_races = int((cfg.get("general") or {}).get("min_races_season", 8))

    load_fn = load_session_fn or load_session
    run_fn = run_pipeline_fn or run_pipeline
    event_names = list(events) if events is not None else iter_race_event_names(year)

    per_race_summaries: Dict[str, pd.DataFrame] = {}
    per_race_results: Dict[str, Dict[str, Any]] = {}
    failures: List[Dict[str, str]] = []

    for name in event_names:
        print(f"[season {year}] {name} ({session_type})")
        try:
            session = load_fn(year=year, grand_prix=name, session_type=session_type, cache_dir=cache_dir)
            result = run_fn(
                session,
                config=cfg,
                circuit_config=circuits,
                k_clusters=k_clusters,
                aggregation=aggregation,
                push_mode=push_mode,
                use_pca_fit=use_pca_fit,
                driver_bootstrap=driver_bootstrap,
                compare_aggregators=compare_aggregators,
                residualize=residualize,
            )
        except Exception as exc:
            logger.warning("Skipping %s: %s", name, exc)
            failures.append({"event": name, "error": str(exc)})
            print(f"  skipped: {exc}")
            continue
        if result.get("error"):
            failures.append({"event": name, "error": str(result["error"])})
            print(f"  skipped: {result['error']}")
            continue

        dest = session_output_dir(output_dir, year, name)
        write_session_outputs(result, dest, save_plots=save_plots)
        per_race_summaries[name] = result["df_summary"]
        per_race_results[name] = result
        print_pipeline_summary(result, f"  {event_slug(name)}")

    by_race = archetype_by_race_table(per_race_summaries)
    summary = season_modal_summary(by_race, per_race_summaries, min_races=min_races)
    stability = pd.DataFrame()
    if summary.empty:
        season_result = {
            "df_summary": summary,
            "error": "No drivers met min_races for a season profile.",
            "zone_source": "season_modal",
        }
    else:
        stability = season_stability(by_race, summary)
        stability = stability.loc[stability.index.isin(summary.index)]
        season_result = {
            "df_summary": summary,
            "df_raw": summary,
            "k_used": None,
            "k_rule": "modal_race_archetype",
            "zone_source": "season_modal",
            "n_drivers_profiled": int(summary.shape[0]),
        }
        season_dest = season_output_dir(output_dir, year)
        season_dest.mkdir(parents=True, exist_ok=True)
        summary.to_csv(season_dest / "driver_summary.csv")
        summary.reset_index().to_csv(season_dest / "driver_profiles.csv", index=False)
        by_race.to_csv(season_dest / "archetype_by_race.csv")
        stability.to_csv(season_dest / "stability.csv")
        print_pipeline_summary(season_result, f"[season {year} modal]")

    return {
        "year": year,
        "events": event_names,
        "per_race": per_race_results,
        "failures": failures,
        "season_matrix": summary,
        "season_result": season_result,
        "archetype_by_race": by_race,
        "stability": stability,
        "min_races": min_races,
    }
