"""Normalization and confounder-control strategies for Monza 2025 style metrics.

Recomputes the raw per-zone telemetry metrics, applies each normalization at the
driver × lap × typology grain the clustering matrix uses, and scores the
replacements with ``f1_style_clustering.analysis.feature_evaluation``.

The official evaluator is invoked at the end for the per-feature score table.
Replacement-set clustering (the comparison that matters for this family) is
computed here with ``clustering_gain``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import warnings
from pathlib import Path

# Shared machine: keep BLAS from grabbing every core.
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "2")

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import SplineTransformer, StandardScaler

sys.path.insert(0, "/workspace/src")

from f1_style_clustering.analysis.feature_evaluation import (  # noqa: E402
    clustering_gain,
    score_features,
)
from f1_style_clustering.features.aggregators import (  # noqa: E402
    collapse_to_driver_lap_typology,
    extract_style_features_from_telemetry,
    lap_vectors_from_typology,
)
from f1_style_clustering.features.metrics import get_braking_point  # noqa: E402
from f1_style_clustering.features.preprocessor import (  # noqa: E402
    normalize_typology_session_median,
)
from f1_style_clustering.features.screening import select_features_by_icc, style_columns  # noqa: E402
from f1_style_clustering.features.zoi import get_corner_fragments  # noqa: E402

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

DATA = Path("/workspace/cache/derived/2025_italian_grand_prix_r")
OUT = Path("/workspace/experiments/telemetry_candidates/normalization")
PYTHON = "/tmp/venv/bin/python"
EVALUATOR = "/workspace/scripts/evaluate_candidate_features.py"

METRICS = [
    "brake_point_rel",
    "trail_brake_frac",
    "apex_speed_rel",
    "coast_frac",
]
# ICC-selected base set from the thesis diagnosis, plus the three brake points.
BASE7 = [
    "fast__apex_speed_rel",
    "medium__apex_speed_rel",
    "slow__coast_frac",
    "medium__coast_frac",
    "fast__coast_frac",
    "slow__trail_brake_frac",
    "medium__trail_brake_frac",
]
BRAKE3 = [
    "slow__brake_point_rel",
    "medium__brake_point_rel",
    "fast__brake_point_rel",
]
FOCUS = BASE7 + BRAKE3

# Normalizations that replace the 7 base columns in a clustering refit.
REPLACEMENT_NORMS = [
    "session",
    "lapsync",
    "lapsync_roll",
    "lapsync_zone",
    "reg_lap",
    "reg_lap_fe",
    "reg_lin",
    "reg_lin_fe",
    "reg_int",
    "reg_int_fe",
    "reg_spline_fe",
    "reg_lin_fe_gap",
    "lapsync_tyre_fe",
    "reg_lin_fe_xgap50",
    "session_xgap30",
    "session_xgap50",
    "session_xgap100",
    "session_xslip50",
    "teammate",
    "detrend",
    "z_driver",
]


def _finite_interp(dist: np.ndarray, values: np.ndarray, x: float, tol_m: float = 25.0) -> float:
    """Gap at distance x from the nearest sample that actually has a car ahead."""
    if dist.size == 0 or not np.isfinite(x):
        return np.nan
    i = int(np.searchsorted(dist, x))
    best_v, best_d = np.nan, np.inf
    for j in (i - 1, i, i + 1):
        if j < 0 or j >= dist.size:
            continue
        if not np.isfinite(values[j]):
            continue
        d = abs(float(dist[j]) - float(x))
        if d < best_d:
            best_d, best_v = d, float(values[j])
    if best_d > tol_m:
        return np.nan
    return best_v


def _window_median(dist: np.ndarray, values: np.ndarray, start: float, end: float) -> float:
    if dist.size == 0:
        return np.nan
    m = (dist >= start) & (dist < end) & np.isfinite(values)
    if int(m.sum()) < 3:
        return np.nan
    return float(np.median(values[m]))


def extract_zone_table(car: pd.DataFrame, tel: pd.DataFrame, zones: dict) -> pd.DataFrame:
    """Raw zone metrics plus traffic gaps. One row per driver × lap × zone."""
    tel_idx: dict[tuple, tuple[np.ndarray, np.ndarray]] = {}
    for (driver, lap), g in tel.groupby(["Driver", "LapNumber"], sort=False):
        dist = g["Distance"].to_numpy(dtype=float)
        gap = pd.to_numeric(g["DistanceToDriverAhead"], errors="coerce").to_numpy(dtype=float)
        ahead = g["DriverAhead"].astype(str).str.strip().to_numpy()
        order = np.argsort(dist, kind="mergesort")
        dist, gap, ahead = dist[order], gap[order], ahead[order]
        # Empty DriverAhead is clean air, not a zero gap.
        gap = gap.copy()
        gap[(ahead == "") | (ahead == "nan") | (ahead == "None")] = np.nan
        tel_idx[(str(driver), int(lap))] = (dist, gap)

    rows: list[dict] = []
    grouped = car.groupby(["Driver", "LapNumber"], sort=False)
    n_laps = grouped.ngroups
    for i, ((driver, lap), g) in enumerate(grouped, start=1):
        if i % 200 == 0:
            print(f"  extract {i}/{n_laps}", flush=True)
        driver, lap = str(driver), int(lap)
        feats = extract_style_features_from_telemetry(g, zones, include_throttle_onset=False)
        by_corner = {f["corner"]: f for f in feats}
        dist, gap = tel_idx.get((driver, lap), (np.array([]), np.array([])))
        for corner, zone in zones.items():
            feat = by_corner.get(corner)
            if feat is None:
                continue
            fragments = get_corner_fragments(g, zone)
            brake_dist = get_braking_point(fragments["braking"])
            b0 = float(zone["braking"][0])
            row = {
                "Driver": driver,
                "LapNumber": lap,
                "corner": corner,
                "typology": zone.get("typology"),
                "brake_point_rel": feat.get("brake_point_rel"),
                "trail_brake_frac": feat.get("trail_brake_frac"),
                "apex_speed_rel": feat.get("apex_speed_rel"),
                "throttle_attack": feat.get("throttle_attack"),
                "coast_frac": feat.get("coast_frac"),
                "full_throttle_frac": feat.get("full_throttle_frac"),
                "brake_distance_m": brake_dist,
                "gap_brake_m": _finite_interp(dist, gap, brake_dist),
                "gap_straight_m": _window_median(dist, gap, b0 - 200.0, b0),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def session_matrix(zone: pd.DataFrame) -> pd.DataFrame:
    """Official pipeline: typology session-median, then median per lap × typology."""
    feature_cols = [c for c in METRICS if c in zone.columns]
    long_rel = normalize_typology_session_median(zone, feature_cols=feature_cols)
    lap_typ = collapse_to_driver_lap_typology(long_rel, feature_cols=feature_cols)
    vectors = lap_vectors_from_typology(lap_typ, feature_cols=feature_cols)
    return vectors


def _median_by_typology(zone: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = (
        zone.groupby(["Driver", "LapNumber", "typology"], dropna=False)[cols]
        .median()
        .reset_index()
    )
    return out


def _pivot_typology(long_df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    wide = long_df.pivot_table(
        index=["Driver", "LapNumber"],
        columns="typology",
        values=cols,
        aggfunc="median",
    )
    wide.columns = [f"{typ}__{feat}" for feat, typ in wide.columns.to_list()]
    return wide.reset_index()


def _field_reference(values: np.ndarray, laps: np.ndarray, window: int) -> np.ndarray:
    """Median of all drivers' values on laps in [L-window, L+window], per row."""
    buckets: dict[int, np.ndarray] = {}
    for lap in np.unique(laps[np.isfinite(values)]):
        chunk = values[laps == lap]
        chunk = chunk[np.isfinite(chunk)]
        if chunk.size:
            buckets[int(lap)] = chunk
    lap_ids = np.array(sorted(buckets))
    ref_at = {}
    for lap in lap_ids:
        parts = [buckets[int(other)] for other in lap_ids if abs(int(other) - int(lap)) <= window]
        ref_at[int(lap)] = float(np.median(np.concatenate(parts))) if parts else np.nan
    return np.array([ref_at.get(int(lap), np.nan) for lap in laps], dtype=float)


def _demean(values: np.ndarray, groups: np.ndarray) -> np.ndarray:
    s = pd.Series(values)
    return (s - s.groupby(groups, sort=False).transform("mean")).to_numpy(dtype=float)


def _ols_residual(y: np.ndarray, X: np.ndarray, groups: np.ndarray | None) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Residuals of y on X.

    groups is None for a pooled fit (intercept included). Otherwise slopes are
    the within-driver slopes and the returned series is y − Xβ (driver effects
    kept: α_d + ε). Rows with non-finite y or X stay NaN and are not used to fit.
    """
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    resid = np.full(y.shape, np.nan)
    beta = np.zeros(X.shape[1], dtype=float)
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    if groups is not None:
        ok = ok & pd.notna(groups)
    if int(ok.sum()) < X.shape[1] + 5:
        return resid, beta, np.nan, np.nan
    y_ok = y[ok]
    X_ok = X[ok]
    if groups is None:
        A = np.column_stack([np.ones(len(y_ok)), X_ok])
        coef, _, rank, singular = np.linalg.lstsq(A, y_ok, rcond=None)
        fitted = A @ coef
        beta = coef[1:]
        ss_tot = float(((y_ok - y_ok.mean()) ** 2).sum())
        ss_res = float(((y_ok - fitted) ** 2).sum())
        cond = float(singular[0] / singular[rank - 1]) if rank > 0 and singular[rank - 1] > 0 else np.nan
        resid[ok] = y_ok - fitted
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
        return resid, beta, r2, cond

    g_ok = np.asarray(groups)[ok]
    y_dm = _demean(y_ok, g_ok)
    X_dm = np.column_stack([_demean(X_ok[:, j], g_ok) for j in range(X_ok.shape[1])])
    keep = np.nanstd(X_dm, axis=0) > 1e-8
    if int(keep.sum()) == 0:
        resid[ok] = y_ok
        return resid, beta, 0.0, np.nan
    coef, _, rank, singular = np.linalg.lstsq(X_dm[:, keep], y_dm, rcond=None)
    beta[keep] = coef
    fitted_within = X_dm[:, keep] @ coef
    ss_tot = float((y_dm ** 2).sum())
    ss_res = float(((y_dm - fitted_within) ** 2).sum())
    cond = float(singular[0] / singular[rank - 1]) if rank > 0 and singular[rank - 1] > 0 else np.nan
    # y − Xβ keeps α_d = ȳ_d − X̄_d β.
    resid[ok] = y_ok - X_ok @ beta
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return resid, beta, r2, cond


def _compound_dummies(compound: pd.Series) -> pd.DataFrame:
    cat = pd.Categorical(compound.astype(str), categories=["HARD", "MEDIUM", "SOFT"])
    return pd.get_dummies(cat, prefix="cmp", drop_first=True, dtype=float)


def _spline_basis(lap: np.ndarray) -> np.ndarray:
    """Quantile cubic spline of LapNumber, 4 knots, bias dropped (6 columns)."""
    spl = SplineTransformer(
        n_knots=4,
        degree=3,
        knots="quantile",
        extrapolation="continue",
        include_bias=False,
    )
    return spl.fit_transform(np.asarray(lap, dtype=float).reshape(-1, 1))


def build_candidates(zone: pd.DataFrame, meta: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return candidate wide frame, regression diagnostics, traffic summary."""
    zone = zone.merge(meta[["Driver", "LapNumber", "Team", "Compound", "TyreLife"]], on=["Driver", "LapNumber"], how="inner")
    for col in METRICS:
        zone[col] = pd.to_numeric(zone[col], errors="coerce")

    # Zone-synchronous: subtract the field median of that corner on that lap, then
    # collapse with the typology median. This is not the same as subtracting the
    # median of the typology aggregate.
    zone_sync = zone.copy()
    for col in METRICS:
        ref = zone_sync.groupby(["corner", "LapNumber"])[col].transform("median")
        zone_sync[col] = zone_sync[col] - ref
    wide_zone = _pivot_typology(_median_by_typology(zone_sync, METRICS), METRICS)

    raw_long = _median_by_typology(zone, METRICS)
    gap_long = (
        zone.groupby(["Driver", "LapNumber", "typology"], dropna=False)
        .agg(
            gap_brake_min=("gap_brake_m", "min"),
            gap_brake_median=("gap_brake_m", "median"),
            gap_straight_min=("gap_straight_m", "min"),
            n_zones=("corner", "size"),
            n_gap_brake=("gap_brake_m", "count"),
        )
        .reset_index()
    )
    raw_long = raw_long.merge(gap_long, on=["Driver", "LapNumber", "typology"], how="left")
    raw_long = raw_long.merge(meta, on=["Driver", "LapNumber"], how="left")

    wide_raw = _pivot_typology(raw_long, METRICS)

    # The exported matrix is the current pipeline (typology session median).
    # Recomputed zone medians match those columns up to an additive constant
    # (see reconstruction_check.csv); pinning `session` to the export makes the
    # baseline identical to the thesis diagnosis. Location does not affect the
    # other strategies: lap-sync subtracts a median, and the regressions include
    # an intercept or a within-driver demean.
    wide_session = meta[["Driver", "LapNumber"] + [c for c in FOCUS if c in meta.columns]].copy()
    if not all(c in wide_session.columns for c in FOCUS):
        raise ValueError("meta must carry the exported focus columns")

    pieces = {"raw": wide_raw, "session": wide_session, "lapsync_zone": wide_zone}

    # Typology-level lap sync and rolling field median, on the raw aggregate.
    lap_sync = wide_raw[["Driver", "LapNumber"]].copy()
    lap_roll = wide_raw[["Driver", "LapNumber"]].copy()
    laps = wide_raw["LapNumber"].to_numpy(dtype=float)
    for col in FOCUS:
        values = wide_raw[col].to_numpy(dtype=float)
        ref = wide_raw.groupby("LapNumber")[col].transform("median").to_numpy(dtype=float)
        lap_sync[col] = values - ref
        lap_roll[col] = values - _field_reference(values, laps, window=2)
    pieces["lapsync"] = lap_sync
    pieces["lapsync_roll"] = lap_roll

    # Design matrices are lap-level; gap is typology-specific and added per column.
    base = wide_raw[["Driver", "LapNumber"]].merge(meta, on=["Driver", "LapNumber"], how="left")
    base = base.sort_values(["Driver", "LapNumber"]).reset_index(drop=True)
    # Reindex every wide frame to this lap order.
    key = ["Driver", "LapNumber"]
    for name in list(pieces):
        pieces[name] = base[key].merge(pieces[name], on=key, how="left")

    dummies = _compound_dummies(base["Compound"])
    lap_v = base["LapNumber"].to_numpy(dtype=float)
    life = base["TyreLife"].to_numpy(dtype=float)
    drivers = base["Driver"].astype(str).to_numpy()
    dummy_mat = dummies.to_numpy(dtype=float)
    inter = dummy_mat * life.reshape(-1, 1)
    spline = _spline_basis(lap_v)

    designs: dict[str, np.ndarray] = {
        "reg_lap": lap_v.reshape(-1, 1),
        "reg_lin": np.column_stack([lap_v, life, dummy_mat]),
        "reg_int": np.column_stack([lap_v, life, dummy_mat, inter]),
        "reg_spline_fe": np.column_stack([spline, life, dummy_mat]),
    }
    design_names = {
        "reg_lap": ["LapNumber"],
        "reg_lin": ["LapNumber", "TyreLife"] + list(dummies.columns),
        "reg_int": ["LapNumber", "TyreLife"] + list(dummies.columns) + [f"{c}_x_TyreLife" for c in dummies.columns],
        "reg_spline_fe": [f"spline{i}" for i in range(spline.shape[1])] + ["TyreLife"] + list(dummies.columns),
    }

    # Gap covariate aligned to each FOCUS column (median gap of that typology).
    gap_wide = raw_long.pivot_table(
        index=["Driver", "LapNumber"], columns="typology", values="gap_brake_median", aggfunc="median"
    )
    gap_wide.columns = [f"{typ}__gap" for typ in gap_wide.columns]
    gap_wide = gap_wide.reset_index()
    straight_wide = raw_long.pivot_table(
        index=["Driver", "LapNumber"], columns="typology", values="gap_straight_min", aggfunc="min"
    )
    straight_wide.columns = [f"{typ}__straight" for typ in straight_wide.columns]
    straight_wide = straight_wide.reset_index()
    flags = base[key].merge(gap_wide, on=key, how="left").merge(straight_wide, on=key, how="left")

    diag_rows = []
    reg_frames: dict[str, pd.DataFrame] = {}

    def _store(norm: str, columns: dict[str, np.ndarray]) -> None:
        frame = base[key].copy()
        for col, values in columns.items():
            frame[col] = values
        reg_frames[norm] = frame

    # Pooled and within-driver fits for the shared designs.
    shared_specs = [
        ("reg_lap", False),
        ("reg_lap_fe", True),
        ("reg_lin", False),
        ("reg_lin_fe", True),
        ("reg_int", False),
        ("reg_int_fe", True),
        ("reg_spline_fe", True),
    ]
    # Map FE names onto the design without the _fe suffix.
    design_key = {
        "reg_lap": "reg_lap",
        "reg_lap_fe": "reg_lap",
        "reg_lin": "reg_lin",
        "reg_lin_fe": "reg_lin",
        "reg_int": "reg_int",
        "reg_int_fe": "reg_int",
        "reg_spline_fe": "reg_spline_fe",
    }

    for norm, use_fe in shared_specs:
        X = designs[design_key[norm]]
        cols_out: dict[str, np.ndarray] = {}
        for feat in FOCUS:
            y = pieces["raw"][feat].to_numpy(dtype=float)
            groups = drivers if use_fe else None
            resid, beta, r2, cond = _ols_residual(y, X, groups)
            cols_out[feat] = resid
            diag_rows.append({
                "feature": feat,
                "normalization": norm,
                "r2": r2,
                "condition": cond,
                "n": int(np.isfinite(resid).sum()),
                "beta_json": json.dumps({
                    name: float(b) for name, b in zip(design_names[design_key[norm]], beta)
                }),
            })
        _store(norm, cols_out)

    # Within-driver fit plus log gap at brake onset (typology-specific).
    X_lin = designs["reg_lin"]
    gap_cols: dict[str, np.ndarray] = {}
    for feat in FOCUS:
        typ = feat.split("__", 1)[0]
        gap = flags[f"{typ}__gap"].to_numpy(dtype=float)
        log_gap = np.log1p(np.clip(gap, 0, None))
        # Missing gap: leave NaN in the column so the fit ignores the row, then
        # fill the residual for those rows with the no-gap prediction only if
        # the other covariates are finite — handled inside _ols_residual by
        # requiring finite X. Impute log-gap with the median so a missing
        # sensor reading does not drop the lap from every other covariate.
        med = np.nanmedian(log_gap)
        log_gap_imp = np.where(np.isfinite(log_gap), log_gap, med)
        X = np.column_stack([X_lin, log_gap_imp])
        y = pieces["raw"][feat].to_numpy(dtype=float)
        resid, beta, r2, cond = _ols_residual(y, X, drivers)
        gap_cols[feat] = resid
        names = design_names["reg_lin"] + ["log1p_gap_brake"]
        diag_rows.append({
            "feature": feat,
            "normalization": "reg_lin_fe_gap",
            "r2": r2,
            "condition": cond,
            "n": int(np.isfinite(resid).sum()),
            "beta_json": json.dumps({n: float(b) for n, b in zip(names, beta)}),
        })
    _store("reg_lin_fe_gap", gap_cols)

    # Lap-sync first (common fuel / track evolution), then within-driver tyre
    # and compound slopes only. LapNumber is not entered again.
    X_tyre = np.column_stack([life, dummy_mat])
    tyre_names = ["TyreLife"] + list(dummies.columns)
    tyre_cols: dict[str, np.ndarray] = {}
    for feat in FOCUS:
        y = pieces["lapsync"][feat].to_numpy(dtype=float)
        resid, beta, r2, cond = _ols_residual(y, X_tyre, drivers)
        tyre_cols[feat] = resid
        diag_rows.append({
            "feature": feat,
            "normalization": "lapsync_tyre_fe",
            "r2": r2,
            "condition": cond,
            "n": int(np.isfinite(resid).sum()),
            "beta_json": json.dumps({n: float(b) for n, b in zip(tyre_names, beta)}),
        })
    _store("lapsync_tyre_fe", tyre_cols)

    # Traffic masks: a typology cell is contaminated when the closest car ahead
    # at any of its zones' brake onsets is inside the threshold. NaN gap
    # (nobody ahead, or no sample) is treated as not in traffic.
    def _mask(threshold: float, source: str) -> pd.DataFrame:
        out = pd.DataFrame(index=base.index)
        for typ in ("slow", "medium", "fast"):
            if source == "brake":
                gap = flags[f"{typ}__gap"].to_numpy(dtype=float)
            else:
                gap = flags[f"{typ}__straight"].to_numpy(dtype=float)
            out[typ] = np.isfinite(gap) & (gap < threshold)
        return out

    masks = {
        "session_xgap30": _mask(30.0, "brake"),
        "session_xgap50": _mask(50.0, "brake"),
        "session_xgap100": _mask(100.0, "brake"),
        "session_xslip50": _mask(50.0, "straight"),
    }
    for norm, mask in masks.items():
        frame = pieces["session"][key].copy()
        for feat in FOCUS:
            typ = feat.split("__", 1)[0]
            values = pieces["session"][feat].to_numpy(dtype=float).copy()
            values[mask[typ].to_numpy()] = np.nan
            frame[feat] = values
        pieces[norm] = frame

    # Same 50 m exclusion applied to the within-driver linear residual.
    frame = reg_frames["reg_lin_fe"][key].copy()
    mask50 = masks["session_xgap50"]
    for feat in FOCUS:
        typ = feat.split("__", 1)[0]
        values = reg_frames["reg_lin_fe"][feat].to_numpy(dtype=float).copy()
        values[mask50[typ].to_numpy()] = np.nan
        frame[feat] = values
    pieces["reg_lin_fe_xgap50"] = frame

    # Teammate contrast at the same lap. Singleton team-laps (Kick Sauber, or a
    # teammate already out) stay missing: there is no within-team contrast.
    team = base["Team"].astype(str)
    mate = base[key].copy()
    for feat in FOCUS:
        tmp = pd.DataFrame({
            "Team": team,
            "LapNumber": base["LapNumber"],
            "y": pieces["raw"][feat].to_numpy(dtype=float),
        })
        n_pair = tmp.groupby(["Team", "LapNumber"])["y"].transform(lambda s: np.isfinite(s).sum())
        team_mean = tmp.groupby(["Team", "LapNumber"])["y"].transform("mean")
        contrast = tmp["y"] - team_mean
        contrast = contrast.where(n_pair >= 2)
        mate[feat] = contrast.to_numpy(dtype=float)
    pieces["teammate"] = mate

    # Within-driver linear detrend, driver mean kept. And a full within-driver
    # z-score, which removes the driver level and is expected to fail as a
    # style feature.
    detrend = base[key].copy()
    zdriver = base[key].copy()
    for feat in FOCUS:
        y = pieces["raw"][feat].to_numpy(dtype=float)
        out_d = np.full(len(y), np.nan)
        out_z = np.full(len(y), np.nan)
        for driver, idx in pd.Series(drivers).groupby(drivers).groups.items():
            idx = np.asarray(list(idx))
            yy = y[idx]
            xx = lap_v[idx]
            ok = np.isfinite(yy) & np.isfinite(xx)
            if int(ok.sum()) < 8 or np.nanstd(xx[ok]) == 0:
                continue
            slope, intercept = np.polyfit(xx[ok], yy[ok], 1)
            # Remove the slope, keep the driver's mean level.
            out_d[idx] = yy - slope * (xx - np.nanmean(xx[ok]))
            mu, sd = np.nanmean(yy[ok]), np.nanstd(yy[ok], ddof=0)
            if sd > 1e-8:
                out_z[idx] = (yy - mu) / sd
        detrend[feat] = out_d
        zdriver[feat] = out_z
        diag_rows.append({
            "feature": feat,
            "normalization": "detrend",
            "r2": np.nan,
            "condition": np.nan,
            "n": int(np.isfinite(out_d).sum()),
            "beta_json": "{}",
        })
    pieces["detrend"] = detrend
    pieces["z_driver"] = zdriver

    # Stack to one candidate row per lap.
    cand = base[key].copy()
    for norm, frame in {**pieces, **reg_frames}.items():
        if norm in ("raw",):
            # Raw is scored so the constant-shift invariance of the session
            # median is visible, but it is not a proposed replacement.
            pass
        use = frame[key + [c for c in FOCUS if c in frame.columns]].copy()
        use = use.rename(columns={c: f"{c}__{norm}" for c in FOCUS if c in use.columns})
        cand = cand.merge(use, on=key, how="left")

    diag = pd.DataFrame(diag_rows)

    # Traffic exposure at the typology grain and at the lap grain.
    traffic_rows = []
    for typ in ("slow", "medium", "fast"):
        gap = flags[f"{typ}__gap"]
        straight = flags[f"{typ}__straight"]
        traffic_rows.append({
            "grain": "typology",
            "typology": typ,
            "n": int(len(flags)),
            "n_gap_observed": int(gap.notna().sum()),
            "frac_gap_lt_30": float((gap < 30).mean()),
            "frac_gap_lt_50": float((gap < 50).mean()),
            "frac_gap_lt_100": float((gap < 100).mean()),
            "frac_straight_lt_50": float((straight < 50).mean()),
            "median_gap_m": float(gap.median(skipna=True)),
        })
    # A lap is "affected" if any of the three typologies is inside the threshold.
    any30 = np.zeros(len(flags), dtype=bool)
    any50 = np.zeros(len(flags), dtype=bool)
    any100 = np.zeros(len(flags), dtype=bool)
    any_slip = np.zeros(len(flags), dtype=bool)
    for typ in ("slow", "medium", "fast"):
        gap = flags[f"{typ}__gap"].to_numpy(dtype=float)
        straight = flags[f"{typ}__straight"].to_numpy(dtype=float)
        any30 |= np.isfinite(gap) & (gap < 30)
        any50 |= np.isfinite(gap) & (gap < 50)
        any100 |= np.isfinite(gap) & (gap < 100)
        any_slip |= np.isfinite(straight) & (straight < 50)
    traffic_rows.append({
        "grain": "lap_any_typology",
        "typology": "any",
        "n": int(len(flags)),
        "n_gap_observed": int(flags[[c for c in flags.columns if c.endswith("__gap")]].notna().any(axis=1).sum()),
        "frac_gap_lt_30": float(any30.mean()),
        "frac_gap_lt_50": float(any50.mean()),
        "frac_gap_lt_100": float(any100.mean()),
        "frac_straight_lt_50": float(any_slip.mean()),
        "median_gap_m": np.nan,
    })
    # Zone-level exposure (before typology aggregation).
    for typ, g in zone.groupby("typology"):
        gap = g["gap_brake_m"]
        traffic_rows.append({
            "grain": "zone",
            "typology": typ,
            "n": int(len(g)),
            "n_gap_observed": int(gap.notna().sum()),
            "frac_gap_lt_30": float((gap < 30).mean()),
            "frac_gap_lt_50": float((gap < 50).mean()),
            "frac_gap_lt_100": float((gap < 100).mean()),
            "frac_straight_lt_50": float((g["gap_straight_m"] < 50).mean()),
            "median_gap_m": float(gap.median(skipna=True)),
        })
    traffic = pd.DataFrame(traffic_rows)
    return cand, diag, traffic


def _focus_cols(norm: str) -> list[str]:
    return [f"{feat}__{norm}" for feat in BASE7]


def cluster_leakage(df: pd.DataFrame, cols: list[str], k: int) -> list[dict]:
    frame = df.dropna(subset=cols).reset_index(drop=True)
    if len(frame) < 30:
        return []
    X = StandardScaler().fit_transform(frame[cols].to_numpy(dtype=float))
    labels = KMeans(n_clusters=k, n_init=20, random_state=42).fit_predict(X)
    rows = []
    order = []
    for lab in range(k):
        m = labels == lab
        order.append((float(frame.loc[m, "LapNumber"].median()), lab))
    order.sort()
    for rank, (_, lab) in enumerate(order):
        m = labels == lab
        sub = frame.loc[m]
        n = int(m.sum())
        comp = sub["Compound"].astype(str).value_counts(normalize=True)
        rows.append({
            "k": k,
            "cluster_by_lap": rank,
            "kmeans_label": int(lab),
            "n": n,
            "median_tyre_life": float(sub["TyreLife"].median()),
            "median_lap": float(sub["LapNumber"].median()),
            "pct_hard": float(comp.get("HARD", 0.0)),
            "pct_medium": float(comp.get("MEDIUM", 0.0)),
            "pct_soft": float(comp.get("SOFT", 0.0)),
        })
    return rows


def summarize(scores: pd.DataFrame, gain: pd.DataFrame, leakage: pd.DataFrame) -> pd.DataFrame:
    scores = scores.copy()
    parts = scores["feature"].str.rsplit("__", n=1)
    scores["base_feature"] = parts.str[0]
    scores["normalization"] = parts.str[1]
    rows = []
    for norm, g in scores.groupby("normalization"):
        base = g[g["base_feature"].isin(BASE7)]
        brake = g[g["base_feature"].isin(BRAKE3)]

        def pack(block: pd.DataFrame, prefix: str) -> dict:
            if block.empty:
                return {}
            return {
                f"{prefix}_omega2_driver": float(block["omega2_driver_in_team"].mean()),
                f"{prefix}_omega2_compound": float(block["omega2_compound_within"].mean()),
                f"{prefix}_rho_lap": float(block["rho_lap_within"].mean()),
                f"{prefix}_abs_rho_lap": float(block["rho_lap_within"].abs().mean()),
                f"{prefix}_rho_tyre": float(block["rho_tyre_life_within"].mean()),
                f"{prefix}_spearman_brown": float(block["spearman_brown"].mean()),
                f"{prefix}_share_team": float(block["share_team"].mean()),
                f"{prefix}_coverage": float(block["coverage"].mean()),
                f"{prefix}_sign_agree": float(block["teammate_sign_agreement"].mean()),
            }

        row = {"normalization": norm}
        row.update(pack(base, "base7"))
        row.update(pack(brake, "brake3"))
        sub = gain[gain["normalization"] == norm]
        for _, r in sub.iterrows():
            k = int(r["k"])
            row[f"k{k}_silhouette"] = r["silhouette"]
            row[f"k{k}_null"] = r["null_silhouette"]
            row[f"k{k}_gap"] = r["silhouette_gap"]
            row[f"k{k}_ps"] = r["prediction_strength"]
            row[f"k{k}_boot_ari"] = r["bootstrap_ari"]
            row[f"k{k}_ami_driver"] = r["ami_driver"]
            row[f"k{k}_ami_compound"] = r["ami_compound"]
            row[f"k{k}_teammate_split"] = r["teammate_split_rate"]
            row[f"k{k}_n_laps"] = r["n_laps"]
        leak = leakage[leakage["normalization"] == norm]
        for k, lk in leak.groupby("k"):
            row[f"k{int(k)}_tyre_span"] = float(lk["median_tyre_life"].max() - lk["median_tyre_life"].min())
            row[f"k{int(k)}_lap_span"] = float(lk["median_lap"].max() - lk["median_lap"].min())
        rows.append(row)
    return pd.DataFrame(rows).sort_values("normalization").reset_index(drop=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("loading exported tables", flush=True)
    matrix = pd.read_csv(DATA / "lap_matrix.csv")
    zones = json.loads((DATA / "zones.json").read_text())
    meta = matrix[["Driver", "LapNumber", "Team", "Compound", "TyreLife"] + FOCUS].copy()
    meta["LapNumber"] = meta["LapNumber"].astype(int)

    icc_cols = select_features_by_icc(matrix, style_columns(matrix), min_icc=0.25)
    print("ICC base columns:", icc_cols)
    missing = [c for c in BASE7 if c not in icc_cols]
    if missing:
        raise SystemExit(f"BASE7 does not match ICC selection, missing {missing}, got {icc_cols}")

    cache = OUT / "raw_zones.csv"
    if cache.exists():
        print(f"loading cached zone table {cache}", flush=True)
        zone = pd.read_csv(cache)
    else:
        print("extracting raw zone metrics from car.pkl + tel.pkl", flush=True)
        car = pd.read_pickle(DATA / "car.pkl")
        tel = pd.read_pickle(DATA / "tel.pkl")
        # Restrict to the laps that already survived the canonical filter.
        car = car.merge(meta[["Driver", "LapNumber"]], on=["Driver", "LapNumber"], how="inner")
        tel = tel.merge(meta[["Driver", "LapNumber"]], on=["Driver", "LapNumber"], how="inner")
        zone = extract_zone_table(car, tel, zones)
        zone.to_csv(cache, index=False)
        print(f"zone rows {len(zone)} -> {cache}", flush=True)
        del car, tel

    print("validating session-median reconstruction", flush=True)
    rebuilt = session_matrix(zone)
    check = matrix.merge(
        rebuilt,
        on=["Driver", "LapNumber"],
        suffixes=("_export", "_rebuilt"),
    )
    val_rows = []
    for col in FOCUS:
        a = check[f"{col}_export"]
        b = check[f"{col}_rebuilt"]
        ok = a.notna() & b.notna()
        diff = (a[ok] - b[ok]).abs()
        rho = float(a[ok].corr(b[ok])) if ok.sum() > 5 else np.nan
        val_rows.append({
            "feature": col,
            "n": int(ok.sum()),
            "max_abs_diff": float(diff.max()) if len(diff) else np.nan,
            "median_abs_diff": float(diff.median()) if len(diff) else np.nan,
            "pearson": rho,
        })
        print(f"  {col}: n={ok.sum()} max|diff|={diff.max():.4g} pearson={rho:.6f}")
    # A pure location shift means the per-lap aggregate matches and only the
    # subtracted session reference differs (dropped laps in the original median,
    # or an equivalent constant). Variance shares, rank correlations and
    # z-scored K-means are invariant to that constant.
    offsets = []
    for col in FOCUS:
        a = check[f"{col}_export"].to_numpy(dtype=float)
        b = check[f"{col}_rebuilt"].to_numpy(dtype=float)
        delta = a - b
        offsets.append({"feature": col, "offset_export_minus_rebuilt": float(np.nanmean(delta)), "offset_std": float(np.nanstd(delta))})
    val = pd.DataFrame(val_rows).merge(pd.DataFrame(offsets), on="feature")
    val.to_csv(OUT / "reconstruction_check.csv", index=False)
    if (val["pearson"] < 0.999).any() or (val["offset_std"] > 1e-4).any():
        raise SystemExit("session reconstruction is not a pure location shift of lap_matrix")
    print("  reconstruction is a pure location shift; baseline will use the exported columns")

    print("building normalizations", flush=True)
    cand, diag, traffic = build_candidates(zone, meta)
    # Attach metadata so score_features and clustering_gain can run on this
    # frame directly. Candidate names do not collide with the 17 style columns.
    scored_frame = matrix.merge(cand, on=["Driver", "LapNumber"], how="left")
    cand_path = OUT / "candidates.csv"
    cand.to_csv(cand_path, index=False)
    diag.to_csv(OUT / "regression_diagnostics.csv", index=False)
    traffic.to_csv(OUT / "traffic_summary.csv", index=False)
    print(f"candidates {cand.shape} -> {cand_path}", flush=True)
    print(traffic.to_string(index=False))

    focus_names = [c for c in scored_frame.columns if any(c.startswith(f + "__") for f in FOCUS)]
    # Keep raw in the score table; it is the un-normalized typology median.
    print(f"scoring {len(focus_names)} columns", flush=True)
    current = style_columns(matrix)
    scores = score_features(scored_frame, focus_names, reference_cols=current)
    scores.to_csv(OUT / "candidates_scores.csv", index=False)

    print("replacement clustering", flush=True)
    gain_rows = []
    leak_rows = []
    # Baseline: the exported 7 columns, same estimator as clustering_gain.
    base_gain = clustering_gain(scored_frame, BASE7, (), k_range=(2, 3))
    base_gain.insert(0, "normalization", "exported_base7")
    gain_rows.append(base_gain)
    for k in (2, 3):
        for row in cluster_leakage(scored_frame, BASE7, k):
            row["normalization"] = "exported_base7"
            leak_rows.append(row)

    for norm in REPLACEMENT_NORMS:
        cols = _focus_cols(norm)
        missing_cols = [c for c in cols if c not in scored_frame.columns]
        if missing_cols:
            print(f"  skip {norm}: missing {missing_cols}")
            continue
        print(f"  cluster {norm}", flush=True)
        try:
            gain = clustering_gain(scored_frame, cols, (), k_range=(2, 3))
        except Exception as exc:  # a degenerate mask should not kill the rest
            print(f"    FAILED {norm}: {exc}")
            continue
        gain.insert(0, "normalization", norm)
        gain_rows.append(gain)
        for k in (2, 3):
            for row in cluster_leakage(scored_frame, cols, k):
                row["normalization"] = norm
                leak_rows.append(row)

    gain = pd.concat(gain_rows, ignore_index=True)
    leakage = pd.DataFrame(leak_rows)
    gain.to_csv(OUT / "replacement_clustering.csv", index=False)
    leakage.to_csv(OUT / "cluster_leakage.csv", index=False)
    summary = summarize(scores, gain, leakage)
    summary.to_csv(OUT / "strategy_summary.csv", index=False)
    focus = scores.copy()
    parts = focus["feature"].str.rsplit("__", n=1)
    focus["base"] = parts.str[0]
    focus["norm"] = parts.str[1]
    key_cols = [
        "base", "norm", "omega2_driver_in_team", "omega2_compound_within", "rho_lap_within",
        "rho_tyre_life_within", "spearman_brown", "share_team", "teammate_sign_agreement",
        "coverage", "icc_driver", "p_driver_in_team",
    ]
    focus.loc[focus["base"].isin(FOCUS), key_cols].to_csv(OUT / "per_feature_key_metrics.csv", index=False)

    with pd.option_context("display.width", 220, "display.max_columns", 40, "display.max_rows", 80):
        show = [
            "normalization",
            "base7_omega2_driver", "base7_omega2_compound", "base7_rho_lap", "base7_abs_rho_lap",
            "base7_spearman_brown", "base7_coverage",
            "k2_silhouette", "k2_null", "k2_gap", "k2_ps", "k2_ami_driver", "k2_ami_compound",
            "k2_teammate_split", "k2_tyre_span", "k2_lap_span", "k2_n_laps",
            "k3_silhouette", "k3_ps", "k3_ami_driver", "k3_ami_compound", "k3_teammate_split",
            "k3_tyre_span", "k3_lap_span",
        ]
        show = [c for c in show if c in summary.columns]
        print(summary[show].to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    # Official evaluator: score table (already written; re-run so the script
    # path is the one the thesis notes) and an add-on gain, which is the wrong
    # comparison for a renormalization and is expected to be flat.
    extra = ",".join(_focus_cols("lapsync"))
    cmd = [
        PYTHON, EVALUATOR, str(cand_path),
        "--k", "2,3",
        "--extra", extra,
        "--out", str(OUT),
    ]
    print("running official evaluator", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
