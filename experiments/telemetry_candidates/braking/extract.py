"""Braking-dynamics candidate features for the Monza 2025 race.

Brake is a boolean channel and car speed is updated at about 4 Hz, so every
deceleration below is a speed-vs-time slope, not a brake-pressure reading.

Primary event
    Inside braking ∪ apex, contiguous Brake==True runs separated by an off-gap
    shorter than 0.40 s are merged (a one-sample dropout). The primary event is
    the earliest run of at least two samples whose speed falls by ≥ 8 km/h
    (otherwise the run with the largest speed drop). Peak, mean, duration,
    attack and the front-loaded profile are measured on that run. Release
    relative to the apex uses the last Brake==True sample in braking ∪ apex,
    which can be a later chicane application.

Outputs
    candidates.csv          lap-level columns scored by evaluate_candidate_features.py
    long_zone_metrics.csv   one row per lap × zone, raw units
    sanity.txt              physical checks (T1 peak in g, worked example, slip R²)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/workspace/src")

from f1_style_clustering.features.metrics import (  # noqa: E402
    along_track_delta,
    get_kinematic_apex_distance,
    is_brake_on,
)
from f1_style_clustering.features.zoi import get_corner_fragments  # noqa: E402

DATA_DIR = Path("/workspace/cache/derived/2025_italian_grand_prix_r")
OUT_DIR = Path(__file__).resolve().parent

G = 9.80665
MIN_GAP_S = 0.40
DT_MIN = 0.12
DT_MAX = 0.50
PEAK_CAP = 8.0 * G  # steeper than 8 g is treated as a 4 Hz glitch
MIN_DROP_MS = 8.0 / 3.6
LOOKBACK_LIFT_M = 100.0
SLIP_LOOKBACK_M = 150.0
SLIP_SCALE_M = 40.0
TRAFFIC_M = 50.0

SHORT = {
    "T1_Variante_del_Rettifilo": "T1",
    "T3_Curva_Grande": "T3",
    "T4_Variante_della_Roggia": "T4",
    "T6_Curva_di_Lesmo": "T6",
    "T7_Seconda_di_Lesmo": "T7",
    "T8_Variante_Ascari": "T8",
    "T11_Curva_Parabolica_Alboreto": "T11",
}

# Raw zone metrics written to the long table and aggregated.
BASE_METRICS = [
    "peak_decel",
    "peak_decel_med3",
    "mean_decel",
    "brake_effort",
    "brake_duration_s",
    "brake_duration_m",
    "brake_on_time_s",
    "entry_speed",
    "speed_drop_ratio",
    "brake_attack_s",
    "attack_frac",
    "decel_first_0_5",
    "frontload_ratio",
    "frontload_speed_frac",
    "release_to_apex_m",
    "release_to_apex_s",
    "release_speed",
    "lift_coast_s",
    "lift_coast_m",
    "brake_stabs",
]

# Heterogeneous across corners: center each zone before the typology median.
CENTER_METRICS = [
    "peak_decel",
    "peak_decel_med3",
    "mean_decel",
    "brake_effort",
    "brake_duration_s",
    "brake_duration_m",
    "brake_on_time_s",
    "entry_speed",
    "speed_drop_ratio",
    "brake_attack_s",
    "attack_frac",
    "decel_first_0_5",
    "frontload_ratio",
    "frontload_speed_frac",
    "release_to_apex_m",
    "release_to_apex_s",
    "release_speed",
    "lift_coast_s",
    "lift_coast_m",
    "brake_stabs",
]

# Same aggregation on the raw scale (pipeline-like; a later typology-wide
# constant would not change ranks). Kept for the metrics most likely to differ
# from the zone-centered median.
RAW_AGG_METRICS = [
    "peak_decel",
    "mean_decel",
    "brake_effort",
    "brake_duration_s",
    "entry_speed",
    "speed_drop_ratio",
    "release_to_apex_m",
    "lift_coast_s",
    "frontload_ratio",
    "brake_stabs",
    "decel_first_0_5",
    "brake_attack_s",
]

LAPSYNC_METRICS = [
    "peak_decel",
    "peak_decel_med3",
    "mean_decel",
    "brake_effort",
    "brake_duration_s",
    "brake_duration_m",
    "entry_speed",
    "speed_drop_ratio",
    "release_to_apex_m",
    "release_to_apex_s",
    "lift_coast_s",
    "lift_coast_m",
    "frontload_ratio",
    "decel_first_0_5",
    "brake_attack_s",
    "attack_frac",
    "release_speed",
    "frontload_speed_frac",
    "brake_stabs",
    "brake_on_time_s",
]

PER_ZONE = ["T1", "T4", "T8", "T11"]
PER_ZONE_METRICS = [
    "peak_decel",
    "peak_decel_med3",
    "mean_decel",
    "brake_effort",
    "brake_duration_s",
    "brake_duration_m",
    "entry_speed",
    "speed_drop_ratio",
    "release_to_apex_m",
    "lift_coast_s",
    "lift_coast_m",
    "frontload_ratio",
    "decel_first_0_5",
    "brake_attack_s",
    "brake_stabs",
    "release_speed",
    "frontload_speed_frac",
    "brake_on_time_s",
]

CLEAR_METRICS = [
    "peak_decel",
    "mean_decel",
    "brake_effort",
    "brake_duration_s",
    "entry_speed",
    "speed_drop_ratio",
    "release_to_apex_m",
    "lift_coast_s",
    "frontload_ratio",
]

SLIP_METRICS = ["entry_speed", "peak_decel", "brake_effort", "brake_duration_s", "release_to_apex_m"]


def _ols_slope(t: np.ndarray, v: np.ndarray) -> float:
    """Slope of the least-squares line v ≈ a + b t. NaN if the times do not span."""
    if t.size < 2:
        return np.nan
    tc = t - t.mean()
    den = float(np.dot(tc, tc))
    if den <= 1e-8:
        return np.nan
    return float(np.dot(tc, v - v.mean()) / den)


def _pair_acc(t: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Sample-to-sample acceleration (m/s²). Invalid Δt → NaN. No 8 g cap here."""
    dt = np.diff(t)
    acc = np.full(dt.shape, np.nan)
    ok = (dt >= DT_MIN) & (dt <= DT_MAX)
    acc[ok] = np.diff(v)[ok] / dt[ok]
    return acc


def _robust_peak(acc: np.ndarray) -> float:
    """Steepest deceleration (positive m/s²), ignoring steps steeper than 8 g."""
    finite = acc[np.isfinite(acc)]
    if finite.size == 0:
        return np.nan
    usable = finite[finite >= -PEAK_CAP]
    if usable.size == 0:
        return np.nan
    return float(-np.min(usable))


def _median3(v: np.ndarray) -> np.ndarray:
    if v.size < 3:
        return v.copy()
    out = v.copy()
    out[1:-1] = np.median(np.vstack([v[:-2], v[1:-1], v[2:]]), axis=0)
    return out


def _runs(brake: np.ndarray, t: np.ndarray) -> list[tuple[int, int]]:
    """Inclusive index runs of Brake==True, merging off-gaps shorter than MIN_GAP_S."""
    idx = np.flatnonzero(brake)
    if idx.size == 0:
        return []
    splits = np.where(np.diff(idx) > 1)[0]
    raw: list[tuple[int, int]] = []
    start = 0
    for s in splits:
        raw.append((int(idx[start]), int(idx[s])))
        start = s + 1
    raw.append((int(idx[start]), int(idx[-1])))
    merged: list[tuple[int, int]] = [raw[0]]
    for a, b in raw[1:]:
        pa, pb = merged[-1]
        if t[a] - t[pb] < MIN_GAP_S:
            merged[-1] = (pa, b)
        else:
            merged.append((a, b))
    return merged


def _select_primary(runs: list[tuple[int, int]], v: np.ndarray) -> tuple[int, int] | None:
    cands = [(a, b) for a, b in runs if b - a >= 1]
    if not cands:
        return None
    for a, b in cands:
        if v[a] - v[b] >= MIN_DROP_MS:
            return a, b
    return max(cands, key=lambda ab: v[ab[0]] - v[ab[1]])


def _lift_before_brake(
    lap: pd.DataFrame,
    zone: dict,
    onset_t: float,
    onset_d: float,
) -> tuple[float, float]:
    """Time (s) and distance (m) from throttle release to brake onset.

    Release = first sample with Throttle ≤ 5 after the last sample with
    Throttle ≥ 95, searching backward from onset and stopping at a previous
    brake application or at 100 m before the braking window. 0 if the driver
    brakes without a ≤5 % coast sample. NaN if full throttle is never seen
    in that lookback (the lift started outside the window and is censored).
    """
    track_length = zone.get("track_length")
    b0 = float(zone["braking"][0])
    look = b0 - LOOKBACK_LIFT_M
    dist = lap["Distance"].to_numpy(dtype=float)
    if track_length and look < 0:
        mask = (dist >= look + track_length) | (dist <= onset_d)
    else:
        mask = (dist >= look) & (dist <= onset_d + 1.0)
    pre = lap.loc[mask]
    if pre.empty or not np.isfinite(onset_t):
        return np.nan, np.nan
    pre = pre.sort_values("t_s")
    pre = pre.loc[pre["t_s"] <= onset_t + 1e-9]
    if pre.empty:
        return np.nan, np.nan
    t = pre["t_s"].to_numpy(dtype=float)
    d = pre["Distance"].to_numpy(dtype=float)
    th = pre["Throttle"].to_numpy(dtype=float)
    br = is_brake_on(pre["Brake"]).to_numpy()
    # Drop the onset sample itself from the lookback when it is in the slice.
    if t.size and abs(t[-1] - onset_t) < 1e-6:
        t, d, th, br = t[:-1], d[:-1], th[:-1], br[:-1]
    if t.size == 0:
        return np.nan, np.nan
    # Stop the search at the previous brake application.
    prev = np.flatnonzero(br)
    lo = int(prev[-1] + 1) if prev.size else 0
    t, d, th = t[lo:], d[lo:], th[lo:]
    if t.size == 0:
        return np.nan, np.nan
    full = np.flatnonzero(th >= 95.0)
    if full.size == 0:
        return np.nan, np.nan
    last_full = int(full[-1])
    after_th = th[last_full + 1 :]
    coast = np.flatnonzero(after_th <= 5.0)
    if coast.size == 0:
        return 0.0, 0.0
    i = last_full + 1 + int(coast[0])
    return float(onset_t - t[i]), float(along_track_delta(onset_d, d[i], track_length))


def _min_dtd(tel_lap: pd.DataFrame | None, onset_d: float, track_length: float | None) -> float:
    """Minimum DistanceToDriverAhead in the 150 m before brake onset.

    +inf when a car is never named ahead in that window (clean air).
    NaN when onset is unknown.
    """
    if tel_lap is None or not np.isfinite(onset_d):
        return np.nan
    dist = tel_lap["Distance"].to_numpy(dtype=float)
    start = onset_d - SLIP_LOOKBACK_M
    if track_length and start < 0:
        mask = (dist >= start + track_length) | (dist <= onset_d)
    else:
        mask = (dist >= start) & (dist <= onset_d)
    if not mask.any():
        return np.inf
    ahead = tel_lap["DriverAhead"].to_numpy()
    dtd = tel_lap["DistanceToDriverAhead"].to_numpy(dtype=float)
    names = pd.Series(ahead).astype(str).str.strip()
    valid = mask & ~names.isin(["", "nan", "None", "<NA>", "NaN"]).to_numpy() & np.isfinite(dtd)
    if not valid.any():
        return np.inf
    return float(np.min(dtd[valid]))


def zone_metrics(lap: pd.DataFrame, zone: dict, tel_lap: pd.DataFrame | None) -> dict:
    """All raw braking metrics for one lap and one zone. NaN if the car does not brake."""
    out = {m: np.nan for m in BASE_METRICS}
    out["min_dtd"] = np.nan
    out["traffic_50"] = False
    fr = get_corner_fragments(lap, zone)
    parts = []
    for phase in ("braking", "apex"):
        frag = fr[phase]
        if frag is not None and not frag.empty:
            parts.append(frag)
    if not parts:
        return out
    w = pd.concat(parts, ignore_index=True).sort_values("t_s")
    brake = is_brake_on(w["Brake"]).to_numpy()
    t = w["t_s"].to_numpy(dtype=float)
    v = w["Speed"].to_numpy(dtype=float) / 3.6
    dist = w["Distance"].to_numpy(dtype=float)
    track_length = fr.get("track_length") or zone.get("track_length")
    runs = _runs(brake, t)
    out["brake_stabs"] = float(len(runs)) if runs else np.nan
    if runs:
        on_time = 0.0
        for a, b in runs:
            on_time += float(t[b] - t[a])
        out["brake_on_time_s"] = on_time

    primary = _select_primary(runs, v)
    apex = fr["apex"]
    kin_d = get_kinematic_apex_distance(apex) if apex is not None else np.nan
    kin_t = np.nan
    if apex is not None and not apex.empty and np.isfinite(kin_d):
        speeds = apex["Speed"].replace([np.inf, -np.inf], np.nan)
        if speeds.notna().any():
            kin_t = float(apex.loc[speeds.idxmin(), "t_s"])

    if primary is not None:
        a, b = primary
        tt = t[a : b + 1]
        vv = v[a : b + 1]
        dd = dist[a : b + 1]
        acc = _pair_acc(tt, vv)
        out["peak_decel"] = _robust_peak(acc)
        out["peak_decel_med3"] = _robust_peak(_pair_acc(tt, _median3(vv)))
        slope = _ols_slope(tt, vv)
        out["mean_decel"] = float(-slope) if np.isfinite(slope) else np.nan
        out["brake_duration_s"] = float(tt[-1] - tt[0])
        out["brake_duration_m"] = float(along_track_delta(dd[-1], dd[0], track_length))
        out["entry_speed"] = float(vv[0] * 3.6)

        finite_acc = np.isfinite(acc)
        if finite_acc.any():
            usable = finite_acc & (acc >= -PEAK_CAP)
            if usable.any():
                k = int(np.argmin(np.where(usable, acc, np.inf)))
                t_peak = 0.5 * (tt[k] + tt[k + 1])
                out["brake_attack_s"] = float(t_peak - tt[0])
                dur = out["brake_duration_s"]
                if np.isfinite(dur) and dur > 0.05:
                    out["attack_frac"] = float(out["brake_attack_s"] / dur)
            first = finite_acc & ((tt[:-1] - tt[0]) <= 0.50)
            rest = finite_acc & ((tt[:-1] - tt[0]) > 0.50)
            if first.any():
                out["decel_first_0_5"] = float(-np.mean(acc[first]))
            if first.any() and rest.any():
                m_first = float(-np.mean(acc[first]))
                m_rest = float(-np.mean(acc[rest]))
                if m_rest >= 2.0 and np.isfinite(m_first):
                    ratio = m_first / m_rest
                    out["frontload_ratio"] = float(np.clip(ratio, 0.0, 8.0))

        # Minimum speed from onset through the end of the apex window.
        tail_v = v[a:]
        tail_d = dist[a:]
        j = int(np.argmin(tail_v))
        v_min = float(tail_v[j])
        d_min = float(tail_d[j])
        if vv[0] > 1.0:
            out["speed_drop_ratio"] = float(v_min / vv[0])
        d_eff = float(along_track_delta(d_min, dd[0], track_length))
        if d_eff > 5.0 and vv[0] > v_min:
            out["brake_effort"] = float((vv[0] ** 2 - v_min ** 2) / (2.0 * d_eff))
        if np.isfinite(v_min) and tt.size >= 2:
            # Speed lost in the first 0.5 s over speed lost by the end of the primary run.
            v_end = float(vv[-1])
            lost = vv[0] - min(v_end, v_min)
            if lost > 1.0:
                k05 = int(np.argmax(tt >= tt[0] + 0.50))
                # argmax returns 0 if no sample reaches +0.5 s; require a real hit.
                if tt[k05] >= tt[0] + 0.45:
                    out["frontload_speed_frac"] = float(np.clip((vv[0] - vv[k05]) / lost, -0.5, 1.5))

        out["min_dtd"] = _min_dtd(tel_lap, float(dd[0]), track_length)
        lift_s, lift_m = _lift_before_brake(lap, zone, float(tt[0]), float(dd[0]))
        out["lift_coast_s"] = lift_s
        out["lift_coast_m"] = lift_m

    # Release = last on-brake sample in the window (trail), relative to kinematic apex.
    if brake.any() and np.isfinite(kin_d):
        last = int(np.flatnonzero(brake)[-1])
        out["release_to_apex_m"] = float(along_track_delta(kin_d, dist[last], track_length))
        # Speed at the same sample used for the release point (last Brake==True).
        out["release_speed"] = float(v[last] * 3.6)
        if np.isfinite(kin_t):
            out["release_to_apex_s"] = float(kin_t - t[last])

    dtd = out["min_dtd"]
    out["traffic_50"] = bool(np.isfinite(dtd) and dtd < TRAFFIC_M)
    return out


def _subtract_group_median(
    df: pd.DataFrame,
    cols: list[str],
    keys: list[str],
    min_n: int,
) -> pd.DataFrame:
    """Return cols minus the group median. Groups with fewer than min_n finite values stay NaN."""
    grouped = df.groupby(keys, sort=False)
    med = grouped[cols].transform("median")
    cnt = grouped[cols].transform("count")
    out = df[cols] - med
    return out.where(cnt >= min_n)


def _wide_from_long(long_df: pd.DataFrame, metrics: list[str], suffix: str) -> pd.DataFrame:
    """Median across zones of one typology → columns ``{typology}__{metric}{suffix}``."""
    present = [m for m in metrics if m in long_df.columns]
    g = (
        long_df.groupby(["Driver", "LapNumber", "typology"], dropna=False)[present]
        .median()
        .reset_index()
    )
    wide = g.pivot(index=["Driver", "LapNumber"], columns="typology", values=present)
    wide.columns = [f"{typ}__{metric}{suffix}" for metric, typ in wide.columns.to_list()]
    return wide


def _per_zone_wide(long_df: pd.DataFrame, metrics: list[str], suffix: str) -> pd.DataFrame:
    sub = long_df.loc[long_df["zone_short"].isin(PER_ZONE)].copy()
    present = [m for m in metrics if m in sub.columns]
    wide = sub.pivot(index=["Driver", "LapNumber"], columns="zone_short", values=present)
    wide.columns = [f"{zone}__{metric}{suffix}" for metric, zone in wide.columns.to_list()]
    return wide


def _slip_residual(y: np.ndarray, dtd: np.ndarray) -> tuple[np.ndarray, float]:
    """Residual of y after a linear term in exp(-min_dtd / 40 m). NaN y stays NaN."""
    slip = np.exp(-np.clip(dtd, 0.0, 500.0) / SLIP_SCALE_M)
    slip[~np.isfinite(dtd)] = np.nan
    # Clean air (dtd = +inf) → slip 0. clip maps inf to 500, exp(-12.5) ≈ 0.
    resid = np.full(y.shape, np.nan)
    ok = np.isfinite(y) & np.isfinite(slip)
    r2 = np.nan
    if int(ok.sum()) < 40 or np.nanstd(y[ok]) < 1e-8:
        return resid, r2
    X = np.column_stack([np.ones(int(ok.sum())), slip[ok]])
    coef, _, _, _ = np.linalg.lstsq(X, y[ok], rcond=None)
    pred = coef[0] + coef[1] * slip
    resid[ok] = y[ok] - pred[ok]
    ss_tot = float(np.var(y[ok]))
    r2 = float(1.0 - np.var(resid[ok]) / ss_tot) if ss_tot > 0 else np.nan
    return resid, r2


def _fmt(v: float, digits: int = 2) -> str:
    if v is None or not np.isfinite(v):
        return "nan"
    return f"{v:.{digits}f}"


def build() -> pd.DataFrame:
    zones = json.loads((DATA_DIR / "zones.json").read_text())
    car = pd.read_pickle(DATA_DIR / "car.pkl")
    tel = pd.read_pickle(DATA_DIR / "tel.pkl")
    car = car.copy()
    car["t_s"] = car["Time"].dt.total_seconds()
    tel = tel.copy()
    keep_tel = ["Driver", "LapNumber", "Distance", "DistanceToDriverAhead", "DriverAhead"]
    tel = tel[keep_tel]

    car_laps = {
        key: g.reset_index(drop=True)
        for key, g in car.groupby(["Driver", "LapNumber"], sort=False)
    }
    tel_laps = {
        key: g.reset_index(drop=True)
        for key, g in tel.groupby(["Driver", "LapNumber"], sort=False)
    }

    rows = []
    for (driver, lap_number), lap in car_laps.items():
        tel_lap = tel_laps.get((driver, lap_number))
        for name, zone in zones.items():
            metrics = zone_metrics(lap, zone, tel_lap)
            metrics["Driver"] = driver
            metrics["LapNumber"] = int(lap_number)
            metrics["zone"] = name
            metrics["zone_short"] = SHORT[name]
            metrics["typology"] = zone.get("typology")
            rows.append(metrics)
    long_df = pd.DataFrame(rows)

    r2_lines = []
    for zone_short, idx in long_df.groupby("zone_short").groups.items():
        dtd = long_df.loc[idx, "min_dtd"].to_numpy(dtype=float)
        for metric in SLIP_METRICS:
            resid, r2 = _slip_residual(long_df.loc[idx, metric].to_numpy(dtype=float), dtd)
            col = f"{metric}_slipresid"
            if col not in long_df.columns:
                long_df[col] = np.nan
            long_df.loc[idx, col] = resid
            r2_lines.append(f"slip_r2 {zone_short} {metric} {_fmt(r2, 3)}")

    # Clear-air copies: NaN when a car is within 50 m in the 150 m before onset.
    for metric in CLEAR_METRICS:
        cleared = long_df[metric].to_numpy(dtype=float).copy()
        cleared[long_df["traffic_50"].to_numpy(dtype=bool)] = np.nan
        long_df[f"{metric}_clear"] = cleared

    # Zone-centered (session median of that zone removed) before typology median.
    centered = long_df.copy()
    centered[CENTER_METRICS] = _subtract_group_median(long_df, CENTER_METRICS, ["zone_short"], min_n=20)

    lapsync = long_df.copy()
    # A lap-number median needs a field, not one or two cars (that would zero the row).
    lapsync[LAPSYNC_METRICS] = _subtract_group_median(
        long_df, LAPSYNC_METRICS, ["zone_short", "LapNumber"], min_n=8
    )

    clear_cols = [f"{m}_clear" for m in CLEAR_METRICS]
    clear_centered = long_df.copy()
    clear_centered[clear_cols] = _subtract_group_median(long_df, clear_cols, ["zone_short"], min_n=20)

    parts = [
        _wide_from_long(centered, CENTER_METRICS, ""),
        _wide_from_long(long_df, RAW_AGG_METRICS, "_rawmed"),
        _wide_from_long(lapsync, LAPSYNC_METRICS, "_lapsync"),
        _wide_from_long(long_df, [f"{m}_slipresid" for m in SLIP_METRICS], ""),
        _wide_from_long(clear_centered, [f"{m}_clear" for m in CLEAR_METRICS], ""),
        _per_zone_wide(long_df, PER_ZONE_METRICS, ""),
        _per_zone_wide(long_df, [f"{m}_clear" for m in CLEAR_METRICS], ""),
        _per_zone_wide(long_df, [f"{m}_slipresid" for m in SLIP_METRICS], ""),
    ]
    # Per-zone lap-synchronous for the heavy-braking corners (physical deltas).
    per_sync_metrics = [
        "peak_decel",
        "mean_decel",
        "brake_effort",
        "entry_speed",
        "brake_duration_s",
        "release_to_apex_m",
        "lift_coast_s",
        "speed_drop_ratio",
        "frontload_ratio",
    ]
    parts.append(_per_zone_wide(lapsync, per_sync_metrics, "_lapsync"))

    wide = parts[0]
    for extra in parts[1:]:
        wide = wide.join(extra, how="outer")
    wide = wide.reset_index()
    # Stable column order: keys, then features.
    feature_cols = [c for c in wide.columns if c not in ("Driver", "LapNumber")]
    wide = wide[["Driver", "LapNumber"] + feature_cols]

    long_path = OUT_DIR / "long_zone_metrics.csv"
    cand_path = OUT_DIR / "candidates.csv"
    long_df.to_csv(long_path, index=False)
    wide.to_csv(cand_path, index=False)

    sanity = _sanity(long_df, r2_lines, car_laps, zones)
    (OUT_DIR / "sanity.txt").write_text(sanity)
    print(sanity)
    print(f"wrote {cand_path} shape={wide.shape}")
    print(f"wrote {long_path} shape={long_df.shape}")
    return wide


def _sanity(long_df: pd.DataFrame, r2_lines: list[str], car_laps: dict, zones: dict) -> str:
    lines = ["# Braking-dynamics sanity", ""]
    lines.append("T1 peak deceleration (positive m/s² and g), all laps with a primary event:")
    t1 = long_df.loc[long_df["zone_short"] == "T1", "peak_decel"]
    lines.append(
        f"  n={int(t1.notna().sum())} median={_fmt(t1.median())} m/s² "
        f"({_fmt(t1.median() / G)} g)  p10={_fmt(t1.quantile(0.1) / G)} g  "
        f"p90={_fmt(t1.quantile(0.9) / G)} g"
    )
    lines.append("Median peak_decel (g) and brake_effort (g) by zone:")
    for short, g in long_df.groupby("zone_short"):
        pk = g["peak_decel"]
        ef = g["brake_effort"]
        lines.append(
            f"  {short}: peak {_fmt(pk.median() / G)} g (n={int(pk.notna().sum())})  "
            f"effort {_fmt(ef.median() / G)} g  "
            f"duration {_fmt(g['brake_duration_s'].median())} s  "
            f"stabs median {_fmt(g['brake_stabs'].median(), 1)}  "
            f"traffic_50 {g['traffic_50'].mean():.2f}  "
            f"lift_s {_fmt(g['lift_coast_s'].median())}"
        )
    # Worked example: VER lap 10, T1, if present.
    key = ("VER", 10)
    if key in car_laps:
        ex = zone_metrics(car_laps[key], zones["T1_Variante_del_Rettifilo"], None)
        lines.append("")
        lines.append("Worked example VER lap 10, T1 (no traffic lookup):")
        for k in (
            "peak_decel",
            "peak_decel_med3",
            "mean_decel",
            "brake_effort",
            "brake_duration_s",
            "brake_duration_m",
            "entry_speed",
            "speed_drop_ratio",
            "brake_attack_s",
            "decel_first_0_5",
            "frontload_ratio",
            "release_to_apex_m",
            "release_to_apex_s",
            "lift_coast_s",
            "lift_coast_m",
            "brake_stabs",
        ):
            val = ex[k]
            extra = f"  ({_fmt(val / G)} g)" if k in ("peak_decel", "peak_decel_med3", "mean_decel", "brake_effort", "decel_first_0_5") else ""
            lines.append(f"  {k} = {_fmt(val, 3)}{extra}")
    lines.append("")
    lines.append("Fraction of zone-rows with a finite value:")
    for m in BASE_METRICS:
        lines.append(f"  {m}: {long_df[m].notna().mean():.3f}")
    lines.append("")
    lines.extend(r2_lines)
    lines.append("")
    lines.append(
        "Sampling: peak_decel is the steepest car-sample Δv/Δt on the primary "
        "brake run (Δt in [0.12, 0.50] s), with steps steeper than 8 g dropped. "
        "A Savitzky–Golay derivative on tel.pkl cannot exceed this: get_telemetry "
        "linearly interpolates the same ~4 Hz speed channel, so the interpolated "
        "slope between car samples equals the car finite difference."
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    build()
