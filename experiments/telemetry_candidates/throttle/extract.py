"""Candidate telemetry metrics: throttle application, gear/RPM, corner speed shape.

Source is the exported car-data pickle (≈4 Hz), sliced with the pipeline ZOIs.
Does not reload FastF1 and does not modify the package.

Run:
    /tmp/venv/bin/python /workspace/experiments/telemetry_candidates/throttle/extract.py

Writes, next to this file:
    zone_metrics.csv   one row per driver × lap × zone (raw, before masking)
    candidates.csv     one row per driver × lap, typology aggregates and per-zone columns
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/workspace/src")

from f1_style_clustering.features.metrics import spatial_fraction  # noqa: E402
from f1_style_clustering.features.zoi import get_corner_fragments  # noqa: E402

DATA = Path("/workspace/cache/derived/2025_italian_grand_prix_r")
OUT = Path("/workspace/experiments/telemetry_candidates/throttle")

THROTTLE_FULL = 95.0
THROTTLE_PICKUP = 10.0
THROTTLE_PARTIAL_LO = 10.0
THROTTLE_PARTIAL_HI = 90.0
OVERLAP_SOFT = 2.0
LIFT_DROP = 10.0
DWELL_BAND_KMH = 5.0
DWELL_BAND_FRAC = 0.03
MIN_SPEED_DROP_KMH = 15.0
MIN_SHAPE_DIST_M = 2.0

# Application / shape metrics are undefined when the corner is taken flat
# (no brake and throttle never closes). Gear and exit-gain stay numeric.
MASK_IF_INACTIVE = [
    "t_full_s",
    "ramp_s",
    "t_pickup_to_apex_s",
    "d_full_m",
    "t_brake_to_full_s",
    "partial_thr_frac",
    "partial_thr_apex",
    "thr_lifts",
    "thr_mod_per_m",
    "overlap_frac",
    "overlap_soft_frac",
    "pickup_rate",
    "n_downshifts",
    "upshift_rpm",
    "dwell_m",
    "dwell_m_3pct",
    "decel_accel_ratio",
    "min_gear",
    "gear_at_apex",
    "rpm_at_apex",
]

METRICS = [
    "t_full_s",
    "ramp_s",
    "t_pickup_to_apex_s",
    "d_full_m",
    "t_brake_to_full_s",
    "thr_at_apex",
    "partial_thr_frac",
    "partial_thr_apex",
    "thr_exit_mean",
    "thr_apex_mean",
    "thr_lifts",
    "thr_mod_per_m",
    "overlap_frac",
    "overlap_soft_frac",
    "pickup_rate",
    "min_gear",
    "gear_at_apex",
    "rpm_at_apex",
    "upshift_rpm",
    "n_downshifts",
    "exit_gain_100",
    "exit_gain_200",
    "dwell_m",
    "dwell_m_3pct",
    "decel_accel_ratio",
]

# Per-zone columns. Slow has a single zone, so T1 would duplicate slow__.
PER_ZONE = ["T3", "T4", "T6", "T7", "T8", "T11"]
PER_ZONE_METRICS = [
    "t_full_s",
    "ramp_s",
    "t_pickup_to_apex_s",
    "d_full_m",
    "t_brake_to_full_s",
    "thr_at_apex",
    "partial_thr_frac",
    "partial_thr_apex",
    "thr_apex_mean",
    "thr_exit_mean",
    "thr_lifts",
    "thr_mod_per_m",
    "overlap_frac",
    "overlap_soft_frac",
    "pickup_rate",
    "min_gear",
    "gear_at_apex",
    "rpm_at_apex",
    "upshift_rpm",
    "n_downshifts",
    "exit_gain_100",
    "exit_gain_200",
    "dwell_m",
    "dwell_m_3pct",
    "decel_accel_ratio",
]

ZONE_SHORT = {
    "T1_Variante_del_Rettifilo": "T1",
    "T3_Curva_Grande": "T3",
    "T4_Variante_della_Roggia": "T4",
    "T6_Curva_di_Lesmo": "T6",
    "T7_Seconda_di_Lesmo": "T7",
    "T8_Variante_Ascari": "T8",
    "T11_Curva_Parabolica_Alboreto": "T11",
}


def _dist_deltas(dist: np.ndarray, track_length: float | None) -> np.ndarray:
    dd = np.diff(dist.astype(float))
    if track_length is not None and track_length > 0:
        dd = np.where(dd < 0, dd + track_length, dd)
    return np.abs(dd)


def dist_wmean(dist: np.ndarray, val: np.ndarray, track_length: float | None) -> float:
    """Trapezoidal distance-weighted mean. Integral of the channel over the window, per metre."""
    if len(val) == 0:
        return np.nan
    if len(val) == 1:
        return float(val[0])
    dd = _dist_deltas(dist, track_length)
    total = float(dd.sum())
    if total <= 0:
        return np.nan
    trap = 0.5 * (val[:-1].astype(float) + val[1:].astype(float))
    return float(np.sum(trap * dd) / total)


def excess_tv_per_m(dist: np.ndarray, thr: np.ndarray, track_length: float | None) -> float:
    """Throttle variation beyond a monotone path, per metre (%/m).

    sum(|Δthrottle|) − |throttle_end − throttle_start|, divided by window length.
    Zero when the pedal only moves one way.
    """
    if len(thr) < 2:
        return np.nan
    dd = _dist_deltas(dist, track_length)
    total = float(dd.sum())
    if total <= 1.0:
        return np.nan
    dthr = np.diff(thr.astype(float))
    excess = float(np.abs(dthr).sum() - abs(float(thr[-1]) - float(thr[0])))
    if excess < 0 and excess > -1e-6:
        excess = 0.0
    return max(excess, 0.0) / total


def count_lifts(thr: np.ndarray, start: int, drop: float = LIFT_DROP) -> float:
    """How many times the pedal falls by ≥ `drop` points after `start`, then recovers.

    A new lift is armed only after the trace climbs by `drop` points off the trough
    (or makes a new high). Single-sample noise below `drop` is ignored. No smoothing:
    at 4 Hz a 3-sample median would erase a real one-sample lift.
    """
    if start is None or start < 0 or start >= len(thr):
        return np.nan
    seg = np.asarray(thr[start:], dtype=float)
    if len(seg) < 2 or not np.isfinite(seg).all():
        seg = seg[np.isfinite(seg)]
        if len(seg) < 2:
            return 0.0
    peak = float(seg[0])
    lifts = 0
    dropped = False
    trough = peak
    for v in seg[1:]:
        v = float(v)
        if not dropped:
            if v > peak:
                peak = v
            elif peak - v >= drop:
                dropped = True
                trough = v
                lifts += 1
        else:
            if v < trough:
                trough = v
            if v > peak:
                dropped = False
                peak = v
            elif v >= trough + drop:
                dropped = False
                peak = v
    return float(lifts)


def _upward_cross(t: np.ndarray, d: np.ndarray, y: np.ndarray, i_from: int, level: float):
    """Linear interpolation of the first upward crossing of `level` at or after index i_from.

    If y[i_from] is already at or above `level`, the crossing is that sample.
    Returns (time_s, distance_m, right_index) or (nan, nan, -1).
    """
    n = len(y)
    if i_from < 0 or i_from >= n:
        return np.nan, np.nan, -1
    if y[i_from] >= level:
        return float(t[i_from]), float(d[i_from]), int(i_from)
    for i in range(i_from, n - 1):
        y0 = float(y[i])
        y1 = float(y[i + 1])
        if y0 < level <= y1:
            denom = y1 - y0
            frac = 0.0 if denom == 0 else (level - y0) / denom
            frac = float(np.clip(frac, 0.0, 1.0))
            tc = float(t[i] + frac * (t[i + 1] - t[i]))
            dc = float(d[i] + frac * (d[i + 1] - d[i]))
            return tc, dc, int(i + 1)
    return np.nan, np.nan, -1


def _interp_at(dist: np.ndarray, values: np.ndarray, target: float) -> float:
    if len(dist) < 2 or not np.isfinite(target):
        return np.nan
    if target < dist[0] or target > dist[-1]:
        return np.nan
    j = int(np.searchsorted(dist, target, side="left"))
    if j <= 0:
        return float(values[0])
    if j >= len(dist):
        return float(values[-1])
    d0, d1 = float(dist[j - 1]), float(dist[j])
    if d1 == d0:
        return float(values[j])
    w = (target - d0) / (d1 - d0)
    return float(values[j - 1] * (1.0 - w) + values[j] * w)


def _plateau_center(speed: np.ndarray) -> int:
    """Middle sample of the minimum-speed plateau (speed is integer km/h)."""
    vmin = np.nanmin(speed)
    idx = np.flatnonzero(speed == vmin)
    if len(idx) == 0:
        return int(np.nanargmin(speed))
    return int(idx[len(idx) // 2])


def _band_edges(t, d, spd, apex_i, level: float):
    """Entry and exit of the contiguous Speed <= level region that contains the apex.

    Returns (t_entry, d_entry, t_exit, d_exit) or Nones if the trace never
    leaves the band on that side (censored by the window — not a real edge).
    """
    n = len(spd)
    # Backward: last sample strictly above the band.
    prev = None
    for j in range(apex_i - 1, -1, -1):
        if spd[j] > level:
            prev = j
            break
    nxt = None
    for j in range(apex_i + 1, n):
        if spd[j] > level:
            nxt = j
            break
    if prev is None or nxt is None:
        return None

    def _cross(i_out: int, i_in: int):
        s_out = float(spd[i_out])
        s_in = float(spd[i_in])
        denom = s_out - s_in
        frac = 0.0 if denom == 0 else (s_out - level) / denom
        frac = float(np.clip(frac, 0.0, 1.0))
        tc = float(t[i_out] + frac * (t[i_in] - t[i_out]))
        dc = float(d[i_out] + frac * (d[i_in] - d[i_out]))
        return tc, dc

    t_entry, d_entry = _cross(prev, prev + 1)
    t_exit, d_exit = _cross(nxt, nxt - 1)
    return t_entry, d_entry, t_exit, d_exit


def _as_arrays(frag: pd.DataFrame):
    if frag is None or frag.empty:
        return None
    return {
        "t": frag["t_s"].to_numpy(dtype=float),
        "d": frag["Distance"].to_numpy(dtype=float),
        "thr": frag["Throttle"].to_numpy(dtype=float),
        "spd": frag["Speed"].to_numpy(dtype=float),
        "gear": frag["nGear"].to_numpy(dtype=float),
        "rpm": frag["RPM"].to_numpy(dtype=float),
        "brk": frag["Brake"].to_numpy(dtype=bool),
        "rate": frag["ThrottleRate"].to_numpy(dtype=float),
    }


def _cat(parts: list[dict | None], key: str) -> np.ndarray:
    chunks = [p[key] for p in parts if p is not None and len(p[key])]
    if not chunks:
        return np.array([], dtype=float)
    return np.concatenate(chunks)


def _nan_metrics() -> dict:
    return {m: np.nan for m in METRICS}


def compute_zone_metrics(
    braking: pd.DataFrame,
    apex: pd.DataFrame,
    exit_z: pd.DataFrame,
    lap_dist: np.ndarray,
    lap_speed: np.ndarray,
    track_length: float | None,
) -> dict:
    """Metrics for one driver-lap-zone. See REPORT.md for definitions."""
    out = _nan_metrics()
    b = _as_arrays(braking)
    a = _as_arrays(apex)
    e = _as_arrays(exit_z)
    if a is None:
        out["active"] = False
        return out

    n_b = 0 if b is None else len(b["t"])
    corner_parts = [p for p in (b, a, e) if p is not None]
    ba_parts = [p for p in (b, a) if p is not None]
    ae_parts = [p for p in (a, e) if p is not None]

    t = _cat(corner_parts, "t")
    d = _cat(corner_parts, "d")
    thr = _cat(corner_parts, "thr")
    spd = _cat(corner_parts, "spd")
    gear = _cat(corner_parts, "gear")
    rpm = _cat(corner_parts, "rpm")
    brk = np.concatenate([p["brk"] for p in corner_parts])
    rate = _cat(corner_parts, "rate")

    t_ba = _cat(ba_parts, "t")
    d_ba = _cat(ba_parts, "d")
    thr_ba = _cat(ba_parts, "thr")
    gear_ba = _cat(ba_parts, "gear")
    brk_ba = np.concatenate([p["brk"] for p in ba_parts]) if ba_parts else np.array([], dtype=bool)

    d_ae = _cat(ae_parts, "d")
    thr_ae = _cat(ae_parts, "thr")

    apex_local = _plateau_center(a["spd"])
    apex_i = n_b + apex_local
    if apex_i >= len(spd):
        out["active"] = False
        return out

    active = bool((np.nanmin(thr) <= THROTTLE_PICKUP) or brk.any())
    out["active"] = active

    # --- levels that stay defined on a flat corner ---
    out["thr_at_apex"] = float(thr[apex_i])
    out["thr_apex_mean"] = dist_wmean(a["d"], a["thr"], track_length)
    if e is not None:
        out["thr_exit_mean"] = dist_wmean(e["d"], e["thr"], track_length)
    out["min_gear"] = float(np.nanmin(a["gear"]))
    out["gear_at_apex"] = float(gear[apex_i])
    out["rpm_at_apex"] = float(rpm[apex_i])

    # Downshifts: gears descended (sum of negative steps), braking ∪ apex.
    if len(gear_ba) >= 2:
        dg = np.diff(gear_ba)
        out["n_downshifts"] = float((-dg[dg < 0]).sum()) if np.any(dg < 0) else 0.0
    else:
        out["n_downshifts"] = np.nan

    # First upshift at or after the kinematic apex, inside apex ∪ exit.
    if apex_i < len(gear) - 1:
        dg = np.diff(gear[apex_i:])
        pos = np.flatnonzero(dg > 0)
        if len(pos):
            out["upshift_rpm"] = float(rpm[apex_i + int(pos[0])])

    # Exit speed gain vs the minimum, interpolated on the full lap.
    d_apex = float(d[apex_i])
    v_min = float(spd[apex_i])
    out["exit_gain_100"] = _interp_at(lap_dist, lap_speed, d_apex + 100.0) - v_min
    out["exit_gain_200"] = _interp_at(lap_dist, lap_speed, d_apex + 200.0) - v_min

    # Spatial fractions (same distance weighting as coast_frac / full_throttle_frac).
    if len(thr_ae) >= 2:
        ae = pd.DataFrame({"Distance": d_ae, "Throttle": thr_ae})
        partial = (ae["Throttle"] > THROTTLE_PARTIAL_LO) & (ae["Throttle"] < THROTTLE_PARTIAL_HI)
        out["partial_thr_frac"] = spatial_fraction(ae, partial, track_length)
        out["thr_mod_per_m"] = excess_tv_per_m(d_ae, thr_ae, track_length)
    if len(a["thr"]) >= 2:
        ap = pd.DataFrame({"Distance": a["d"], "Throttle": a["thr"]})
        partial_a = (ap["Throttle"] > THROTTLE_PARTIAL_LO) & (ap["Throttle"] < THROTTLE_PARTIAL_HI)
        out["partial_thr_apex"] = spatial_fraction(ap, partial_a, track_length)
    if len(thr_ba) >= 2:
        ba = pd.DataFrame({"Distance": d_ba, "Throttle": thr_ba, "Brake": brk_ba})
        on = ba["Brake"].astype(bool)
        out["overlap_frac"] = spatial_fraction(ba, on & (ba["Throttle"] > THROTTLE_PICKUP), track_length)
        out["overlap_soft_frac"] = spatial_fraction(ba, on & (ba["Throttle"] > OVERLAP_SOFT), track_length)

    # Final ramp: last closure (throttle <= 10) before the first full-throttle
    # sample at or after the apex, then interpolated crossings of 10 and of 95.
    full_idx = np.flatnonzero(thr >= THROTTLE_FULL)
    full_after = full_idx[full_idx >= apex_i] if len(full_idx) else full_idx
    if len(full_after):
        f = int(full_after[0])
        if thr[apex_i] >= THROTTLE_FULL:
            t95, d95 = float(t[apex_i]), float(d[apex_i])
        else:
            t95, d95, _ = _upward_cross(t, d, thr, apex_i, THROTTLE_FULL)
        if np.isfinite(t95):
            out["t_full_s"] = float(t95 - t[apex_i])
            out["d_full_m"] = float(d95 - d_apex)

        closed = np.flatnonzero(thr[:f] <= THROTTLE_PICKUP)
        if len(closed):
            c = int(closed[-1])
            t10, d10, i_right = _upward_cross(t, d, thr, c, THROTTLE_PICKUP)
            if np.isfinite(t10) and np.isfinite(t95):
                ramp = float(t95 - t10)
                # A crossing ordered backwards means the 95% sample is not this ramp.
                if ramp >= -1e-3:
                    out["ramp_s"] = max(ramp, 0.0)
                    out["t_pickup_to_apex_s"] = float(t[apex_i] - t10)
            # Lifts counted from the first sample that is back above 10.
            lift_start = i_right if i_right >= 0 else c + 1
            out["thr_lifts"] = count_lifts(thr, min(lift_start, len(thr) - 1))
            if np.isfinite(t95):
                rate_end = f
                rate_start = min(max(lift_start, 0), rate_end)
                seg = rate[rate_start : rate_end + 1]
                seg = seg[np.isfinite(seg) & (seg > 0)]
                if len(seg):
                    out["pickup_rate"] = float(np.percentile(seg, 95))

        # Last brake sample at or before the full-throttle sample.
        brake_idx = np.flatnonzero(brk)
        brake_before = brake_idx[brake_idx <= f] if len(brake_idx) else brake_idx
        if len(brake_before) and np.isfinite(t95):
            last_b = int(brake_before[-1])
            out["t_brake_to_full_s"] = float(t95 - t[last_b])
    elif active:
        # Lifted or braked but never reached 95% inside the zone: leave NaN.
        out["thr_lifts"] = np.nan

    # If the pedal never closed, lifts / ramp stay NaN (not a structural zero).
    if out["thr_lifts"] != out["thr_lifts"]:  # NaN check without importing math on the sentinel
        pass

    # V vs U around the kinematic apex. Requires a real speed drop so a flat
    # acceleration zone is not described as a corner.
    pre_max = float(np.nanmax(spd[: apex_i + 1])) if apex_i >= 0 else v_min
    if active and (pre_max - v_min) >= MIN_SPEED_DROP_KMH:
        for key, level in (
            ("dwell_m", v_min + DWELL_BAND_KMH),
            ("dwell_m_3pct", v_min * (1.0 + DWELL_BAND_FRAC)),
        ):
            edges = _band_edges(t, d, spd, apex_i, level)
            if edges is None:
                continue
            t_entry, d_entry, t_exit, d_exit = edges
            d_decel = float(d_apex - d_entry)
            d_accel = float(d_exit - d_apex)
            if d_decel < 0 or d_accel < 0:
                continue
            if key == "dwell_m":
                out["dwell_m"] = d_decel + d_accel
                if d_accel >= MIN_SHAPE_DIST_M and d_decel >= MIN_SHAPE_DIST_M:
                    out["decel_accel_ratio"] = d_decel / d_accel
            else:
                out["dwell_m_3pct"] = d_decel + d_accel

    return out


def _self_check() -> None:
    t = np.array([0.0, 0.25, 0.50])
    d = np.array([0.0, 10.0, 20.0])
    y = np.array([0.0, 40.0, 100.0])
    tc, dc, idx = _upward_cross(t, d, y, 0, 10.0)
    assert idx == 1 and abs(tc - 0.0625) < 1e-9 and abs(dc - 2.5) < 1e-9, (tc, dc, idx)
    tc, dc, idx = _upward_cross(t, d, y, 0, 95.0)
    # (95-40)/(100-40) = 55/60 of the second interval
    assert idx == 2 and abs(tc - (0.25 + 0.25 * 55 / 60)) < 1e-9, tc
    assert count_lifts(np.array([0, 30, 60, 100]), 0) == 0
    assert count_lifts(np.array([100, 70, 100, 80]), 0) == 2
    assert count_lifts(np.array([100, 95, 100]), 0) == 0
    # excess TV: 0→100→50→100 has L1 variation 200 and net change 100.
    tv = excess_tv_per_m(
        np.array([0.0, 10.0, 20.0, 30.0]),
        np.array([0.0, 100.0, 50.0, 100.0]),
        None,
    )
    assert abs(tv - (200 - 100) / 30) < 1e-9, tv


def _wide_from_long(long_df: pd.DataFrame, metrics: list[str], suffix: str) -> pd.DataFrame:
    grouped = (
        long_df.groupby(["Driver", "LapNumber", "typology"], dropna=False)[metrics]
        .median()
        .reset_index()
    )
    pieces = []
    for typ, sub in grouped.groupby("typology"):
        block = sub.set_index(["Driver", "LapNumber"])[metrics]
        block = block.rename(columns={m: f"{typ}__{m}{suffix}" for m in metrics})
        pieces.append(block)
    wide = pieces[0]
    for extra in pieces[1:]:
        wide = wide.join(extra, how="outer")
    return wide


def _per_zone_wide(long_df: pd.DataFrame) -> pd.DataFrame:
    sub = long_df[long_df["zone_short"].isin(PER_ZONE)].copy()
    # One row per driver-lap-zone already.
    frames = []
    for zone, g in sub.groupby("zone_short"):
        block = g.set_index(["Driver", "LapNumber"])[PER_ZONE_METRICS]
        block = block.rename(columns={m: f"{zone}__{m}" for m in PER_ZONE_METRICS})
        frames.append(block)
    wide = frames[0]
    for extra in frames[1:]:
        wide = wide.join(extra, how="outer")
    return wide


def _sanity(raw: pd.DataFrame) -> None:
    print("\n=== sanity (raw zone medians; active rate) ===")
    cols = [
        "active",
        "t_full_s",
        "ramp_s",
        "t_pickup_to_apex_s",
        "thr_at_apex",
        "partial_thr_apex",
        "overlap_soft_frac",
        "thr_lifts",
        "min_gear",
        "gear_at_apex",
        "rpm_at_apex",
        "upshift_rpm",
        "n_downshifts",
        "exit_gain_100",
        "dwell_m",
        "decel_accel_ratio",
    ]
    for zone, g in raw.groupby("zone_short"):
        med = g[cols].median(numeric_only=True)
        active = float(g["active"].mean())
        print(
            f"{zone:4} n={len(g):4} active={active:.2f} "
            f"t_full={med['t_full_s']:.2f} ramp={med['ramp_s']:.2f} "
            f"tpick={med['t_pickup_to_apex_s']:.2f} thr@apex={med['thr_at_apex']:.0f} "
            f"partA={med['partial_thr_apex']:.2f} ovSoft={med['overlap_soft_frac']:.3f} "
            f"lifts={med['thr_lifts']:.2f} gear={med['min_gear']:.1f} "
            f"gApex={med['gear_at_apex']:.1f} rpm={med['rpm_at_apex']:.0f} "
            f"up={med['upshift_rpm']:.0f} dn={med['n_downshifts']:.1f} "
            f"g100={med['exit_gain_100']:.1f} dwell={med['dwell_m']:.0f} "
            f"ratio={med['decel_accel_ratio']:.2f}"
        )

    # Physical bounds
    bad = []
    if (raw["ramp_s"].dropna() < -1e-6).any():
        bad.append("negative ramp")
    if (raw["t_full_s"].dropna() < -0.05).any():
        bad.append("negative t_full")
    thr = raw["thr_at_apex"].dropna()
    if ((thr < -0.1) | (thr > 110)).any():
        bad.append("throttle out of range")
    gear = raw["min_gear"].dropna()
    if ((gear < 1) | (gear > 8)).any():
        bad.append("gear out of range")
    if (raw["dwell_m"].dropna() < -1e-6).any():
        bad.append("negative dwell")
    if (raw["decel_accel_ratio"].dropna() <= 0).any():
        bad.append("nonpositive ratio")
    print("bound checks:", "ok" if not bad else ", ".join(bad))

    ver = raw[(raw["Driver"] == "VER") & (raw["LapNumber"] == 20)]
    print("\nVER lap 20 (spot check vs a manual trace):")
    show = ["zone_short", "active", "t_full_s", "ramp_s", "thr_at_apex", "min_gear", "gear_at_apex", "exit_gain_100", "dwell_m"]
    print(ver[show].to_string(index=False, float_format=lambda v: f"{v:.3f}"))


def main() -> None:
    _self_check()
    t0 = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)

    zones = json.loads((DATA / "zones.json").read_text())
    lap_index = pd.read_csv(DATA / "lap_matrix.csv", usecols=["Driver", "LapNumber"])
    lap_index["LapNumber"] = lap_index["LapNumber"].astype(int)
    keys = set(zip(lap_index["Driver"], lap_index["LapNumber"]))

    car = pd.read_pickle(DATA / "car.pkl")
    car = car.merge(lap_index, on=["Driver", "LapNumber"], how="inner")
    print(f"loaded car rows={len(car)} laps={car.groupby(['Driver','LapNumber']).ngroups} in {time.perf_counter()-t0:.1f}s")

    car = car.sort_values(["Driver", "LapNumber", "Distance"]).reset_index(drop=True)
    car["t_s"] = car["Time"].dt.total_seconds()

    rows = []
    n_laps = 0
    for (driver, lap_number), lap in car.groupby(["Driver", "LapNumber"], sort=False):
        lap_number = int(lap_number)
        if (driver, lap_number) not in keys:
            continue
        n_laps += 1
        lap_dist = lap["Distance"].to_numpy(dtype=float)
        lap_speed = lap["Speed"].to_numpy(dtype=float)
        for zone_name, zone in zones.items():
            fr = get_corner_fragments(lap, zone)
            metrics = compute_zone_metrics(
                fr["braking"],
                fr["apex"],
                fr["exit"],
                lap_dist,
                lap_speed,
                zone.get("track_length"),
            )
            metrics.update(
                {
                    "Driver": driver,
                    "LapNumber": lap_number,
                    "zone": zone_name,
                    "zone_short": ZONE_SHORT.get(zone_name, zone_name),
                    "typology": zone.get("typology"),
                }
            )
            rows.append(metrics)
        if n_laps % 200 == 0:
            print(f"  processed {n_laps} laps, {time.perf_counter()-t0:.1f}s")

    raw = pd.DataFrame(rows)
    raw_path = OUT / "zone_metrics.csv"
    raw.to_csv(raw_path, index=False)
    print(f"zone rows={len(raw)} laps={n_laps} -> {raw_path}")
    _sanity(raw)

    # Typology path: flat corners (inactive) do not enter the median. Otherwise
    # Curva Grande's constant full-throttle would dilute Ascari inside "fast".
    masked = raw.copy()
    inactive = ~masked["active"].astype(bool)
    for col in MASK_IF_INACTIVE:
        masked.loc[inactive, col] = np.nan

    # Levels that are genuinely ~100 or ~0 when flat stay in the raw per-zone
    # table; typology medians below also drop them via MASK_IF_INACTIVE.
    # thr_at_apex / thr_*_mean / exit_gain are comparable numbers on a flat
    # corner but are not a driving-style event. Mask exit gains and means too
    # so the fast aggregate is Ascari, and keep the raw T3 columns.
    for col in ("thr_at_apex", "thr_apex_mean", "thr_exit_mean", "exit_gain_100", "exit_gain_200"):
        masked.loc[inactive, col] = np.nan

    raw_wide = _wide_from_long(masked, METRICS, suffix="")

    zmed = masked.copy()
    zmed[METRICS] = zmed[METRICS] - zmed.groupby("zone")[METRICS].transform("median")
    zmed_wide = _wide_from_long(zmed, METRICS, suffix="_zmed")

    lapsync = masked.copy()
    lapsync[METRICS] = lapsync[METRICS] - lapsync.groupby(["zone", "LapNumber"])[METRICS].transform("median")
    sync_wide = _wide_from_long(lapsync, METRICS, suffix="_lapsync")

    # Per-zone columns keep the raw measurement, including flat Curva Grande,
    # so a constant full-throttle corner is visible to the evaluator.
    # Typology medians above use `masked` and skip those laps.
    zone_wide = _per_zone_wide(raw)

    wide = raw_wide.join(zmed_wide, how="outer").join(sync_wide, how="outer").join(zone_wide, how="outer")
    wide = wide.reset_index()

    # Drop columns that are entirely empty or exact copies (correlation 1 and
    # identical values). Exact copies still get a one-line note.
    feature_cols = [c for c in wide.columns if c not in ("Driver", "LapNumber")]
    drop = []
    seen: dict[tuple, str] = {}
    for col in feature_cols:
        s = wide[col]
        if int(s.notna().sum()) == 0:
            drop.append(col)
            continue
        # Duplicate detection on finite pairs is done after, cheaply, by hash of rounded values.
        values = s.to_numpy(dtype=float)
        key = tuple(np.where(np.isfinite(values), np.round(values, 6), -999999.0))
        if key in seen:
            drop.append(col)
            print(f"drop duplicate {col} == {seen[key]}")
        else:
            seen[key] = col
    if drop:
        wide = wide.drop(columns=drop)

    cand_path = OUT / "candidates.csv"
    wide.to_csv(cand_path, index=False)
    n_feat = wide.shape[1] - 2
    print(f"candidates {wide.shape[0]} laps × {n_feat} features -> {cand_path}")
    print(f"elapsed {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()
