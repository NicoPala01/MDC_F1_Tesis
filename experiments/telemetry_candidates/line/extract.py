"""Racing-line / lateral-dynamics candidates for the Monza 2025 race.

Builds one session reference line in the FastF1 X/Y frame (position units are
1/10 m) and measures each lap against it. Per-zone columns are physical units.
Typology columns (medium, fast) are the median, across zones of that typology,
of the within-zone deviation from the session median. The single slow zone is
T1, so it is reported only as ``T1__*`` (a typology copy would be the same
feature up to a constant).

Run:
    /tmp/venv/bin/python /workspace/experiments/telemetry_candidates/line/extract.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.spatial import cKDTree

sys.path.insert(0, "/workspace/src")
from f1_style_clustering.features.metrics import is_brake_on  # noqa: E402
from f1_style_clustering.features.zoi import get_corner_fragments  # noqa: E402

DATA = Path("/workspace/cache/derived/2025_italian_grand_prix_r")
OUT = Path("/workspace/experiments/telemetry_candidates/line")

# Resample step of the reference line and of each lap's own arc length.
DS = 2.0
# Light smooth for the driven path used in lateral offset and path length.
POS_WIN = 11  # 22 m, poly 3
# Curvature / heading smooth. 31 samples * 2 m = 62 m. Tuned so Parabolica
# peak lateral acceleration lands near 3–4 g (see REPORT.md).
CURV_WIN = 31
SPEED_WIN = 15  # 30 m, for longitudinal acceleration
POLY = 3
# Reject a projection this far from the reference (pit, spike, off track).
MAX_OFFSET_M = 12.0
# Turn-in: |κ| must clear max(floor, fraction * peak) for this many metres.
TURNIN_KAPPA_FLOOR = 0.0015  # 1/m ≈ 667 m radius
TURNIN_KAPPA_FRAC = 0.25
TURNIN_HOLD_M = 8.0
# Bands, metres along the reference, fixed for every driver.
ENTRY_BAND = (-100.0, -40.0)  # relative to the first geometric corner
EXIT_BAND = (30.0, 110.0)  # relative to the last geometric corner
APEX_OFFSET_HALF_M = 10.0  # band around the kinematic-apex station
GEOM_MATCH_M = 80.0  # nearest geometric marker must lie within this of min-speed
TRAFFIC_M = 50.0
G = 9.81

ZONE_SHORT = {
    "T1_Variante_del_Rettifilo": "T1",
    "T3_Curva_Grande": "T3",
    "T4_Variante_della_Roggia": "T4",
    "T6_Curva_di_Lesmo": "T6",
    "T7_Seconda_di_Lesmo": "T7",
    "T8_Variante_Ascari": "T8",
    "T11_Curva_Parabolica_Alboreto": "T11",
}

# Direction-invariant, or sign-normalised before the median, so zones can be pooled.
TYPOLOGY_METRICS = [
    "inside_apex",
    "inside_entry",
    "inside_exit",
    "inside_brake",
    "line_width",
    "mean_inside",
    "apex_late",
    "apex_vs_curv",
    "turnin_dist",
    "turnin_vs_brake",
    "min_radius",
    "peak_lat_g",
    "mean_gg",
    "lat_grip_share",
    "path_delta",
    "curv_rise",
]

ZONE_METRICS = [
    "apex_offset",
    "entry_offset",
    "exit_offset",
    "brake_offset",
    "line_width",
    "mean_offset",
    "apex_late",
    "apex_vs_curv",
    "turnin_dist",
    "turnin_vs_brake",
    "min_radius",
    "peak_lat_g",
    "mean_gg",
    "lat_grip_share",
    "path_delta",
    "curv_rise",
]


def _savgol_closed(y: np.ndarray, win: int, deriv: int = 0, delta: float = 1.0) -> np.ndarray:
    """Savitzky–Golay on a closed loop (wrap-pad)."""
    w = int(win)
    if w % 2 == 0:
        w += 1
    if len(y) < w + 2:
        return np.full_like(y, np.nan, dtype=float)
    pad = w
    yp = np.r_[y[-pad:], y, y[:pad]]
    out = savgol_filter(yp, w, POLY, deriv=deriv, delta=delta, mode="interp")
    return out[pad:-pad]


def _clean_xy(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop duplicate steps and single-sample spikes, in metres."""
    if len(x) < 5:
        return x, y
    x = np.asarray(x, dtype=float).copy()
    y = np.asarray(y, dtype=float).copy()
    # 3-sample median kills isolated GPS spikes without shifting the line much.
    x = savgol_filter(x, 3, 1, mode="interp") if False else _median3(x)
    y = _median3(y)
    step = np.hypot(np.diff(x), np.diff(y))
    keep = np.concatenate([[True], step > 0.4])
    # Also drop a point that jumps > 25 m (impossible at this sample rate).
    jump = np.concatenate([[False], step > 25.0])
    keep = keep & ~jump
    return x[keep], y[keep]


def _median3(v: np.ndarray) -> np.ndarray:
    out = v.copy()
    if len(v) < 3:
        return out
    out[1:-1] = np.median(np.stack([v[:-2], v[1:-1], v[2:]]), axis=0)
    return out


def _arc(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    step = np.hypot(np.diff(x), np.diff(y))
    return np.concatenate([[0.0], np.cumsum(step)])


def resample_open(x: np.ndarray, y: np.ndarray, ds: float = DS) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s = _arc(x, y)
    _, ui = np.unique(np.round(s, 3), return_index=True)
    x, y, s = x[ui], y[ui], s[ui]
    if s[-1] < 10 * ds:
        return np.array([]), np.array([]), np.array([])
    grid = np.arange(0.0, s[-1], ds)
    return grid, np.interp(grid, s, x), np.interp(grid, s, y)


def resample_closed(xy: np.ndarray, ds: float = DS) -> tuple[np.ndarray, np.ndarray, float]:
    """Uniform closed polyline. Stations are 0, d, 2d, ... and the loop length is n*d."""
    ring = np.vstack([xy, xy[0]])
    step = np.hypot(np.diff(ring[:, 0]), np.diff(ring[:, 1]))
    s = np.concatenate([[0.0], np.cumsum(step)])
    length = float(s[-1])
    n = max(int(np.floor(length / ds)), 10)
    d = length / n
    grid = np.arange(n) * d
    x = np.interp(grid, s, ring[:, 0])
    y = np.interp(grid, s, ring[:, 1])
    return np.column_stack([x, y]), grid.astype(float), float(n * d)


def project_points(
    pts: np.ndarray,
    ref_xy: np.ndarray,
    ref_s: np.ndarray,
    length: float,
    tree: cKDTree,
) -> tuple[np.ndarray, np.ndarray]:
    """Project points onto a closed reference.

    Returns station in ``[0, length)`` and signed lateral offset (m), positive
    to the left of the direction of travel.
    """
    _, idx = tree.query(pts, k=1)
    m = len(ref_xy)
    # Two candidate segments around the nearest vertex: (idx-1 -> idx), (idx -> idx+1).
    i_prev = (idx - 1) % m
    i_here = idx % m
    i_next = (idx + 1) % m

    def _seg(i0: np.ndarray, i1: np.ndarray):
        a = ref_xy[i0]
        b = ref_xy[i1]
        ab = b - a
        l2 = np.sum(ab * ab, axis=1)
        ell = np.sqrt(np.maximum(l2, 1e-12))
        t = np.sum((pts - a) * ab, axis=1) / np.maximum(l2, 1e-12)
        tc = np.clip(t, 0.0, 1.0)
        proj = a + tc[:, None] * ab
        delta = pts - proj
        dist = np.linalg.norm(delta, axis=1)
        nx = -ab[:, 1] / ell
        ny = ab[:, 0] / ell
        signed = delta[:, 0] * nx + delta[:, 1] * ny
        # Station: s(i0) + t * segment length. Closing segment steps past `length`.
        s0 = ref_s[i0]
        station = np.mod(s0 + tc * ell, length)
        return dist, signed, station

    d0, n0, s0 = _seg(i_prev, i_here)
    d1, n1, s1 = _seg(i_here, i_next)
    take1 = d1 < d0
    signed = np.where(take1, n1, n0)
    station = np.where(take1, s1, s0)
    return station.astype(float), signed.astype(float)


def unwrap_forward(station: np.ndarray, length: float) -> np.ndarray:
    """Make station increase along the lap; kill projection jumps larger than 30 m."""
    if len(station) == 0:
        return station
    d = np.diff(station)
    d = (d + length / 2.0) % length - length / 2.0
    d = np.where(np.abs(d) > 30.0, 0.0, d)
    return np.concatenate([[station[0]], station[0] + np.cumsum(d)])


def _interp_signal(s_src: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    _, ui = np.unique(np.round(s_src, 3), return_index=True)
    return np.interp(grid, s_src[ui], values[ui])


def prepare_lap(g: pd.DataFrame) -> dict | None:
    g = g.sort_values("Distance")
    x = g["X"].to_numpy(dtype=float) / 10.0
    y = g["Y"].to_numpy(dtype=float) / 10.0
    dist = g["Distance"].to_numpy(dtype=float)
    speed_kmh = g["Speed"].to_numpy(dtype=float)
    throttle = g["Throttle"].to_numpy(dtype=float)
    brake = is_brake_on(g["Brake"]).to_numpy(dtype=bool)
    ahead = g["DistanceToDriverAhead"].to_numpy(dtype=float)
    x, y = _clean_xy(x, y)
    if len(x) < 50:
        return None
    # _clean_xy may have dropped points; rebuild signals on the same mask by
    # repeating the filter on the raw arrays together.
    return _prepare_aligned(g)


def _prepare_aligned(g: pd.DataFrame) -> dict | None:
    g = g.sort_values("Distance")
    x = g["X"].to_numpy(dtype=float) / 10.0
    y = g["Y"].to_numpy(dtype=float) / 10.0
    dist = g["Distance"].to_numpy(dtype=float)
    speed = g["Speed"].to_numpy(dtype=float) / 3.6
    throttle = g["Throttle"].to_numpy(dtype=float)
    brake = is_brake_on(g["Brake"]).to_numpy(dtype=float)
    ahead = g["DistanceToDriverAhead"].to_numpy(dtype=float)
    ahead = np.where(np.isfinite(ahead), ahead, 9999.0)
    xm = _median3(x)
    ym = _median3(y)
    step = np.hypot(np.diff(xm), np.diff(ym))
    keep = np.concatenate([[True], (step > 0.4) & (step < 25.0)])
    xm, ym, dist, speed, throttle, brake, ahead = (
        xm[keep],
        ym[keep],
        dist[keep],
        speed[keep],
        throttle[keep],
        brake[keep],
        ahead[keep],
    )
    s = _arc(xm, ym)
    _, ui = np.unique(np.round(s, 3), return_index=True)
    xm, ym, s = xm[ui], ym[ui], s[ui]
    dist, speed, throttle, brake, ahead = dist[ui], speed[ui], throttle[ui], brake[ui], ahead[ui]
    if s[-1] < 5000:
        return None
    grid = np.arange(0.0, s[-1], DS)
    xg = np.interp(grid, s, xm)
    yg = np.interp(grid, s, ym)
    # Position used for the line (short window) and curvature (long window) share the grid.
    xs = _savgol_closed(xg, POS_WIN, deriv=0, delta=DS)
    ys = _savgol_closed(yg, POS_WIN, deriv=0, delta=DS)
    xp = _savgol_closed(xg, CURV_WIN, deriv=1, delta=DS)
    yp = _savgol_closed(yg, CURV_WIN, deriv=1, delta=DS)
    xpp = _savgol_closed(xg, CURV_WIN, deriv=2, delta=DS)
    ypp = _savgol_closed(yg, CURV_WIN, deriv=2, delta=DS)
    speed_n = np.maximum((xp * xp + yp * yp), 1e-8) ** 1.5
    kappa = (xp * ypp - yp * xpp) / speed_n
    # Kill non-physical spikes (radius < 8 m) left by a bad sample.
    kappa = np.where(np.abs(kappa) > 1.0 / 8.0, np.nan, kappa)
    vg = _interp_signal(s, speed, grid)
    vg_s = _savgol_closed(np.nan_to_num(vg, nan=float(np.nanmedian(vg))), SPEED_WIN, deriv=0, delta=DS)
    dv_ds = _savgol_closed(np.nan_to_num(vg, nan=float(np.nanmedian(vg))), SPEED_WIN, deriv=1, delta=DS)
    a_lon = vg_s * dv_ds
    a_lat = np.where(np.isfinite(kappa), (vg_s ** 2) * kappa, np.nan)
    return {
        "grid": grid,
        "x": xs,
        "y": ys,
        "x_raw": xg,
        "y_raw": yg,
        "kappa": kappa,
        "speed": vg_s,
        "a_lon": a_lon,
        "a_lat": a_lat,
        "brake": _interp_signal(s, brake, grid) >= 0.5,
        "throttle": _interp_signal(s, throttle, grid),
        "ahead": _interp_signal(s, ahead, grid),
        "dist": _interp_signal(s, dist, grid),
        "arc0_x": float(xm[0]),
        "arc0_y": float(ym[0]),
        "src_x": xm,
        "src_y": ym,
    }


def build_reference(laps: list[dict]) -> tuple[np.ndarray, np.ndarray, float, cKDTree]:
    """Median path of every lap, two projection passes, then a light smooth."""
    arcs = []
    for lap in laps:
        s = _arc(lap["src_x"], lap["src_y"])
        arcs.append(s[-1])
    seed_i = int(np.argmin(np.abs(np.asarray(arcs) - np.median(arcs))))
    seed = laps[seed_i]
    sx = _savgol_closed(seed["x_raw"], CURV_WIN, deriv=0, delta=DS)
    sy = _savgol_closed(seed["y_raw"], CURV_WIN, deriv=0, delta=DS)
    ref_xy, ref_s, length = resample_closed(np.column_stack([sx, sy]), DS)
    anchor = np.median([[lap["arc0_x"], lap["arc0_y"]] for lap in laps], axis=0)

    def _rotate_to_anchor(xy: np.ndarray) -> np.ndarray:
        i0 = int(np.argmin((xy[:, 0] - anchor[0]) ** 2 + (xy[:, 1] - anchor[1]) ** 2))
        return np.roll(xy, -i0, axis=0)

    ref_xy = _rotate_to_anchor(ref_xy)
    ref_xy, ref_s, length = resample_closed(ref_xy, DS)

    all_xy = np.vstack([np.column_stack([lap["src_x"], lap["src_y"]]) for lap in laps])

    for _pass in range(2):
        tree = cKDTree(ref_xy)
        station, signed = project_points(all_xy, ref_xy, ref_s, length, tree)
        bins = np.floor(station / (length / len(ref_xy))).astype(int) % len(ref_xy)
        ok = np.abs(signed) < 15.0
        frame = pd.DataFrame({"b": bins[ok], "x": all_xy[ok, 0], "y": all_xy[ok, 1]})
        med = frame.groupby("b")[["x", "y"]].median()
        xy = np.full_like(ref_xy, np.nan)
        xy[med.index.to_numpy(), 0] = med["x"].to_numpy()
        xy[med.index.to_numpy(), 1] = med["y"].to_numpy()
        # Interpolate empty bins along the loop index.
        idx = np.arange(len(xy))
        good = np.isfinite(xy[:, 0])
        xy[:, 0] = np.interp(idx, idx[good], xy[good, 0], period=len(xy))
        xy[:, 1] = np.interp(idx, idx[good], xy[good, 1], period=len(xy))
        xs = _savgol_closed(xy[:, 0], POS_WIN, deriv=0, delta=DS)
        ys = _savgol_closed(xy[:, 1], POS_WIN, deriv=0, delta=DS)
        ref_xy, ref_s, length = resample_closed(np.column_stack([xs, ys]), DS)
        ref_xy = _rotate_to_anchor(ref_xy)
        ref_xy, ref_s, length = resample_closed(ref_xy, DS)

    # Final normals from a slightly smoother centerline so the normal does not chatter.
    xs = _savgol_closed(ref_xy[:, 0], 15, deriv=0, delta=DS)
    ys = _savgol_closed(ref_xy[:, 1], 15, deriv=0, delta=DS)
    ref_xy, ref_s, length = resample_closed(np.column_stack([xs, ys]), DS)
    ref_xy = _rotate_to_anchor(ref_xy)
    ref_xy, ref_s, length = resample_closed(ref_xy, DS)
    return ref_xy, ref_s, length, cKDTree(ref_xy)


def reference_kappa(ref_xy: np.ndarray) -> np.ndarray:
    return _kappa_xy(ref_xy[:, 0], ref_xy[:, 1])


def _kappa_xy(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    xp = _savgol_closed(x, CURV_WIN, deriv=1, delta=DS)
    yp = _savgol_closed(y, CURV_WIN, deriv=1, delta=DS)
    xpp = _savgol_closed(x, CURV_WIN, deriv=2, delta=DS)
    ypp = _savgol_closed(y, CURV_WIN, deriv=2, delta=DS)
    return (xp * ypp - yp * xpp) / np.maximum((xp * xp + yp * yp), 1e-8) ** 1.5


def _along(later: float, earlier: float, length: float) -> float:
    """Signed forward distance from earlier to later, in (-L/2, L/2]."""
    delta = (later - earlier) % length
    if delta > length / 2.0:
        delta -= length
    return float(delta)


def zone_geometry(zones: dict, corners: pd.DataFrame, ref_xy, ref_s, length, tree, kappa_ref) -> dict:
    """Locate each analysis zone on the reference via the corner marker XY."""
    cxy = np.column_stack([corners["X"].to_numpy(dtype=float) / 10.0, corners["Y"].to_numpy(dtype=float) / 10.0])
    csta, coff = project_points(cxy, ref_xy, ref_s, length, tree)
    s_geom = {int(n): float(s) for n, s in zip(corners["Number"].to_numpy(), csta)}
    off_geom = {int(n): float(o) for n, o in zip(corners["Number"].to_numpy(), coff)}

    out = {}
    for name, z in zones.items():
        short = ZONE_SHORT[name]
        nums = [int(n) for n in z["corner_numbers"]]
        tl = float(z["track_length"])
        apex_d = float(z["apex_distance"])
        apex_last = float(z["apex_distance_last"])
        brake_pre = _along(apex_d, float(z["braking"][0]), tl)
        apex_pre = _along(apex_d, float(z["apex"][0]), tl)
        apex_post = _along(float(z["apex"][1]), apex_last, tl)
        exit_post = _along(float(z["exit"][1]), apex_last, tl)
        s_first = s_geom[nums[0]]
        s_last = s_geom[nums[-1]]
        # Travel forward from the first marker to the last.
        if _along(s_last, s_first, length) < 0:
            s_last = s_first  # degenerate; should not happen
        s_brake0 = (s_first - brake_pre) % length
        s_apex0 = (s_first - apex_pre) % length
        s_apex1 = (s_last + apex_post) % length
        s_exit1 = (s_last + exit_post) % length
        # Sign of the turn from the reference curvature inside the apex window.
        # Chicanes flip sign; use the sign at the strongest |κ| sample so
        # "inside" means inside that kink, and pool only after this flip.
        k_zone = _window_values(ref_s, kappa_ref, s_apex0, s_apex1, length)
        if k_zone.size == 0 or not np.any(np.isfinite(k_zone)):
            sign = 1.0
            k_at = np.nan
        else:
            j = int(np.nanargmax(np.abs(k_zone)))
            k_at = float(k_zone[j])
            sign = 1.0 if k_at >= 0 else -1.0
        out[short] = {
            "name": name,
            "typology": z["typology"],
            "numbers": nums,
            "s_geom": {n: s_geom[n] for n in nums},
            "off_geom": {n: off_geom[n] for n in nums},
            "s_first": s_first,
            "s_last": s_last,
            "s_brake0": s_brake0,
            "s_apex0": s_apex0,
            "s_apex1": s_apex1,
            "s_exit1": s_exit1,
            "brake_pre": brake_pre,
            "apex_pre": apex_pre,
            "apex_post": apex_post,
            "exit_post": exit_post,
            "sign": sign,
            "kappa_at_peak": k_at,
        }
    return out


def _window_mask(station: np.ndarray, start: float, end: float, length: float) -> np.ndarray:
    u = (station - start) % length
    span = (end - start) % length
    if span <= 0:
        span = length
    return u <= span


def _window_values(station: np.ndarray, values: np.ndarray, start: float, end: float, length: float) -> np.ndarray:
    m = _window_mask(station, start, end, length)
    return values[m]


def _window_frame(lap_s: np.ndarray, start: float, end: float, length: float) -> np.ndarray:
    """Indices of samples in the window, ordered along the track."""
    u = (lap_s - start) % length
    span = (end - start) % length
    if span <= 0:
        span = length
    idx = np.flatnonzero(u <= span)
    if idx.size == 0:
        return idx
    return idx[np.argsort(u[idx])]


def _median_band(station: np.ndarray, values: np.ndarray, center: float, half: float, length: float) -> float:
    m = _window_mask(station, (center - half) % length, (center + half) % length, length)
    v = values[m]
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan")
    return float(np.median(v))


def _first_sustained(idx: np.ndarray, flag: np.ndarray, station: np.ndarray, hold_m: float) -> float:
    """Station of the first run of True flags covering at least ``hold_m`` metres."""
    if idx.size == 0:
        return float("nan")
    run = 0
    run_start = 0
    for i, ok in enumerate(flag):
        if ok:
            if run == 0:
                run_start = i
            run += 1
            if i > run_start and (station[idx[i]] - station[idx[run_start]]) >= hold_m:
                return float(station[idx[run_start]])
        else:
            run = 0
    return float("nan")


def metrics_for_zone(lap: dict, zone: dict, length: float) -> dict:
    s = lap["s"]
    n = lap["n"]
    # Usable samples only.
    valid = np.isfinite(n) & (np.abs(n) <= MAX_OFFSET_M) & np.isfinite(lap["kappa"])
    s_v = s
    kappa = np.where(valid, lap["kappa"], np.nan)
    offset = np.where(np.isfinite(n) & (np.abs(n) <= MAX_OFFSET_M), n, np.nan)
    speed = lap["speed"]
    a_lat = lap["a_lat"]
    a_lon = lap["a_lon"]

    whole0 = zone["s_brake0"]
    whole1 = zone["s_exit1"]
    idx_all = _window_frame(s_v, whole0, whole1, length)
    idx_apex = _window_frame(s_v, zone["s_apex0"], zone["s_apex1"], length)
    out = {k: float("nan") for k in ZONE_METRICS}
    out["min_ahead"] = float("nan")
    out["traffic"] = False
    if idx_all.size < 8 or idx_apex.size < 4:
        return out

    ahead = lap["ahead"][idx_all]
    out["min_ahead"] = float(np.nanmin(ahead)) if ahead.size else float("nan")
    out["traffic"] = bool(np.nanmin(ahead) < TRAFFIC_M) if ahead.size else False

    # Kinematic apex: minimum speed inside the apex window.
    sp_a = speed[idx_apex]
    if not np.any(np.isfinite(sp_a)):
        return out
    k_min = int(np.nanargmin(sp_a))
    s_kapex = float(s_v[idx_apex[k_min]])

    out["apex_offset"] = _median_band(s_v, offset, s_kapex, APEX_OFFSET_HALF_M, length)

    s_entry0 = (zone["s_first"] + ENTRY_BAND[0]) % length
    s_entry1 = (zone["s_first"] + ENTRY_BAND[1]) % length
    ent = offset[_window_frame(s_v, s_entry0, s_entry1, length)]
    ent = ent[np.isfinite(ent)]
    out["entry_offset"] = float(np.median(ent)) if ent.size else float("nan")

    s_exit0 = (zone["s_last"] + EXIT_BAND[0]) % length
    s_exit1b = (zone["s_last"] + EXIT_BAND[1]) % length
    ex = offset[_window_frame(s_v, s_exit0, s_exit1b, length)]
    ex = ex[np.isfinite(ex)]
    out["exit_offset"] = float(np.median(ex)) if ex.size else float("nan")

    off_all = offset[idx_all]
    off_all = off_all[np.isfinite(off_all)]
    if off_all.size >= 5:
        out["line_width"] = float(np.max(off_all) - np.min(off_all))
        out["mean_offset"] = float(np.mean(off_all))

    # Brake onset inside the braking window (first sustained brake sample).
    idx_br = _window_frame(s_v, zone["s_brake0"], zone["s_apex0"], length)
    s_brake = float("nan")
    if idx_br.size:
        br_flag = lap["brake"][idx_br]
        # 4 m hold ≈ two grid steps, so a one-sample flicker does not count.
        s_brake = _first_sustained(idx_br, br_flag, s_v, hold_m=4.0)
        if np.isfinite(s_brake):
            out["brake_offset"] = _median_band(s_v, offset, s_brake, 8.0, length)

    # Curva Grande is flat-out: speed only rises, so argmin sits on the window
    # edge and is not an apex. Keep a minimum that is a real trough (enough
    # speed drop, and not a monotone trace clipped by the window).
    drop_kmh = float((np.nanmax(sp_a) - np.nanmin(sp_a)) * 3.6)
    dsp = np.diff(sp_a[np.isfinite(sp_a)])
    monotone = dsp.size > 0 and (float(np.mean(dsp > 0)) > 0.85 or float(np.mean(dsp < 0)) > 0.85)
    on_edge = k_min <= 1 or k_min >= len(idx_apex) - 2
    interior_apex = bool(drop_kmh >= 15.0 and not (on_edge and monotone))
    out["apex_interior"] = interior_apex
    out["speed_drop_kmh"] = drop_kmh

    # Geometric marker nearest the kinematic apex, among this zone's corners.
    best_g, best_abs = None, 1e9
    for num, sg in zone["s_geom"].items():
        delta = _along(s_kapex, sg, length)
        if abs(delta) < best_abs:
            best_abs = abs(delta)
            best_g = sg
    if interior_apex and best_g is not None and best_abs <= GEOM_MATCH_M:
        out["apex_late"] = _along(s_kapex, best_g, length)

    k_all = kappa[idx_all]
    if np.any(np.isfinite(k_all)):
        j = int(np.nanargmax(np.abs(k_all)))
        s_kmax = float(s_v[idx_all[j]])
        k_peak = float(np.abs(k_all[j]))
        if interior_apex:
            out["apex_vs_curv"] = _along(s_kapex, s_kmax, length)
        thr = max(TURNIN_KAPPA_FLOOR, TURNIN_KAPPA_FRAC * k_peak)
        # Search turn-in from the braking start up to the curvature peak.
        idx_search = _window_frame(s_v, zone["s_brake0"], s_kmax, length)
        if idx_search.size:
            flag = np.abs(kappa[idx_search]) >= thr
            s_turn = _first_sustained(idx_search, flag, s_v, TURNIN_HOLD_M)
            if np.isfinite(s_turn):
                out["turnin_dist"] = _along(s_kmax, s_turn, length)
                if np.isfinite(s_brake):
                    out["turnin_vs_brake"] = _along(s_turn, s_brake, length)
                # Curvature rise: metres between 30% and 70% of peak |κ| before the peak.
                abs_k = np.abs(kappa[idx_search])
                above_lo = np.flatnonzero(abs_k >= 0.30 * k_peak)
                above_hi = np.flatnonzero(abs_k >= 0.70 * k_peak)
                if above_lo.size and above_hi.size:
                    out["curv_rise"] = _along(
                        float(s_v[idx_search[above_hi[0]]]),
                        float(s_v[idx_search[above_lo[0]]]),
                        length,
                    )

    k_apex = kappa[idx_apex]
    k_apex = k_apex[np.isfinite(k_apex)]
    if k_apex.size:
        k95 = float(np.nanpercentile(np.abs(k_apex), 95))
        # p95, not the single max sample: one noisy κ sample would invent a radius.
        out["min_radius"] = float(1.0 / k95) if k95 > 1e-4 else float("nan")

    alat = a_lat[idx_apex]
    along = a_lon[idx_apex]
    gg = np.sqrt(np.nan_to_num(alat, nan=np.nan) ** 2 + np.nan_to_num(along, nan=np.nan) ** 2)
    # Where either component is non-finite, drop the sample.
    good = np.isfinite(alat) & np.isfinite(along)
    if np.any(good):
        gg_g = gg[good] / G
        out["peak_lat_g"] = float(np.nanpercentile(np.abs(alat[good]) / G, 95))
        out["mean_gg"] = float(np.mean(gg_g))
        use = gg[good] > 0.5 * G
        if np.any(use):
            out["lat_grip_share"] = float(np.mean(np.abs(alat[good][use]) / gg[good][use]))

    # Path length of the smoothed line versus the reference span.
    xy = np.column_stack([lap["x"][idx_all], lap["y"][idx_all]])
    own = float(np.sum(np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1]))))
    span = (zone["s_exit1"] - zone["s_brake0"]) % length
    if span == 0:
        span = length
    out["path_delta"] = own - float(span)

    # Inside-positive copies (zone sign is a property of the reference, not the lap).
    sgn = zone["sign"]
    out["inside_apex"] = out["apex_offset"] * sgn if np.isfinite(out["apex_offset"]) else float("nan")
    out["inside_entry"] = out["entry_offset"] * sgn if np.isfinite(out["entry_offset"]) else float("nan")
    out["inside_exit"] = out["exit_offset"] * sgn if np.isfinite(out["exit_offset"]) else float("nan")
    out["inside_brake"] = out["brake_offset"] * sgn if np.isfinite(out["brake_offset"]) else float("nan")
    out["mean_inside"] = out["mean_offset"] * sgn if np.isfinite(out["mean_offset"]) else float("nan")
    return out


def _brake_drift_diagnostic(tel: pd.DataFrame, zones: dict, laps_by_key: dict, length: float, n: int = 30) -> dict:
    """Compare pipeline Distance brake onset with the reference-station brake onset.

    Quantifies how many metres of station the Distance-based slice is off, on a
    handful of laps. Uses ``get_corner_fragments`` exactly as the style pipeline.
    """
    deltas = []
    keys = list(laps_by_key.keys())[:n]
    for drv, lapn in keys:
        g = tel[(tel["Driver"] == drv) & (tel["LapNumber"] == lapn)].sort_values("Distance")
        lap = laps_by_key[(drv, lapn)]
        for name, z in zones.items():
            try:
                fr = get_corner_fragments(g, z)
            except Exception:
                continue
            br = fr["braking"]
            if br is None or br.empty:
                continue
            on = is_brake_on(br["Brake"])
            if not on.any():
                continue
            d_on = float(br.loc[on.idxmax(), "Distance"]) if on.loc[on.idxmax()] else np.nan
            if not np.isfinite(d_on):
                continue
            # Station of the lap sample nearest that Distance.
            j = int(np.argmin(np.abs(lap["dist"] - d_on)))
            s_dist = float(lap["s"][j] % length)
            short = ZONE_SHORT[name]
            # Filled later: caller passes zone geom. Stored as raw station delta vs lap s.
            deltas.append((short, s_dist, d_on))
    return {"n_pairs": len(deltas)}


def attach_projection(lap: dict, ref_xy, ref_s, length, tree) -> dict:
    pts = np.column_stack([lap["x"], lap["y"]])
    station, signed = project_points(pts, ref_xy, ref_s, length, tree)
    lap = dict(lap)
    lap["s"] = np.mod(unwrap_forward(station, length), length)
    # unwrap_forward then mod loses the monotonic fix inside a window that does
    # not contain a discontinuity. Windows are short, so mod is fine as long as
    # jumps were removed. Recompute a clean modulo station:
    lap["s"] = np.mod(station, length)
    # Repair isolated jumps by replacing them with neighbours before modulo logic
    # is used window-wise. Do it on the unwrapped series, then fold.
    unw = unwrap_forward(station, length)
    lap["s_unwrap"] = unw
    lap["s"] = np.mod(unw, length)
    lap["n"] = signed
    return lap


def typology_aggregate(long_df: pd.DataFrame) -> pd.DataFrame:
    """Per-zone session-median centering, then median over zones of one typology.

    Only typologies with at least two zones are returned. Centering is per zone
    so a corner with a different physical scale does not dominate the median.
    """
    rows = []
    metrics = [m for m in TYPOLOGY_METRICS if m in long_df.columns]
    for (drv, lapn, typ), g in long_df.groupby(["Driver", "LapNumber", "typology"], sort=False):
        if typ == "slow":
            continue
        rec = {"Driver": drv, "LapNumber": lapn, "typology": typ}
        for m in metrics:
            rec[m] = float(np.nanmedian(g[m].to_numpy(dtype=float))) if g[m].notna().any() else np.nan
        rows.append(rec)
    wide_parts = []
    tab = pd.DataFrame(rows)
    if tab.empty:
        return pd.DataFrame(columns=["Driver", "LapNumber"])
    for typ, g in tab.groupby("typology"):
        piv = g.set_index(["Driver", "LapNumber"])[metrics]
        piv.columns = [f"{typ}__{c}" for c in piv.columns]
        wide_parts.append(piv)
    out = wide_parts[0]
    for extra in wide_parts[1:]:
        out = out.join(extra, how="outer")
    return out.reset_index()


def center_by_zone(long_df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    out = long_df.copy()
    for m in metrics:
        out[m] = out[m] - out.groupby("zone")[m].transform("median")
    return out


def choose_plot_pair(zone_df: pd.DataFrame, teams: pd.DataFrame) -> tuple[str, str]:
    """Teammate pair with the largest gap in median T1 apex offset."""
    t1 = zone_df[zone_df["zone"] == "T1"]
    med = t1.groupby("Driver")["apex_offset"].median()
    team_of = teams.groupby("Driver")["Team"].first()
    best, gap = None, -1.0
    for team, members in team_of.groupby(team_of):
        ds = [d for d in members.index if d in med.index]
        if len(ds) != 2:
            continue
        delta = abs(float(med[ds[0]] - med[ds[1]]))
        if np.isfinite(delta) and delta > gap:
            gap = delta
            best = (ds[0], ds[1])
    if best is None:
        return "VER", "NOR"
    return best


def _ref_step(ref_xy: np.ndarray) -> float:
    return float(np.median(np.hypot(np.diff(ref_xy[:, 0]), np.diff(ref_xy[:, 1]))))


def _chord_swing(ref_xy: np.ndarray, zone: dict, length: float) -> float:
    """How far the reference line itself sits off the entry–exit chord (m).

    This is the geometric out-in-out of the median racing line. Driver offsets
    are residuals around this line, so they are much smaller than this swing.
    """
    step = _ref_step(ref_xy)
    stations = np.arange(len(ref_xy)) * step
    idx = _window_frame(stations, zone["s_brake0"], zone["s_exit1"], length)
    if idx.size < 5:
        return float("nan")
    xy = ref_xy[idx]
    chord = xy[-1] - xy[0]
    ell = float(np.linalg.norm(chord))
    if ell < 1:
        return float("nan")
    normal = np.array([-chord[1], chord[0]]) / ell
    return float(np.max(np.abs((xy - xy[0]) @ normal)))


def make_plot(ref_xy, zones_geom, laps_by_key, pair, path: Path, length: float) -> None:
    """Full reference line, plus T1 lateral offset of two teammates.

    XY traces of the two drivers sit on top of each other at map scale: the
    residual to the median line is decimetres, so the right panel is n(s).
    """
    z = zones_geom["T1"]
    step = _ref_step(ref_xy)
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 5.3))

    ax = axes[0]
    ax.plot(ref_xy[:, 0], ref_xy[:, 1], color="0.25", lw=1.15, zorder=1)
    for short, color in (("T1", "#c0392b"), ("T8", "#1a7a4c"), ("T11", "#1f4e79")):
        zg = zones_geom[short]
        i = int(round(zg["s_first"] / step)) % len(ref_xy)
        ax.scatter(ref_xy[i, 0], ref_xy[i, 1], s=28, c=color, zorder=3, label=short)
    ax.set_aspect("equal")
    ax.set_title("Session reference line (median path)")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    colors = ["#c0392b", "#2471a3"]
    s0 = z["s_brake0"]
    for drv, color in zip(pair, colors):
        chunks = []
        for (d, _ln), lap in laps_by_key.items():
            if d != drv:
                continue
            idx = _window_frame(lap["s"], s0, z["s_exit1"], length)
            if idx.size < 5:
                continue
            u = (lap["s"][idx] - s0) % length
            chunks.append(np.column_stack([u, lap["n"][idx]]))
        if not chunks:
            continue
        allp = np.vstack(chunks)
        bins = np.floor(allp[:, 0] / 4.0).astype(int)
        frame = pd.DataFrame({"b": bins, "n": allp[:, 1]})
        med = frame.groupby("b")["n"].median()
        q1 = frame.groupby("b")["n"].quantile(0.25)
        q3 = frame.groupby("b")["n"].quantile(0.75)
        x = med.index.to_numpy() * 4.0
        ax.fill_between(x, q1.reindex(med.index), q3.reindex(med.index), color=color, alpha=0.18, linewidth=0)
        ax.plot(x, med.to_numpy(), color=color, lw=1.7, label=drv)
    # Geometric markers, metres after the braking point.
    for num, sg in z["s_geom"].items():
        u = (sg - s0) % length
        ax.axvline(u, color="0.4", lw=0.7, ls="--")
        ax.text(u + 4, 1.35, f"T{num}", fontsize=8, color="0.25")
    ax.axhline(0.0, color="0.5", lw=0.6)
    ax.set_title(f"T1 lateral offset  {pair[0]} vs {pair[1]}")
    ax.set_xlabel("Metres after braking point")
    ax.set_ylabel("Signed offset (m, left > 0)")
    ax.set_ylim(-1.6, 1.6)
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("loading telemetry…")
    lm = pd.read_csv(DATA / "lap_matrix.csv", usecols=["Driver", "LapNumber", "Team"])
    lm["Driver"] = lm["Driver"].astype(str)
    lm["LapNumber"] = lm["LapNumber"].astype(int)
    zones = json.loads((DATA / "zones.json").read_text())
    corners = pd.read_csv(DATA / "corners.csv")
    tel = pd.read_pickle(DATA / "tel.pkl")
    tel["Driver"] = tel["Driver"].astype(str)
    tel["LapNumber"] = tel["LapNumber"].astype(int)
    lap_index = pd.MultiIndex.from_frame(lm[["Driver", "LapNumber"]])
    tel_index = pd.MultiIndex.from_frame(tel[["Driver", "LapNumber"]])
    tel = tel.loc[tel_index.isin(lap_index)].copy()
    print(f"samples={len(tel)} laps={tel.groupby(['Driver','LapNumber']).ngroups}")

    print("preparing laps…")
    laps = []
    lap_meta = []
    for (drv, lapn), g in tel.groupby(["Driver", "LapNumber"], sort=False):
        prepared = _prepare_aligned(g)
        if prepared is None:
            print("skip", drv, lapn)
            continue
        prepared["Driver"] = str(drv)
        prepared["LapNumber"] = int(lapn)
        laps.append(prepared)
        lap_meta.append((str(drv), int(lapn)))
    print(f"prepared {len(laps)}")

    print("building reference line…")
    ref_xy, ref_s, length, tree = build_reference(laps)
    k_ref = reference_kappa(ref_xy)
    print(f"reference length {length:.1f} m  points {len(ref_xy)}")
    geom = zone_geometry(zones, corners, ref_xy, ref_s, length, tree, k_ref)
    for short, z in geom.items():
        print(
            f"  {short:4s} {z['typology']:6s} sign={z['sign']:+.0f} "
            f"s_first={z['s_first']:.0f} s_last={z['s_last']:.0f} "
            f"brake_pre={z['brake_pre']:.0f} apex_pre={z['apex_pre']:.0f} "
            f"exit_post={z['exit_post']:.0f} k_peak={z['kappa_at_peak']:.4f} "
            f"marker_off={[round(v,1) for v in z['off_geom'].values()]}"
        )

    print("projecting laps and computing zone metrics…")
    records = []
    laps_by_key = {}
    n_big = 0
    n_pts = 0
    for lap in laps:
        lap = attach_projection(lap, ref_xy, ref_s, length, tree)
        laps_by_key[(lap["Driver"], lap["LapNumber"])] = lap
        n_big += int(np.sum(np.abs(lap["n"]) > MAX_OFFSET_M))
        n_pts += len(lap["n"])
        for short, z in geom.items():
            m = metrics_for_zone(lap, z, length)
            m["Driver"] = lap["Driver"]
            m["LapNumber"] = lap["LapNumber"]
            m["zone"] = short
            m["typology"] = z["typology"]
            records.append(m)
    long_df = pd.DataFrame(records)
    print(f"projection |n|>{MAX_OFFSET_M:.0f} m: {n_big}/{n_pts} ({n_big / max(n_pts,1):.3%})")

    # Physical sanity: lateral g and radius.
    print("physical sanity (median across laps):")
    sanity = {}
    for short, g in long_df.groupby("zone"):
        rec = {
            "peak_lat_g": float(g["peak_lat_g"].median()),
            "min_radius": float(g["min_radius"].median()),
            "line_width": float(g["line_width"].median()),
            "apex_offset_std": float(g["apex_offset"].std()),
            "path_delta": float(g["path_delta"].median()),
            "traffic_frac": float(g["traffic"].mean()),
            "apex_late": float(g["apex_late"].median()),
            "coverage_apex": float(g["apex_offset"].notna().mean()),
        }
        sanity[short] = rec
        rec["apex_interior_frac"] = float(g["apex_interior"].mean()) if "apex_interior" in g.columns else float("nan")
        rec["speed_drop_kmh"] = float(g["speed_drop_kmh"].median()) if "speed_drop_kmh" in g.columns else float("nan")
        rec["chord_swing_m"] = _chord_swing(ref_xy, geom[short], length)
        print(
            f"  {short:4s} peak_lat_g={rec['peak_lat_g']:.2f}  Rmin={rec['min_radius']:.0f} m  "
            f"width={rec['line_width']:.2f} m  chord={rec['chord_swing_m']:.1f} m  "
            f"path_delta={rec['path_delta']:.1f} m  dV={rec['speed_drop_kmh']:.0f} km/h  "
            f"traffic={rec['traffic_frac']:.2%}  interior_apex={rec['apex_interior_frac']:.0%}"
        )

    # Distance-window vs reference-station brake onset, via get_corner_fragments.
    print("brake-onset drift vs Distance slicing…")
    drift_rows = []
    sample_keys = lap_meta[:: max(len(lap_meta) // 40, 1)][:40]
    for drv, lapn in sample_keys:
        g = tel[(tel["Driver"] == drv) & (tel["LapNumber"] == lapn)].sort_values("Distance")
        lap = laps_by_key[(drv, lapn)]
        for name, zraw in zones.items():
            fr = get_corner_fragments(g, zraw)
            br = fr["braking"]
            if br is None or br.empty or "Brake" not in br.columns:
                continue
            on = is_brake_on(br["Brake"])
            if not bool(on.any()):
                continue
            first = on.idxmax()
            if not bool(on.loc[first]):
                continue
            d_on = float(br.loc[first, "Distance"])
            j = int(np.argmin(np.abs(lap["dist"] - d_on)))
            s_from_dist = float(lap["s"][j])
            short = ZONE_SHORT[name]
            # Reference-window brake station reconstructed as apex_offset's companion:
            # recompute quickly from the stored brake by scanning the lap.
            z = geom[short]
            idx_br = _window_frame(lap["s"], z["s_brake0"], z["s_apex0"], length)
            if idx_br.size == 0:
                continue
            s_brake = _first_sustained(idx_br, lap["brake"][idx_br], lap["s"], hold_m=4.0)
            if not np.isfinite(s_brake):
                continue
            drift_rows.append(abs(_along(s_from_dist, s_brake, length)))
    drift_med = float(np.median(drift_rows)) if drift_rows else float("nan")
    drift_p90 = float(np.percentile(drift_rows, 90)) if drift_rows else float("nan")
    print(f"  |s(Distance brake) - s(reference brake)| median={drift_med:.2f} m  p90={drift_p90:.2f} m  n={len(drift_rows)}")

    # Typology aggregate on zone-centered values.
    centered = center_by_zone(long_df, TYPOLOGY_METRICS)
    typ = typology_aggregate(centered)

    # Per-zone wide raw columns.
    zone_wide_parts = []
    for short, g in long_df.groupby("zone", sort=False):
        cols = ["Driver", "LapNumber"] + ZONE_METRICS
        part = g[cols].copy()
        part = part.rename(columns={m: f"{short}__{m}" for m in ZONE_METRICS})
        zone_wide_parts.append(part.set_index(["Driver", "LapNumber"]))
    zone_wide = zone_wide_parts[0]
    for extra in zone_wide_parts[1:]:
        zone_wide = zone_wide.join(extra, how="outer")
    zone_wide = zone_wide.reset_index()

    # Optional consistency: rolling std of T1 / T11 apex offset over 5 laps of the same driver.
    base = lm[["Driver", "LapNumber"]].astype({"Driver": str, "LapNumber": int}).drop_duplicates()
    merged = base.merge(zone_wide, on=["Driver", "LapNumber"], how="left")
    merged = merged.merge(typ, on=["Driver", "LapNumber"], how="left")
    merged = merged.sort_values(["Driver", "LapNumber"])
    for col in ("T1__apex_offset", "T11__apex_offset", "T4__apex_offset", "T8__line_width"):
        if col not in merged.columns:
            continue
        merged[col.replace("__", "__rollstd_").replace("rollstd_" + col.split("__")[1], "rollstd")] if False else None
        name = f"{col.split('__')[0]}__{col.split('__')[1]}_rollstd"
        merged[name] = (
            merged.groupby("Driver")[col]
            .transform(lambda s: s.rolling(5, min_periods=4).std())
        )

    # Traffic flags alongside, not as style features. Written separately.
    traffic = long_df.pivot_table(index=["Driver", "LapNumber"], columns="zone", values="min_ahead", aggfunc="first")
    traffic.columns = [f"{c}__min_ahead" for c in traffic.columns]
    traffic = traffic.reset_index()
    tflag = long_df.pivot_table(index=["Driver", "LapNumber"], columns="zone", values="traffic", aggfunc="first")
    tflag.columns = [f"{c}__traffic" for c in tflag.columns]
    traffic = traffic.merge(tflag.reset_index(), on=["Driver", "LapNumber"], how="left")
    traffic.to_csv(OUT / "traffic_by_zone.csv", index=False)

    # Candidate matrix: drop helper columns if any non-numeric slipped in.
    id_cols = ["Driver", "LapNumber"]
    feat_cols = [c for c in merged.columns if c not in id_cols]
    cand = merged[id_cols + feat_cols].copy()
    cand.to_csv(OUT / "candidates.csv", index=False)
    print(f"wrote {OUT / 'candidates.csv'}  rows={len(cand)} cols={len(feat_cols)}")

    pair = choose_plot_pair(long_df, lm.assign(Driver=lm["Driver"].astype(str)))
    print("plot pair", pair)
    make_plot(ref_xy, geom, laps_by_key, pair, OUT / "T1_reference_lines.png", length)

    # Traffic sensitivity of the apex-location metrics: same omega2 on laps
    # whose zone never comes within 50 m of the car ahead.
    from f1_style_clustering.analysis.feature_evaluation import nested_variance_shares

    teams = lm.assign(Driver=lm["Driver"].astype(str)).groupby(["Driver", "LapNumber"])["Team"].first()
    traffic_note = {}
    for metric in ("apex_late", "apex_vs_curv", "apex_offset"):
        for short in ("T1", "T8", "T11", "T4", "T6", "T7"):
            g = long_df[long_df["zone"] == short][["Driver", "LapNumber", metric, "traffic"]].dropna(subset=[metric])
            if g.empty:
                continue
            g = g.join(teams, on=["Driver", "LapNumber"])
            y = g[metric].to_numpy(dtype=float)
            drv = g["Driver"].astype(str).to_numpy()
            team = g["Team"].astype(str).to_numpy()
            all_o = nested_variance_shares(y, drv, team)["omega2_driver_in_team"]
            clean = ~g["traffic"].astype(bool).to_numpy()
            clean_o = nested_variance_shares(y[clean], drv[clean], team[clean])["omega2_driver_in_team"]
            traffic_note[f"{short}__{metric}"] = {
                "omega2_all": all_o,
                "omega2_no_traffic": clean_o,
                "clean_frac": float(clean.mean()),
            }
    print("traffic sensitivity (omega2 all → clean):")
    for k, v in traffic_note.items():
        if v["omega2_all"] is None or not np.isfinite(v["omega2_all"]):
            continue
        if v["omega2_all"] >= 0.03 or (np.isfinite(v["omega2_no_traffic"]) and v["omega2_no_traffic"] >= 0.03):
            print(f"  {k:22s} {v['omega2_all']:.3f} → {v['omega2_no_traffic']:.3f}  clean={v['clean_frac']:.0%}")

    diag = {
        "ds_m": DS,
        "pos_win_samples": POS_WIN,
        "pos_win_m": POS_WIN * DS,
        "curv_win_samples": CURV_WIN,
        "curv_win_m": CURV_WIN * DS,
        "speed_win_m": SPEED_WIN * DS,
        "polyorder": POLY,
        "max_offset_m": MAX_OFFSET_M,
        "reference_length_m": length,
        "n_laps": len(laps),
        "projection_reject_frac": n_big / max(n_pts, 1),
        "brake_distance_vs_reference_median_m": drift_med,
        "brake_distance_vs_reference_p90_m": drift_p90,
        "zones": {
            short: {
                "typology": z["typology"],
                "sign_left_positive_kappa": z["sign"],
                "s_first_m": z["s_first"],
                "s_last_m": z["s_last"],
                "kappa_peak_ref_1_per_m": z["kappa_at_peak"],
                "marker_offset_m": z["off_geom"],
                **sanity[short],
            }
            for short, z in geom.items()
        },
        "plot_pair": list(pair),
        "traffic_sensitivity": traffic_note,
        "definitions": {
            "apex_offset": "median signed lateral offset (m, left of reference > 0) within ±10 m of min speed in the apex window",
            "entry_offset": "median signed offset on the fixed band [s_first-100, s_first-40] m",
            "exit_offset": "median signed offset on the fixed band [s_last+30, s_last+110] m",
            "brake_offset": "median signed offset within ±8 m of brake onset",
            "line_width": "max(n) - min(n) over braking→exit, samples with |n|≤12 m",
            "inside_*": "offset multiplied by the sign of reference curvature at the zone's |κ| peak; >0 is inside that kink",
            "apex_late": "station(min speed) − station(nearest geometric corner), m; >0 is a late apex",
            "min_radius": "1 / p95(|κ|) in the apex window, m",
            "peak_lat_g": "p95(|v^2 κ|) / 9.81 in the apex window",
            "path_delta": "smoothed driven arc length minus reference span over the zone, m; <0 is a shorter path",
        },
    }
    (OUT / "diagnostics.json").write_text(json.dumps(diag, indent=2))
    print("wrote diagnostics and plot")


if __name__ == "__main__":
    main()
