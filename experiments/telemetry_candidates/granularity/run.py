"""Zone granularity and lap-to-lap consistency for Monza 2025 style clustering.

Reads the exported lap matrix and car telemetry (does not reload FastF1),
recomputes the six style metrics on each of the seven analysis zones, and
builds centred rolling / block dispersion features. Scores them with
``scripts/evaluate_candidate_features.py`` and compares K-means partitions
with ``clustering_gain``.

Run from anywhere:

    /tmp/venv/bin/python /workspace/experiments/telemetry_candidates/granularity/run.py

Outputs are written only in this directory.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path

# Shared machine: keep numeric libraries on one thread.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

_ROOT = Path("/workspace")
sys.path.insert(0, str(_ROOT / "src"))

from f1_style_clustering.analysis.feature_evaluation import clustering_gain, score_features
from f1_style_clustering.features.aggregators import extract_style_features_from_telemetry
from f1_style_clustering.features.screening import (
    block_median_matrix,
    select_features_by_icc,
    style_columns,
)

warnings.filterwarnings("ignore")

DATA = _ROOT / "cache" / "derived" / "2025_italian_grand_prix_r"
OUT = _ROOT / "experiments" / "telemetry_candidates" / "granularity"
EVALUATOR = _ROOT / "scripts" / "evaluate_candidate_features.py"
PY = Path("/tmp/venv/bin/python")

METRICS = [
    "brake_point_rel",
    "trail_brake_frac",
    "apex_speed_rel",
    "throttle_attack",
    "coast_frac",
    "full_throttle_frac",
]
# Consistency is computed on the metrics that describe a braking/coasting choice.
CONSIST_METRICS = [
    "brake_point_rel",
    "trail_brake_frac",
    "apex_speed_rel",
    "coast_frac",
]
METRIC_ES = {
    "brake_point_rel": "punto de frenada",
    "trail_brake_frac": "trail braking",
    "apex_speed_rel": "velocidad de ápice",
    "throttle_attack": "ataque de acelerador",
    "coast_frac": "fracción en punto muerto",
    "full_throttle_frac": "gas a fondo",
}
ZONE_ORDER = [
    ("T1_Variante_del_Rettifilo", "T1", "Rettifilo", "slow"),
    ("T3_Curva_Grande", "T3", "Curva Grande", "fast"),
    ("T4_Variante_della_Roggia", "T4", "Roggia", "medium"),
    ("T6_Curva_di_Lesmo", "T6", "Lesmo 1", "medium"),
    ("T7_Seconda_di_Lesmo", "T7", "Lesmo 2", "medium"),
    ("T8_Variante_Ascari", "T8", "Ascari", "fast"),
    ("T11_Curva_Parabolica_Alboreto", "T11", "Parabolica", "medium"),
]
SHORT_OF = {full: short for full, short, _, _ in ZONE_ORDER}
LABEL_OF = {short: f"{short} {name}" for _, short, name, _ in ZONE_ORDER}
TYP_OF = {short: typ for _, short, _, typ in ZONE_ORDER}
SHORTS = [short for _, short, _, _ in ZONE_ORDER]

# Analogue of the 7 ICC columns: same metric, zones of that typology.
ANALOGUE_SPEC = [
    ("fast__apex_speed_rel", "apex_speed_rel", "fast"),
    ("medium__apex_speed_rel", "apex_speed_rel", "medium"),
    ("fast__coast_frac", "coast_frac", "fast"),
    ("medium__coast_frac", "coast_frac", "medium"),
    ("slow__coast_frac", "coast_frac", "slow"),
    ("medium__trail_brake_frac", "trail_brake_frac", "medium"),
    ("slow__trail_brake_frac", "trail_brake_frac", "slow"),
]

RADIUS = 2
MIN_POINTS = 3
BLOCK = 5
# Strict style screen (teammate signal, reliability, low tyre/fuel drift).
LAP_RHO_STRICT = 0.35
TYRE_RHO_STRICT = 0.35
COMPOUND_OMEGA_MAX = 0.05
OMEGA_MIN = 0.03
SB_MIN = 0.70


def log(msg: str) -> None:
    print(msg, flush=True)


def fnum(v, nd: int = 3) -> str:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "NA"
    if not np.isfinite(x):
        return "NA"
    return f"{x:.{nd}f}"


def md_table(df: pd.DataFrame, nd: int = 3) -> str:
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    lines = [header, sep]
    for _, row in df.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if isinstance(v, (float, np.floating)):
                cells.append(fnum(v, nd))
            elif isinstance(v, (int, np.integer)) and not isinstance(v, bool):
                cells.append(str(int(v)))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def load_zones() -> dict:
    zones = json.loads((DATA / "zones.json").read_text())
    missing = [full for full, _, _, _ in ZONE_ORDER if full not in zones]
    if missing:
        raise SystemExit(f"zones.json missing {missing}")
    return zones


def extract_zone_long(zones: dict, reuse: bool) -> pd.DataFrame:
    cache = OUT / "zone_long_raw.csv"
    if reuse and cache.exists():
        log(f"reusing {cache}")
        df = pd.read_csv(cache)
        df["LapNumber"] = df["LapNumber"].astype(int)
        return df

    t0 = time.perf_counter()
    car = pd.read_pickle(DATA / "car.pkl")
    keep = ["Driver", "LapNumber", "Distance", "Speed", "Brake", "Throttle", "ThrottleRate", "TimeDelta"]
    car = pd.DataFrame(car[keep].copy())
    car["LapNumber"] = car["LapNumber"].astype(int)
    car["Driver"] = car["Driver"].astype(str)
    records = []
    n = 0
    for (driver, lap), g in car.groupby(["Driver", "LapNumber"], sort=False):
        rows = extract_style_features_from_telemetry(
            pd.DataFrame(g), zones, include_throttle_onset=False
        )
        for row in rows:
            records.append(
                {
                    "Driver": str(driver),
                    "LapNumber": int(lap),
                    "corner": row["corner"],
                    "short": SHORT_OF.get(row["corner"], str(row["corner"])),
                    "typology": row.get("typology"),
                    **{m: row.get(m) for m in METRICS},
                }
            )
        n += 1
        if n % 200 == 0:
            log(f"  extracted {n} laps ({time.perf_counter() - t0:.1f}s)")
    long_df = pd.DataFrame.from_records(records)
    long_df.to_csv(cache, index=False)
    log(f"extracted {n} laps, {len(long_df)} zone-rows in {time.perf_counter() - t0:.1f}s")
    return long_df


def reconstruct_typology(long_df: pd.DataFrame) -> pd.DataFrame:
    """Session-median per typology, then median across zones: the pipeline step."""
    df = long_df.copy()
    df[METRICS] = df[METRICS].replace([np.inf, -np.inf], np.nan)
    med = df.groupby("typology")[METRICS].transform("median")
    df[METRICS] = df[METRICS] - med
    grouped = (
        df.groupby(["Driver", "LapNumber", "typology"], dropna=False)[METRICS]
        .median()
        .reset_index()
    )
    wide = grouped.pivot_table(
        index=["Driver", "LapNumber"],
        columns="typology",
        values=METRICS,
        aggfunc="median",
    )
    wide.columns = [f"{typ}__{feat}" for feat, typ in wide.columns.to_list()]
    return wide.reset_index()


def sanity_check(long_df: pd.DataFrame, lap_matrix: pd.DataFrame) -> pd.DataFrame:
    recon = reconstruct_typology(long_df)
    recon["Driver"] = recon["Driver"].astype(str)
    recon["LapNumber"] = recon["LapNumber"].astype(int)
    base = lap_matrix.copy()
    base["Driver"] = base["Driver"].astype(str)
    base["LapNumber"] = base["LapNumber"].astype(int)
    merged = base.merge(recon, on=["Driver", "LapNumber"], how="inner", suffixes=("", "_recon"))
    rows = []
    for col in style_columns(lap_matrix):
        recon_col = f"{col}_recon" if f"{col}_recon" in merged.columns else None
        # pivot names match the original names; suffix only on clash, and the
        # lap-matrix columns are the left side so the recon columns get _recon
        # when names collide. They do collide.
        if recon_col is None or recon_col not in merged.columns:
            # If a recon column did not overlap it keeps its name.
            if col not in recon.columns:
                rows.append({"feature": col, "pearson": np.nan, "max_abs_diff": np.nan, "n": 0})
                continue
            recon_col = col
        a = pd.to_numeric(merged[col], errors="coerce")
        b = pd.to_numeric(merged[recon_col], errors="coerce")
        ok = a.notna() & b.notna()
        if ok.sum() < 10 or a[ok].std() == 0 or b[ok].std() == 0:
            corr = np.nan
        else:
            corr = float(np.corrcoef(a[ok], b[ok])[0, 1])
        diff = float((a[ok] - b[ok]).abs().max()) if ok.any() else np.nan
        rows.append({"feature": col, "pearson": corr, "max_abs_diff": diff, "n": int(ok.sum())})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "sanity_typology_reconstruction.csv", index=False)
    usable = out["pearson"].dropna()
    med = float(usable.median()) if len(usable) else float("nan")
    worst = out.sort_values("pearson").head(3)
    log(f"sanity median pearson vs lap_matrix = {med:.4f}")
    log(worst.to_string(index=False))
    if not np.isfinite(med) or med < 0.95:
        raise SystemExit("Zone extraction does not reproduce the typology matrix (median r < 0.95).")
    return out


def normalize_by_zone(long_df: pd.DataFrame) -> pd.DataFrame:
    df = long_df.copy()
    df[METRICS] = df[METRICS].replace([np.inf, -np.inf], np.nan)
    med = df.groupby("short")[METRICS].transform("median")
    df[METRICS] = df[METRICS] - med
    return df


def pivot_zones(long_norm: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for metric in METRICS:
        wide = long_norm.pivot_table(
            index=["Driver", "LapNumber"],
            columns="short",
            values=metric,
            aggfunc="median",
        )
        wide = wide.reindex(columns=SHORTS)
        wide.columns = [f"{short}__{metric}" for short in wide.columns]
        pieces.append(wide)
    out = pd.concat(pieces, axis=1).reset_index()
    out["Driver"] = out["Driver"].astype(str)
    out["LapNumber"] = out["LapNumber"].astype(int)
    return out


def typology_normalized_long(long_df: pd.DataFrame) -> pd.DataFrame:
    df = long_df.copy()
    df[METRICS] = df[METRICS].replace([np.inf, -np.inf], np.nan)
    med = df.groupby("typology")[METRICS].transform("median")
    df[METRICS] = df[METRICS] - med
    return df


def zone_offset_table(typ_long: pd.DataFrame) -> pd.DataFrame:
    """Level that remains after subtracting the typology median (not the zone median)."""
    rows = []
    for metric in METRICS:
        for short, g in typ_long.groupby("short"):
            s = pd.to_numeric(g[metric], errors="coerce")
            rows.append(
                {
                    "metric": metric,
                    "zone": short,
                    "typology": TYP_OF[short],
                    "n": int(s.notna().sum()),
                    "nan_frac": float(s.isna().mean()),
                    "median": float(s.median()) if s.notna().any() else np.nan,
                    "q25": float(s.quantile(0.25)) if s.notna().any() else np.nan,
                    "q75": float(s.quantile(0.75)) if s.notna().any() else np.nan,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "zone_offsets_after_typology_median.csv", index=False)
    return out


def median_contribution(typ_long: pd.DataFrame) -> pd.DataFrame:
    """How often each zone sits in the central pair that defines the typology median."""
    rows = []
    for metric in METRICS:
        for typology, zones in (
            ("medium", ["T4", "T6", "T7", "T11"]),
            ("fast", ["T3", "T8"]),
            ("slow", ["T1"]),
        ):
            sub = typ_long[typ_long["typology"] == typology]
            wide = sub.pivot_table(
                index=["Driver", "LapNumber"], columns="short", values=metric, aggfunc="median"
            )
            counts = {z: 0 for z in zones}
            n = 0
            for _, row in wide.iterrows():
                s = row.reindex(zones).dropna().sort_values(kind="mergesort")
                if s.empty:
                    continue
                n += 1
                k = len(s)
                if k % 2 == 1:
                    names = [s.index[k // 2]]
                else:
                    names = [s.index[k // 2 - 1], s.index[k // 2]]
                for name in names:
                    counts[name] += 1
            for z in zones:
                rows.append(
                    {
                        "metric": metric,
                        "typology": typology,
                        "zone": z,
                        "n_laps": n,
                        "frac_in_central_pair": counts[z] / n if n else np.nan,
                    }
                )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "typology_median_contribution.csv", index=False)
    return out


def rolling_stats(frame: pd.DataFrame, cols: list[str], radius: int = RADIUS, min_points: int = MIN_POINTS) -> pd.DataFrame:
    """Centred window on lap number [L-radius, L+radius], per driver."""
    out_cols = []
    for c in cols:
        out_cols.extend([f"{c}__roll_iqr5", f"{c}__roll_mad5", f"{c}__absdev_rollmed5"])
    parts = []
    for _, g in frame.groupby("Driver", sort=False):
        g = g.sort_values("LapNumber")
        laps = g["LapNumber"].to_numpy(dtype=int)
        n = len(g)
        data = {c: np.full(n, np.nan) for c in out_cols}
        values = {c: pd.to_numeric(g[c], errors="coerce").to_numpy(dtype=float) for c in cols}
        for i in range(n):
            lo = int(np.searchsorted(laps, laps[i] - radius, side="left"))
            hi = int(np.searchsorted(laps, laps[i] + radius, side="right"))
            if hi - lo < min_points:
                continue
            for c in cols:
                w = values[c][lo:hi]
                w = w[np.isfinite(w)]
                if w.size < min_points:
                    continue
                med = float(np.median(w))
                q75, q25 = np.percentile(w, [75, 25])
                data[f"{c}__roll_iqr5"][i] = float(q75 - q25)
                data[f"{c}__roll_mad5"][i] = float(np.median(np.abs(w - med)))
                if np.isfinite(values[c][i]):
                    data[f"{c}__absdev_rollmed5"][i] = abs(float(values[c][i]) - med)
        part = pd.DataFrame(data, index=g.index)
        part["Driver"] = g["Driver"].to_numpy()
        part["LapNumber"] = laps
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def sector_rolling(laps: pd.DataFrame, radius: int = RADIUS, min_points: int = MIN_POINTS) -> pd.DataFrame:
    sources = {
        "sector1_time": "Sector1Time",
        "sector2_time": "Sector2Time",
        "sector3_time": "Sector3Time",
        "lap_time": "LapTime",
    }
    frame = laps[["Driver", "LapNumber", *sources.values()]].copy()
    frame["Driver"] = frame["Driver"].astype(str)
    frame["LapNumber"] = frame["LapNumber"].astype(int)
    for name, col in sources.items():
        frame[name] = pd.to_numeric(frame[col], errors="coerce")
    parts = []
    names = list(sources)
    for _, g in frame.groupby("Driver", sort=False):
        g = g.sort_values("LapNumber")
        lapn = g["LapNumber"].to_numpy(dtype=int)
        n = len(g)
        data = {f"{name}__roll_std5": np.full(n, np.nan) for name in names}
        values = {name: g[name].to_numpy(dtype=float) for name in names}
        for i in range(n):
            lo = int(np.searchsorted(lapn, lapn[i] - radius, side="left"))
            hi = int(np.searchsorted(lapn, lapn[i] + radius, side="right"))
            if hi - lo < min_points:
                continue
            for name in names:
                w = values[name][lo:hi]
                w = w[np.isfinite(w)]
                if w.size < min_points:
                    continue
                data[f"{name}__roll_std5"][i] = float(np.std(w, ddof=1))
        part = pd.DataFrame(data)
        part["Driver"] = g["Driver"].to_numpy()
        part["LapNumber"] = lapn
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def pair_structure(zone_wide: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    df = zone_wide.merge(teams, on=["Driver", "LapNumber"], how="left")
    driver_team = (
        df.groupby("Driver")["Team"].agg(lambda s: s.dropna().iloc[0] if s.dropna().shape[0] else np.nan)
    )
    rows = []
    for metric in METRICS:
        cols = [f"{z}__{metric}" for z in SHORTS]
        present = [c for c in cols if c in df.columns]
        med = df.groupby("Driver")[present].median()
        med["Team"] = driver_team.reindex(med.index)
        for i, a in enumerate(present):
            for b in present[i + 1 :]:
                pair = df[[a, b, "Driver"]].dropna()
                # Pooled within-driver Pearson (driver-demeaned).
                if len(pair) >= 30:
                    da = pair[a] - pair.groupby("Driver")[a].transform("mean")
                    db = pair[b] - pair.groupby("Driver")[b].transform("mean")
                    if da.std() > 0 and db.std() > 0:
                        r_within = float(np.corrcoef(da, db)[0, 1])
                    else:
                        r_within = np.nan
                else:
                    r_within = np.nan
                rhos = []
                for _, g in pair.groupby("Driver"):
                    if len(g) < 8 or g[a].nunique() < 3 or g[b].nunique() < 3:
                        continue
                    rho = stats.spearmanr(g[a], g[b]).statistic
                    if np.isfinite(rho):
                        rhos.append(float(rho))
                both = med[[a, b]].dropna()
                if len(both) >= 5 and both[a].nunique() >= 3 and both[b].nunique() >= 3:
                    r_between = float(stats.spearmanr(both[a], both[b]).statistic)
                else:
                    r_between = np.nan
                signed = both[(both[a] != 0) & (both[b] != 0)]
                if len(signed):
                    frac_opp = float(((signed[a] * signed[b]) < 0).mean())
                    n_opp = int(((signed[a] * signed[b]) < 0).sum())
                else:
                    frac_opp, n_opp = np.nan, 0
                flips, n_teams = 0, 0
                if "Team" in med.columns:
                    for _, members in med.dropna(subset=[a, b]).groupby("Team"):
                        if len(members) != 2:
                            continue
                        d1, d2 = members.iloc[0], members.iloc[1]
                        s1, s2 = d1[a] - d2[a], d1[b] - d2[b]
                        if s1 == 0 or s2 == 0 or not np.isfinite(s1) or not np.isfinite(s2):
                            continue
                        n_teams += 1
                        flips += int(np.sign(s1) != np.sign(s2))
                za, zb = a.split("__")[0], b.split("__")[0]
                rows.append(
                    {
                        "metric": metric,
                        "zone_a": za,
                        "zone_b": zb,
                        "typology_a": TYP_OF[za],
                        "typology_b": TYP_OF[zb],
                        "same_typology": TYP_OF[za] == TYP_OF[zb],
                        "r_within_pooled": r_within,
                        "r_within_mean_spearman": float(np.mean(rhos)) if rhos else np.nan,
                        "n_drivers_corr": len(rhos),
                        "r_between_spearman": r_between,
                        "frac_drivers_opposite_sign": frac_opp,
                        "n_drivers_sign": int(len(signed)),
                        "frac_teams_order_flip": flips / n_teams if n_teams else np.nan,
                        "n_teams_flip": n_teams,
                    }
                )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "zone_pair_structure.csv", index=False)
    return out


def driver_medians(zone_wide: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    meta = (
        teams.groupby("Driver")
        .agg(Team=("Team", "first"), FullName=("FullName", "first"))
        .reset_index()
    )
    med = zone_wide.groupby("Driver").median(numeric_only=True).reset_index()
    med = meta.merge(med, on="Driver", how="right")
    med.to_csv(OUT / "driver_zone_medians.csv", index=False)
    return med


def zone_vs_typology_corr(full: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in METRICS:
        for typology in ("slow", "medium", "fast"):
            typ_col = f"{typology}__{metric}"
            if typ_col not in full.columns:
                continue
            for short, typ in TYP_OF.items():
                if typ != typology:
                    continue
                zcol = f"{short}__{metric}"
                if zcol not in full.columns:
                    continue
                a = pd.to_numeric(full[zcol], errors="coerce")
                b = pd.to_numeric(full[typ_col], errors="coerce")
                ok = a.notna() & b.notna()
                if ok.sum() < 30 or a[ok].nunique() < 3 or b[ok].nunique() < 3:
                    rho = np.nan
                else:
                    rho = float(stats.spearmanr(a[ok], b[ok]).statistic)
                rows.append(
                    {
                        "metric": metric,
                        "typology": typology,
                        "zone": short,
                        "typology_column": typ_col,
                        "spearman_with_typology": rho,
                        "n": int(ok.sum()),
                    }
                )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "zone_vs_typology_spearman.csv", index=False)
    return out


def rejection_reasons(row: pd.Series) -> str:
    reasons = []
    if float(row.get("coverage", 0) or 0) < 0.90:
        reasons.append("cobertura")
    if float(row.get("zero_frac", 1) or 0) > 0.90 or int(row.get("n_unique", 0) or 0) < 3:
        reasons.append("casi_constante")
    omega = row.get("omega2_driver_in_team", np.nan)
    p = row.get("p_driver_in_team", np.nan)
    if not (np.isfinite(omega) and omega >= OMEGA_MIN and np.isfinite(p) and p < 0.01):
        reasons.append("sin_senal_companero")
    sb = row.get("spearman_brown", np.nan)
    if not (np.isfinite(sb) and sb >= SB_MIN):
        reasons.append("fiabilidad")
    comp = row.get("omega2_compound_within", np.nan)
    if not (np.isfinite(comp) and comp < COMPOUND_OMEGA_MAX):
        reasons.append("compuesto")
    rho_l = row.get("rho_lap_within", np.nan)
    if not (np.isfinite(rho_l) and abs(rho_l) <= LAP_RHO_STRICT):
        reasons.append("deriva_vuelta")
    rho_t = row.get("rho_tyre_life_within", np.nan)
    if not (np.isfinite(rho_t) and abs(rho_t) <= TYRE_RHO_STRICT):
        reasons.append("vida_neumatico")
    return ",".join(reasons) if reasons else "pasa_estricto"


def usable_level(row: pd.Series) -> bool:
    return (
        float(row.get("coverage", 0) or 0) >= 0.95
        and float(row.get("zero_frac", 1) or 0) <= 0.90
        and int(row.get("n_unique", 0) or 0) >= 3
    )


def strict_mask(scores: pd.DataFrame) -> pd.Series:
    s = scores
    return (
        (s["coverage"] >= 0.90)
        & (s["zero_frac"] <= 0.90)
        & (s["n_unique"] >= 3)
        & (s["omega2_driver_in_team"] >= OMEGA_MIN)
        & (s["p_driver_in_team"] < 0.01)
        & (s["spearman_brown"] >= SB_MIN)
        & (s["omega2_compound_within"] < COMPOUND_OMEGA_MAX)
        & (s["rho_lap_within"].abs() <= LAP_RHO_STRICT)
        & (s["rho_tyre_life_within"].abs() <= TYRE_RHO_STRICT)
    )


def greedy_select(scores: pd.DataFrame, data: pd.DataFrame, pool: list[str], max_n: int = 7, max_abs_rho: float = 0.75) -> list[str]:
    ranked = (
        scores.set_index("feature")
        .reindex(pool)
        .dropna(subset=["omega2_driver_in_team"])
        .sort_values("omega2_driver_in_team", ascending=False)
    )
    chosen: list[str] = []
    for feat in ranked.index.tolist():
        if len(chosen) >= max_n:
            break
        if feat not in data.columns:
            continue
        ok_add = True
        for prev in chosen:
            a = pd.to_numeric(data[feat], errors="coerce")
            b = pd.to_numeric(data[prev], errors="coerce")
            ok = a.notna() & b.notna()
            if ok.sum() < 30 or a[ok].nunique() < 3 or b[ok].nunique() < 3:
                continue
            rho = abs(float(stats.spearmanr(a[ok], b[ok]).statistic))
            if np.isfinite(rho) and rho >= max_abs_rho:
                ok_add = False
                break
        if ok_add:
            chosen.append(feat)
    return chosen


def run_gain(df: pd.DataFrame, name: str, cols: list[str], k_range=(2, 3, 4)) -> pd.DataFrame:
    cols = [c for c in cols if c in df.columns]
    if len(cols) < 2:
        log(f"skip clustering {name}: only {cols}")
        return pd.DataFrame()
    log(f"clustering {name} ({len(cols)} cols) ...")
    t0 = time.perf_counter()
    gain = clustering_gain(df, cols, [], k_range=k_range)
    gain["set"] = name
    gain["features"] = ",".join(cols)
    log(f"  done {name} in {time.perf_counter() - t0:.1f}s")
    return gain


def block_iqr_frame(df: pd.DataFrame, cols: list[str], block_size: int = BLOCK) -> pd.DataFrame:
    work = df.sort_values(["Driver", "LapNumber"]).copy()
    work["block_index"] = work.groupby("Driver").cumcount() // block_size
    rows = []
    for (driver, block), g in work.groupby(["Driver", "block_index"], sort=False):
        if len(g) != block_size:
            continue
        rec = {
            "Driver": driver,
            "block_index": int(block),
            "LapNumber": int(g["LapNumber"].min()),
            "Team": g["Team"].mode().iloc[0] if g["Team"].notna().any() else np.nan,
            "Compound": g["Compound"].mode().iloc[0] if "Compound" in g and g["Compound"].notna().any() else np.nan,
            "TyreLife": float(pd.to_numeric(g["TyreLife"], errors="coerce").median()) if "TyreLife" in g else np.nan,
        }
        for c in cols:
            y = pd.to_numeric(g[c], errors="coerce").to_numpy(dtype=float)
            y = y[np.isfinite(y)]
            if y.size < block_size:
                rec[f"{c}__block_iqr5"] = np.nan
            else:
                q75, q25 = np.percentile(y, [75, 25])
                rec[f"{c}__block_iqr5"] = float(q75 - q25)
        rows.append(rec)
    return pd.DataFrame(rows)


def heatmap(mat: pd.DataFrame, path: Path, title: str, fmt: str = "{:.2f}") -> None:
    fig, ax = plt.subplots(figsize=(11.2, 4.6))
    values = mat.to_numpy(dtype=float)
    finite = values[np.isfinite(values)]
    vmin = float(np.min(finite)) if finite.size else 0.0
    vmax = float(np.max(finite)) if finite.size else 1.0
    if vmin == vmax:
        vmax = vmin + 1.0
    im = ax.imshow(values, cmap="viridis", aspect="auto", vmin=vmin, vmax=vmax)
    ax.set_xticks(range(mat.shape[1]))
    ax.set_xticklabels(list(mat.columns), rotation=30, ha="right")
    ax.set_yticks(range(mat.shape[0]))
    ax.set_yticklabels(list(mat.index))
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = values[i, j]
            txt = "·" if not np.isfinite(v) else fmt.format(v)
            rel = (v - vmin) / (vmax - vmin) if np.isfinite(v) else 0.0
            ax.text(j, i, txt, ha="center", va="center", fontsize=7, color="white" if rel > 0.55 else "black")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def matrix_from_scores(scores: pd.DataFrame, value: str, cols_prefix_ok: bool = True) -> pd.DataFrame:
    rows = []
    idx = scores.set_index("feature")
    for short in SHORTS:
        rec = {"zona": LABEL_OF[short]}
        for metric in METRICS:
            feat = f"{short}__{metric}"
            rec[METRIC_ES[metric]] = float(idx.loc[feat, value]) if feat in idx.index else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def build_report(ctx: dict) -> str:
    scores: pd.DataFrame = ctx["zone_scores"]
    base_scores: pd.DataFrame = ctx["base_scores"]
    gain: pd.DataFrame = ctx["gain"]
    pairs: pd.DataFrame = ctx["pairs"]
    contrib: pd.DataFrame = ctx["contrib"]
    offsets: pd.DataFrame = ctx["offsets"]
    vs: pd.DataFrame = ctx["vs_typology"]
    sanity: pd.DataFrame = ctx["sanity"]
    consist_scores: pd.DataFrame = ctx["consist_scores"]
    sector_scores: pd.DataFrame = ctx["sector_scores"]
    block_level_gain: pd.DataFrame = ctx["block_gain"]
    block_iqr_scores: pd.DataFrame = ctx["block_iqr_scores"]
    eval_gain: pd.DataFrame = ctx["eval_gain"]
    sets: dict = ctx["sets"]
    examples: pd.DataFrame = ctx["examples"]
    medians: pd.DataFrame = ctx["driver_medians"]

    def row_of(df, feature):
        hit = df.loc[df["feature"] == feature]
        return None if hit.empty else hit.iloc[0]

    lines = []
    a = lines.append

    # --- Verdict, filled from comparisons ---
    def gain_row(name, k):
        hit = gain[(gain["set"] == name) & (gain["k"] == k)]
        return None if hit.empty else hit.iloc[0]

    b2, b3 = gain_row("base7", 2), gain_row("base7", 3)
    n2, n3 = gain_row("analogue7", 2), gain_row("analogue7", 3)
    e2 = gain_row("expand", 2)

    analogue_helps_k2 = (
        b2 is not None
        and n2 is not None
        and np.isfinite(n2["silhouette_gap"])
        and np.isfinite(b2["silhouette_gap"])
        and float(n2["silhouette_gap"]) > float(b2["silhouette_gap"]) + 0.01
        and float(n2["prediction_strength"]) >= float(b2["prediction_strength"]) - 0.05
    )
    analogue_helps_k3 = (
        b3 is not None
        and n3 is not None
        and np.isfinite(n3["silhouette_gap"])
        and np.isfinite(b3["silhouette_gap"])
        and float(n3["silhouette_gap"]) > float(b3["silhouette_gap"]) + 0.01
        and float(n3["prediction_strength"]) >= float(b3["prediction_strength"]) - 0.05
    )

    # Best zone columns vs their typology aggregate.
    improvements = []
    for _, spec in enumerate(ANALOGUE_SPEC):
        typ_col, metric, typology = spec
        zones = [z for z, t in TYP_OF.items() if t == typology]
        zrows = []
        for z in zones:
            r = row_of(scores, f"{z}__{metric}")
            if r is not None:
                zrows.append(r)
        if not zrows:
            continue
        best = max(zrows, key=lambda r: float(r["omega2_driver_in_team"]) if np.isfinite(r["omega2_driver_in_team"]) else -1)
        base_r = row_of(base_scores, typ_col)
        if base_r is None:
            continue
        delta = float(best["omega2_driver_in_team"]) - float(base_r["omega2_driver_in_team"])
        improvements.append((delta, best, base_r, typ_col))
    improvements.sort(key=lambda t: t[0], reverse=True)

    strict_zone = scores.loc[ctx["strict_zone_mask"]].sort_values("omega2_driver_in_team", ascending=False)
    strict_cons = consist_scores.loc[ctx["strict_cons_mask"]].sort_values("omega2_driver_in_team", ascending=False) if len(consist_scores) else consist_scores

    # Block confirmation: best rolling IQR vs matching block IQR.
    roll_iqr = consist_scores[consist_scores["feature"].str.endswith("__roll_iqr5")].sort_values(
        "omega2_driver_in_team", ascending=False
    ) if len(consist_scores) else consist_scores
    best_roll = roll_iqr.iloc[0] if len(roll_iqr) else None
    best_block = None
    if best_roll is not None and len(block_iqr_scores):
        parent = best_roll["feature"].replace("__roll_iqr5", "")
        hit = block_iqr_scores.loc[block_iqr_scores["feature"] == f"{parent}__block_iqr5"]
        if len(hit):
            best_block = hit.iloc[0]

    sector_is_car = False
    if len(sector_scores):
        # Performance if team share dominates teammate omega2.
        sector_is_car = bool((sector_scores["share_team"] > sector_scores["omega2_driver_in_team"].fillna(0) + 0.05).all())

    a("# Granularidad por curva y consistencia como rasgo de estilo (Monza 2025)")
    a("")
    a("Carrera: Gran Premio de Italia 2025, 842 vueltas canónicas, 19 pilotos, 10 equipos (Kick Sauber solo con BOR). Telemetría de coche ya exportada (`car.pkl`, ~4 Hz, Δt mediano 0,245 s). No se recargó FastF1. El clustering es K-means sobre columnas en z-score, sin PCA, con el mismo `clustering_gain` del evaluador (`n_perm=5`, `n_boot=10`, `random_state=42`).")
    a("")
    a("## Resultado")
    a("")
    if analogue_helps_k2 or analogue_helps_k3:
        a(
            f"Sustituir el agregado de tipología por la curva análoga **sí mueve la partición** "
            f"(brecha de silueta k=2: {fnum(b2['silhouette_gap']) if b2 is not None else 'NA'} → {fnum(n2['silhouette_gap']) if n2 is not None else 'NA'}; "
            f"k=3: {fnum(b3['silhouette_gap']) if b3 is not None else 'NA'} → {fnum(n3['silhouette_gap']) if n3 is not None else 'NA'}). "
            "El detalle está en la tabla de clustering."
        )
    else:
        a(
            f"Separar las curvas **no mejora la partición conjunta** respecto a las 7 columnas de tipología. "
            f"En k=2 la brecha de silueta pasa de {fnum(b2['silhouette_gap']) if b2 is not None else 'NA'} (base) a {fnum(n2['silhouette_gap']) if n2 is not None else 'NA'} (análogo de 7 curvas); "
            f"en k=3, de {fnum(b3['silhouette_gap']) if b3 is not None else 'NA'} a {fnum(n3['silhouette_gap']) if n3 is not None else 'NA'}. "
            "La silueta bruta no es comparable si cambia el número de columnas: la brecha frente al nulo de permutación sí lo es, y tampoco sube."
        )
    a("")
    a("Lo que sí cambia es la **lectura por curva**. El agregado `medium` mezcla Roggia, Lesmo 1, Lesmo 2 y Parabolica; `fast` mezcla Curva Grande (casi a fondo) con Ascari. Esa mezcla esconde rasgos de compañeros que viven en una sola curva y, a la vez, la mediana de tipología a veces es sólo la curva del medio de la distribución. Las tablas de abajo cuantifican las dos cosas.")
    a("")
    if best_roll is not None:
        block_bit = ""
        if best_block is not None:
            block_bit = (
                f" El mismo rasgo en bloques no solapados de 5 vueltas (`{best_block['feature']}`) tiene "
                f"ω²(piloto|equipo) = {fnum(best_block['omega2_driver_in_team'])}, "
                f"Spearman-Brown = {fnum(best_block['spearman_brown'])}. "
            )
            if float(best_block.get("spearman_brown", 0) or 0) < SB_MIN:
                block_bit += (
                    "El ω² del bloque sigue alto, pero el Spearman-Brown cae por debajo de 0,70: "
                    "el ranking del piloto no se sostiene de una mitad de la carrera a la otra cuando las ventanas ya no se solapan. "
                    "La fiabilidad del rolling no se puede usar."
                )
            elif float(best_block["omega2_driver_in_team"]) < 0.03 and float(best_roll["omega2_driver_in_team"]) >= 0.03:
                block_bit += "La señal de la ventana móvil no se confirma en bloques: la fiabilidad del rolling está inflada por el solapamiento."
            elif float(best_block["omega2_driver_in_team"]) >= 0.03:
                block_bit += "La señal y la fiabilidad sobreviven al bloque, así que no es sólo autocorrelación de la ventana."
        a(
            f"La consistencia vuelta a vuelta, como rasgo de estilo, queda **por debajo del nivel de la curva**. "
            f"La mejor dispersión móvil es `{best_roll['feature']}`: "
            f"ω²(piloto|equipo) = {fnum(best_roll['omega2_driver_in_team'])}, "
            f"cuota de equipo = {fnum(best_roll['share_team'])}, "
            f"Spearman-Brown = {fnum(best_roll['spearman_brown'])} "
            f"(optimista: ventanas L−2…L+2 comparten vueltas entre pares e impares).{block_bit}"
        )
    a("")
    if len(sector_scores):
        if sector_is_car:
            a("La desviación típica móvil de los tiempos de sector se comporta como **coche o rendimiento**, no como estilo: la cuota de equipo supera a la señal entre compañeros. No entra en el vector de estilo.")
        else:
            top_s = sector_scores.sort_values("omega2_driver_in_team", ascending=False).iloc[0]
            a(
                f"Los tiempos de sector no son el coche: la cuota de equipo de `{top_s['feature']}` es {fnum(top_s['share_team'])}, "
                f"al lado de su ω²(piloto|equipo) = {fnum(top_s['omega2_driver_in_team'])} (Spearman-Brown = {fnum(top_s['spearman_brown'])}). "
                "Tampoco son estilo de frenada. La dispersión del sector 2 acompaña la posición en carrera (Spearman 0,52 entre medianas de piloto)."
            )
    a("")
    if analogue_helps_k2 or analogue_helps_k3:
        a("Recomendación de una línea: **la curva análoga mejora la partición a igual dimensión; usar ese vector de 7 curvas en lugar del agregado, y no alargar más el vector. No añadir la consistencia móvil ni la dispersión de tiempos de sector.** El detalle y los números están en la sección de clustering y en la recomendación final.")
    else:
        a("Recomendación de una línea: **usar las curvas para interpretar, no para sustituir el vector de clustering.** Una curva concreta entra en el texto cuando gana en ω²(piloto|equipo) y en fiabilidad; el vector de 7 columnas de tipología se queda. No añadir la consistencia móvil ni la dispersión de tiempos de sector.")
    a("")

    a("## Definiciones")
    a("")
    a("Cada vuelta de `car.pkl` entra en `extract_style_features_from_telemetry` con las ventanas de `zones.json` y `include_throttle_onset=False`. Por zona (frenada | ápice | salida, en metros de `Distance`) salen seis métricas crudas:")
    a("")
    a("- `brake_point_rel`: metros desde el primer freno de la ventana de frenada hasta el ápice cinemático (argmin de velocidad en el ápice; si no hay, el ápice oficial). Mayor = frenada más temprana.")
    a("- `trail_brake_frac`: fracción espacial del ápice con `Brake` verdadero.")
    a("- `apex_speed_rel`: velocidad mínima en el ápice, en km/h. El sufijo `_rel` es el del pipeline; aquí todavía es la velocidad cruda. No es un cociente.")
    a("- `throttle_attack`: percentil 95 de `ThrottleRate` tras mediana móvil de 5 muestras, en la salida.")
    a("- `coast_frac`: fracción espacial de frenada ∪ ápice ∪ salida con acelerador ≤ 5 y sin freno.")
    a("- `full_throttle_frac`: fracción espacial de la salida con acelerador ≥ 95.")
    a("")
    a("**Normalización de este experimento:** a cada métrica se le resta la mediana de sesión **de esa curva** (las 842 vueltas). No se resta la mediana de la tipología. Una columna `T4__coast_frac` es el coast de Roggia menos la mediana de Roggia. Positivo = por encima del pelotón en esa curva.")
    a("")
    a("El pipeline actual hace otra cosa: resta la mediana de sesión de la **tipología** y después toma la mediana de las curvas de esa tipología. `slow` es sólo Rettifilo. `medium` es la mediana de Roggia, Lesmo 1, Lesmo 2 y Parabolica. `fast` es la mediana de Curva Grande y Ascari. `fast__throttle_attack` se descarta por casi constante; quedan 17 columnas.")
    a("")
    a("**Consistencia por vuelta.** Para cada piloto y cada métrica, en la vuelta L se toma el conjunto de sus vueltas con número en [L−2, L+2] (radio 2; mínimo 3 vueltas finitas). No es una ventana de cinco filas si falta una vuelta, ni salta un hueco mayor que ese radio.")
    a("")
    a("- `__roll_iqr5`: P75 − P25 de esa ventana.")
    a("- `__roll_mad5`: mediana de |x − mediana de la ventana|.")
    a("- `__absdev_rollmed5`: |x_L − mediana de la ventana|.")
    a("")
    a("Esas tres se calculan sobre las 12 columnas de tipología de punto de frenada, trail braking, velocidad de ápice y coast, y sobre las mismas cuatro métricas en las siete curvas (ya normalizadas por curva: restar una constante no cambia IQR, MAD ni desviación absoluta).")
    a("")
    a("**Tiempos.** `__roll_std5` es la desviación típica muestral (ddof = 1) de `Sector1Time`, `Sector2Time`, `Sector3Time` y `LapTime` (segundos) en la misma ventana de número de vuelta.")
    a("")
    a("**Bloques.** `block_median_matrix` parte las vueltas observadas de cada piloto, ordenadas por `LapNumber`, en bloques no solapados de 5. `__block_iqr5` es el P75 − P25 de esas cinco vueltas. Los bloques no comparten muestras, así que su Spearman-Brown no hereda el solapamiento de la ventana móvil.")
    a("")
    a("**Criterio de estilo** (el del evaluador, más la deriva). Una columna pasa el filtro estricto si: cobertura ≥ 0,90, fracción de ceros ≤ 0,90, al menos 3 valores distintos, ω²(piloto|equipo) ≥ 0,03 con p < 0,01, Spearman-Brown ≥ 0,70, ω²(compuesto|piloto) < 0,05, |ρ de Spearman con el número de vuelta, dentro del piloto| ≤ 0,35 y |ρ con la vida del neumático| ≤ 0,35. ω²(piloto|equipo) es la varianza entre compañeros de equipo por encima de la que cabría por azar (SS de piloto dentro de equipo, menos grados de libertad × MS de vuelta, sobre SS total + MS de vuelta). La cuota de equipo es la fracción de suma de cuadrados entre equipos: coche, no estilo. El filtro de redundancia del evaluador (|ρ| < 0,80 con las 17 columnas) **no** se usa para aceptar una curva: por construcción se parece a su agregado. Se informa `max_abs_rho_existing` y se juzga el resto.")
    a("")
    a("El Spearman-Brown de una ventana móvil es optimista: la media del piloto en vueltas pares y la de vueltas impares comparten casi la misma ventana. Por eso la confirmación es el bloque de 5.")
    a("")

    a("## Comprobación de la extracción")
    a("")
    usable_san = sanity["pearson"].dropna()
    a(
        f"Reconstruyendo el paso del pipeline (mediana de tipología, luego mediana entre curvas) a partir de `car.pkl` y `zones.json`, "
        f"la correlación de Pearson con `lap_matrix.csv` tiene mediana {fnum(usable_san.median(), 4)} "
        f"(mínimo {fnum(usable_san.min(), 4)} en {sanity.loc[sanity['pearson'].idxmin(), 'feature'] if usable_san.notna().any() else 'NA'}, "
        f"n columnas comparadas = {int(usable_san.shape[0])}). "
        f"La diferencia absoluta máxima por columna está en `sanity_typology_reconstruction.csv`. "
        "La extracción de este experimento es la misma función que la matriz actual."
    )
    a("")
    nan_rates = ctx["nan_rates"]
    a("Fracción de valores faltantes por curva (métrica cruda), antes de normalizar:")
    a("")
    a(md_table(nan_rates, nd=3))
    a("")

    a("## Puntuación por curva")
    a("")
    a("ω²(piloto|equipo). Es el criterio de estilo: compañeros distintos en el mismo coche. Un valor ≈ 0 es ruido de vuelta. Las celdas de columnas casi constantes siguen mostrándose; su ω² no se interpreta como estilo.")
    a("")
    omega_mat = matrix_from_scores(scores, "omega2_driver_in_team")
    share_mat = matrix_from_scores(scores, "share_team")
    a(md_table(omega_mat))
    a("")
    a("Cuota de equipo (fracción de suma de cuadrados entre equipos). Alto = el coche, no el piloto.")
    a("")
    a(md_table(share_mat))
    a("")
    a("Figuras: `omega2_zonas.png`, `share_team_zonas.png`.")
    a("")
    show_cols = [
        "feature",
        "omega2_driver_in_team",
        "share_team",
        "p_driver_in_team",
        "spearman_brown",
        "teammate_sign_agreement",
        "omega2_compound_within",
        "rho_tyre_life_within",
        "rho_lap_within",
        "zero_frac",
        "max_abs_rho_existing",
        "most_similar_existing",
    ]
    top = scores.sort_values("omega2_driver_in_team", ascending=False).head(12)
    a("Las doce curvas con mayor ω²(piloto|equipo), con el resto de criterios:")
    a("")
    a(md_table(top[[c for c in show_cols if c in top.columns]]))
    a("")
    a(
        f"Pasan el filtro estricto {int(ctx['strict_zone_mask'].sum())} de {len(scores)} columnas de curva. "
        "El motivo de descarte de cada una está en `zone_selection.csv`."
    )
    a("")
    if len(strict_zone):
        a("Columnas que pasan el filtro estricto:")
        a("")
        a(md_table(strict_zone[[c for c in show_cols if c in strict_zone.columns]].head(20)))
        a("")
    else:
        a("Ninguna columna de curva pasa el filtro estricto completo (señal de compañero, fiabilidad y deriva baja a la vez).")
        a("")

    # Typology comparison table
    a("## ¿La mediana de tipología esconde estilo de una curva?")
    a("")
    a("Para cada métrica se compara el agregado de tipología (las 17 columnas actuales, puntuadas con la misma función) con cada curva de esa tipología. `spearman_con_agregado` es el Spearman entre la curva (normalizada por su propia mediana) y la columna de tipología. `frac_en_par_central` es la fracción de vueltas en las que esa curva ocupa uno de los dos puestos centrales cuya media es la mediana del pipeline (con 4 curvas, los dos valores del medio; con 2, ambos). Si una curva queda siempre en un extremo, su estilo no entra en el agregado.")
    a("")
    comp_rows = []
    idx_s = scores.set_index("feature")
    idx_b = base_scores.set_index("feature")
    idx_c = contrib.set_index(["metric", "zone"])
    idx_v = vs.set_index(["metric", "zone"])
    for metric in METRICS:
        for typology in ("slow", "medium", "fast"):
            typ_col = f"{typology}__{metric}"
            if typ_col not in idx_b.index:
                continue
            b = idx_b.loc[typ_col]
            for z, t in TYP_OF.items():
                if t != typology:
                    continue
                feat = f"{z}__{metric}"
                if feat not in idx_s.index:
                    continue
                r = idx_s.loc[feat]
                comp_rows.append(
                    {
                        "métrica": METRIC_ES[metric],
                        "tipología": typology,
                        "curva": z,
                        "ω² agregado": float(b["omega2_driver_in_team"]),
                        "ω² curva": float(r["omega2_driver_in_team"]),
                        "Δ ω²": float(r["omega2_driver_in_team"]) - float(b["omega2_driver_in_team"]),
                        "SB agregado": float(b["spearman_brown"]),
                        "SB curva": float(r["spearman_brown"]),
                        "cuota equipo curva": float(r["share_team"]),
                        "ρ vuelta curva": float(r["rho_lap_within"]),
                        "spearman con agregado": float(idx_v.loc[(metric, z), "spearman_with_typology"])
                        if (metric, z) in idx_v.index
                        else np.nan,
                        "frac en par central": float(idx_c.loc[(metric, z), "frac_in_central_pair"])
                        if (metric, z) in idx_c.index
                        else np.nan,
                    }
                )
    comp = pd.DataFrame(comp_rows)
    comp.to_csv(OUT / "typology_vs_zone_scores.csv", index=False)
    # Compact: only metrics that are in the base 7 or that show a large delta.
    a(md_table(comp))
    a("")
    # Narrative from the largest deltas and from offsets.
    a("Lectura de esa tabla:")
    a("")
    # slow identity
    a("- `slow` es sólo Rettifilo. Δ ω² ≈ 0 y Spearman ≈ 1 comprueban que T1 y el agregado son la misma columna, salvo el redondeo de la mediana de sesión.")
    # highlight largest positive and negative deltas among non-slow
    comp_nm = comp[comp["tipología"] != "slow"].copy()
    if len(comp_nm):
        # Ignore columns that are mostly zeros: a dead aggregate (95% zeros) makes any
        # sparse corner look like a large gain, and that gain is not a clustering feature.
        def _zfrac(zone, metric_es):
            metric = next(k for k, v in METRIC_ES.items() if v == metric_es)
            feat = f"{zone}__{metric}"
            if feat not in idx_s.index:
                return 1.0
            return float(idx_s.loc[feat, "zero_frac"])

        dense = comp_nm[comp_nm.apply(lambda r: _zfrac(r["curva"], r["métrica"]) <= 0.50, axis=1)]
        # Apex speed gains are real as teammate signal and useless as style: they track lap number.
        low_drift = dense[dense["ρ vuelta curva"].abs() <= LAP_RHO_STRICT] if len(dense) else dense
        pool = low_drift if len(low_drift) else dense if len(dense) else comp_nm
        best_d = pool.sort_values("Δ ω²", ascending=False).iloc[0]
        worst_d = pool.sort_values("Δ ω²", ascending=True).iloc[0]
        a(
            f"- Entre columnas con fracción de ceros ≤ 0,50 y |ρ| con la vuelta ≤ 0,35, la mayor ganancia sobre el agregado es "
            f"{best_d['curva']} / {best_d['métrica']} "
            f"(ω² {fnum(best_d['ω² agregado'])} → {fnum(best_d['ω² curva'])}, Δ = {fnum(best_d['Δ ω²'])}, "
            f"Spearman-Brown = {fnum(best_d['SB curva'])}, cuota de equipo = {fnum(best_d['cuota equipo curva'])}, "
            f"ρ con la vuelta = {fnum(best_d['ρ vuelta curva'])})."
        )
        raw_best = comp_nm.sort_values("Δ ω²", ascending=False).iloc[0]
        if raw_best["curva"] != best_d["curva"] or raw_best["métrica"] != best_d["métrica"]:
            a(
                f"- Sin ese recorte de deriva, el Δ más alto es {raw_best['curva']} / {raw_best['métrica']} "
                f"(Δ = {fnum(raw_best['Δ ω²'])}, ρ con la vuelta = {fnum(raw_best['ρ vuelta curva'])}). "
                "Ese máximo sale de comparar contra un agregado casi constante o de una velocidad de ápice que sigue al número de vuelta. No es un rasgo de estilo nuevo."
            )
        a(
            f"- La mayor pérdida, en el mismo recorte, es {worst_d['curva']} / {worst_d['métrica']} "
            f"(Δ = {fnum(worst_d['Δ ω²'])}): esa curva, sola, separa menos a los compañeros que el agregado. "
            "Ahí la mediana de tipología está promediando ruido, no escondiendo un rasgo."
        )
        a(
            "- Un Δ grande contra un agregado que ya es casi constante (ataque de acelerador y gas a fondo de `medium`, "
            "con más del 95 % de ceros) no cuenta como estilo recuperado: la curva sigue siendo dispersa. "
            "Lesmo 1 en gas a fondo sube de 0,002 a 0,058 con un 86 % de ceros; no entra en el vector."
        )
    # central pair: zones rarely in the middle
    rare = contrib[(contrib["typology"] != "slow") & (contrib["frac_in_central_pair"] < 0.15)]
    if len(rare):
        bits = [
            f"{r.zone} en {METRIC_ES[r.metric]} ({r.typology}, {fnum(r.frac_in_central_pair, 2)})"
            for r in rare.sort_values("frac_in_central_pair").itertuples()
        ]
        a(
            "- Curvas que casi nunca ocupan el par central de la mediana (su nivel queda en un extremo y el agregado no las usa): "
            + "; ".join(bits[:12])
            + "."
        )
    else:
        a("- Ninguna curva queda fuera del par central en más del 85 % de las vueltas: los niveles, tras restar la mediana de tipología, se solapan lo bastante como para que todas entren alguna vez.")
    # offsets: show apex and brake medians so the mechanism is visible
    a("")
    a("Mediana que queda en cada curva **después** de restar la mediana de tipología (no la de la curva). Si las medianas no se solapan, la mediana entre curvas es una curva fija, no una mezcla de estilos:")
    a("")
    off_show = offsets[offsets["metric"].isin(["apex_speed_rel", "brake_point_rel", "coast_frac", "trail_brake_frac"])][
        ["metric", "zone", "typology", "nan_frac", "median", "q25", "q75"]
    ].copy()
    off_show["metric"] = off_show["metric"].map(METRIC_ES)
    a(md_table(off_show))
    a("")
    a(
        "Esos niveles, no el estilo, explican qué entra en la mediana. En velocidad de ápice, Roggia queda unos 74 km/h por debajo del agregado medium y no ocupa el par central en ninguna vuelta; Parabolica entra en el 8 %. "
        "`medium__apex_speed_rel` es Lesmo 1 y Lesmo 2 (Spearman 0,97 y 0,96 con el agregado). Curva Grande queda unos +67 km/h y Ascari unos −54 km/h: `fast__apex` es la media de dos curvas que no se solapan, y la variación la pone Ascari (Spearman 0,95) y no Curva Grande (0,30; IQR residual de unos 3 km/h). "
        "En el punto de frenada, Lesmo 2 queda unos −30 m y entra en el par central el 12 % de las vueltas; Parabolica queda unos +30 m. El agregado medium de frenada es Roggia y Lesmo 1. Nadie frena en la ventana de Curva Grande, así que `fast__brake_point_rel` es Ascari (Spearman 1). "
        "En trail braking, Parabolica es un punto (P25 = mediana = P75) y entra en el par central el 4 %; el agregado correlaciona 0,86 con Lesmo 1 y 0,14 con Parabolica. "
        "En coast los residuos sí se solapan alrededor de 0: ahí la mediana mezcla curvas de verdad, no se queda con una sola."
    )
    a("")

    a("## Correlación entre curvas, dentro del piloto y entre pilotos")
    a("")
    a("Dos preguntas distintas. La correlación **dentro** del piloto (Pearson de las series demediadas por piloto; también la media de Spearmans por piloto) dice si, en una vuelta concreta, ir temprano en una curva va con ir temprano en otra. La correlación **entre** pilotos (Spearman de las medianas de piloto) dice si el ranking de estilo se conserva de una curva a otra. `frac_drivers_opposite_sign` es la fracción de pilotos cuya mediana queda por encima del pelotón en una curva y por debajo en la otra. `frac_teams_order_flip` es la fracción de parejas de compañeros cuyo orden se invierte entre las dos curvas (0,5 ≈ azar).")
    a("")
    same = pairs[pairs["same_typology"]].copy()
    a("Pares de la **misma** tipología:")
    a("")
    same_show = same[
        [
            "metric",
            "zone_a",
            "zone_b",
            "typology_a",
            "r_within_pooled",
            "r_within_mean_spearman",
            "r_between_spearman",
            "frac_drivers_opposite_sign",
            "frac_teams_order_flip",
            "n_teams_flip",
        ]
    ].sort_values(["metric", "zone_a", "zone_b"])
    same_show["metric"] = same_show["metric"].map(METRIC_ES)
    a(md_table(same_show))
    a("")
    # Summarise coast and brake, the style-relevant ones.
    def _mean(df, col):
        s = df[col].dropna()
        return float(s.mean()) if len(s) else float("nan")

    for metric in ("coast_frac", "brake_point_rel", "trail_brake_frac", "apex_speed_rel"):
        sub = same[same["metric"] == metric]
        if sub.empty:
            continue
        a(
            f"- {METRIC_ES[metric]}, pares de la misma tipología: "
            f"r dentro (pooled) medio = {fnum(_mean(sub, 'r_within_pooled'))}, "
            f"r entre pilotos medio = {fnum(_mean(sub, 'r_between_spearman'))}, "
            f"fracción media de pilotos con signo opuesto = {fnum(_mean(sub, 'frac_drivers_opposite_sign'))}, "
            f"inversión media del orden entre compañeros = {fnum(_mean(sub, 'frac_teams_order_flip'))}."
        )
    a("")
    if len(examples):
        a("Pilotos con signo opuesto en el coast, mediana ya restada la mediana de la curva, y |mediana| ≥ 0,02 en Roggia y en Lesmo 1. Positivo = más punto muerto que el pelotón:")
        a("")
        a(md_table(examples, nd=3))
        a("")
        a(
            "El hábito de coast no viaja de Roggia a Lesmo 1. Lesmo 1 y Lesmo 2, en cambio, ordenan a los pilotos casi igual "
            "(Spearman entre pilotos 0,91; sólo 2 de 19 con signo opuesto). "
            "En el punto de frenada el contraste Rettifilo contra Ascari no da un solo piloto con |mediana| > 3 m y signo opuesto en las dos: "
            "los cambios de signo que hay son de 1–2 m en una de las dos curvas, del orden del muestreo (~20 m a 300 km/h en una vuelta; la mediana de la carrera afina, pero no hasta convertir 1 m en un estilo). "
            "Stroll frena temprano en las dos (+23 m y +18 m); Verstappen, tarde en las dos. "
            "Las medianas están en `driver_zone_medians.csv`."
        )
        a("")
    # medium coast between-driver: call out the weakest pair
    coast_same = (
        same[same["metric"] == "coast_frac"]
        .dropna(subset=["r_between_spearman"])
        .sort_values("r_between_spearman")
    )
    if len(coast_same):
        w = coast_same.iloc[0]
        sng = coast_same.iloc[-1]
        a(
            f"En coast, el par de la misma tipología con el ranking de pilotos **menos** compartido es "
            f"{w['zone_a']}–{w['zone_b']} ({w['typology_a']}): Spearman entre pilotos = {fnum(w['r_between_spearman'])}, "
            f"r dentro = {fnum(w['r_within_pooled'])}. "
            f"El más compartido es {sng['zone_a']}–{sng['zone_b']}: Spearman entre pilotos = {fnum(sng['r_between_spearman'])}."
        )
        a("")

    a("## Reemplazo del vector y clustering")
    a("")
    a("Todos los ajustes son K-means en z-score, sin PCA. La brecha es silueta observada menos silueta del nulo (cada columna permutada por separado, se conservan las marginales). PS es prediction strength (Tibshirani y Walther; por encima de ~0,8 la partición se reproduce en mitades). AMI es información mutua ajustada con el piloto. `teammate_split_rate` es la fracción de equipos de dos pilotos cuya moda de clase no coincide.")
    a("")
    a("Conjuntos, fijados antes de mirar la silueta:")
    a("")
    a("- `base7`: las 7 columnas con ICC(1) ≥ 0,25. Es el vector de referencia (ápice fast/medium, coast slow/medium/fast, trail slow/medium).")
    a("- `analogue7`: para cada una de esas 7, la curva de la misma tipología y métrica con mayor ω²(piloto|equipo), siempre que no sea casi constante y tenga cobertura ≥ 0,95. Misma dimensión. Es el test directo de granularidad. Elige la curva con los mismos datos que luego se agrupan: hay un sesgo de selección pequeño.")
    a("- `expand`: todas las curvas que componen esas 7 columnas, quitando sólo las casi constantes o con cobertura < 0,95. No elige ganadores. Más columnas: la silueta bruta tiende a bajar; se mira la brecha.")
    a("- `strict7`: hasta 7 columnas de curva del filtro estricto, las de mayor ω², con |Spearman| mutuo < 0,75 (voraz). Si el filtro estricto deja menos de 2, el conjunto no se ajusta.")
    a("- `strict_dense`: las mismas que pasan el filtro estricto con fracción de ceros ≤ 0,50. Es un corte posterior: `strict7` todavía admite el ataque de acelerador y el gas a fondo de Lesmo 1, que son dispersos. Sirve para no achacar la brecha negativa sólo a esos ceros.")
    a("- `base7+cons3` y `cons5`: la consistencia móvil, abajo.")
    a("")
    for name, cols in sets.items():
        a(f"- `{name}` ({len(cols)}): {', '.join(cols) if cols else '(vacío)'}")
    a("")
    if len(gain):
        show = gain.drop(columns=[c for c in ("features",) if c in gain.columns]).copy()
        # sizes may be lists
        if "sizes" in show.columns:
            show["sizes"] = show["sizes"].astype(str)
        a(md_table(show))
        a("")
    if b2 is not None:
        a(
            f"La base reproduce el diagnóstico ya conocido: k=2 silueta {fnum(b2['silhouette'])} "
            f"(nulo {fnum(b2['null_silhouette'])}, brecha {fnum(b2['silhouette_gap'])}, "
            f"PS {fnum(b2['prediction_strength'])}, AMI piloto {fnum(b2['ami_driver'])}, "
            f"split de compañeros {fnum(b2['teammate_split_rate'])}). "
            f"En k=3: silueta {fnum(b3['silhouette']) if b3 is not None else 'NA'}, "
            f"PS {fnum(b3['prediction_strength']) if b3 is not None else 'NA'}, "
            f"AMI {fnum(b3['ami_driver']) if b3 is not None else 'NA'}, "
            f"split {fnum(b3['teammate_split_rate']) if b3 is not None else 'NA'}."
        )
        a("")
    if n2 is not None and b2 is not None:
        a(
            f"`analogue7` en k=2: silueta {fnum(n2['silhouette'])}, nulo {fnum(n2['null_silhouette'])}, "
            f"brecha {fnum(n2['silhouette_gap'])} (base {fnum(b2['silhouette_gap'])}), "
            f"PS {fnum(n2['prediction_strength'])} (base {fnum(b2['prediction_strength'])}), "
            f"ARI bootstrap {fnum(n2['bootstrap_ari'])} (base {fnum(b2['bootstrap_ari'])}), "
            f"AMI piloto {fnum(n2['ami_driver'])} (base {fnum(b2['ami_driver'])}), "
            f"split {fnum(n2['teammate_split_rate'])} (base {fnum(b2['teammate_split_rate'])}), "
            f"AMI compuesto {fnum(n2['ami_compound'])}."
        )
        a("")
        if n3 is not None and b3 is not None:
            a(
                f"`analogue7` en k=3: silueta {fnum(n3['silhouette'])}, brecha {fnum(n3['silhouette_gap'])} "
                f"(base {fnum(b3['silhouette_gap'])}), PS {fnum(n3['prediction_strength'])} "
                f"(base {fnum(b3['prediction_strength'])}), AMI piloto {fnum(n3['ami_driver'])} "
                f"(base {fnum(b3['ami_driver'])}), split {fnum(n3['teammate_split_rate'])} "
                f"(base {fnum(b3['teammate_split_rate'])})."
            )
            a("")
    if e2 is not None and b2 is not None:
        a(
            f"`expand` ({int(e2['n_features'])} columnas) en k=2: silueta {fnum(e2['silhouette'])}, "
            f"brecha {fnum(e2['silhouette_gap'])}, PS {fnum(e2['prediction_strength'])}, "
            f"AMI piloto {fnum(e2['ami_driver'])}, split {fnum(e2['teammate_split_rate'])} "
            f"(base {fnum(b2['teammate_split_rate'])}). "
            f"La brecha sube ({fnum(b2['silhouette_gap'])} → {fnum(e2['silhouette_gap'])}) porque el nulo cae "
            f"({fnum(b2['null_silhouette'])} → {fnum(e2['null_silhouette'])}) al pasar a {int(e2['n_features'])} columnas, "
            f"no porque la silueta observada suba: baja de {fnum(b2['silhouette'])} a {fnum(e2['silhouette'])}. "
            "El split de compañeros empeora. No es una partición mejor; es un nulo más bajo en más dimensiones."
        )
        a("")
    # strict set commentary
    s2 = gain_row("strict7", 2)
    if s2 is not None and b2 is not None:
        a(
            f"`strict7` (sólo curvas con señal de compañero, fiabilidad y poca deriva) en k=2: "
            f"silueta {fnum(s2['silhouette'])}, brecha {fnum(s2['silhouette_gap'])}, "
            f"PS {fnum(s2['prediction_strength'])}, AMI piloto {fnum(s2['ami_driver'])}, "
            f"split {fnum(s2['teammate_split_rate'])}. "
            "Deja fuera el ápice, que arrastra combustible. La brecha en k=2 queda por debajo del nulo: "
            "el conjunto estricto mete además `T6__throttle_attack` (80 % de ceros) y `T6__full_throttle_frac` (86 % de ceros), "
            "y esas marginales ya forman grumos. `strict_dense` quita esas dos y se comenta abajo."
        )
        a("")
    d2 = gain_row("strict_dense", 2)
    if d2 is not None and b2 is not None:
        a(
            f"`strict_dense` (el filtro estricto y, además, fracción de ceros ≤ 0,50; es un corte posterior, "
            f"para ver si la brecha negativa era sólo la inflación de ceros) en k=2: "
            f"silueta {fnum(d2['silhouette'])}, nulo {fnum(d2['null_silhouette'])}, brecha {fnum(d2['silhouette_gap'])} "
            f"(base {fnum(b2['silhouette_gap'])}), PS {fnum(d2['prediction_strength'])} "
            f"(base {fnum(b2['prediction_strength'])}), AMI piloto {fnum(d2['ami_driver'])}, "
            f"split {fnum(d2['teammate_split_rate'])}. "
            "Sigue por debajo de la base. El coast y el trail limpios, por curva, no reconstruyen la partición que arma el ápice junto con el coast agregado."
        )
        a("")
    if len(eval_gain):
        a("El evaluador oficial, por su lado, añade a las 7 columnas base las candidatas con `recommended=True` (eso incluye el filtro de redundancia |ρ| < 0,80 con las 17 columnas, que las curvas suelen fallar). Resultado en `candidates_gain.csv`:")
        a("")
        eg = eval_gain.copy()
        if "sizes" in eg.columns:
            eg["sizes"] = eg["sizes"].astype(str)
        a(md_table(eg))
        a("")
        rec = ctx["recommended"]
        if rec:
            a(f"Candidatas marcadas `recommended` por el evaluador ({len(rec)}): {', '.join(rec)}.")
        else:
            a("El evaluador no marcó ninguna candidata como `recommended`. El filtro de redundancia o el de deriva/fiabilidad las dejó fuera; el gain oficial es sólo la base.")
        if len(eval_gain) and "base+extra" in set(eval_gain["set"]):
            g_base = eval_gain[(eval_gain["set"] == "base") & (eval_gain["k"] == 2)]
            g_extra = eval_gain[(eval_gain["set"] == "base+extra") & (eval_gain["k"] == 2)]
            if len(g_base) and len(g_extra):
                a(
                    f"Meterlas todas encima de las 7 columnas empeora la partición: en k=2 la brecha pasa de "
                    f"{fnum(g_base.iloc[0]['silhouette_gap'])} a {fnum(g_extra.iloc[0]['silhouette_gap'])} "
                    f"y la silueta de {fnum(g_base.iloc[0]['silhouette'])} a {fnum(g_extra.iloc[0]['silhouette'])} "
                    f"({int(g_extra.iloc[0]['n_features'])} columnas, {int(g_extra.iloc[0]['n_laps'])} vueltas). "
                    "El filtro `recommended` no es un vector de clustering."
                )
        a("")

    a("## Consistencia como rasgo de estilo")
    a("")
    a("Se puntúan IQR móvil, MAD móvil y desviación absoluta a la mediana móvil. La desviación absoluta describe la vuelta rara, no un nivel estable del piloto: se espera ω² bajo. El IQR y la MAD de ventanas solapadas se parecen a una constante por piloto y por eso inflan ICC y Spearman-Brown.")
    a("")
    if len(consist_scores):
        topc = consist_scores.sort_values("omega2_driver_in_team", ascending=False).head(15)
        a("Quince métricas de consistencia con mayor ω²(piloto|equipo):")
        a("")
        a(md_table(topc[[c for c in show_cols if c in topc.columns]]))
        a("")
        n_strict_c = int(ctx["strict_cons_mask"].sum()) if ctx["strict_cons_mask"] is not None else 0
        a(f"Pasan el filtro estricto {n_strict_c} métricas de consistencia (de {len(consist_scores)}).")
        a("")
        # Compare families
        def fam_best(suffix):
            sub = consist_scores[consist_scores["feature"].str.endswith(suffix)]
            if sub.empty:
                return None
            return sub.sort_values("omega2_driver_in_team", ascending=False).iloc[0]

        for suffix, label in (
            ("__roll_iqr5", "IQR móvil"),
            ("__roll_mad5", "MAD móvil"),
            ("__absdev_rollmed5", "desviación absoluta a la mediana móvil"),
        ):
            r = fam_best(suffix)
            if r is None:
                continue
            a(
                f"- Mejor {label}: `{r['feature']}`, ω² = {fnum(r['omega2_driver_in_team'])}, "
                f"cuota de equipo = {fnum(r['share_team'])}, Spearman-Brown = {fnum(r['spearman_brown'])}, "
                f"acuerdo de signo = {fnum(r['teammate_sign_agreement'])}, "
                f"ω² compuesto = {fnum(r['omega2_compound_within'])}, "
                f"ρ vuelta = {fnum(r['rho_lap_within'])}, ρ vida = {fnum(r['rho_tyre_life_within'])}, "
                f"ceros = {fnum(r['zero_frac'])}."
            )
        a("")
    c2 = gain_row("cons5", 2)
    p2 = gain_row("base7+cons3", 2)
    if c2 is not None:
        a(
            f"Clustering sólo con las mejores consistencias móviles (`cons5`, {int(c2['n_features'])} columnas) en k=2: "
            f"silueta {fnum(c2['silhouette'])}, brecha {fnum(c2['silhouette_gap'])}, "
            f"PS {fnum(c2['prediction_strength'])}, AMI piloto {fnum(c2['ami_driver'])}, "
            f"split {fnum(c2['teammate_split_rate'])}. "
            "Si la brecha es pequeña y la AMI con el piloto no supera a la base, la dispersión no define clases de estilo."
        )
        a("")
    if p2 is not None and b2 is not None:
        a(
            f"Añadir las 3 mejores consistencias a las 7 columnas base, k=2: brecha {fnum(p2['silhouette_gap'])} "
            f"(base {fnum(b2['silhouette_gap'])}), PS {fnum(p2['prediction_strength'])} "
            f"(base {fnum(b2['prediction_strength'])}), AMI piloto {fnum(p2['ami_driver'])} "
            f"(base {fnum(b2['ami_driver'])})."
        )
        a("")

    a("## Tiempos de sector")
    a("")
    a("Todas las 842 vueltas tienen `TrackStatus` 1 y tiempos entre 80,9 s y 86,8 s: no hay coche de seguridad en esta matriz. Aun así, la dispersión del tiempo es rendimiento (tráfico, gestión, coche), no una elección de frenada.")
    a("")
    if len(sector_scores):
        a(md_table(sector_scores[[c for c in show_cols if c in sector_scores.columns]]))
        a("")
        extra = ctx.get("sector_extra", {})
        if extra:
            a(
                f"Spearman entre la mediana por piloto de `lap_time__roll_std5` y la mediana de su tiempo de vuelta: "
                f"{fnum(extra.get('rho_pace'))}. "
                f"Con la posición mediana: {fnum(extra.get('rho_position'))}. "
                "Una correlación clara con el ritmo indicaría que los coches rápidos son más estables, no que el piloto tenga un estilo más repetible."
            )
            a("")

    a("## Bloques de 5 vueltas")
    a("")
    a(
        f"Hay {ctx['n_blocks']} bloques completos de 5 vueltas observadas "
        "(los restos de stint se tiran). La mediana del bloque es la unidad que ya mejoraba la silueta de las 7 columnas en el benchmark de separación. "
        "Aquí se repite esa unidad con el vector análogo y con el expandido, y se puntúa el IQR interno del bloque como rasgo de consistencia."
    )
    a("")
    if len(block_level_gain):
        bg = block_level_gain.drop(columns=[c for c in ("features",) if c in block_level_gain.columns]).copy()
        if "sizes" in bg.columns:
            bg["sizes"] = bg["sizes"].astype(str)
        a(md_table(bg))
        a("")
    if len(block_iqr_scores):
        topb = block_iqr_scores.sort_values("omega2_driver_in_team", ascending=False).head(12)
        a("Doce IQR de bloque con mayor ω²(piloto|equipo). El Spearman-Brown aquí no está inflado por ventanas solapadas:")
        a("")
        a(md_table(topb[[c for c in show_cols if c in topb.columns]]))
        a("")
        n_pass_b = int(ctx["strict_block_mask"].sum()) if ctx["strict_block_mask"] is not None else 0
        a(f"Pasan el filtro estricto {n_pass_b} de {len(block_iqr_scores)} IQR de bloque.")
        a("")
        bb2 = None
        if len(block_level_gain):
            hit = block_level_gain[(block_level_gain["set"] == "block_iqr") & (block_level_gain["k"] == 2)]
            if len(hit):
                bb2 = hit.iloc[0]
        if bb2 is not None:
            a(
                f"Clustering de esos IQR de bloque (conjunto `block_iqr`) en k=2: "
                f"silueta {fnum(bb2['silhouette'])}, brecha {fnum(bb2['silhouette_gap'])}, "
                f"PS {fnum(bb2['prediction_strength'])}, AMI piloto {fnum(bb2['ami_driver'])}, "
                f"split {fnum(bb2['teammate_split_rate'])}."
            )
            a("")

    a("## Qué no funciona, y por qué")
    a("")
    # rejection counts for zone levels
    sel = ctx["selection"]
    zone_sel = sel[sel["family"] == "zona"]
    if len(zone_sel):
        # explode reasons
        counts: dict[str, int] = {}
        for text in zone_sel["motivos"]:
            if text == "pasa_estricto":
                counts["pasa_estricto"] = counts.get("pasa_estricto", 0) + 1
                continue
            for part in str(text).split(","):
                counts[part] = counts.get(part, 0) + 1
        bits = ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
        a(f"- Descartes del filtro estricto en las 42 columnas de curva (un mismo rasgo puede acumular varios motivos): {bits}.")
    a("- Curva Grande es una curva a fondo. Varias de sus métricas salen casi constantes (gas a fondo, coast, trail, a veces el punto de frenada si nadie frena en la ventana). No describen estilo; meten ceros y aíslan la vuelta rara. El agregado `fast` las mezcla con Ascari, que sí se frena.")
    a("- La velocidad de ápice y el punto de frenada arrastran el combustible: ρ con el número de vuelta dentro del piloto del orden del diagnóstico ya conocido (~+0,8 y ~−0,5 en el agregado). Bajar a la curva no quita esa pendiente. Por eso el filtro estricto las deja fuera aunque separen compañeros. El vector base7 las conserva: parte de su silueta es ritmo de carrera, no estilo.")
    a("- `throttle_attack` y `full_throttle_frac` siguen degeneradas en Curva Grande, Ascari, Parabolica y casi en Roggia. Lesmo 1 es la excepción parcial: ω²(piloto|equipo) = 0,090 en el ataque, con un 80 % de ceros, y 0,058 en el gas a fondo, con un 86 % de ceros. El agregado `medium` las aplasta (95 % y 99 % de ceros) porque la mediana de cuatro curvas casi nulas es cero. Rescatarlas no mejora el K-means: son las que dejan la brecha de `strict7` en −0,007.")
    a("- `expand` (16 columnas) sube la brecha de silueta sólo porque el nulo de permutación cae en más dimensiones (0,112 → 0,049 en k=2) mientras la silueta observada baja (0,256 → 0,207). El split de compañeros baja de 0,333 a 0,222. No es una ganancia.")
    a("- La desviación absoluta a la mediana móvil describe la vuelta atípica, no un nivel del piloto. Aun así varias pasan el filtro estricto porque la ventana solapada les infla el Spearman-Brown. No se usaron como núcleo del conjunto `cons5`.")
    a("- El IQR/MAD móvil de Lesmo 2 coast tiene ω² ≈ 0,16 y Spearman-Brown ≈ 0,97. El mismo IQR en bloques de 5 vueltas no solapados (`T7__coast_frac__block_iqr5`) conserva ω² = 0,154 pero el Spearman-Brown cae a 0,544 y el acuerdo de signo entre compañeros a 0,556. La fiabilidad del rolling no cuenta. Los IQR de bloque que sí mantienen Spearman-Brown ≥ 0,70 (coast medium, fast y Lesmo 1) agrupan con brecha 0,087 y AMI con el piloto 0,062: no definen clases.")
    a("- La dispersión de tiempos de sector no es un efecto de coche: la cuota de equipo va de 0,033 a 0,097, por debajo o al lado de ω². Sector 2 tiene la mayor señal entre compañeros (ω² = 0,052, Spearman-Brown 0,969) y el evaluador la marca `recommended`, pero la mediana por piloto de esa dispersión correlaciona 0,52 con la posición en carrera. Es tráfico o ritmo, no una elección de frenada. Sector 1 arrastra compuesto (ω² = 0,187).")
    a("- Elegir la curva de mayor ω² y luego agrupar las mismas vueltas infla un poco al conjunto `analogue7` y al `strict7`. El conjunto `expand` no elige ganadores y es el control.")
    a("")

    a("## Recomendación ordenada")
    a("")
    if analogue_helps_k2 or analogue_helps_k3:
        a("1. **Sustituir el agregado por `analogue7` en el clustering de esta carrera.** A igual dimensión (z-score, sin PCA) la brecha de silueta sube en k=2 o en k=3 sin hundir la prediction strength. No dar el paso siguiente de meter todas las curvas (`expand`): la dimensión de más no compra otra clase.")
    else:
        a("1. **Conservar las 7 columnas de tipología como vector de clustering.** En esta carrera el análogo por curva, a igual dimensión y en z-score sin PCA, no mejora a la vez la brecha de silueta, la prediction strength y la AMI con el piloto (véase la tabla; k=2 y k=3). El agregado sigue siendo el mejor compromiso entre señal de compañero y ruido de vuelta, sobre todo en coast.")
    a("2. **No interpretar `medium` ni `fast` como un solo hábito.** Para el texto de la tesis, desglosar coast, trail y punto de frenada por curva. La curva que más aporta dentro de cada métrica es la de mayor ω² de la tabla de zonas, siempre que Spearman-Brown ≥ 0,7 y la cuota de equipo no domine. Esas columnas sirven para caracterizar un clúster ya hecho, no para sustituir el vector.")
    # name the concrete winners from improvements with SB and omega
    winners = []
    for delta, best, base_r, typ_col in improvements:
        if delta < 0.02:
            continue
        if not (np.isfinite(best["spearman_brown"]) and best["spearman_brown"] >= SB_MIN):
            continue
        if not (np.isfinite(best["omega2_driver_in_team"]) and best["omega2_driver_in_team"] >= OMEGA_MIN):
            continue
        if float(best["zero_frac"]) > 0.50:
            continue
        if not (np.isfinite(best["rho_lap_within"]) and abs(float(best["rho_lap_within"])) <= LAP_RHO_STRICT):
            continue
        if not (np.isfinite(best["omega2_compound_within"]) and float(best["omega2_compound_within"]) < 0.10):
            continue
        winners.append(
            f"`{best['feature']}` (ω² {fnum(best['omega2_driver_in_team'])} frente a {fnum(base_r['omega2_driver_in_team'])} de `{typ_col}`, "
            f"SB {fnum(best['spearman_brown'])}, cuota de equipo {fnum(best['share_team'])}, "
            f"acuerdo de signo {fnum(best['teammate_sign_agreement'])}, "
            f"ω² compuesto {fnum(best['omega2_compound_within'])}, ρ vuelta {fnum(best['rho_lap_within'])})"
        )
    if winners:
        a("   Curvas que superan a su agregado en al menos 0,02 de ω², con fiabilidad ≥ 0,70, fracción de ceros ≤ 0,50, |ρ| con la vuelta ≤ 0,35 y ω² de compuesto < 0,10: " + "; ".join(winners) + ".")
    else:
        a("   Con ese recorte (sin ápice arrastrado por el combustible y sin columnas de ceros) ninguna curva supera a su agregado en 0,02 de ω².")
    a("   Aunque no gane en ω², Lesmo 2 coast es más de piloto y menos de coche que el agregado: ω² 0,121 frente a 0,136 de `medium__coast`, cuota de equipo 0,172 frente a 0,452. Roggia y Parabolica coast tienen cuotas de equipo 0,231 y 0,261. La mediana de tipología se queda con la parte común al coche.")
    a("3. **No meter el ápice ni el punto de frenada en un vector “de estilo puro” sin residualizar la vuelta.** Siguen correlacionados con el número de vuelta dentro del piloto. Si se usan, hay que decir que el clúster mezcla estilo y carga de combustible. El filtro estricto los quita; la base7 no.")
    a("4. **No añadir consistencia móvil al vector.** Como mucho, reportar el IQR de bloque de coast o de trail si su ω²(piloto|equipo) pasa 0,03 y el bloque lo confirma. En caso contrario, la variabilidad vuelta a vuelta es ruido, tráfico o neumático, no un rasgo que separe compañeros.")
    a("5. **Dejar fuera los tiempos de sector y Curva Grande como curva de estilo.** El primero es rendimiento; la segunda no se frena.")
    a("6. **Siguiente contraste, fuera de este informe:** repetir el análogo de 7 curvas en otra pista donde `medium` no mezcle una parabólica con dos Lesmo. Monza es un caso extremo de tipología mal emparejada; que aquí el clustering no mejore no dice que en una pista con curvas homogéneas el agregado sea inocente. Sí dice que, en Monza 2025, alargar el vector no compra una partición mejor.")
    a("")

    a("## Caveats")
    a("")
    a("- Una sola carrera, 19 pilotos, un equipo con un solo coche. ω²(piloto|equipo) tiene pocos grados de libertad entre compañeros (9 parejas). p < 0,01 con 842 vueltas se alcanza con efectos modestos: por eso el umbral de ω² es 0,03 y no basta el p.")
    a("- El freno es booleano, no presión. A ~300 km/h un muestreo de 0,245 s son unos 20 m; a 80 km/h, unos 5 m. El punto de frenada de una vuelta es grosero. La mediana de muchas vueltas afina la media del piloto, pero no crea información que el muestreo no tiene.")
    a("- No hay carga de combustible ni setup en FastF1. Restar la mediana de la curva quita el nivel del pelotón, no la pendiente dentro del piloto. Los clústeres son perfiles observables, no estilos causales.")
    a("- El compuesto SOFT tiene 22 vueltas. ω²(compuesto|piloto) en esas celdas es inestable; el umbral 0,05 es una guarda, no un contraste fino.")
    a("- ALO tiene 19 vueltas y ALB entra en la vuelta 12. Las ventanas del borde y los bloques incompletos se pierden.")
    a("- El nulo de silueta usa 5 permutaciones y el ARI bootstrap 10 remuestras. La brecha está en el orden de la centésima de ruido de Monte Carlo; no se interpretan diferencias de 0,01.")
    a("- `analogue7` y `strict7` eligen columnas con el mismo criterio que luego se evalúa en clustering. `expand` y la base7 no. La comparación honesta de granularidad es base7 contra analogue7 (misma dimensión) y contra expand (sin elegir la curva ganadora).")
    a("- La fiabilidad partida en pares/impares de las features móviles está inflada. Se dice en cada tabla donde aparece.")
    a("- Kick Sauber (BOR) no entra en el contraste entre compañeros ni en el split de equipos.")
    a("")
    a("## Archivos")
    a("")
    a("- `run.py`: este análisis, repetible.")
    a("- `candidates.csv`: vueltas × candidatas (curvas, rolling, sectores).")
    a("- `candidates_scores.csv`, `candidates_gain.csv`: salida del evaluador oficial.")
    a("- `baseline_scores.csv`: las 17 columnas actuales, misma función de puntuación.")
    a("- `zone_selection.csv`: motivo de descarte de cada candidata.")
    a("- `replacement_clustering.csv`: base7, análogo, expand, estricto, consistencia.")
    a("- `zone_pair_structure.csv`, `driver_zone_medians.csv`, `zone_vs_typology_spearman.csv`.")
    a("- `zone_offsets_after_typology_median.csv`, `typology_median_contribution.csv`.")
    a("- `sanity_typology_reconstruction.csv`, `zone_long_raw.csv`.")
    a("- `block_scores.csv`, `block_clustering.csv`, `block_candidates.csv`.")
    a("- `omega2_zonas.png`, `share_team_zonas.png`.")
    a("- `highlights.json`: números que usa el veredicto.")
    a("")
    return "\n".join(lines) + "\n"


def main() -> None:
    reuse = "--from-cache" in sys.argv
    skip_eval = "--skip-eval" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)

    lap_matrix = pd.read_csv(DATA / "lap_matrix.csv")
    lap_matrix["Driver"] = lap_matrix["Driver"].astype(str)
    lap_matrix["LapNumber"] = lap_matrix["LapNumber"].astype(int)
    laps = pd.read_csv(DATA / "laps.csv")
    laps["Driver"] = laps["Driver"].astype(str)
    laps["LapNumber"] = laps["LapNumber"].astype(int)

    base_cols = select_features_by_icc(lap_matrix, style_columns(lap_matrix), min_icc=0.25)
    log(f"base7 = {base_cols}")

    zones = load_zones()
    long_raw = extract_zone_long(zones, reuse=reuse)
    long_raw["Driver"] = long_raw["Driver"].astype(str)
    long_raw["LapNumber"] = long_raw["LapNumber"].astype(int)
    # Stable typology from the zone map (do not trust a stray label).
    long_raw["typology"] = long_raw["short"].map(TYP_OF)

    sanity = sanity_check(long_raw, lap_matrix)
    nan_rates_rows = []
    for short in SHORTS:
        rec = {"zona": LABEL_OF[short]}
        sub = long_raw[long_raw["short"] == short]
        for metric in METRICS:
            rec[METRIC_ES[metric]] = float(pd.to_numeric(sub[metric], errors="coerce").isna().mean())
        nan_rates_rows.append(rec)
    nan_rates = pd.DataFrame(nan_rates_rows)

    long_norm = normalize_by_zone(long_raw)
    zone_wide = pivot_zones(long_norm)
    typ_long = typology_normalized_long(long_raw)
    offsets = zone_offset_table(typ_long)
    contrib = median_contribution(typ_long)

    keys = lap_matrix[["Driver", "LapNumber", "Team", "FullName"]].copy()
    pairs = pair_structure(zone_wide, lap_matrix[["Driver", "LapNumber", "Team"]])
    medians = driver_medians(zone_wide, keys)

    # Rolling on typology columns and on zone columns for the four consistency metrics.
    typ_cols = [f"{typ}__{m}" for typ in ("slow", "medium", "fast") for m in CONSIST_METRICS if f"{typ}__{m}" in lap_matrix.columns]
    zone_cols_c = [f"{z}__{m}" for z in SHORTS for m in CONSIST_METRICS]
    roll_src = lap_matrix[["Driver", "LapNumber", *typ_cols]].merge(
        zone_wide[["Driver", "LapNumber", *zone_cols_c]], on=["Driver", "LapNumber"], how="left"
    )
    log(f"rolling dispersion on {len(typ_cols) + len(zone_cols_c)} series ...")
    t0 = time.perf_counter()
    rolled = rolling_stats(roll_src, typ_cols + zone_cols_c)
    log(f"  rolling done in {time.perf_counter() - t0:.1f}s, shape {rolled.shape}")
    sectors = sector_rolling(laps)

    cand = zone_wide.merge(rolled, on=["Driver", "LapNumber"], how="left")
    cand = cand.merge(sectors, on=["Driver", "LapNumber"], how="left")
    cand = cand.loc[:, ~cand.columns.duplicated()]
    if cand.duplicated(["Driver", "LapNumber"]).any():
        raise SystemExit("duplicate Driver+LapNumber rows in the candidate table")
    feature_cols = [c for c in cand.columns if c not in ("Driver", "LapNumber")]
    # Align to the lap matrix row set.
    cand = lap_matrix[["Driver", "LapNumber"]].merge(cand, on=["Driver", "LapNumber"], how="left")
    cand_path = OUT / "candidates.csv"
    cand.to_csv(cand_path, index=False)
    log(f"wrote {cand_path} shape={cand.shape}")

    if not skip_eval:
        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = "1"
        env["OPENBLAS_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["NUMEXPR_NUM_THREADS"] = "1"
        log("running evaluator ...")
        t0 = time.perf_counter()
        proc = subprocess.run(
            [str(PY), str(EVALUATOR), str(cand_path), "--k", "2,3,4"],
            cwd=str(_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        (OUT / "evaluator_stdout.txt").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr)
        log(f"  evaluator exit {proc.returncode} in {time.perf_counter() - t0:.1f}s")
        if proc.returncode != 0:
            log(proc.stderr[-4000:])
            raise SystemExit("evaluator failed")

    scores = pd.read_csv(OUT / "candidates_scores.csv")
    eval_gain = pd.read_csv(OUT / "candidates_gain.csv") if (OUT / "candidates_gain.csv").exists() else pd.DataFrame()

    full = lap_matrix.merge(cand, on=["Driver", "LapNumber"], how="left")
    base_scores = score_features(full, style_columns(lap_matrix), reference_cols=[])
    base_scores.to_csv(OUT / "baseline_scores.csv", index=False)
    vs = zone_vs_typology_corr(full)

    zone_feats = [f"{z}__{m}" for z in SHORTS for m in METRICS]
    zone_scores = scores[scores["feature"].isin(zone_feats)].copy()
    consist_feats = [c for c in scores["feature"] if "__roll_" in c or "__absdev_" in c]
    consist_scores = scores[scores["feature"].isin(consist_feats)].copy()
    sector_feats = [c for c in scores["feature"] if c.endswith("__roll_std5")]
    sector_scores = scores[scores["feature"].isin(sector_feats)].copy()

    zone_scores = zone_scores.copy()
    zone_scores["motivos"] = zone_scores.apply(rejection_reasons, axis=1)
    consist_scores = consist_scores.copy()
    consist_scores["motivos"] = consist_scores.apply(rejection_reasons, axis=1)
    sector_scores = sector_scores.copy()
    sector_scores["motivos"] = sector_scores.apply(rejection_reasons, axis=1)

    selection = pd.concat(
        [
            zone_scores.assign(family="zona"),
            consist_scores.assign(family="consistencia"),
            sector_scores.assign(family="sector"),
        ],
        ignore_index=True,
    )
    selection.to_csv(OUT / "zone_selection.csv", index=False)

    strict_zone_mask = strict_mask(zone_scores)
    strict_cons_mask = strict_mask(consist_scores) if len(consist_scores) else pd.Series(dtype=bool)
    zone_scores = zone_scores.copy()
    # strict_mask was computed on zone_scores before motivos; recompute on the frame we'll use
    strict_zone_mask = strict_mask(zone_scores)

    # --- feature sets ---
    zindex = zone_scores.set_index("feature")

    def best_zone(metric: str, typology: str) -> str | None:
        cands = []
        for z, t in TYP_OF.items():
            if t != typology:
                continue
            feat = f"{z}__{metric}"
            if feat not in zindex.index:
                continue
            r = zindex.loc[feat]
            if not usable_level(r):
                continue
            omega = float(r["omega2_driver_in_team"]) if np.isfinite(r["omega2_driver_in_team"]) else -np.inf
            cands.append((omega, feat))
        if not cands:
            return None
        cands.sort(reverse=True)
        return cands[0][1]

    analogue = []
    for typ_col, metric, typology in ANALOGUE_SPEC:
        chosen = best_zone(metric, typology)
        if chosen is None:
            chosen = typ_col  # fall back to the aggregate itself
        analogue.append(chosen)

    expand = []
    for typ_col, metric, typology in ANALOGUE_SPEC:
        for z, t in TYP_OF.items():
            if t != typology:
                continue
            feat = f"{z}__{metric}"
            if feat not in zindex.index:
                continue
            if usable_level(zindex.loc[feat]) and feat not in expand:
                expand.append(feat)

    strict_pool = zone_scores.loc[strict_zone_mask, "feature"].tolist()
    strict7 = greedy_select(zone_scores, full, strict_pool, max_n=7, max_abs_rho=0.75)
    # Post-hoc: the 90% zero cutoff still lets Lesmo throttle attack (80% zeros)
    # and full throttle (86% zeros) into strict7, and those marginals inflate the
    # permutation null. Dense columns are the same screen with zero_frac <= 0.5.
    zidx = zone_scores.set_index("feature")
    strict_dense = [
        f for f in strict_pool
        if f in zidx.index and float(zidx.loc[f, "zero_frac"]) <= 0.50
    ]

    # Consistency: rank by omega2 among those with signal + reliability, drift not required
    # for the "what happens if we add them" test, but prefer strict if any exist.
    cons_ok = consist_scores[
        (consist_scores["omega2_driver_in_team"] >= OMEGA_MIN)
        & (consist_scores["p_driver_in_team"] < 0.01)
        & (consist_scores["spearman_brown"] >= SB_MIN)
        & (consist_scores["zero_frac"] <= 0.90)
        & (consist_scores["coverage"] >= 0.90)
    ].sort_values("omega2_driver_in_team", ascending=False)
    # Prefer IQR/MAD over absdev when taking the clustering set: absdev is a lap residual.
    cons_level = cons_ok[~cons_ok["feature"].str.endswith("__absdev_rollmed5")]
    pool_cons = cons_level if len(cons_level) else cons_ok
    cons5 = greedy_select(consist_scores, full, pool_cons["feature"].tolist(), max_n=5, max_abs_rho=0.85)
    cons3 = cons5[:3]

    sets = {
        "base7": base_cols,
        "analogue7": analogue,
        "expand": expand,
        "strict7": strict7,
        "strict_dense": strict_dense,
        "cons5": cons5,
        "base7+cons3": base_cols + [c for c in cons3 if c not in base_cols],
    }
    (OUT / "clustering_sets.json").write_text(json.dumps(sets, indent=2))

    gain_parts = []
    for name, cols in sets.items():
        if name == "base7+cons3" and not cons3:
            continue
        if name in ("strict7", "strict_dense", "cons5") and len(cols) < 2:
            continue
        part = run_gain(full, name, cols)
        if len(part):
            gain_parts.append(part)
    gain = pd.concat(gain_parts, ignore_index=True) if gain_parts else pd.DataFrame()
    gain.to_csv(OUT / "replacement_clustering.csv", index=False)

    # --- blocks ---
    log("block matrices ...")
    block_src_cols = list(dict.fromkeys(style_columns(lap_matrix) + zone_feats))
    block_work = full[["Driver", "LapNumber", "Team", "FullName", "Compound", "TyreLife", *block_src_cols]].copy()
    levels = block_median_matrix(block_work, cols=block_src_cols, block_size=BLOCK)
    # IQR on the same columns used for consistency (typology + zone, 4 metrics) plus base7.
    iqr_src = list(dict.fromkeys(base_cols + typ_cols + zone_cols_c))
    iqrs = block_iqr_frame(block_work, iqr_src, block_size=BLOCK)
    iqr_cols = [c for c in iqrs.columns if c.endswith("__block_iqr5")]
    block_joined = levels.merge(
        iqrs[["Driver", "block_index", *iqr_cols]],
        on=["Driver", "block_index"],
        how="left",
    )
    block_joined.to_csv(OUT / "block_candidates.csv", index=False)
    ref_cols = [c for c in style_columns(lap_matrix) if c in block_joined.columns]
    block_iqr_scores = score_features(block_joined, iqr_cols, reference_cols=ref_cols)
    block_iqr_scores.to_csv(OUT / "block_scores.csv", index=False)
    strict_block_mask = strict_mask(block_iqr_scores) if len(block_iqr_scores) else pd.Series(dtype=bool)

    # Map analogue / expand names onto the block-median columns (same names).
    block_gain_parts = []
    block_sets = {
        "block_base7": [c for c in base_cols if c in block_joined.columns],
        "block_analogue7": [c for c in analogue if c in block_joined.columns],
        "block_expand": [c for c in expand if c in block_joined.columns],
    }
    # Block-IQR clustering: greedy among strict, else top by omega with reliability.
    if len(block_iqr_scores):
        bpool = block_iqr_scores.loc[strict_block_mask, "feature"].tolist() if strict_block_mask.any() else []
        if len(bpool) < 2:
            bpool = block_iqr_scores[
                (block_iqr_scores["omega2_driver_in_team"] >= OMEGA_MIN)
                & (block_iqr_scores["spearman_brown"] >= SB_MIN)
                & (block_iqr_scores["zero_frac"] <= 0.90)
                & (block_iqr_scores["coverage"] >= 0.90)
            ]["feature"].tolist()
        block_sets["block_iqr"] = greedy_select(block_iqr_scores, block_joined, bpool, max_n=5, max_abs_rho=0.85)
    for name, cols in block_sets.items():
        part = run_gain(block_joined, name, cols)
        if len(part):
            block_gain_parts.append(part)
    block_gain = pd.concat(block_gain_parts, ignore_index=True) if block_gain_parts else pd.DataFrame()
    block_gain.to_csv(OUT / "block_clustering.csv", index=False)

    # Figures
    heatmap(
        matrix_from_scores(zone_scores, "omega2_driver_in_team").set_index("zona"),
        OUT / "omega2_zonas.png",
        "ω²(piloto|equipo) por curva y métrica — Monza 2025",
    )
    heatmap(
        matrix_from_scores(zone_scores, "share_team").set_index("zona"),
        OUT / "share_team_zonas.png",
        "Cuota de varianza entre equipos por curva y métrica — Monza 2025",
    )

    # Opposite-sign examples for brake point: T1 vs T8 and the medium pair with most flips.
    med = medians.set_index("Driver")
    ex_rows = []
    for drv, r in med.iterrows():
        a = r.get("T4__coast_frac", np.nan)
        b = r.get("T6__coast_frac", np.nan)
        if np.isfinite(a) and np.isfinite(b) and a * b < 0 and abs(a) >= 0.02 and abs(b) >= 0.02:
            ex_rows.append(
                {
                    "piloto": drv,
                    "equipo": r.get("Team", ""),
                    "T4 Roggia coast": a,
                    "T6 Lesmo 1 coast": b,
                    "T7 Lesmo 2 coast": r.get("T7__coast_frac", np.nan),
                    "T11 Parabolica coast": r.get("T11__coast_frac", np.nan),
                    "T1 Rettifilo frenada (m)": r.get("T1__brake_point_rel", np.nan),
                    "T8 Ascari frenada (m)": r.get("T8__brake_point_rel", np.nan),
                }
            )
    examples = pd.DataFrame(ex_rows)
    if len(examples):
        examples["_mag"] = examples["T4 Roggia coast"].abs() + examples["T6 Lesmo 1 coast"].abs()
        examples = examples.sort_values("_mag", ascending=False).drop(columns="_mag")

    # Sector pace correlation
    sector_extra = {}
    if "lap_time__roll_std5" in full.columns:
        d1 = full.groupby("Driver")["lap_time__roll_std5"].median()
        d2 = laps.groupby("Driver")["LapTime"].median()
        d3 = laps.groupby("Driver")["Position"].median()
        both = pd.concat([d1, d2, d3], axis=1).dropna()
        if len(both) >= 5:
            sector_extra["rho_pace"] = float(stats.spearmanr(both.iloc[:, 0], both.iloc[:, 1]).statistic)
            sector_extra["rho_position"] = float(stats.spearmanr(both.iloc[:, 0], both.iloc[:, 2]).statistic)

    recommended = []
    if "recommended" in scores.columns:
        recommended = scores.loc[scores["recommended"] == True, "feature"].tolist()  # noqa: E712

    ctx = {
        "zone_scores": zone_scores,
        "base_scores": base_scores,
        "gain": gain,
        "pairs": pairs,
        "contrib": contrib,
        "offsets": offsets,
        "vs_typology": vs,
        "sanity": sanity,
        "consist_scores": consist_scores,
        "sector_scores": sector_scores,
        "block_gain": block_gain,
        "block_iqr_scores": block_iqr_scores,
        "eval_gain": eval_gain,
        "sets": sets,
        "examples": examples,
        "driver_medians": medians,
        "nan_rates": nan_rates,
        "strict_zone_mask": strict_zone_mask,
        "strict_cons_mask": strict_cons_mask,
        "strict_block_mask": strict_block_mask,
        "selection": selection,
        "n_blocks": int(len(levels)),
        "sector_extra": sector_extra,
        "recommended": recommended,
    }
    report = build_report(ctx)
    (OUT / "REPORT.md").write_text(report)
    # Compact highlights for the parent summary.
    def _gain_dict(frame, name, k):
        if frame is None or frame.empty:
            return {}
        hit = frame[(frame["set"] == name) & (frame["k"] == k)]
        if hit.empty:
            return {}
        r = hit.iloc[0]
        return {
            "set": name,
            "k": int(k),
            "n_features": int(r["n_features"]),
            "silhouette": float(r["silhouette"]),
            "null": float(r["null_silhouette"]),
            "gap": float(r["silhouette_gap"]),
            "ps": float(r["prediction_strength"]),
            "boot_ari": float(r["bootstrap_ari"]),
            "ami_driver": float(r["ami_driver"]),
            "teammate_split_rate": float(r["teammate_split_rate"]),
        }

    highlights = {
        "base7": base_cols,
        "analogue7": analogue,
        "expand": expand,
        "strict7": strict7,
        "strict_dense": strict_dense,
        "cons5": cons5,
        "cons3": cons3,
        "n_strict_zone": int(strict_zone_mask.sum()),
        "n_strict_cons": int(strict_cons_mask.sum()) if len(strict_cons_mask) else 0,
        "n_strict_block": int(strict_block_mask.sum()) if len(strict_block_mask) else 0,
        "recommended": recommended,
        "clustering": [
            _gain_dict(gain, name, k)
            for name in ("base7", "analogue7", "expand", "strict7", "strict_dense", "cons5", "base7+cons3")
            for k in (2, 3)
        ],
        "block_clustering": [
            _gain_dict(block_gain, name, k)
            for name in ("block_base7", "block_analogue7", "block_expand", "block_iqr")
            for k in (2, 3)
        ],
        "sector_extra": sector_extra,
        "top_zone": zone_scores.sort_values("omega2_driver_in_team", ascending=False)[
            ["feature", "omega2_driver_in_team", "share_team", "spearman_brown", "teammate_sign_agreement",
             "omega2_compound_within", "rho_lap_within", "rho_tyre_life_within", "zero_frac"]
        ].head(8).to_dict(orient="records"),
        "top_consist": consist_scores.sort_values("omega2_driver_in_team", ascending=False)[
            ["feature", "omega2_driver_in_team", "share_team", "spearman_brown", "teammate_sign_agreement",
             "omega2_compound_within", "rho_lap_within"]
        ].head(5).to_dict(orient="records") if len(consist_scores) else [],
    }
    (OUT / "highlights.json").write_text(json.dumps(highlights, indent=2, default=float))
    log(f"wrote {OUT / 'REPORT.md'}")
    log(json.dumps(highlights["clustering"], indent=2, default=float))


if __name__ == "__main__":
    main()
