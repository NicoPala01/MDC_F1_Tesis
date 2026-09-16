"""Zone of Interest (ZOI) extraction with disjoint windows and track wrap-around.

Pipeline B ownership
--------------------
``config/circuits.yaml`` owns ZOIs when the session event matches a
``benchmark_circuits`` entry: one zone per ``key_corners`` group (not one
per FastF1 corner ``Number``). Chicane groups (e.g. Monza T1 = [1, 2]) are
a single analysis unit.

If there is no benchmark match, a **speed-threshold fallback** builds one
zone per FastF1 ``Number`` and typology is filled later from
``corner_speed_classification``. That path does **not** pretend
``key_corners`` governs the circuit.
"""

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from fastf1.core import Session

from ..config import load_circuit_config

DistanceWindow = Tuple[float, float]

ZONE_SOURCE_KEY_CORNERS = "key_corners"
ZONE_SOURCE_SPEED_FALLBACK = "speed_threshold_fallback"


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
    return group_zone_bounds(
        first_apex=apex_distance,
        last_apex=apex_distance,
        braking_pre_m=braking_pre_m,
        apex_pre_m=apex_pre_m,
        apex_post_m=apex_post_m,
        exit_post_m=exit_post_m,
        track_length=track_length,
    )


def group_zone_bounds(
    first_apex: float,
    last_apex: float,
    braking_pre_m: float = 350.0,
    apex_pre_m: float = 60.0,
    apex_post_m: float = 60.0,
    exit_post_m: float = 250.0,
    track_length: Optional[float] = None,
) -> Dict[str, DistanceWindow]:
    """Disjoint windows for a key_corners group spanning ``first_apex`` → ``last_apex``.

    Apex covers the whole group; braking is before the first numbered corner;
    exit is after the last. A single-corner group reduces to the usual 350/±60/250.
    """
    apex_start = _wrap(first_apex - apex_pre_m, track_length)
    apex_end = _wrap(last_apex + apex_post_m, track_length)
    braking_start = _wrap(first_apex - braking_pre_m, track_length)
    braking_end = apex_start
    exit_start = apex_end
    exit_end = _wrap(last_apex + exit_post_m, track_length)

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


def session_event_name(session: Any) -> Optional[str]:
    """Best-effort EventName from a FastF1 session or test double."""
    try:
        event = session.event
    except Exception:
        return None
    if event is None:
        return None
    try:
        name = event["EventName"]
        if name:
            return str(name)
    except Exception:
        pass
    try:
        name = event.EventName
        if name:
            return str(name)
    except Exception:
        pass
    if isinstance(event, str) and event:
        return event
    return None


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


def key_corner_numbers(benchmark: Dict[str, Any]) -> List[int]:
    """Union of FastF1 Numbers listed under YAML ``key_corners`` (order preserved)."""
    numbers: List[int] = []
    seen = set()
    for spec in (benchmark.get("key_corners") or {}).values():
        for n in spec.get("corner_numbers") or []:
            try:
                num = int(n)
            except (TypeError, ValueError):
                continue
            if num not in seen:
                seen.add(num)
                numbers.append(num)
    return numbers


def resolve_selected_corners(
    session: Any,
    circuit_config: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[List[int]], str]:
    """Return (selected_corners, zone_source) according to circuits.yaml ownership.

    ``key_corners`` if the event matches a benchmark; otherwise
    ``speed_threshold_fallback`` with ``selected_corners is None`` (all FastF1
    Numbers). The fallback does not read ``key_corners``.
    """
    cfg = circuit_config if circuit_config is not None else {}
    event_name = session_event_name(session)
    benchmark = _match_benchmark_circuit(cfg, event_name)
    if not benchmark or not (benchmark.get("key_corners") or {}):
        return None, ZONE_SOURCE_SPEED_FALLBACK
    numbers = key_corner_numbers(benchmark)
    return (numbers or None), ZONE_SOURCE_KEY_CORNERS


def _corner_yaml_overrides(
    benchmark: Optional[Dict[str, Any]],
    corner_number: int,
    circuit_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return per-corner typology / window overrides from benchmark key_corners.

    Diagnostic helper for the fallback/legacy Number path. Pipeline B grouping
    uses ``_zones_from_key_corners`` instead of per-Number overrides.
    """
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


def _linear_interval(
    start: float,
    end: float,
    track_length: Optional[float],
) -> Tuple[float, float]:
    """Unwrapped [start, end]; ``end`` may exceed track_length when the window wraps."""
    if track_length is not None and track_length > 0 and start > end:
        return float(start), float(end) + float(track_length)
    return float(start), float(end)


def _apex_windows_overlap(
    za: Dict[str, Any],
    zb: Dict[str, Any],
    track_length: Optional[float],
) -> bool:
    a0, a1 = _linear_interval(*za["apex"], track_length)
    b0, b1 = _linear_interval(*zb["apex"], track_length)
    # Also compare zb wrapped forward when za is near the end of the lap.
    if track_length is not None and track_length > 0 and zb["apex_distance"] < za["apex_distance"]:
        b0 += track_length
        b1 += track_length
    return (a0 < b1) and (b0 < a1)


def _merge_zone_pair(za: Dict[str, Any], zb: Dict[str, Any]) -> Dict[str, Any]:
    """Union two overlapping-apex zones along Distance (chicane remnant)."""
    nums_a = list(
        za.get("corner_numbers")
        or ([za["corner_number"]] if za.get("corner_number") is not None else [])
    )
    nums_b = list(
        zb.get("corner_numbers")
        or ([zb["corner_number"]] if zb.get("corner_number") is not None else [])
    )
    numbers = nums_a + [n for n in nums_b if n not in nums_a]
    first_apex = min(float(za["apex_distance"]), float(zb["apex_distance"]))
    last_apex = max(
        float(za.get("apex_distance_last", za["apex_distance"])),
        float(zb.get("apex_distance_last", zb["apex_distance"])),
    )
    merged = dict(za)
    merged["apex"] = (za["apex"][0], zb["apex"][1])
    merged["braking"] = (za["braking"][0], za["apex"][0])
    merged["exit"] = (zb["apex"][1], zb["exit"][1])
    merged["apex_distance"] = first_apex
    merged["apex_distance_last"] = last_apex
    merged["corner_numbers"] = numbers
    merged["corner_number"] = numbers[0] if numbers else za.get("corner_number")
    name_a = za.get("yaml_zone_name") or ""
    name_b = zb.get("yaml_zone_name") or ""
    merged["yaml_zone_name"] = "+".join(p for p in (name_a, name_b) if p)
    return merged


def _clip_consecutive_windows(
    za: Dict[str, Any],
    zb: Dict[str, Any],
    track_length: Optional[float],
    *,
    wrapped: bool,
) -> None:
    """Clip za.exit vs zb.braking at the overlap midpoint (outer edges only)."""
    a_lo, a_hi = _linear_interval(*za["exit"], track_length)
    b_lo, b_hi = _linear_interval(*zb["braking"], track_length)
    if wrapped and track_length is not None and track_length > 0:
        if b_lo < a_lo:
            b_lo += track_length
            b_hi += track_length
    if a_hi <= b_lo:
        return
    mid_u = 0.5 * (b_lo + a_hi)
    mid = _wrap(mid_u, track_length) if track_length else mid_u
    za["exit"] = (za["exit"][0], mid)
    zb["braking"] = (mid, zb["braking"][1])


def clip_and_merge_zones(
    analysis_zones: Dict[str, Dict[str, Any]],
    track_length: Optional[float] = None,
) -> Dict[str, Dict[str, Any]]:
    """Merge overlapping apex windows; clip consecutive braking/exit along Distance.

    Intended for chicane groups that still overlap after construction, and for
    the speed-threshold fallback where adjacent FastF1 Numbers share Distance.
    """
    if not analysis_zones or len(analysis_zones) < 2:
        return analysis_zones

    items: List[Tuple[str, Dict[str, Any]]] = sorted(
        ((k, dict(v)) for k, v in analysis_zones.items()),
        key=lambda kv: float(kv[1].get("apex_distance", 0.0)),
    )

    merged: List[Tuple[str, Dict[str, Any]]] = []
    for name, zone in items:
        if merged and _apex_windows_overlap(merged[-1][1], zone, track_length):
            prev_name, prev = merged[-1]
            merged[-1] = (f"{prev_name}+{name}", _merge_zone_pair(prev, zone))
        else:
            merged.append((name, zone))

    if (
        track_length
        and len(merged) >= 2
        and _apex_windows_overlap(merged[-1][1], merged[0][1], track_length)
    ):
        last_name, last_z = merged[-1]
        first_name, first_z = merged[0]
        merged = [(f"{last_name}+{first_name}", _merge_zone_pair(last_z, first_z))] + merged[1:-1]

    n = len(merged)
    for i in range(n):
        j = (i + 1) % n
        if j == 0 and (track_length is None or track_length <= 0):
            break
        _clip_consecutive_windows(
            merged[i][1],
            merged[j][1],
            track_length,
            wrapped=(j == 0),
        )

    return {name: zone for name, zone in merged}


def _lookup_corner_distance(corners: pd.DataFrame, number: int) -> Optional[float]:
    if corners is None or corners.empty or "Number" not in corners.columns:
        return None
    hit = corners[corners["Number"].astype(int) == int(number)]
    if hit.empty or "Distance" not in hit.columns:
        return None
    return float(hit.iloc[0]["Distance"])


def _zones_from_key_corners(
    corners: pd.DataFrame,
    benchmark: Dict[str, Any],
    circuit_config: Dict[str, Any],
    offsets: Dict[str, float],
    track_length: Optional[float],
) -> Dict[str, Dict[str, Any]]:
    """One ZOI per YAML ``key_corners`` entry (grouped Numbers share a window)."""
    analysis_zones: Dict[str, Dict[str, Any]] = {}
    key_corners = benchmark.get("key_corners") or {}

    for zone_name, spec in key_corners.items():
        raw_numbers = spec.get("corner_numbers") or []
        numbers: List[int] = []
        distances: List[float] = []
        for n in raw_numbers:
            try:
                num = int(n)
            except (TypeError, ValueError):
                continue
            dist = _lookup_corner_distance(corners, num)
            if dist is None:
                continue
            numbers.append(num)
            distances.append(dist)
        if not numbers:
            continue

        first_apex = min(distances)
        last_apex = max(distances)
        braking_pre = float(spec.get("braking_distance_window") or offsets["braking_pre_m"])
        exit_post = float(spec.get("exit_distance_window") or offsets["exit_post_m"])
        bounds = group_zone_bounds(
            first_apex=first_apex,
            last_apex=last_apex,
            braking_pre_m=braking_pre,
            apex_pre_m=offsets["apex_pre_m"],
            apex_post_m=offsets["apex_post_m"],
            exit_post_m=exit_post,
            track_length=track_length,
        )
        bucket = spec.get("bucket") or map_typology_to_bucket(spec.get("typology"), circuit_config)
        analysis_zones[str(zone_name)] = {
            **bounds,
            "apex_distance": first_apex,
            "apex_distance_last": last_apex,
            "track_length": track_length,
            "typology": bucket,
            "typology_raw": spec.get("typology"),
            "corner_number": numbers[0],
            "corner_numbers": numbers,
            "yaml_zone_name": str(zone_name),
            "zone_source": ZONE_SOURCE_KEY_CORNERS,
        }

    return analysis_zones


def _zones_from_speed_threshold_fallback(
    corners: pd.DataFrame,
    offsets: Dict[str, float],
    track_length: Optional[float],
    selected_corners: Optional[List[int]] = None,
) -> Dict[str, Dict[str, Any]]:
    """One ZOI per FastF1 Number. Typology is *not* taken from key_corners.

    ``typology`` is left unset; ``assign_missing_typologies`` fills it from
    session apex-speed thresholds (``corner_speed_classification``).
    """
    analysis_zones: Dict[str, Dict[str, Any]] = {}
    rows = corners
    if selected_corners is not None and "Number" in rows.columns:
        rows = rows[rows["Number"].isin(selected_corners)]

    for idx, row in rows.iterrows():
        corner_num = int(row.get("Number", idx + 1))
        apex_dist = float(row["Distance"])
        bounds = disjoint_zone_bounds(
            apex_distance=apex_dist,
            braking_pre_m=offsets["braking_pre_m"],
            apex_pre_m=offsets["apex_pre_m"],
            apex_post_m=offsets["apex_post_m"],
            exit_post_m=offsets["exit_post_m"],
            track_length=track_length,
        )
        key = f"Turn_{corner_num}"
        analysis_zones[key] = {
            **bounds,
            "apex_distance": apex_dist,
            "apex_distance_last": apex_dist,
            "track_length": track_length,
            "typology": None,
            "typology_raw": None,
            "corner_number": corner_num,
            "corner_numbers": [corner_num],
            "yaml_zone_name": key,
            "zone_source": ZONE_SOURCE_SPEED_FALLBACK,
        }
    return analysis_zones


def extract_circuit_zones(
    session: Session,
    braking_pre_window: float = 350.0,
    apex_window: float = 60.0,
    exit_post_window: float = 250.0,
    selected_corners: Optional[list] = None,
    circuit_config: Optional[Dict[str, Any]] = None,
    track_length: Optional[float] = None,
) -> Dict[str, Dict[str, Any]]:
    """Extract disjoint Braking / Apex / Exit ZOIs, owned by ``config/circuits.yaml``.

    If the session event matches a benchmark, **only** ``key_corners`` groups
    are extracted (one zone per YAML entry, windows/typology from YAML).
    ``selected_corners`` should be the union of those Numbers (see
    ``resolve_selected_corners``).

    If there is no match, the speed-threshold fallback is used: one zone per
    FastF1 Number (optionally filtered by ``selected_corners``). ``key_corners``
    does not govern that path.

    Adjacent windows are clip/merged along Distance after construction.
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

    offsets = {
        "braking_pre_m": braking_pre,
        "apex_pre_m": apex_pre,
        "apex_post_m": apex_post,
        "exit_post_m": exit_post,
    }

    circuit_info = session.get_circuit_info()
    if circuit_info is None or circuit_info.corners is None or circuit_info.corners.empty:
        raise ValueError("Circuit information with corner positions is not available for this session.")

    corners = circuit_info.corners.copy()

    if track_length is None:
        track_length = infer_track_length(session)

    event_name = session_event_name(session)
    benchmark = _match_benchmark_circuit(circuit_config, event_name)

    if benchmark and (benchmark.get("key_corners") or {}):
        if selected_corners is not None and "Number" in corners.columns:
            corners = corners[corners["Number"].isin(selected_corners)]
        analysis_zones = _zones_from_key_corners(
            corners, benchmark, circuit_config, offsets, track_length
        )
    else:
        # Explicit speed-threshold fallback — key_corners is not applied.
        analysis_zones = _zones_from_speed_threshold_fallback(
            corners, offsets, track_length, selected_corners=selected_corners
        )

    return clip_and_merge_zones(analysis_zones, track_length)


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
        "corner_numbers": zone_dict.get("corner_numbers"),
        "zone_source": zone_dict.get("zone_source"),
    }
