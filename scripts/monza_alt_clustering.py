"""K-medians, DBSCAN, and t-SNE on the Monza 2025 lap matrix.

Uses the same scaled laps as the race pipeline (onset off, fast throttle
attack removed, residualized, robust-scaled). Does not fit K-means.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from f1_style_clustering.config import load_circuit_config, load_config
from f1_style_clustering.data.loader import enable_cache, load_session
from f1_style_clustering.features.aggregators import build_lap_style_matrix
from f1_style_clustering.features.zoi import extract_circuit_zones, resolve_selected_corners
from f1_style_clustering.models.kmedians import k_medians
from f1_style_clustering.pipeline import _prepare_scaled_fit_space

PERPLEXITY = 30
RANDOM_STATE = 42
K_RANGE = range(2, 8)
MIN_CLUSTER = 3
FIGURE = _ROOT / "docs" / "monza_2025_tsne.png"
OUT_JSON = Path("/tmp/monza_alt.json")


def _style_columns(df: pd.DataFrame) -> list:
    return [c for c in df.columns if "__" in str(c)]


def _driver_rows(labels: pd.Series, drivers: pd.Series, noise_label=None) -> list:
    frame = pd.DataFrame({"Driver": drivers.reindex(labels.index), "label": labels.to_numpy()})
    rows = []
    for driver, grp in frame.groupby("Driver", sort=True):
        n_laps = int(len(grp))
        if noise_label is None:
            use = grp
            n_noise = 0
        else:
            n_noise = int((grp["label"] == noise_label).sum())
            use = grp[grp["label"] != noise_label]
        if use.empty:
            rows.append(
                {
                    "Driver": str(driver),
                    "n_laps": n_laps,
                    "n_noise": n_noise,
                    "n_assigned": 0,
                    "modal": None,
                    "n_modal": 0,
                    "fraction": None,
                    "tie": False,
                }
            )
            continue
        counts = use["label"].value_counts()
        top = int(counts.max())
        tied = sorted(int(v) for v in counts[counts == top].index)
        modal = tied[0]
        rows.append(
            {
                "Driver": str(driver),
                "n_laps": n_laps,
                "n_noise": n_noise,
                "n_assigned": int(len(use)),
                "modal": modal,
                "n_modal": top,
                "fraction": top / float(len(use)),
                "tie": len(tied) > 1,
            }
        )
    return rows


def _knee_eps(k_dist_desc: np.ndarray) -> int:
    """Index of the geometric knee on a descending k-distance curve."""
    y = np.asarray(k_dist_desc, dtype=float)
    x = np.linspace(0.0, 1.0, len(y))
    span = float(y.max() - y.min())
    y_n = (y - y.min()) / span if span > 0 else np.zeros_like(y)
    # Distance from each point to the chord joining the first and last.
    line = y_n[0] + (y_n[-1] - y_n[0]) * x
    return int(np.argmax(np.abs(y_n - line)))


def build_scaled_matrix() -> tuple:
    cfg = load_config()
    circuits = load_circuit_config()
    enable_cache((cfg.get("general") or {}).get("cache_dir", "cache"))
    session = load_session(year=2025, grand_prix="Italian Grand Prix", session_type="R")
    selected, zone_source = resolve_selected_corners(session, circuits)
    zones = extract_circuit_zones(session, circuit_config=circuits, selected_corners=selected)
    include_onset = bool((cfg.get("features") or {}).get("include_throttle_onset", True))
    raw = build_lap_style_matrix(
        session,
        analysis_zones=zones,
        circuit_config=circuits,
        push_mode=False,
        min_valid_laps=int((cfg.get("data_filtering") or {}).get("min_valid_laps_per_driver", 3)),
        include_throttle_onset=include_onset,
    )
    style = _style_columns(raw)
    if include_onset:
        raise SystemExit("include_throttle_onset is true; expected false")
    if "fast__throttle_attack" in raw.columns:
        raise SystemExit("fast__throttle_attack is still in the matrix")
    if "fast__full_throttle_frac" not in raw.columns:
        raise SystemExit("fast__full_throttle_frac is missing")
    if any("onset" in c for c in raw.columns):
        raise SystemExit("throttle onset column is present")
    scaled, meta, _fit, _pca, pca_info, *_rest = _prepare_scaled_fit_space(
        raw,
        scaler_type=str((cfg.get("features") or {}).get("standardization", "robust")),
        residualize=bool((cfg.get("features") or {}).get("residualize_team_tyre", True)),
        prefilter=False,
        variance_threshold=float(
            ((cfg.get("dimensionality_reduction") or {}).get("pca") or {}).get("variance_threshold", 0.85)
        ),
        force_pca=False,
    )
    scaled.attrs = {}
    if meta is not None and not meta.empty:
        meta.attrs = {}
    drivers = raw["Driver"].reindex(scaled.index)
    return raw, scaled, drivers, style, zone_source, pca_info


def choose_k(rows: list) -> dict:
    """Keep the valid k with the highest Manhattan silhouette.

    Valid means every cluster has at least 3 laps and silhouette is defined.
    If none qualify, keep the k with the largest minimum size, then silhouette.
    A silhouette tie keeps the smaller k.
    """
    scored = [r for r in rows if r["silhouette_manhattan"] is not None]
    valid = [r for r in scored if r["min_size"] >= MIN_CLUSTER]
    if valid:
        best_sil = max(r["silhouette_manhattan"] for r in valid)
        tied = [r for r in valid if r["silhouette_manhattan"] == best_sil]
        chosen = sorted(tied, key=lambda r: r["k"])[0]
        rule = "max manhattan silhouette among k with min cluster size >= 3"
        n_valid = len(valid)
    else:
        best_min = max(r["min_size"] for r in rows)
        pool = [r for r in rows if r["min_size"] == best_min and r["silhouette_manhattan"] is not None]
        pool = pool or [r for r in rows if r["min_size"] == best_min]
        best_sil = max(r["silhouette_manhattan"] or -1.0 for r in pool)
        tied = [r for r in pool if (r["silhouette_manhattan"] or -1.0) == best_sil]
        chosen = sorted(tied, key=lambda r: r["k"])[0]
        rule = "no k has min cluster size >= 3 and a silhouette; largest min size, then manhattan silhouette"
        n_valid = 0
    return {"k": int(chosen["k"]), "rule": rule, "n_valid": n_valid}


def main() -> None:
    raw, scaled, drivers, style, zone_source, pca_info = build_scaled_matrix()
    X = scaled.to_numpy(dtype=float)
    print(f"laps={len(scaled)} style={len(style)} scaled_cols={scaled.shape[1]} zone={zone_source}")
    print("scaled", list(scaled.columns))

    k_rows = []
    label_sets = {}
    for k in K_RANGE:
        labels, _centers, cost = k_medians(scaled, n_clusters=k, random_state=RANDOM_STATE, n_init=20)
        sizes = labels.value_counts().sort_index()
        try:
            sil_l1 = float(silhouette_score(X, labels, metric="manhattan"))
        except ValueError:
            sil_l1 = None
        row = {
            "k": int(k),
            "l1_cost": float(cost),
            "silhouette_manhattan": sil_l1,
            "min_size": int(sizes.min()),
            "sizes": {str(int(i)): int(n) for i, n in sizes.items()},
            "drivers": _driver_rows(labels, drivers),
        }
        k_rows.append(row)
        label_sets[int(k)] = labels
        sil_txt = "nan" if sil_l1 is None else f"{sil_l1:.4f}"
        print(
            f"k={k} min={row['min_size']} sizes={sorted(sizes.tolist(), reverse=True)} "
            f"sil_L1={sil_txt} cost={cost:.2f}"
        )

    choice = choose_k(k_rows)
    chosen_k = int(choice["k"])
    print("chosen", choice)

    n_features = int(scaled.shape[1])
    min_samples = int(2 * n_features)
    nn = NearestNeighbors(n_neighbors=min_samples, metric="euclidean")
    nn.fit(X)
    k_dist = nn.kneighbors(X)[0][:, -1]
    order = np.argsort(k_dist)[::-1]
    k_dist_desc = k_dist[order]
    knee_i = _knee_eps(k_dist_desc)
    eps = float(k_dist_desc[knee_i])
    print(
        f"dbscan min_samples={min_samples} knee_index={knee_i} eps={eps:.6f} "
        f"kdist p50={np.median(k_dist):.4f} p90={np.quantile(k_dist, 0.9):.4f} "
        f"p99={np.quantile(k_dist, 0.99):.4f} max={k_dist.max():.4f}"
    )
    db_labels = pd.Series(DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X), index=scaled.index, name="Cluster")
    n_noise = int((db_labels == -1).sum())
    cluster_ids = sorted(int(v) for v in db_labels.unique() if int(v) != -1)
    db_sizes = {str(i): int((db_labels == i).sum()) for i in cluster_ids}
    print(f"dbscan clusters={len(cluster_ids)} noise={n_noise} sizes={db_sizes}")

    tsne = TSNE(
        n_components=2,
        perplexity=PERPLEXITY,
        random_state=RANDOM_STATE,
        init="pca",
        max_iter=1000,
        learning_rate="auto",
    )
    embedding = tsne.fit_transform(X)
    km_labels = label_sets[chosen_k].to_numpy()
    noise = db_labels.to_numpy() == -1

    fig, ax = plt.subplots(figsize=(8.2, 6.2))
    cmap = plt.get_cmap("tab10")
    for lab in sorted(set(int(v) for v in km_labels)):
        mask = (km_labels == lab) & ~noise
        ax.scatter(
            embedding[mask, 0],
            embedding[mask, 1],
            s=18,
            color=cmap(lab % 10),
            label=f"k-medianas {lab}",
            alpha=0.85,
            linewidths=0,
        )
    if noise.any():
        ax.scatter(
            embedding[noise, 0],
            embedding[noise, 1],
            s=28,
            marker="x",
            c="black",
            label=f"ruido DBSCAN (n={int(noise.sum())})",
            zorder=3,
        )
    ax.set_title(f"t-SNE Monza 2025 (perplexity {PERPLEXITY}), color = k-medianas k={chosen_k}")
    ax.set_xlabel("t-SNE 1")
    ax.set_ylabel("t-SNE 2")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=140)
    plt.close(fig)
    print(f"wrote {FIGURE}")

    payload = {
        "n_laps": int(len(scaled)),
        "n_drivers": int(drivers.nunique()),
        "n_style": len(style),
        "style_columns": style,
        "scaled_columns": [str(c) for c in scaled.columns],
        "zone_source": zone_source,
        "pca_unused_for_these_fits": {
            "used_by_kmeans_path": bool(pca_info.get("used")),
            "n_components": pca_info.get("n_components"),
            "cumulative_variance": float(pca_info.get("cumulative_variance", float("nan"))),
        },
        "k_medians": {
            "random_state": RANDOM_STATE,
            "n_init": 20,
            "metric": "manhattan",
            "choice": choice,
            "by_k": k_rows,
        },
        "dbscan": {
            "metric": "euclidean",
            "min_samples": min_samples,
            "min_samples_rule": "2 * n_scaled_features",
            "eps": eps,
            "eps_rule": "geometric knee of the descending distance to the min_samples-th neighbor (self included)",
            "knee_index": knee_i,
            "k_distance_percentiles": {
                "p50": float(np.median(k_dist)),
                "p90": float(np.quantile(k_dist, 0.9)),
                "p95": float(np.quantile(k_dist, 0.95)),
                "p99": float(np.quantile(k_dist, 0.99)),
                "max": float(k_dist.max()),
            },
            "n_clusters": len(cluster_ids),
            "n_noise": n_noise,
            "sizes": db_sizes,
            "drivers": _driver_rows(db_labels, drivers, noise_label=-1),
        },
        "tsne": {
            "perplexity": PERPLEXITY,
            "random_state": RANDOM_STATE,
            "init": "pca",
            "max_iter": 1000,
            "figure": str(FIGURE),
            "colored_by_k": chosen_k,
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    print(f"wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
