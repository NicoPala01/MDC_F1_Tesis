"""Separation benchmark on the Monza 2025 lap matrix.

Compares feature sets (all style columns / without near-constant columns /
ICC-selected), scalers (robust / z-score), sample units (laps / 5-lap block
medians) and algorithms (K-means, k-medians, GMM, Ward, cosine average
linkage, spectral, HDBSCAN) across k. For every fit it reports silhouette,
Davies-Bouldin, Calinski-Harabasz, Dunn, the permutation-null silhouette gap,
AMI with Driver / Team / Compound and the mean per-driver modal fraction. It
also runs the k selectors (gap statistic, prediction strength, GMM BIC/ICL)
and the driver-level energy-distance clustering.

Run from the repo root with a FastF1 cache available:

    python scripts/monza_separation_benchmark.py [--year 2025] [--circuit "Italian Grand Prix"]
                                                 [--out results/2025/italian_grand_prix/separation]
                                                 [--quick]

The main K-means path in ``pipeline.py`` is not modified. Findings are in
``docs/separacion_algoritmos_metricas.md``.
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler, StandardScaler

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from f1_style_clustering.config import load_circuit_config, load_config  # noqa: E402
from f1_style_clustering.data.loader import enable_cache, load_session  # noqa: E402
from f1_style_clustering.features.aggregators import build_lap_style_matrix  # noqa: E402
from f1_style_clustering.features.screening import (  # noqa: E402
    block_median_matrix,
    icc_by_group,
    near_constant_columns,
    select_features_by_icc,
    style_columns,
)
from f1_style_clustering.features.zoi import extract_circuit_zones, resolve_selected_corners  # noqa: E402
from f1_style_clustering.models.alternatives import benchmark_partitions, cluster_groups_by_distribution  # noqa: E402
from f1_style_clustering.models.dimensionality import pca_for_clustering  # noqa: E402
from f1_style_clustering.models.separation import (  # noqa: E402
    gap_statistic,
    gmm_information_criteria,
    hopkins_statistic,
    prediction_strength_sweep,
    select_k_gap,
)

warnings.filterwarnings("ignore")
META_COLS = ["Driver", "Team", "Compound", "TyreLife"]


def build_matrix(year: int, circuit: str, session_type: str) -> pd.DataFrame:
    cfg = load_config()
    circuits = load_circuit_config()
    enable_cache((cfg.get("general") or {}).get("cache_dir", "cache"))
    session = load_session(year=year, grand_prix=circuit, session_type=session_type)
    selected, _source = resolve_selected_corners(session, circuits)
    zones = extract_circuit_zones(session, circuit_config=circuits, selected_corners=selected)
    feat_cfg = cfg.get("features") or {}
    raw = build_lap_style_matrix(
        session,
        analysis_zones=zones,
        circuit_config=circuits,
        push_mode=bool((cfg.get("data_filtering") or {}).get("push_mode", False)),
        min_valid_laps=int((cfg.get("data_filtering") or {}).get("min_valid_laps_per_driver", 3)),
        include_throttle_onset=bool(feat_cfg.get("include_throttle_onset", True)),
    )
    if raw is None or raw.empty:
        raise SystemExit("empty lap matrix")
    return raw


def scale(df: pd.DataFrame, cols, scaler: str) -> np.ndarray:
    block = df[cols].replace([np.inf, -np.inf], np.nan)
    block = block.apply(lambda c: c.fillna(c.median()))
    sc = RobustScaler() if scaler == "robust" else StandardScaler()
    return sc.fit_transform(block)


def spaces(raw: pd.DataFrame, min_icc: float, block_size: int, variance_threshold: float):
    """Yield (name, X, meta, unit) for every feature-set × scaler × unit × PCA combination."""
    style = style_columns(raw)
    constant = near_constant_columns(raw, style)
    sets = {
        "all": style,
        "no_const": [c for c in style if c not in constant],
        f"icc>={min_icc}": select_features_by_icc(raw, style, min_icc=min_icc),
    }
    blocks = block_median_matrix(raw, style, block_size=block_size)
    for set_name, cols in sets.items():
        for scaler in ("robust", "zscore"):
            for unit, frame in (("lap", raw), (f"block{block_size}", blocks)):
                X = scale(frame, cols, scaler)
                meta = frame[[c for c in META_COLS if c in frame.columns]].reset_index(drop=True)
                yield f"{set_name}|{scaler}|{unit}|direct", X, meta, cols
                fit_space, _model, info = pca_for_clustering(pd.DataFrame(X), variance_threshold=variance_threshold, max_features_direct=0)
                yield f"{set_name}|{scaler}|{unit}|pca{info['n_components']}", fit_space.to_numpy(), meta, cols


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--circuit", default="Italian Grand Prix")
    ap.add_argument("--session", default="R")
    ap.add_argument("--out", default=None, help="output directory (default results/<year>/<circuit>/separation)")
    ap.add_argument("--min-icc", type=float, default=0.25)
    ap.add_argument("--block-size", type=int, default=5)
    ap.add_argument("--k-max", type=int, default=5)
    ap.add_argument("--n-perm", type=int, default=5)
    ap.add_argument("--n-boot", type=int, default=0, help="bootstrap ARI per fit (slow)")
    ap.add_argument("--quick", action="store_true", help="only z-score spaces and three methods")
    args = ap.parse_args()

    out_dir = Path(args.out) if args.out else _ROOT / "results" / str(args.year) / args.circuit.lower().replace(" ", "_") / "separation"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = build_matrix(args.year, args.circuit, args.session)
    style = style_columns(raw)
    print(f"laps={len(raw)} drivers={raw['Driver'].nunique()} style_cols={len(style)}")

    icc_table = icc_by_group(raw, style)
    icc_table.to_csv(out_dir / "feature_icc.csv", index=False)
    print(icc_table.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    constant = near_constant_columns(raw, style)
    selected = select_features_by_icc(raw, style, min_icc=args.min_icc)
    print(f"near-constant: {constant}")
    print(f"ICC >= {args.min_icc}: {selected}")

    min_size = max(3, int(np.ceil(0.05 * len(raw))))
    cfg = load_config()
    var_thr = float(((cfg.get("dimensionality_reduction") or {}).get("pca") or {}).get("variance_threshold", 0.85))
    methods = ("kmeans", "gmm_full", "ward") if args.quick else ("kmeans", "kmedians", "gmm_full", "ward", "average_cosine", "spectral", "hdbscan")

    frames = []
    hopkins = {}
    for name, X, meta, _cols in spaces(raw, args.min_icc, args.block_size, var_thr):
        if args.quick and "robust" in name:
            continue
        floor = min_size if "|lap|" in name else max(3, int(np.ceil(0.05 * len(X))))
        hopkins[name] = hopkins_statistic(X, random_state=0)
        table = benchmark_partitions(
            X,
            meta=meta,
            methods=methods,
            k_range=range(2, args.k_max + 1),
            min_cluster_size=floor,
            n_perm=args.n_perm,
            n_boot=args.n_boot,
            space_name=name,
        )
        table["n_rows"] = len(X)
        table["n_features"] = X.shape[1]
        table["hopkins"] = hopkins[name]
        frames.append(table)
        best = table[table.get("valid", True) == True].sort_values("silhouette_gap", ascending=False).head(1)  # noqa: E712
        if not best.empty:
            b = best.iloc[0]
            print(
                f"{name:40s} n={len(X):4d} H={hopkins[name]:.3f} best-gap: {b['method']} k={b['k']} "
                f"sil={b['silhouette']:.3f} null={b['null_silhouette']:.3f} gap={b['silhouette_gap']:+.3f} AMI_drv={b.get('ami_driver', float('nan')):.3f}"
            )
    bench = pd.concat(frames, ignore_index=True)
    bench.to_csv(out_dir / "separation_benchmark.csv", index=False)

    # k selectors on the two reference spaces: baseline-like (all, robust, PCA) and ICC z-score.
    selectors = {}
    reference = {
        "all|robust|lap|pca": scale(raw, style, "robust"),
        f"icc>={args.min_icc}|zscore|lap|direct": scale(raw, selected, "zscore"),
        f"icc>={args.min_icc}|zscore|block{args.block_size}|direct": scale(block_median_matrix(raw, style, block_size=args.block_size), selected, "zscore"),
    }
    reference["all|robust|lap|pca"] = pca_for_clustering(
        pd.DataFrame(reference["all|robust|lap|pca"]), variance_threshold=var_thr, max_features_direct=0
    )[0].to_numpy()
    for name, X in reference.items():
        gap_df = gap_statistic(X, k_range=range(1, args.k_max + 2), n_refs=10, random_state=0)
        ps_df = prediction_strength_sweep(X, k_range=range(2, args.k_max + 1), n_splits=5, random_state=0)
        ic_df = gmm_information_criteria(X, k_range=range(1, args.k_max + 2), random_state=0)
        selectors[name] = {
            "gap_k": select_k_gap(gap_df),
            "gap": gap_df.to_dict(orient="records"),
            "prediction_strength": ps_df.to_dict(orient="records"),
            "gmm_bic_k": {cov: int(sub.loc[sub["bic"].idxmin(), "k"]) for cov, sub in ic_df.groupby("covariance_type")},
            "gmm_icl_k": {cov: int(sub.loc[sub["icl"].idxmin(), "k"]) for cov, sub in ic_df.groupby("covariance_type")},
            "gmm": ic_df.to_dict(orient="records"),
        }
        print(f"[{name}] gap k*={selectors[name]['gap_k']} BIC k*={selectors[name]['gmm_bic_k']} ICL k*={selectors[name]['gmm_icl_k']} "
              f"PS={[(int(r['k']), round(r['prediction_strength'], 2)) for r in selectors[name]['prediction_strength']]}")

    # Driver-level: energy distance between lap clouds.
    driver_level = {}
    for name, cols in (("no_const", [c for c in style if c not in constant]), (f"icc>={args.min_icc}", selected)):
        X = scale(raw, cols, "zscore")
        for k in range(2, 5):
            res = cluster_groups_by_distribution(X, raw["Driver"].to_numpy(), n_clusters=k)
            driver_level[f"{name}|k={k}"] = {"silhouette_precomputed": res["silhouette_precomputed"], "members": res["members"]}
            print(f"[driver energy {name}] k={k} sil={res['silhouette_precomputed']:.3f} {res['members']}")
    (out_dir / "k_selectors.json").write_text(json.dumps(selectors, indent=2, default=float))
    (out_dir / "driver_energy_clusters.json").write_text(json.dumps(driver_level, indent=2, default=str))
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
