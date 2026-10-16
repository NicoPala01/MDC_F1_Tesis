"""Braking-window edge and an optional speed-scaled length.

The default windows stay as they are in ``config/circuits.yaml``. Scaling is
used only when ``features.speed_scaled_windows`` is true.

An onset sits on the edge of a window when the first sample inside that window
is already braking: the window opened after the driver had started to brake.
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from ..data.filters import filter_canonical_laps
from ..data.loader import prepare_lap_telemetry
from .metrics import along_track_delta, is_brake_on
from .zoi import _slice_window, _wrap, clip_and_merge_zones, get_corner_fragments


def scale_braking_distance(
    base_m: float,
    approach_kmh: Optional[float],
    ref_kmh: float = 300.0,
    min_m: float = 80.0,
    max_m: float = 700.0,
) -> float:
    """``base_m * (approach / ref)^2``, clipped. A missing speed leaves ``base_m``."""
    base = float(base_m)
    if approach_kmh is None or not np.isfinite(approach_kmh) or float(approach_kmh) <= 0:
        return base
    if not np.isfinite(ref_kmh) or float(ref_kmh) <= 0:
        return base
    scaled = base * (float(approach_kmh) / float(ref_kmh)) ** 2
    return float(np.clip(scaled, min_m, max_m))


def braking_pre_apex_m(zone: Dict[str, Any]) -> float:
    """Metres from the braking-window start forward to the apex."""
    start = float(zone["braking"][0])
    apex = float(zone["apex_distance"])
    return float(along_track_delta(apex, start, zone.get("track_length")))


def rescale_zone_braking(zone: Dict[str, Any], pre_m: float) -> Dict[str, Any]:
    """Move the braking start to ``pre_m`` before the apex. Apex and exit stay."""
    out = dict(zone)
    apex = float(zone["apex_distance"])
    track = zone.get("track_length")
    out["braking"] = (_wrap(apex - float(pre_m), track), zone["apex"][0])
    out["braking_pre_m"] = float(pre_m)
    return out


def apply_scaled_braking(
    zones: Dict[str, Dict[str, Any]],
    approach_kmh_by_zone: Dict[str, float],
    ref_kmh: float = 300.0,
    min_m: float = 80.0,
    max_m: float = 700.0,
) -> Dict[str, Dict[str, Any]]:
    """Rescale every zone, then clip neighbours the same way the extractor does."""
    scaled: Dict[str, Dict[str, Any]] = {}
    for name, zone in zones.items():
        base = braking_pre_apex_m(zone)
        pre = scale_braking_distance(
            base,
            approach_kmh_by_zone.get(name),
            ref_kmh=ref_kmh,
            min_m=min_m,
            max_m=max_m,
        )
        scaled[name] = rescale_zone_braking(zone, pre)
    track = next((z.get("track_length") for z in zones.values() if z.get("track_length")), None)
    return clip_and_merge_zones(scaled, track)


def classify_onset(
    fragment: pd.DataFrame,
    window_start: float,
    track_length: Optional[float],
) -> Optional[Dict[str, Any]]:
    """One braking fragment. ``None`` when the window has no samples.

    ``edge`` is true when the first sample is already braking.
    ``within_5m`` is true when the onset is at most 5 m after the window start.
    """
    if fragment is None or fragment.empty or "Distance" not in fragment.columns:
        return None
    entry_speed = np.nan
    if "Speed" in fragment.columns and pd.notna(fragment["Speed"].iloc[0]):
        entry_speed = float(fragment["Speed"].iloc[0])
    if "Brake" not in fragment.columns:
        return {
            "has_onset": False,
            "edge": False,
            "within_5m": False,
            "onset_from_start_m": np.nan,
            "entry_speed": entry_speed,
            "n_samples": int(len(fragment)),
        }
    brakes = is_brake_on(fragment["Brake"]).to_numpy()
    if not brakes.any():
        return {
            "has_onset": False,
            "edge": False,
            "within_5m": False,
            "onset_from_start_m": np.nan,
            "entry_speed": entry_speed,
            "n_samples": int(len(fragment)),
        }
    pos = int(np.flatnonzero(brakes)[0])
    onset = float(fragment["Distance"].iloc[pos])
    dist = float(along_track_delta(onset, float(window_start), track_length))
    return {
        "has_onset": True,
        "edge": bool(pos == 0),
        "within_5m": bool(np.isfinite(dist) and 0.0 <= dist <= 5.0),
        "onset_from_start_m": dist,
        "entry_speed": entry_speed,
        "n_samples": int(len(fragment)),
    }


def _fixed_pre_apex_fragment(telemetry: pd.DataFrame, zone: Dict[str, Any], pre_m: float) -> tuple:
    apex = float(zone["apex_distance"])
    track = zone.get("track_length")
    start = _wrap(apex - float(pre_m), track)
    end = zone["apex"][0]
    fragment = _slice_window(
        telemetry, start, end, track, start_inclusive=True, end_inclusive=False
    )
    return fragment, start


def scan_brake_onsets(
    session,
    zones: Dict[str, Dict[str, Any]],
    fixed_pre_m: float = 350.0,
    push_mode: bool = False,
    min_valid_laps: int = 3,
) -> pd.DataFrame:
    """One row per lap × zone × window (``pipeline`` and a fixed pre-apex length)."""
    rows = []
    driver_list = list(getattr(session, "drivers", []) or [])
    for driver_code in driver_list:
        try:
            info = session.get_driver(driver_code)
            abbr = info["Abbreviation"] if "Abbreviation" in info else str(driver_code)
        except Exception:
            abbr = str(driver_code)
        laps = filter_canonical_laps(session, driver=abbr, push_mode=push_mode)
        if laps is None or getattr(laps, "empty", True):
            continue
        if min_valid_laps and len(laps) < min_valid_laps:
            continue
        for _, lap in laps.iterlaps():
            telemetry = prepare_lap_telemetry(lap)
            if telemetry is None or telemetry.empty:
                continue
            try:
                lap_number = int(lap["LapNumber"]) if "LapNumber" in lap else None
            except Exception:
                lap_number = None
            for zone_name, zone in zones.items():
                track = zone.get("track_length")
                try:
                    fragments = get_corner_fragments(telemetry, zone)
                except Exception:
                    continue
                actual = classify_onset(fragments.get("braking"), zone["braking"][0], track)
                try:
                    fixed_frag, fixed_start = _fixed_pre_apex_fragment(telemetry, zone, fixed_pre_m)
                    fixed = classify_onset(fixed_frag, fixed_start, track)
                except Exception:
                    fixed = None
                for label, rec in (("pipeline", actual), (f"{int(fixed_pre_m)}m", fixed)):
                    if rec is None:
                        continue
                    rows.append(
                        {
                            "Driver": abbr,
                            "LapNumber": lap_number,
                            "zone": zone_name,
                            "window": label,
                            **rec,
                        }
                    )
    return pd.DataFrame(rows)


def summarize_onsets(records: pd.DataFrame) -> pd.DataFrame:
    """Edge fraction by window and zone, plus a total row per window.

    ``edge_frac_of_onsets`` is the share of brake starts whose first sample is
    already on the brakes. ``within_5m_frac_of_onsets`` uses a 5 m tolerance
    from the geometric start of the window.
    """
    if records is None or records.empty:
        return pd.DataFrame(
            columns=[
                "window",
                "zone",
                "n_fragments",
                "n_onsets",
                "n_edge",
                "n_within_5m",
                "edge_frac_of_onsets",
                "within_5m_frac_of_onsets",
                "median_entry_speed",
            ]
        )

    def _one(frame: pd.DataFrame, window: str, zone: str) -> Dict[str, Any]:
        onsets = frame[frame["has_onset"] == True]  # noqa: E712
        n_onsets = int(len(onsets))
        n_edge = int(onsets["edge"].sum()) if n_onsets else 0
        n_near = int(onsets["within_5m"].sum()) if n_onsets else 0
        return {
            "window": window,
            "zone": zone,
            "n_fragments": int(len(frame)),
            "n_onsets": n_onsets,
            "n_edge": n_edge,
            "n_within_5m": n_near,
            "edge_frac_of_onsets": (n_edge / n_onsets) if n_onsets else float("nan"),
            "within_5m_frac_of_onsets": (n_near / n_onsets) if n_onsets else float("nan"),
            "median_entry_speed": float(frame["entry_speed"].median()) if frame["entry_speed"].notna().any() else float("nan"),
        }

    rows = []
    for window, wframe in records.groupby("window", sort=False):
        for zone, zframe in wframe.groupby("zone", sort=False):
            rows.append(_one(zframe, str(window), str(zone)))
        rows.append(_one(wframe, str(window), "TOTAL"))
    return pd.DataFrame(rows)


def median_entry_speed_by_zone(records: pd.DataFrame, window: str = "pipeline") -> Dict[str, float]:
    if records is None or records.empty:
        return {}
    part = records[records["window"] == window]
    out = {}
    for zone, frame in part.groupby("zone"):
        speeds = pd.to_numeric(frame["entry_speed"], errors="coerce").dropna()
        if not speeds.empty:
            out[str(zone)] = float(speeds.median())
    return out


def apply_speed_scaled_windows(
    session,
    zones: Dict[str, Dict[str, Any]],
    ref_kmh: float = 300.0,
    push_mode: bool = False,
    min_valid_laps: int = 3,
    min_m: float = 80.0,
    max_m: float = 700.0,
) -> Dict[str, Dict[str, Any]]:
    """Off-path helper: scale braking windows by the median entry speed of each zone."""
    records = scan_brake_onsets(
        session,
        zones,
        push_mode=push_mode,
        min_valid_laps=min_valid_laps,
    )
    speeds = median_entry_speed_by_zone(records, window="pipeline")
    return apply_scaled_braking(zones, speeds, ref_kmh=ref_kmh, min_m=min_m, max_m=max_m)
