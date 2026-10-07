"""Integrated comparison of feature sets on Monza 2025 (src implementation of the candidate metrics).

Builds the lap matrix with the 17 current columns plus ``EXTENDED_STYLE_FEATURES``
from the exported car data, then compares, on the same laps:

- ``base7_session``: the 7 ICC-selected current columns, session-median normalized (current study).
- ``base7_lapsync``: the same 7, lap-synchronous normalized.
- ``base7_lapsync_tyrefe``: the same 7 after lap-synchronous centring and within-driver Compound/TyreLife effects.
- ``base7_lapsync+new3``: lap-synchronous 7 plus medium release→full, Ascari throttle excess variation,
  Ascari lift-and-coast.
- ``v2``: greedy selection over all lap-synchronous columns (recommended, then by teammate ω²,
  skipping |ρ| > 0.6 with a chosen column).

Units: laps, 5-lap block medians, drivers (energy distance between lap clouds).

    python experiments/telemetry_candidates/integrated/run.py
"""

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from f1_style_clustering.analysis.feature_evaluation import clustering_gain, score_features, teammate_split_rate  # noqa: E402
from f1_style_clustering.features.aggregators import (  # noqa: E402
    CORE_STYLE_FEATURES,
    EXTENDED_STYLE_FEATURES,
    LAP_MATRIX_DROP_COLUMNS,
    assign_missing_typologies,
    collapse_to_driver_lap_typology,
    extract_style_features_from_telemetry,
    lap_vectors_from_typology,
)
from f1_style_clustering.features.preprocessor import (  # noqa: E402
    normalize_lap_synchronous,
    normalize_typology_session_median,
    remove_within_driver_effects,
)
from f1_style_clustering.features.screening import block_median_matrix, select_features_by_icc, style_columns  # noqa: E402
from f1_style_clustering.models.separation import group_energy_distance_matrix  # noqa: E402

warnings.filterwarnings("ignore")
DATA = ROOT / "cache" / "derived" / "2025_italian_grand_prix_r"
OUT = Path(__file__).resolve().parent
NEW3 = ["medium__release_to_full_s", "fast__throttle_excess_tv", "fast__lift_coast_s"]
META = ["Team", "FullName", "Compound", "TyreLife"]


def build_matrix() -> pd.DataFrame:
    cache = OUT / "lap_matrix_extended.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    base = pd.read_csv(DATA / "lap_matrix.csv")
    car = pd.read_pickle(DATA / "car.pkl")
    zones = json.loads((DATA / "zones.json").read_text())
    meta = base.set_index(["Driver", "LapNumber"])[META]
    rows = []
    for (drv, lap), g in car.groupby(["Driver", "LapNumber"]):
        if (drv, lap) not in meta.index:
            continue
        for r in extract_style_features_from_telemetry(g.reset_index(drop=True), zones, include_throttle_onset=False, include_extended=True):
            r.update(Driver=drv, LapNumber=lap, **meta.loc[(drv, lap)].to_dict())
            rows.append(r)
    long_df = assign_missing_typologies(pd.DataFrame(rows))
    cols = [c for c in CORE_STYLE_FEATURES + EXTENDED_STYLE_FEATURES if c in long_df.columns]
    rel = normalize_typology_session_median(long_df, feature_cols=cols)
    vec = lap_vectors_from_typology(collapse_to_driver_lap_typology(rel, feature_cols=cols), feature_cols=cols)
    vec = vec.drop(columns=[c for c in LAP_MATRIX_DROP_COLUMNS if c in vec.columns]).reset_index(drop=True)
    vec.attrs = {}
    vec.to_pickle(cache)
    return vec


def greedy_selection(scores: pd.DataFrame, df: pd.DataFrame, max_rho: float = 0.6, cap: int = 8) -> list:
    chosen = []
    for feat in scores.loc[scores["recommended"]].sort_values("omega2_driver_in_team", ascending=False)["feature"]:
        if all(abs(stats.spearmanr(df[feat], df[c], nan_policy="omit").statistic) <= max_rho for c in chosen):
            chosen.append(feat)
        if len(chosen) >= cap:
            break
    return chosen


def driver_level(df: pd.DataFrame, cols: list, ks=(2, 3, 4), n_boot: int = 10, seed: int = 0) -> list:
    X = StandardScaler().fit_transform(df[cols].to_numpy(dtype=float))
    drivers = df["Driver"].astype(str).to_numpy()
    teams = df.groupby("Driver")["Team"].first()
    D = group_energy_distance_matrix(X, drivers)
    Z = linkage(squareform(D.to_numpy(), checks=False), method="average")
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        Xb = X.copy()
        for d in D.index:
            idx = np.flatnonzero(drivers == d)
            Xb[idx] = X[rng.choice(idx, len(idx))]
        Db = group_energy_distance_matrix(Xb, drivers)
        boots.append(linkage(squareform(Db.to_numpy(), checks=False), method="average"))
    rows = []
    from sklearn.metrics import silhouette_score

    for k in ks:
        lab = fcluster(Z, k, criterion="maxclust") - 1
        sil = float(silhouette_score(D.to_numpy(), lab, metric="precomputed")) if len(set(lab)) > 1 else np.nan
        ari = float(np.mean([adjusted_rand_score(lab, fcluster(b, k, criterion="maxclust") - 1) for b in boots]))
        lab_s = pd.Series(lab, index=D.index)
        split = teammate_split_rate(lab_s.to_numpy(), lab_s.index.to_numpy(), teams.reindex(lab_s.index).to_numpy())
        members = {int(c): sorted(lab_s.index[lab_s == c].tolist()) for c in sorted(set(lab))}
        rows.append({"k": k, "silhouette_energy": sil, "bootstrap_ari": ari, "teammate_split_rate": split,
                     "sizes": sorted(np.bincount(lab).tolist(), reverse=True), "members": members})
    return rows


def main() -> None:
    vec = build_matrix()
    style = style_columns(vec)
    current = [c for c in style if not any(c.endswith("__" + e) for e in EXTENDED_STYLE_FEATURES)]
    base7 = select_features_by_icc(vec, current, min_icc=0.25)
    sync = normalize_lap_synchronous(vec, style)
    sync.attrs = {}
    sync_fe = remove_within_driver_effects(sync, style)
    sync_fe.attrs = {}
    print(f"laps={len(vec)} style={len(style)} base7={base7}")

    scores = score_features(sync, style, reference_cols=current)
    scores.to_csv(OUT / "scores_lapsync_all.csv", index=False)
    v2 = greedy_selection(scores, sync)
    print("v2 =", v2)

    sets = {
        "base7_session": (vec, base7),
        "base7_lapsync": (sync, base7),
        "base7_lapsync_tyrefe": (sync_fe, base7),
        "base7_lapsync+new3": (sync, base7 + NEW3),
        "v2": (sync, v2),
    }
    lap_rows, block_rows, drv_rows = [], [], {}
    for name, (frame, cols) in sets.items():
        g = clustering_gain(frame, cols, [], k_range=(2, 3, 4), n_perm=5, n_boot=10)
        g["set"], g["unit"] = name, "lap"
        lap_rows.append(g)
        blocks = block_median_matrix(frame, cols, block_size=5)
        gb = clustering_gain(blocks, cols, [], k_range=(2, 3, 4), n_perm=5, n_boot=10)
        gb["set"], gb["unit"] = name, "block5"
        block_rows.append(gb)
        drv_rows[name] = driver_level(frame, cols)
    table = pd.concat(lap_rows + block_rows, ignore_index=True)
    table.to_csv(OUT / "comparison.csv", index=False)
    (OUT / "driver_level.json").write_text(json.dumps(drv_rows, indent=2, default=str))
    show = ["unit", "set", "n_features", "k", "sizes", "silhouette", "null_silhouette", "silhouette_gap", "prediction_strength",
            "bootstrap_ari", "ami_driver", "ami_compound", "teammate_split_rate", "lap_span", "tyre_life_span"]
    with pd.option_context("display.width", 260, "display.max_columns", 30):
        print(table[show].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    for name, rows in drv_rows.items():
        for r in rows:
            print(
                f"[driver {name}] k={r['k']} sil={r['silhouette_energy']:.3f} bootARI={r['bootstrap_ari']:.2f} "
                f"split={r['teammate_split_rate']:.2f} {r['members']}"
            )

    # Classes of v2 at k=3 on laps: who is where and what separates them.
    X = StandardScaler().fit_transform(sync[v2].to_numpy(dtype=float))
    lab = KMeans(3, n_init=20, random_state=42).fit_predict(X)
    prof = sync.assign(cls=lab).groupby("cls")[v2].median().T
    tab = pd.crosstab(sync["Driver"], lab)
    tab["modal"] = tab.idxmax(axis=1)
    tab["frac"] = tab.drop(columns="modal").max(axis=1) / tab.drop(columns="modal").sum(axis=1)
    prof.to_csv(OUT / "v2_k3_class_medians.csv")
    tab.to_csv(OUT / "v2_k3_driver_classes.csv")
    print(prof.round(3).to_string())
    print(tab.to_string())
    print("phase: lap medians", sync.assign(cls=lab).groupby("cls")["LapNumber"].median().tolist(),
          "tyre", sync.assign(cls=lab).groupby("cls")["TyreLife"].median().tolist())


if __name__ == "__main__":
    main()
