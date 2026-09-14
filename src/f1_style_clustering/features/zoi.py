"""Zone of Interest (ZOI) extraction with disjoint windows and track wrap-around."""

from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd
from fastf1.core import Session

from ..config import load_circuit_config

DistanceWindow = Tuple[float, float]


def _wrap(value: float, track_length: Optional[float]) -> float:
    if track_length is None or track_length <= 0:
        return float(value)
    return float(value % track_length)


def in_distance_window(
    distance: Union[float, np.ndarray, pd.Series],
    start: float,
    end: float,
    track_length: Optional[float] = None,
    *,
    end_inclusive: bool = True,
    start_inclusive: bool = True,
) -> Union[bool, np.ndarray, pd.Series]:
    """Return whether distance lies in [start, end], wrapping at track_length when start > end."""
    d = distance
    if track_length is not None and track_length > 0 and start > end:
        left = (d >= start) if start_inclusive else (d > start)
        right = (d <= end) if end_inclusive else (d < end)
        return left | right

    left = (d >= start) if start_inclusive else (d > start)
    right = (d <= end) if end_inclusive else (d < end)
    return left & right


def disjoint_zone_bounds(
    apex_distance: float,
    braking_pre_m: float = 350.0,
    apex_pre_m: float = 60.0,
    apex_post_m: float = 60.0,
    exit_post_m: float = 250.0,
    track_length: Optional[float] = None,
) -> Dict[str, DistanceWindow]:
    """Build abutting braking | apex | exit windows (disjoint interiors).

    Braking ends where the apex window starts; exit starts where apex ends.
    Distances wrap at ``track_length`` so T1 braking can sit at the end of the lap.
    """
    apex_start = _wrap(apex_distance - apex_pre_m, track_length)
    apex_end = _wrap(apex_distance + apex_post_m, track_length)
    braking_start = _wrap(apex_distance - braking_pre_m, track_length)
    braking_end = apex_start
    exit_start = apex_end
    exit_end = _wrap(apex_distance + exit_post_m, track_length)

    return {
        "braking": (braking_start, braking_end),
        "apex": (apex_start, apex_end),
        "exit": (exit_start, exit_end),
    }


def zoi_offsets_from_config(circuit_config: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """Read default ZOI offsets from circuits.yaml (live pipeline, not hardcoded-only)."""
    cfg = circuit_config if circuit_config is not None else {}
    offsets = cfg.get("default_zoi_offsets") or {}
    braking = offsets.get("braking") or {}
    apex = offsets.get("apex") or {}
    exit_z = offsets.get("exit") or {}
    return {
        "braking_pre_m": float(braking.get("pre_apex_meters", 350.0)),
        "apex_pre_m": float(apex.get("pre_apex_meters", 60.0)),
        "apex_post_m": float(apex.get("post_apex_meters", 60.0)),
        "exit_post_m": float(exit_z.get("post_apex_meters", 250.0)),
    }


def map_typology_to_bucket(
    typology: Optional[str],
    circuit_config: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Map a YAML corner typology string to slow | medium | fast."""
    if typology is None:
        return None
    key = str(typology).strip().lower()
    if key in {"slow", "medium", "fast"}:
        return key
    buckets = (circuit_config or {}).get("typology_buckets") or {}
    mapped = buckets.get(typology)
    if mapped is None:
        mapped = buckets.get(key)
    if mapped is None:
        # fuzzy fallback from typology tokens
        if any(tok in key for tok in ("hairpin", "slow", "tight", "heavy_braking", "hard_braking")):
            return "slow"
        if any(tok in key for tok in ("ultra_high", "high_speed", "high-speed", "sweeper", "fast")):
            return "fast"
        if "medium" in key:
            return "medium"
        return None
    return str(mapped).lower()


def classify_speed_typology(
    apex_speed_kmh: float,
    circuit_config: Optional[Dict[str, Any]] = None,
) -> str:
    """Classify a corner as slow/medium/fast from apex speed thresholds in circuits.yaml."""
    spec = (circuit_config or {}).get("corner_speed_classification") or {}
    slow_max = float((spec.get("slow") or {}).get("speed_threshold_max_kmh", 125))
    med_max = float((spec.get("medium") or {}).get("speed_threshold_max_kmh", 205))
    if pd.isna(apex_speed_kmh):
        return "medium"
    if apex_speed_kmh < slow_max:
        return "slow"
    if apex_speed_kmh < med_max:
        return "medium"
    return "fast"


def _match_benchmark_circuit(
    circuit_config: Dict[str, Any],
    event_name: Optional[str],
) -> Optional[Dict[str, Any]]:
    benchmarks = circuit_config.get("benchmark_circuits") or {}
    if not event_name:
        return None
    target = str(event_name).lower()
    for _key, spec in benchmarks.items():
        names = [
            str(spec.get("event_name", "")).lower(),
            str(spec.get("official_name", "")).lower(),
            str(_key).lower(),
        ]
        if any(target == n or n in target or target in n for n in names if n):
            return spec
    return None


def _corner_yaml_overrides(
    benchmark: Optional[Dict[str, Any]],
    corner_number: int,
    circuit_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return per-corner typology / window overrides from benchmark key_corners."""
    if not benchmark:
        return {}
    key_corners = benchmark.get("key_corners") or {}
    for _name, spec in key_corners.items():
        numbers = spec.get("corner_numbers") or []
        if corner_number in numbers or str(corner_number) in [str(n) for n in numbers]:
            bucket = spec.get("bucket") or map_typology_to_bucket(spec.get("typology"), circuit_config)
            return {
                "typology": bucket,
                "typology_raw": spec.get("typology"),
                "braking_pre_m": spec.get("braking_distance_window"),
                "exit_post_m": spec.get("exit_distance_window"),
                "zone_name": _name,
            }
    return {}


def infer_track_length(session: Session, telemetry: Optional[pd.DataFrame] = None) -> Optional[float]:
    """Infer lap distance (m) for wrap-around windows."""
    if telemetry is not None and "Distance" in telemetry.columns and not telemetry.empty:
        max_d = float(telemetry["Distance"].max())
        if max_d > 0:
            return max_d
    try:
        fastest = session.laps.pick_fastest()
        tel = fastest.get_car_data().add_distance()
        if tel is not None and not tel.empty:
            return float(tel["Distance"].max())
    except Exception:
        pass
    try:
        corners = session.get_circuit_info().corners
        if corners is not None and not corners.empty and "Distance" in corners.columns:
            # Last official corner is short of the start/finish; pad conservatively.
            return float(corners["Distance"].max()) * 1.05
    except Exception:
        pass
    return None


def extract_circuit_zones(
    session: Session,
    braking_pre_window: float = 350.0,
    apex_window: float = 60.0,
    exit_post_window: float = 250.0,
    selected_corners: Optional[list] = None,
    circuit_config: Optional[Dict[str, Any]] = None,
    track_length: Optional[float] = None,
) -> Dict[str, Dict[str, Any]]:
    """Extract disjoint Braking / Apex / Exit ZOIs, wired to ``config/circuits.yaml``.

    YAML default_zoi_offsets override the legacy 350/±60/250 defaults when present.
    Circuit-specific key_corners supply typology buckets and optional window lengths.
    """
    if circuit_config is None:
        try:
            circuit_config = load_circuit_config()
        except FileNotFoundError:
            circuit_config = {}

    yaml_offsets = zoi_offsets_from_config(circuit_config)
    braking_pre = yaml_offsets["braking_pre_m"] if circuit_config else braking_pre_window
    apex_pre = yaml_offsets["apex_pre_m"] if circuit_config else apex_window
    apex_post = yaml_offsets["apex_post_m"] if circuit_config else apex_window
    exit_post = yaml_offsets["exit_post_m"] if circuit_config else exit_post_window

    # Explicit call-site arguments still win when they differ from the historical defaults
    # only if the caller passed custom numbers; keep YAML as the live source of defaults.
    if braking_pre_window != 350.0:
        braking_pre = braking_pre_window
    if apex_window != 60.0:
        apex_pre = apex_window
        apex_post = apex_window
    if exit_post_window != 250.0:
        exit_post = exit_post_window

    circuit_info = session.get_circuit_info()
    if circuit_info is None or circuit_info.corners is None or circuit_info.corners.empty:
        raise ValueError("Circuit information with corner positions is not available for this session.")

    corners = circuit_info.corners.copy()
    if "Number" in corners.columns and selected_corners is not None:
        corners = corners[corners["Number"].isin(selected_corners)]

    if track_length is None:
        track_length = infer_track_length(session)

    event_name = None
    try:
        event_name = session.event["EventName"]
    except Exception:
        try:
            event_name = session.event.EventName
        except Exception:
            event_name = None

    benchmark = _match_benchmark_circuit(circuit_config, event_name)

    analysis_zones: Dict[str, Dict[str, Any]] = {}

    for idx, row in corners.iterrows():
        corner_num = int(row.get("Number", idx + 1))
        apex_dist = float(row["Distance"])
        overrides = _corner_yaml_overrides(benchmark, corner_num, circuit_config)
        corner_brake_pre = float(overrides.get("braking_pre_m") or braking_pre)
        corner_exit_post = float(overrides.get("exit_post_m") or exit_post)

        bounds = disjoint_zone_bounds(
            apex_distance=apex_dist,
            braking_pre_m=corner_brake_pre,
            apex_pre_m=apex_pre,
            apex_post_m=apex_post,
            exit_post_m=corner_exit_post,
            track_length=track_length,
        )
        zone_name = overrides.get("zone_name") or f"Turn_{corner_num}"
        # Keep Turn_N keys stable for callers; store YAML name alongside.
        key = f"Turn_{corner_num}"
        analysis_zones[key] = {
            **bounds,
            "apex_distance": apex_dist,
            "track_length": track_length,
            "typology": overrides.get("typology"),
            "typology_raw": overrides.get("typology_raw"),
            "corner_number": corner_num,
            "yaml_zone_name": zone_name,
        }

    return analysis_zones


def _slice_window(
    telemetry: pd.DataFrame,
    start: float,
    end: float,
    track_length: Optional[float],
    *,
    start_inclusive: bool = True,
    end_inclusive: bool = False,
) -> pd.DataFrame:
    mask = in_distance_window(
        telemetry["Distance"],
        start,
        end,
        track_length,
        start_inclusive=start_inclusive,
        end_inclusive=end_inclusive,
    )
    fragment = telemetry.loc[mask].copy()
    if fragment.empty:
        return fragment
    if track_length is not None and track_length > 0 and start > end:
        # Preserve on-track order: start → finish line, then 0 → end.
        first = fragment[fragment["Distance"] >= start].sort_values("Distance")
        second = fragment[fragment["Distance"] <= end].sort_values("Distance")
        return pd.concat([first, second], ignore_index=True)
    return fragment.sort_values("Distance")


def get_corner_fragments(
    telemetry: pd.DataFrame,
    zone_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Extract disjoint sub-zone telemetry fragments (wrap-aware)."""
    if "Distance" not in telemetry.columns:
        raise ValueError("Telemetry DataFrame must contain a 'Distance' column.")

    track_length = zone_dict.get("track_length")
    b_range = zone_dict["braking"]
    a_range = zone_dict["apex"]
    e_range = zone_dict["exit"]

    braking_fragment = _slice_window(
        telemetry, b_range[0], b_range[1], track_length, start_inclusive=True, end_inclusive=False
    )
    apex_fragment = _slice_window(
        telemetry, a_range[0], a_range[1], track_length, start_inclusive=True, end_inclusive=True
    )
    exit_fragment = _slice_window(
        telemetry, e_range[0], e_range[1], track_length, start_inclusive=False, end_inclusive=True
    )

    return {
        "braking": braking_fragment,
        "apex": apex_fragment,
        "exit": exit_fragment,
        "apex_distance": zone_dict.get("apex_distance", (a_range[0] + a_range[1]) / 2.0),
        "track_length": track_length,
        "typology": zone_dict.get("typology"),
        "corner_number": zone_dict.get("corner_number"),
    }
