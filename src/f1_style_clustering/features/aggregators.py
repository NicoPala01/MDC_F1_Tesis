"""Build driver-level style feature matrices from per-lap ZOI telemetry."""

from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
from fastf1.core import Lap, Session

from ..data.filters import filter_canonical_laps
from ..data.loader import prepare_lap_telemetry
from .metrics import (
    get_apex_speed,
    get_brake_point_relative,
    get_coast_frac,
    get_full_throttle_frac,
    get_kinematic_apex_distance,
    get_throttle_attack,
    get_throttle_onset_relative,
    get_trail_brake_frac,
)
from .preprocessor import normalize_typology_session_median
from .zoi import (
    classify_speed_typology,
    extract_circuit_zones,
    get_corner_fragments,
    in_distance_window,
    resolve_selected_corners,
)

# Distance wrap for optional last-Xm trail tail (mirrors zoi._wrap).
def _wrap_distance(value: float, track_length: Optional[float]) -> float:
    if track_length is None or track_length <= 0:
        return float(value)
    return float(value % track_length)

CORE_STYLE_FEATURES: List[str] = [
    "brake_point_rel",
    "trail_brake_frac",
    "apex_speed_rel",
    "throttle_attack",
    "coast_frac",
    "full_throttle_frac",
]

OPTIONAL_STYLE_FEATURES: List[str] = [
    "throttle_onset_rel",
]

POST_AGGREGATION_FEATURES: List[str] = [
    "brake_point_iqr",
]

METADATA_COLS: List[str] = [
    "Team",
    "n_laps",
    "LapsCount",
    "aggregator",
    "Compound",
    "TyreLife",
    "Stint",
    "FreshTyre",
]


def _concat_fragments(*parts: pd.DataFrame) -> pd.DataFrame:
    nonempty = [p for p in parts if p is not None and not p.empty]
    if not nonempty:
        return pd.DataFrame()
    return pd.concat(nonempty, ignore_index=True)


def trail_brake_fragment(
    apex: pd.DataFrame,
    braking: Optional[pd.DataFrame] = None,
    last_braking_m: Optional[float] = None,
    track_length: Optional[float] = None,
    apex_start: Optional[float] = None,
) -> pd.DataFrame:
    """Apex ZOI, optionally concatenated with the last ``last_braking_m`` of braking.

    Default (``last_braking_m`` is None/≤0): apex only — not braking ∪ apex.
    """
    if last_braking_m is None or last_braking_m <= 0 or braking is None or braking.empty:
        return apex if apex is not None else pd.DataFrame()
    if apex_start is None or "Distance" not in braking.columns:
        return apex if apex is not None else pd.DataFrame()
    tail_start = _wrap_distance(float(apex_start) - float(last_braking_m), track_length)
    mask = in_distance_window(
        braking["Distance"],
        tail_start,
        float(apex_start),
        track_length,
        start_inclusive=True,
        end_inclusive=False,
    )
    tail = braking.loc[mask]
    return _concat_fragments(tail, apex)


def extract_style_features_from_telemetry(
    telemetry: pd.DataFrame,
    analysis_zones: Dict[str, Dict[str, Any]],
    include_throttle_onset: bool = True,
    trail_last_braking_m: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Compute style features per ZOI on one lap of telemetry.

    ``trail_brake_frac`` is the spatial Brake==True fraction on the **apex ZOI
    only** (optional last Xm of braking via ``trail_last_braking_m``).
    """
    rows: List[Dict[str, Any]] = []
    if telemetry is None or telemetry.empty:
        return rows

    for corner_name, zone_info in analysis_zones.items():
        try:
            fragments = get_corner_fragments(telemetry, zone_info)
        except Exception:
            continue

        braking = fragments["braking"]
        apex = fragments["apex"]
        exit_z = fragments["exit"]
        track_length = fragments.get("track_length") or zone_info.get("track_length")
        official_apex = fragments.get("apex_distance", zone_info.get("apex_distance"))

        kinematic_apex = get_kinematic_apex_distance(apex)
        if pd.isna(kinematic_apex):
            kinematic_apex = get_kinematic_apex_distance(_concat_fragments(braking, apex, exit_z))
        apex_ref = kinematic_apex if pd.notna(kinematic_apex) else official_apex

        apex_start = None
        if "apex" in zone_info:
            apex_start = zone_info["apex"][0]
        trail_window = trail_brake_fragment(
            apex,
            braking=braking,
            last_braking_m=trail_last_braking_m,
            track_length=track_length,
            apex_start=apex_start,
        )
        corner_window = _concat_fragments(braking, apex, exit_z)
        onset_window = corner_window  # must allow pre-apex samples

        row: Dict[str, Any] = {
            "corner": corner_name,
            "corner_number": zone_info.get("corner_number"),
            "corner_numbers": zone_info.get("corner_numbers"),
            "yaml_zone_name": zone_info.get("yaml_zone_name", corner_name),
            "zone_source": zone_info.get("zone_source"),
            "typology": zone_info.get("typology"),
            "brake_point_rel": get_brake_point_relative(braking, apex_ref, track_length),
            "trail_brake_frac": get_trail_brake_frac(trail_window, track_length),
            "apex_speed_rel": get_apex_speed(apex),
            "throttle_attack": get_throttle_attack(exit_z),
            "coast_frac": get_coast_frac(corner_window, track_length),
            "full_throttle_frac": get_full_throttle_frac(exit_z, track_length),
        }
        if include_throttle_onset:
            row["throttle_onset_rel"] = get_throttle_onset_relative(
                onset_window, apex_ref, track_length
            )
        rows.append(row)

    return rows


def assign_missing_typologies(
    long_df: pd.DataFrame,
    circuit_config: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """Fill typology from session-level median apex speed when YAML did not label the corner."""
    if long_df.empty or "apex_speed_rel" not in long_df.columns:
        return long_df
    out = long_df.copy()
    if "typology" not in out.columns:
        out["typology"] = pd.NA

    ref_speed = out.groupby("corner")["apex_speed_rel"].median()
    for corner, speed in ref_speed.items():
        mask = out["corner"] == corner
        missing = out.loc[mask, "typology"].isna() | (out.loc[mask, "typology"].astype(str) == "None")
        if missing.any():
            bucket = classify_speed_typology(float(speed), circuit_config)
            out.loc[mask & missing, "typology"] = bucket
    out["typology"] = out["typology"].fillna("medium")
    return out


def aggregate_driver_style_features(
    long_df: pd.DataFrame,
    method: str = "median",
    include_brake_point_iqr: bool = True,
    min_valid_laps: int = 1,
    feature_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Median (default) or mean aggregation across laps per driver. Reports n_laps."""
    if long_df.empty:
        return pd.DataFrame()

    df = long_df.copy()
    if "Driver" not in df.columns:
        raise ValueError("long_df must contain a Driver column")

    if feature_cols is None:
        feature_cols = [c for c in CORE_STYLE_FEATURES + OPTIONAL_STYLE_FEATURES if c in df.columns]

    lap_key = "LapNumber" if "LapNumber" in df.columns else None
    n_laps = (
        df.groupby("Driver")[lap_key].nunique()
        if lap_key
        else df.groupby("Driver").size()
    )
    n_laps.name = "n_laps"

    if min_valid_laps and min_valid_laps > 1:
        keep = n_laps[n_laps >= min_valid_laps].index
        df = df[df["Driver"].isin(keep)]
        n_laps = n_laps.loc[keep]
        if df.empty:
            return pd.DataFrame()

    numeric = df.groupby("Driver")[feature_cols]
    if str(method).lower() == "mean":
        aggregated = numeric.mean()
    else:
        aggregated = numeric.median()
        method = "median"

    if include_brake_point_iqr and "brake_point_rel" in df.columns:
        q75 = df.groupby("Driver")["brake_point_rel"].quantile(0.75)
        q25 = df.groupby("Driver")["brake_point_rel"].quantile(0.25)
        aggregated["brake_point_iqr"] = q75 - q25

    aggregated["n_laps"] = n_laps.reindex(aggregated.index)
    aggregated["LapsCount"] = aggregated["n_laps"]
    aggregated["aggregator"] = method

    if "Team" in df.columns:
        team = df.groupby("Driver")["Team"].agg(lambda s: s.dropna().iloc[0] if s.dropna().shape[0] else "Unknown")
        aggregated["Team"] = team

    if "Compound" in df.columns:
        aggregated["Compound"] = df.groupby("Driver")["Compound"].agg(
            lambda s: s.dropna().mode().iloc[0] if s.dropna().shape[0] else pd.NA
        )
    if "TyreLife" in df.columns:
        aggregated["TyreLife"] = df.groupby("Driver")["TyreLife"].median()

    return aggregated


def collapse_to_driver_lap_typology(
    long_df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Median within (Driver × Lap × typology). Turn_N is diagnostic only.

    Stops FastF1 Number inflation: two slow chicane Numbers on the same lap
    contribute one typology observation, not two cluster-matrix weights.
    """
    if long_df.empty:
        return long_df.copy()

    df = long_df.copy()
    if feature_cols is None:
        feature_cols = [c for c in CORE_STYLE_FEATURES + OPTIONAL_STYLE_FEATURES if c in df.columns]

    group_keys = [k for k in ("Driver", "LapNumber", "typology") if k in df.columns]
    if "Driver" not in group_keys:
        raise ValueError("long_df must contain a Driver column")
    if len(group_keys) == 1:
        grouped = df.groupby(group_keys, dropna=False)
        out = grouped[feature_cols].median()
        out["n_zones"] = grouped.size()
        return out.reset_index() if out.index.name or isinstance(out.index, pd.MultiIndex) else out

    grouped = df.groupby(group_keys, dropna=False)
    out = grouped[feature_cols].median()
    out["n_zones"] = grouped.size()
    out = out.reset_index()

    # Diagnostic only — must not re-enter the cluster-matrix group keys.
    if "corner" in df.columns:
        out["corner"] = grouped["corner"].agg("first").to_numpy()
    if "corner_number" in df.columns:
        out["corner_number"] = grouped["corner_number"].agg("first").to_numpy()
    if "yaml_zone_name" in df.columns:
        out["yaml_zone_name"] = grouped["yaml_zone_name"].agg("first").to_numpy()
    if "zone_source" in df.columns:
        out["zone_source"] = grouped["zone_source"].agg("first").to_numpy()
    if "Team" in df.columns:
        out["Team"] = grouped["Team"].agg("first").to_numpy()
    if "Compound" in df.columns:
        out["Compound"] = grouped["Compound"].agg(
            lambda s: s.dropna().mode().iloc[0] if s.dropna().shape[0] else pd.NA
        ).to_numpy()
    if "TyreLife" in df.columns:
        out["TyreLife"] = grouped["TyreLife"].median().to_numpy()
    out["unit"] = "driver_lap_typology"
    return out


def _optional_lap_value(lap: Any, key: str):
    """Read a FastF1 lap field when present; never invent values."""
    try:
        if hasattr(lap, "get"):
            val = lap.get(key)
            if val is not None:
                return val
        contains = False
        try:
            contains = key in lap
        except Exception:
            contains = key in getattr(lap, "index", [])
        if contains:
            return lap[key]
    except Exception:
        return None
    return None


def extract_lap_style_rows(
    lap: Lap,
    analysis_zones: Dict[str, Dict[str, Any]],
    include_throttle_onset: bool = True,
) -> List[Dict[str, Any]]:
    """Per-lap rows (one per ZOI / key_corners group)."""
    telemetry = prepare_lap_telemetry(lap)
    if telemetry is None or telemetry.empty:
        return []
    rows = extract_style_features_from_telemetry(
        telemetry, analysis_zones, include_throttle_onset=include_throttle_onset
    )
    try:
        lap_number = int(lap["LapNumber"]) if "LapNumber" in lap else None
    except Exception:
        lap_number = None
    for row in rows:
        row["LapNumber"] = lap_number
    return rows


def build_long_style_table(
    session: Session,
    analysis_zones: Optional[Dict[str, Dict[str, Any]]] = None,
    drivers: Optional[List[str]] = None,
    circuit_config: Optional[Dict[str, Any]] = None,
    push_mode: bool = False,
    min_valid_laps: int = 3,
    include_throttle_onset: bool = True,
) -> pd.DataFrame:
    """Build the long (driver × lap × zone) table before aggregation."""
    if analysis_zones is None:
        selected, _source = resolve_selected_corners(session, circuit_config)
        analysis_zones = extract_circuit_zones(
            session, circuit_config=circuit_config, selected_corners=selected
        )

    driver_list = drivers or list(session.drivers)
    records: List[Dict[str, Any]] = []

    for driver_code in driver_list:
        try:
            drv_info = session.get_driver(driver_code)
            drv_abbr = drv_info["Abbreviation"] if "Abbreviation" in drv_info else str(driver_code)
        except Exception:
            drv_abbr = str(driver_code)

        driver_laps = filter_canonical_laps(session, driver=drv_abbr, push_mode=push_mode)
        if driver_laps is None or getattr(driver_laps, "empty", True):
            continue
        if min_valid_laps and len(driver_laps) < min_valid_laps:
            continue

        team_name = "Unknown"
        try:
            if "Team" in driver_laps.columns:
                team_name = driver_laps["Team"].iloc[0]
        except Exception:
            pass

        for _, lap in driver_laps.iterlaps():
            rows = extract_lap_style_rows(
                lap, analysis_zones, include_throttle_onset=include_throttle_onset
            )
            compound = _optional_lap_value(lap, "Compound")
            tyre_life = _optional_lap_value(lap, "TyreLife")
            for row in rows:
                row["Driver"] = drv_abbr
                row["Team"] = team_name
                if compound is not None and not (isinstance(compound, float) and pd.isna(compound)):
                    row["Compound"] = compound
                if tyre_life is not None and not (isinstance(tyre_life, float) and pd.isna(tyre_life)):
                    row["TyreLife"] = tyre_life
                records.append(row)

    if not records:
        return pd.DataFrame()

    long_df = pd.DataFrame(records)
    long_df = assign_missing_typologies(long_df, circuit_config=circuit_config)
    return long_df


def build_feature_matrix(
    session: Session,
    analysis_zones: Optional[Dict[str, Dict[str, Any]]] = None,
    drivers: Optional[List[str]] = None,
    aggregation: str = "median",
    circuit_config: Optional[Dict[str, Any]] = None,
    push_mode: bool = False,
    min_valid_laps: int = 3,
    include_throttle_onset: bool = True,
    include_brake_point_iqr: bool = True,
    selected_corners: Optional[List[int]] = None,
    extra_aggregations: Optional[Sequence[str]] = None,
) -> pd.DataFrame:
    """Driver matrix of relative 6–8 style features.

    Cluster-matrix unit: median within (Driver × Lap × typology), then median
    across those rows per driver. Turn_N does not weight the matrix.

    ``extra_aggregations`` (e.g. ``('mean',)``) re-aggregates the same
    typology×session table without re-extracting telemetry. Extra matrices are
    stored on ``result.attrs['extra_aggregations']``.
    """
    if analysis_zones is None:
        selected, _source = resolve_selected_corners(session, circuit_config)
        if selected_corners is None:
            selected_corners = selected
        analysis_zones = extract_circuit_zones(
            session, circuit_config=circuit_config, selected_corners=selected_corners
        )

    long_df = build_long_style_table(
        session,
        analysis_zones=analysis_zones,
        drivers=drivers,
        circuit_config=circuit_config,
        push_mode=push_mode,
        min_valid_laps=min_valid_laps,
        include_throttle_onset=include_throttle_onset,
    )
    if long_df.empty:
        return pd.DataFrame()

    feature_cols = [c for c in CORE_STYLE_FEATURES + OPTIONAL_STYLE_FEATURES if c in long_df.columns]
    long_rel = normalize_typology_session_median(long_df, feature_cols=feature_cols)
    # Turn_N / FastF1 Number is diagnostic only from here on.
    lap_typ = collapse_to_driver_lap_typology(long_rel, feature_cols=feature_cols)

    primary = aggregate_driver_style_features(
        lap_typ,
        method=aggregation,
        include_brake_point_iqr=include_brake_point_iqr,
        min_valid_laps=min_valid_laps,
        feature_cols=feature_cols,
    )
    extras: Dict[str, pd.DataFrame] = {}
    for extra in extra_aggregations or []:
        extra_method = str(extra).lower()
        if extra_method == str(aggregation).lower():
            continue
        extras[extra_method] = aggregate_driver_style_features(
            lap_typ,
            method=extra_method,
            include_brake_point_iqr=include_brake_point_iqr,
            min_valid_laps=min_valid_laps,
            feature_cols=feature_cols,
        )
    if extras:
        primary.attrs["extra_aggregations"] = extras
    return primary
