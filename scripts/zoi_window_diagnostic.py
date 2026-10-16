"""Diagnóstico de ventanas ZOI, temporada 2025.

No cambia el algoritmo. Mide, por circuito y zona, con la telemetría de la
carrera:

(a) inicios de frenada que caen en el borde o fuera de la ventana de frenada
    que usa el pipeline (después de ``clip_and_merge_zones``). El inicio se
    busca en una ventana extendida de 800 m, solo para el diagnóstico.
(b) pares de ZOI consecutivas que se solapan antes del recorte, y cuántas
    zonas fusiona ``clip_and_merge_zones``.

La definición histórica de Monza (el primer sample de la ventana ya trae el
freno puesto) se calcula con ``classify_onset`` para contrastar
``docs/vector_por_zona_monza_2025.md``.

    python scripts/zoi_window_diagnostic.py --year 2025
    python scripts/zoi_window_diagnostic.py --event "Italian Grand Prix"
    python scripts/zoi_window_diagnostic.py --archive /ruta/2025 --label baseline

``--archive`` lee el export de TracingInsights-Archive (``Lap.get_telemetry()``
más ``corners.json``). No usa ``get_car_data().add_distance()``.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from f1_style_clustering.config import load_circuit_config, load_config  # noqa: E402
from f1_style_clustering.data.filters import filter_canonical_laps  # noqa: E402
from f1_style_clustering.data.loader import enable_cache, prepare_lap_telemetry  # noqa: E402
from f1_style_clustering.features.brake_windows import classify_onset  # noqa: E402
from f1_style_clustering.features.metrics import along_track_delta, is_brake_on  # noqa: E402
from f1_style_clustering.features.zoi import (  # noqa: E402
    _apex_windows_overlap,
    _linear_interval,
    _match_benchmark_circuit,
    _slice_window,
    ZONE_SOURCE_KEY_CORNERS,
    ZONE_SOURCE_SPEED_FALLBACK,
    _zones_from_key_corners,
    _zones_from_speed_threshold_fallback,
    classify_speed_typology,
    clip_and_merge_zones,
    infer_track_length,
    key_corner_numbers,
    resolve_selected_corners,
    session_event_name,
    zoi_offsets_from_config,
)
from f1_style_clustering.season import iter_race_event_names  # noqa: E402

EXTENDED_PRE_M = 800.0
EDGE_TOL_M = 5.0
P95_MARGIN_M = 15.0
MIN_ONSETS_FOR_WINDOW = 30
MIN_BRAKE_M = 80.0
MAX_BRAKE_M = 750.0
MIN_EXIT_M = 80.0
FLAT_ONSET_FRAC = 0.05
JUSTIFY_FRAC = 0.05
GROUP_GAP_M = 120.0
HEREDADO_DOMINANT = 0.50
BORDERLINE_KMH = 8.0
PROTECTED_EVENTS = {
    "Italian Grand Prix",
    "British Grand Prix",
    "Monaco Grand Prix",
}

# Cifras publicadas en docs/vector_por_zona_monza_2025.md
MONZA_PUBLISHED = {
    "legacy_350_n_onsets": 5114,
    "legacy_350_n_edge": 261,
    "legacy_350_frac": 261 / 5114,
    "lesmo2_zone": "T7_Seconda_di_Lesmo",
    "lesmo2_n_onsets": 811,
    "lesmo2_n_edge": 250,
    "legacy_pipe_n_onsets": 5074,
    "legacy_pipe_n_edge": 13,
    "legacy_pipe_frac": 13 / 5074,
}


def pipeline_offsets(circuit_config: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Mismos metros que ``extract_circuit_zones`` cuando nadie pisa el default."""
    yaml_offsets = zoi_offsets_from_config(circuit_config or {})
    if circuit_config:
        return {
            "braking_pre_m": float(yaml_offsets["braking_pre_m"]),
            "apex_pre_m": float(yaml_offsets["apex_pre_m"]),
            "apex_post_m": float(yaml_offsets["apex_post_m"]),
            "exit_post_m": float(yaml_offsets["exit_post_m"]),
        }
    return {
        "braking_pre_m": 350.0,
        "apex_pre_m": 60.0,
        "apex_post_m": 60.0,
        "exit_post_m": 250.0,
    }


def zones_before_clip(
    corners: pd.DataFrame,
    event_name: Optional[str],
    circuit_config: Optional[Dict[str, Any]],
    track_length: Optional[float],
    selected_corners: Optional[Sequence[int]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Arma las ZOI con la misma rama que el extractor, sin clip ni fusión."""
    cfg = circuit_config or {}
    offsets = pipeline_offsets(cfg)
    benchmark = _match_benchmark_circuit(cfg, event_name)
    rows = corners
    if benchmark and (benchmark.get("key_corners") or {}):
        if selected_corners is not None and "Number" in rows.columns:
            rows = rows[rows["Number"].isin(list(selected_corners))]
        return _zones_from_key_corners(rows, benchmark, cfg, offsets, track_length)
    return _zones_from_speed_threshold_fallback(
        rows, offsets, track_length, selected_corners=selected_corners
    )


def zones_before_and_after(
    corners: pd.DataFrame,
    event_name: Optional[str],
    circuit_config: Optional[Dict[str, Any]],
    track_length: Optional[float],
    selected_corners: Optional[Sequence[int]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    before = zones_before_clip(
        corners, event_name, circuit_config, track_length, selected_corners
    )
    copied = {key: dict(zone) for key, zone in before.items()}
    after = clip_and_merge_zones(copied, track_length)
    return before, after


def count_merges(n_before: int, n_after: int) -> int:
    """Zonas que ``clip_and_merge_zones`` absorbe. El recorte no borra zonas."""
    before = int(n_before)
    after = int(n_after)
    if after > before:
        raise ValueError(f"clip aumentó las zonas: {before} -> {after}")
    return before - after


def _span(zone: Dict[str, Any], track_length: Optional[float]) -> Tuple[float, float]:
    return _linear_interval(float(zone["braking"][0]), float(zone["exit"][1]), track_length)


def consecutive_overlap_pairs(
    zones: Dict[str, Dict[str, Any]],
    track_length: Optional[float],
) -> List[Dict[str, Any]]:
    """Pares consecutivos, en orden de ápice, cuyo tramo frenada→salida se cruza.

    Incluye el par que cruza la meta cuando hay largo de pista. ``apex_overlap``
    es el caso que ``clip_and_merge_zones`` fusiona.
    """
    items = sorted(
        zones.items(),
        key=lambda kv: (float(kv[1].get("apex_distance", 0.0)), str(kv[0])),
    )
    n = len(items)
    if n < 2:
        return []
    if track_length is not None and track_length > 0:
        seq = [(i, (i + 1) % n, (i + 1) % n == 0) for i in range(n)]
    else:
        seq = [(i, i + 1, False) for i in range(n - 1)]
    pairs: List[Dict[str, Any]] = []
    for i, j, wrapped in seq:
        name_a, za = items[i]
        name_b, zb = items[j]
        a0, a1 = _span(za, track_length)
        b0, b1 = _span(zb, track_length)
        if wrapped and track_length is not None and track_length > 0 and b0 < a0:
            b0 += float(track_length)
            b1 += float(track_length)
        span_overlap = bool((a0 < b1) and (b0 < a1))
        apex_overlap = bool(_apex_windows_overlap(za, zb, track_length))
        if span_overlap or apex_overlap:
            pairs.append(
                {
                    "zone_a": name_a,
                    "zone_b": name_b,
                    "wrapped": bool(wrapped),
                    "span_overlap": span_overlap,
                    "apex_overlap": apex_overlap,
                }
            )
    return pairs


def last_brake_application(fragment: pd.DataFrame) -> Dict[str, Any]:
    """Última aplicación de freno dentro del fragmento.

    Si el fragmento arranca con el freno puesto y no hay un 0→1 posterior, el
    inicio está en el borde de la ventana extendida o antes: ``censored``.
    """
    empty = {
        "has_samples": False,
        "has_onset": False,
        "censored": False,
        "onset_distance": None,
        "entry_speed": None,
        "pos": None,
    }
    if fragment is None or fragment.empty or "Distance" not in fragment.columns:
        return empty
    distances = fragment["Distance"].to_numpy(dtype=float)
    if "Brake" not in fragment.columns:
        brakes = np.zeros(len(fragment), dtype=bool)
    else:
        brakes = is_brake_on(fragment["Brake"]).to_numpy(dtype=bool)
    speeds = (
        fragment["Speed"].to_numpy(dtype=float)
        if "Speed" in fragment.columns
        else np.full(len(fragment), np.nan)
    )
    if not brakes.any():
        return {
            "has_samples": True,
            "has_onset": False,
            "censored": False,
            "onset_distance": None,
            "entry_speed": float(speeds[0]) if np.isfinite(speeds[0]) else None,
            "pos": None,
        }
    real = [
        i
        for i in range(len(brakes))
        if brakes[i] and i > 0 and not brakes[i - 1]
    ]
    if real:
        pos = int(real[-1])
        speed = float(speeds[pos]) if np.isfinite(speeds[pos]) else None
        return {
            "has_samples": True,
            "has_onset": True,
            "censored": False,
            "onset_distance": float(distances[pos]),
            "entry_speed": speed,
            "pos": pos,
        }
    speed0 = float(speeds[0]) if np.isfinite(speeds[0]) else None
    return {
        "has_samples": True,
        "has_onset": True,
        "censored": True,
        "onset_distance": float(distances[0]),
        "entry_speed": speed0,
        "pos": 0,
    }


def classify_onset_position(
    onset_distance: float,
    *,
    censored: bool,
    window_start: float,
    apex: float,
    previous_apex: Optional[float],
    track_length: Optional[float],
    edge_tol_m: float = EDGE_TOL_M,
) -> Dict[str, Any]:
    """Clasifica un inicio contra la ventana de frenada configurada.

    ``fuera_corte``: el inicio de esta curva cae antes de la ventana.
    ``fuera_heredado``: el inicio cae antes del ápice de la zona anterior
    (el freno que se ve es de la curva previa, o no hubo suelta).
    ``borde``: el inicio está a ``edge_tol_m`` o menos del arranque.
    ``adentro``: el resto.
    """
    metres = float(along_track_delta(apex, onset_distance, track_length))
    dist_from_start = float(along_track_delta(onset_distance, window_start, track_length))
    gap_prev = None
    if previous_apex is not None and np.isfinite(previous_apex):
        gap_prev = float(along_track_delta(apex, float(previous_apex), track_length))
    heredado = gap_prev is not None and metres > gap_prev + 1.0
    if heredado:
        status = "fuera_heredado"
    elif dist_from_start < -1e-6:
        status = "fuera_corte"
    elif dist_from_start <= float(edge_tol_m):
        status = "borde"
    else:
        status = "adentro"
    return {
        "status": status,
        "censored": bool(censored),
        "metres_before_apex": metres,
        "dist_from_start": dist_from_start,
        "gap_to_previous_apex": gap_prev,
    }


def _previous_apex_map(zones: Dict[str, Dict[str, Any]]) -> Dict[str, Optional[float]]:
    items = sorted(
        zones.items(),
        key=lambda kv: (float(kv[1].get("apex_distance", 0.0)), str(kv[0])),
    )
    out: Dict[str, Optional[float]] = {}
    if not items:
        return out
    for i, (name, _zone) in enumerate(items):
        prev = items[i - 1][1] if len(items) > 1 else None
        if prev is None:
            out[name] = None
        else:
            out[name] = float(prev.get("apex_distance_last", prev.get("apex_distance")))
    return out


def _fixed_braking_fragment(
    telemetry: pd.DataFrame,
    apex: float,
    apex_window_start: float,
    pre_m: float,
    track_length: Optional[float],
) -> Tuple[pd.DataFrame, float]:
    from f1_style_clustering.features.zoi import _wrap

    start = _wrap(float(apex) - float(pre_m), track_length)
    fragment = _slice_window(
        telemetry,
        start,
        float(apex_window_start),
        track_length,
        start_inclusive=True,
        end_inclusive=False,
    )
    return fragment, float(start)


def _nearest_speed(telemetry: pd.DataFrame, distance: float, track_length: Optional[float]) -> float:
    if telemetry is None or telemetry.empty or "Speed" not in telemetry.columns:
        return float("nan")
    dist = telemetry["Distance"].to_numpy(dtype=float)
    if track_length and track_length > 0:
        delta = np.abs((dist - distance + track_length / 2.0) % track_length - track_length / 2.0)
    else:
        delta = np.abs(dist - distance)
    pos = int(np.nanargmin(delta))
    speed = telemetry["Speed"].iloc[pos]
    return float(speed) if pd.notna(speed) else float("nan")


def _gear_at_min_speed(fragment: pd.DataFrame) -> float:
    if fragment is None or fragment.empty or "Speed" not in fragment.columns:
        return float("nan")
    if "nGear" not in fragment.columns:
        return float("nan")
    valid = fragment["Speed"].replace([np.inf, -np.inf], np.nan).dropna()
    if valid.empty:
        return float("nan")
    gear = fragment.loc[valid.idxmin(), "nGear"]
    return float(gear) if pd.notna(gear) else float("nan")


def _accumulate(bucket: Dict[str, list], key: str, value: Any) -> None:
    bucket.setdefault(key, []).append(value)


def iter_session_telemetry(
    session: Any,
    *,
    push_mode: bool = False,
    min_valid_laps: int = 3,
):
    """Telemetría canónica, una por vuelta, como la arma el pipeline."""
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
            if telemetry is None or telemetry.empty or "Distance" not in telemetry.columns:
                continue
            yield abbr, telemetry


def scan_telemetry(
    session: Any,
    zones_after: Dict[str, Dict[str, Any]],
    corners: pd.DataFrame,
    *,
    track_length: Optional[float],
    extended_m: float = EXTENDED_PRE_M,
    push_mode: bool = False,
    min_valid_laps: int = 3,
    apex_pre_m: float = 60.0,
    exit_post_m: float = 250.0,
    frames: Optional[Iterable[Tuple[str, pd.DataFrame]]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Una fila por zona del pipeline y una por curva FastF1, agregadas."""
    from f1_style_clustering.features.zoi import _wrap

    zone_lists: Dict[str, Dict[str, list]] = {name: {} for name in zones_after}
    prev_apex = _previous_apex_map(zones_after)
    corner_rows = []
    if corners is not None and not corners.empty and "Number" in corners.columns:
        ordered = corners.sort_values("Distance")
        numbers = [int(n) for n in ordered["Number"].tolist()]
        distances = [float(d) for d in ordered["Distance"].tolist()]
        letters = (
            ordered["Letter"].astype(str).tolist()
            if "Letter" in ordered.columns
            else [""] * len(numbers)
        )
        angles = (
            ordered["Angle"].tolist() if "Angle" in ordered.columns else [np.nan] * len(numbers)
        )
    else:
        numbers, distances, letters, angles = [], [], [], []
    corner_lists: Dict[int, Dict[str, list]] = {n: {} for n in numbers}
    prev_corner_apex = {}
    for i, number in enumerate(numbers):
        prev_corner_apex[number] = distances[i - 1] if len(numbers) > 1 else None

    if frames is None:
        frames = iter_session_telemetry(
            session, push_mode=push_mode, min_valid_laps=min_valid_laps
        )
    for _abbr, telemetry in frames:
        if telemetry is None or telemetry.empty or "Distance" not in telemetry.columns:
            continue
        for zone_name, zone in zones_after.items():
            track = zone.get("track_length", track_length)
            apex = float(zone["apex_distance"])
            window_start = float(zone["braking"][0])
            apex_start = float(zone["apex"][0])
            try:
                pipe_frag = _slice_window(
                    telemetry,
                    window_start,
                    apex_start,
                    track,
                    start_inclusive=True,
                    end_inclusive=False,
                )
                legacy_pipe = classify_onset(pipe_frag, window_start, track)
                fixed_frag, fixed_start = _fixed_braking_fragment(
                    telemetry, apex, apex_start, 350.0, track
                )
                legacy_350 = classify_onset(fixed_frag, fixed_start, track)
                ext_frag, ext_start = _fixed_braking_fragment(
                    telemetry, apex, apex_start, extended_m, track
                )
            except Exception:
                continue
            app = last_brake_application(ext_frag)
            slot = zone_lists[zone_name]
            _accumulate(slot, "fragment", 1)
            if legacy_pipe and legacy_pipe.get("has_onset"):
                _accumulate(slot, "pipe_onset", 1)
                _accumulate(slot, "pipe_edge", int(bool(legacy_pipe.get("edge"))))
            elif legacy_pipe is not None:
                _accumulate(slot, "pipe_onset", 0)
            if legacy_350 and legacy_350.get("has_onset"):
                _accumulate(slot, "m350_onset", 1)
                _accumulate(slot, "m350_edge", int(bool(legacy_350.get("edge"))))
            elif legacy_350 is not None:
                _accumulate(slot, "m350_onset", 0)
            if not app["has_onset"] or app["onset_distance"] is None:
                _accumulate(slot, "status", "sin_frenada")
                continue
            classified = classify_onset_position(
                float(app["onset_distance"]),
                censored=bool(app["censored"]),
                window_start=window_start,
                apex=apex,
                previous_apex=prev_apex.get(zone_name),
                track_length=track,
            )
            _accumulate(slot, "status", classified["status"])
            _accumulate(slot, "censored", int(bool(app["censored"])))
            usable = (not app["censored"]) and classified["status"] in {
                "fuera_corte",
                "borde",
                "adentro",
            }
            if usable:
                _accumulate(slot, "metres", classified["metres_before_apex"])
            if app["entry_speed"] is not None and usable:
                _accumulate(slot, "entry_speed", app["entry_speed"])
            _ = ext_start

        for i, number in enumerate(numbers):
            apex = distances[i]
            track = track_length
            apex_start = _wrap(apex - apex_pre_m, track)
            try:
                apex_frag = _slice_window(
                    telemetry,
                    apex_start,
                    _wrap(apex + apex_pre_m, track),
                    track,
                    start_inclusive=True,
                    end_inclusive=True,
                )
                exit_frag = _slice_window(
                    telemetry,
                    _wrap(apex + apex_pre_m, track),
                    _wrap(apex + exit_post_m, track),
                    track,
                    start_inclusive=False,
                    end_inclusive=True,
                )
                ext_frag, _ext_start = _fixed_braking_fragment(
                    telemetry, apex, apex_start, extended_m, track
                )
            except Exception:
                continue
            slot = corner_lists[number]
            if apex_frag is not None and not apex_frag.empty and "Speed" in apex_frag.columns:
                speed = pd.to_numeric(apex_frag["Speed"], errors="coerce")
                if speed.notna().any():
                    _accumulate(slot, "apex_speed", float(speed.min()))
                gear = _gear_at_min_speed(apex_frag)
                if np.isfinite(gear):
                    _accumulate(slot, "gear", gear)
            if exit_frag is not None and not exit_frag.empty and "Speed" in exit_frag.columns:
                exit_speed = pd.to_numeric(exit_frag["Speed"], errors="coerce").dropna()
                if not exit_speed.empty:
                    _accumulate(slot, "exit_speed", float(exit_speed.iloc[-1]))
            app = last_brake_application(ext_frag)
            if not app["has_onset"] or app["onset_distance"] is None:
                continue
            classified = classify_onset_position(
                float(app["onset_distance"]),
                censored=bool(app["censored"]),
                window_start=_wrap(apex - 350.0, track),
                apex=apex,
                previous_apex=prev_corner_apex.get(number),
                track_length=track,
            )
            if (not app["censored"]) and classified["status"] != "fuera_heredado":
                _accumulate(slot, "metres", classified["metres_before_apex"])
                if app["entry_speed"] is not None:
                    _accumulate(slot, "entry_speed", app["entry_speed"])

    zone_table = _summarize_zones(zone_lists, zones_after, track_length)
    for i, number in enumerate(numbers):
        slot = corner_lists[number]
        metres = np.asarray(slot.get("metres", []), dtype=float)
        corner_rows.append(
            {
                "corner_number": number,
                "letter": letters[i],
                "distance_m": distances[i],
                "angle": angles[i],
                "n_apex_speed": len(slot.get("apex_speed", [])),
                "median_apex_speed": _median(slot.get("apex_speed", [])),
                "median_entry_speed": _median(slot.get("entry_speed", [])),
                "median_exit_speed": _median(slot.get("exit_speed", [])),
                "median_gear": _median(slot.get("gear", [])),
                "n_onsets_this_corner": int(len(metres)),
                "p50_brake_m": _percentile(metres, 50),
                "p95_brake_m": _percentile(metres, 95),
            }
        )
    return zone_table, pd.DataFrame(corner_rows)


def _median(values: Sequence[float]) -> float:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    return float(np.median(arr))


def _percentile(values: np.ndarray, q: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return float("nan")
    return float(np.percentile(arr, q))


def _frac(part: int, total: int) -> float:
    if total <= 0:
        return float("nan")
    return float(part) / float(total)


def _summarize_zones(
    zone_lists: Dict[str, Dict[str, list]],
    zones_after: Dict[str, Dict[str, Any]],
    track_length: Optional[float],
) -> pd.DataFrame:
    rows = []
    for name, zone in zones_after.items():
        slot = zone_lists.get(name, {})
        status = list(slot.get("status", []))
        n_fragments = int(len(slot.get("fragment", [])))
        n_onsets = sum(1 for s in status if s != "sin_frenada")
        n_borde = sum(1 for s in status if s == "borde")
        n_corte = sum(1 for s in status if s == "fuera_corte")
        n_heredado = sum(1 for s in status if s == "fuera_heredado")
        n_adentro = sum(1 for s in status if s == "adentro")
        n_censored = int(np.sum(slot.get("censored", []))) if slot.get("censored") else 0
        metres = np.asarray(slot.get("metres", []), dtype=float)
        pipe_flags = [v for v in slot.get("pipe_onset", []) if v == 1 or v == 0]
        # pipe_onset stores 1/0 only when classify returned a record; edges align with onsets
        pipe_onsets_idx = [i for i, v in enumerate(slot.get("pipe_onset", [])) if v == 1]
        pipe_edges = slot.get("pipe_edge", [])
        m350_edges = slot.get("m350_edge", [])
        n_pipe = len(pipe_edges)
        n_350 = len(m350_edges)
        brake_len = float(
            along_track_delta(float(zone["braking"][1]), float(zone["braking"][0]), track_length)
        )
        rows.append(
            {
                "zone": name,
                "corner_numbers": ",".join(str(n) for n in zone.get("corner_numbers") or []),
                "apex_distance": float(zone.get("apex_distance", np.nan)),
                "apex_distance_last": float(
                    zone.get("apex_distance_last", zone.get("apex_distance", np.nan))
                ),
                "braking_start": float(zone["braking"][0]),
                "braking_end": float(zone["braking"][1]),
                "effective_brake_m": brake_len,
                "n_fragments": n_fragments,
                "n_onsets": int(n_onsets),
                "n_adentro": int(n_adentro),
                "n_borde": int(n_borde),
                "n_fuera_corte": int(n_corte),
                "n_fuera_heredado": int(n_heredado),
                "n_censored": int(n_censored),
                "frac_borde_o_fuera": _frac(n_borde + n_corte + n_heredado, n_onsets),
                "p50_before_apex": _percentile(metres, 50),
                "p95_before_apex": _percentile(metres, 95),
                "n_onsets_for_percentile": int(np.isfinite(metres).sum()) if metres.size else 0,
                "legacy_pipe_n_onsets": int(n_pipe),
                "legacy_pipe_n_edge": int(np.sum(pipe_edges)) if pipe_edges else 0,
                "legacy_pipe_frac": _frac(int(np.sum(pipe_edges)) if pipe_edges else 0, n_pipe),
                "legacy_350_n_onsets": int(n_350),
                "legacy_350_n_edge": int(np.sum(m350_edges)) if m350_edges else 0,
                "legacy_350_frac": _frac(int(np.sum(m350_edges)) if m350_edges else 0, n_350),
                "median_entry_speed": _median(slot.get("entry_speed", [])),
                "zone_source": zone.get("zone_source"),
                "typology": zone.get("typology"),
            }
        )
        _ = pipe_onsets_idx
        _ = pipe_flags
    return pd.DataFrame(rows)


def round_up_m(value: float, step: int = 10) -> int:
    return int(math.ceil((float(value) - 1e-9) / float(step)) * step)


def _forward_gap(later_apex: float, earlier_apex: float, track_length: float) -> float:
    gap = float(along_track_delta(later_apex, earlier_apex, track_length))
    if gap <= 0:
        gap += float(track_length)
    return gap


def propose_key_corners(
    corner_stats: pd.DataFrame,
    zone_stats: pd.DataFrame,
    *,
    track_length: float,
    n_overlap_pairs: int,
    n_merges: int,
    event_name: str,
    circuit_config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Propone ``key_corners`` solo si el diagnóstico muestra solape o recorte.

    Monza, Silverstone y Mónaco no se tocan. La regla, sobre la carrera R:

    - Se agrupan curvas cuyo ápice queda a menos de 120 m: el ±60 las fusionaría.
    - La frenada cubre el p95 de los inicios de *esta* curva (no heredados), más
      15 m, redondeado a 10 m, entre 80 m y 750 m. Con menos de 30 inicios
      útiles se deja 350 m.
    - Si casi nadie frena (<5 % de los fragmentos), la frenada baja a 120 m.
    - La salida arranca en 250 m y se acorta, hasta 80 m, para que frenada y
      salida consecutivas no se pisen. Si no entra, se acorta la frenada
      siguiente hasta su piso (el p95) y el resto queda como pendiente.
    - Si más de la mitad de los inicios están antes del ápice anterior, la
      frenada no pasa de 40 m después de ese ápice y queda anotado.
    """
    if event_name in PROTECTED_EVENTS:
        return None
    if zone_stats is None or zone_stats.empty:
        return None
    total_onsets = int(zone_stats["n_onsets"].sum())
    borde = int(
        zone_stats[["n_borde", "n_fuera_corte", "n_fuera_heredado"]].sum().sum()
    )
    frac = (borde / total_onsets) if total_onsets else 0.0
    justified = n_overlap_pairs > 0 or n_merges > 0 or (
        total_onsets >= MIN_ONSETS_FOR_WINDOW and frac >= JUSTIFY_FRAC
    )
    if not justified:
        return None
    if corner_stats is None or corner_stats.empty:
        return None

    stats = corner_stats.sort_values(["distance_m", "corner_number"]).reset_index(drop=True)
    # p95 por número, desde la curva suelta. La zona del pipeline puede estar agrupada;
    # para proponer se usa la curva FastF1.
    by_num = {int(r.corner_number): r for r in stats.itertuples(index=False)}
    numbers = [int(n) for n in stats["corner_number"].tolist()]
    distances = [float(d) for d in stats["distance_m"].tolist()]

    groups: List[List[int]] = []
    current = [numbers[0]]
    for idx in range(1, len(numbers)):
        gap = _forward_gap(distances[idx], distances[idx - 1], track_length)
        if gap < GROUP_GAP_M:
            current.append(numbers[idx])
        else:
            groups.append(current)
            current = [numbers[idx]]
    groups.append(current)
    if len(numbers) >= 2:
        wrap_gap = _forward_gap(distances[0], distances[-1], track_length)
        if wrap_gap < GROUP_GAP_M:
            notes_wrap = (
                f"T{numbers[-1]} y T{numbers[0]} quedan a {wrap_gap:.0f} m cruzando la meta; "
                "no se agrupan porque el ±60 sobre el mínimo y el máximo de distancia "
                "cubriría casi toda la vuelta. Queda pendiente."
            )
            # Se anota después de crear `notes`.
            groups.append({"__wrap_note__": notes_wrap})

    def _target_and_floor(first: int, gap_prev: float) -> Tuple[float, float, List[str]]:
        row = by_num[first]
        notes: List[str] = []
        n_pct = int(getattr(row, "n_onsets_this_corner", 0) or 0)
        p95 = getattr(row, "p95_brake_m", float("nan"))
        n_frag = int(getattr(row, "n_apex_speed", 0) or 0)
        onset_frac = (n_pct / n_frag) if n_frag else 0.0
        if n_frag >= MIN_ONSETS_FOR_WINDOW and onset_frac < FLAT_ONSET_FRAC:
            target = 120.0
            floor = 100.0
            notes.append(
                f"T{first}: casi sin frenada ({n_pct} inicios en {n_frag} fragmentos); ventana 120 m"
            )
            return target, floor, notes
        if n_pct >= MIN_ONSETS_FOR_WINDOW and np.isfinite(p95):
            target = float(min(MAX_BRAKE_M, max(MIN_BRAKE_M, round_up_m(p95 + P95_MARGIN_M))))
            floor = target
        else:
            target = 350.0
            floor = 350.0
            notes.append(f"T{first}: menos de {MIN_ONSETS_FOR_WINDOW} inicios útiles; se deja 350 m")
        # Heredado dominante: no alargar más allá del ápice anterior.
        heredado_share = _heredado_share(zone_stats, first)
        if heredado_share >= HEREDADO_DOMINANT and gap_prev > GROUP_GAP_M:
            cap = max(MIN_BRAKE_M, gap_prev - 40.0)
            if target > cap:
                target = float(round_up_m(cap)) if cap >= MIN_BRAKE_M else MIN_BRAKE_M
                floor = min(floor, target)
                notes.append(
                    f"T{first}: más de la mitad de los inicios caen antes del ápice anterior; "
                    f"la frenada queda en {int(target)} m y el caso sigue pendiente"
                )
        return target, floor, notes

    def _gap_before(group_index: int) -> float:
        first_num = groups[group_index][0]
        prev_group = groups[group_index - 1]
        prev_num = prev_group[-1]
        return _forward_gap(by_num[first_num].distance_m, by_num[prev_num].distance_m, track_length)

    prepared = []
    notes: List[str] = []
    wrap_notes = [g["__wrap_note__"] for g in groups if isinstance(g, dict)]
    groups = [g for g in groups if not isinstance(g, dict)]
    notes.extend(wrap_notes)
    for gidx, group in enumerate(groups):
        target, floor, group_notes = _target_and_floor(group[0], _gap_before(gidx))
        notes.extend(group_notes)
        speed = by_num[group[0]].median_apex_speed
        typology = None
        if np.isfinite(speed) and not _borderline_speed(float(speed)):
            typology = classify_speed_typology(float(speed), circuit_config)
        elif np.isfinite(speed):
            notes.append(
                f"T{group[0]}: velocidad de ápice {float(speed):.0f} km/h, a menos de "
                f"{BORDERLINE_KMH:.0f} km/h de un corte; el cubo queda para la sesión"
            )
        prepared.append(
            {
                "numbers": group,
                "brake": target,
                "floor": floor,
                "exit": 250.0,
                "typology": typology,
                "residual": 0.0,
            }
        )

    for i, group in enumerate(prepared):
        nxt = prepared[(i + 1) % len(prepared)]
        gap = _forward_gap(
            by_num[nxt["numbers"][0]].distance_m,
            by_num[group["numbers"][-1]].distance_m,
            track_length,
        )
        overflow = group["exit"] + nxt["brake"] - gap
        if overflow <= 1.0:
            continue
        exit_shrink = min(overflow, group["exit"] - MIN_EXIT_M)
        if exit_shrink > 0:
            group["exit"] -= exit_shrink
            overflow -= exit_shrink
        if overflow <= 1.0:
            continue
        brake_shrink = min(overflow, nxt["brake"] - nxt["floor"])
        if brake_shrink > 0:
            nxt["brake"] -= brake_shrink
            overflow -= brake_shrink
        if overflow > 1.0:
            nxt["residual"] = overflow
            notes.append(
                f"T{nxt['numbers'][0]}: quedan {overflow:.0f} m de solape con la zona anterior "
                "después de acortar salida y frenada hasta el piso"
            )

    key_corners: Dict[str, Dict[str, Any]] = {}
    for group in prepared:
        nums = group["numbers"]
        name = "_".join(f"T{n}" for n in nums)
        spec: Dict[str, Any] = {
            "corner_numbers": nums,
            "braking_distance_window": int(round(group["brake"])),
            "exit_distance_window": int(round(group["exit"])),
        }
        if group["typology"]:
            spec["typology"] = group["typology"]
        key_corners[name] = spec
    return {"key_corners": key_corners, "notes": notes}


def _borderline_speed(speed_kmh: float) -> bool:
    return min(abs(speed_kmh - 125.0), abs(speed_kmh - 205.0)) < BORDERLINE_KMH


def _heredado_share(zone_stats: pd.DataFrame, corner_number: int) -> float:
    if zone_stats is None or zone_stats.empty or "corner_numbers" not in zone_stats.columns:
        return 0.0
    shares = []
    for row in zone_stats.itertuples(index=False):
        nums = [int(p) for p in str(row.corner_numbers).split(",") if p]
        if corner_number not in nums:
            continue
        total = int(row.n_onsets)
        if total <= 0:
            continue
        shares.append(int(row.n_fuera_heredado) / total)
    if not shares:
        return 0.0
    return float(max(shares))


def circuit_summary_row(
    event_name: str,
    zone_stats: pd.DataFrame,
    n_before: int,
    n_after: int,
    pairs: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    n_onsets = int(zone_stats["n_onsets"].sum()) if not zone_stats.empty else 0
    n_borde = int(zone_stats["n_borde"].sum()) if not zone_stats.empty else 0
    n_corte = int(zone_stats["n_fuera_corte"].sum()) if not zone_stats.empty else 0
    n_heredado = int(zone_stats["n_fuera_heredado"].sum()) if not zone_stats.empty else 0
    n_350_on = int(zone_stats["legacy_350_n_onsets"].sum()) if not zone_stats.empty else 0
    n_350_edge = int(zone_stats["legacy_350_n_edge"].sum()) if not zone_stats.empty else 0
    n_pipe_on = int(zone_stats["legacy_pipe_n_onsets"].sum()) if not zone_stats.empty else 0
    n_pipe_edge = int(zone_stats["legacy_pipe_n_edge"].sum()) if not zone_stats.empty else 0
    return {
        "event": event_name,
        "n_zones_before": int(n_before),
        "n_zones_after": int(n_after),
        "n_overlap_pairs": int(len(pairs)),
        "n_apex_overlap_pairs": int(sum(1 for p in pairs if p["apex_overlap"])),
        "n_merges": count_merges(n_before, n_after),
        "n_onsets": n_onsets,
        "n_borde": n_borde,
        "n_fuera_corte": n_corte,
        "n_fuera_heredado": n_heredado,
        "frac_borde_o_fuera": _frac(n_borde + n_corte + n_heredado, n_onsets),
        "legacy_350_n_onsets": n_350_on,
        "legacy_350_n_edge": n_350_edge,
        "legacy_350_frac": _frac(n_350_edge, n_350_on),
        "legacy_pipe_n_onsets": n_pipe_on,
        "legacy_pipe_n_edge": n_pipe_edge,
        "legacy_pipe_frac": _frac(n_pipe_edge, n_pipe_on),
    }


def monza_reproduction(zone_stats: pd.DataFrame) -> Dict[str, Any]:
    """Contrasta la definición histórica (primer sample ya frenando) con lo publicado."""
    if zone_stats is None or zone_stats.empty:
        return {"coincide": False, "motivo": "sin zonas"}
    total_350_on = int(zone_stats["legacy_350_n_onsets"].sum())
    total_350_edge = int(zone_stats["legacy_350_n_edge"].sum())
    total_pipe_on = int(zone_stats["legacy_pipe_n_onsets"].sum())
    total_pipe_edge = int(zone_stats["legacy_pipe_n_edge"].sum())
    lesmo = zone_stats[zone_stats["zone"] == MONZA_PUBLISHED["lesmo2_zone"]]
    if lesmo.empty:
        lesmo_on = lesmo_edge = None
    else:
        lesmo_on = int(lesmo.iloc[0]["legacy_350_n_onsets"])
        lesmo_edge = int(lesmo.iloc[0]["legacy_350_n_edge"])
    published = MONZA_PUBLISHED
    checks = {
        "350_total": (total_350_on, total_350_edge, published["legacy_350_n_onsets"], published["legacy_350_n_edge"]),
        "pipeline_total": (
            total_pipe_on,
            total_pipe_edge,
            published["legacy_pipe_n_onsets"],
            published["legacy_pipe_n_edge"],
        ),
        "lesmo2_350": (
            lesmo_on,
            lesmo_edge,
            published["lesmo2_n_onsets"],
            published["lesmo2_n_edge"],
        ),
    }
    coincide = all(
        pair[0] == pair[2] and pair[1] == pair[3] for pair in checks.values()
    )
    return {
        "coincide": coincide,
        "medido": {
            "legacy_350_n_onsets": total_350_on,
            "legacy_350_n_edge": total_350_edge,
            "legacy_350_frac": _frac(total_350_edge, total_350_on),
            "lesmo2_n_onsets": lesmo_on,
            "lesmo2_n_edge": lesmo_edge,
            "legacy_pipe_n_onsets": total_pipe_on,
            "legacy_pipe_n_edge": total_pipe_edge,
            "legacy_pipe_frac": _frac(total_pipe_edge, total_pipe_on),
        },
        "publicado": {
            "legacy_350": f"{published['legacy_350_n_edge']}/{published['legacy_350_n_onsets']}",
            "lesmo2": f"{published['lesmo2_n_edge']}/{published['lesmo2_n_onsets']}",
            "pipeline": f"{published['legacy_pipe_n_edge']}/{published['legacy_pipe_n_onsets']}",
        },
    }


def render_circuit_yaml(entries: Sequence[Dict[str, Any]]) -> str:
    """Bloques YAML de circuitos nuevos. No incluye Monza, Silverstone ni Mónaco."""
    lines: List[str] = []
    for entry in entries:
        if entry.get("event_name") in PROTECTED_EVENTS:
            continue
        lines.append(f"  {entry['key']}:")
        lines.append(f"    official_name: \"{entry['official_name']}\"")
        lines.append(f"    event_name: \"{entry['event_name']}\"")
        lines.append("    key_corners:")
        for zone_name, spec in entry["key_corners"].items():
            nums = ", ".join(str(n) for n in spec["corner_numbers"])
            lines.append(f"      {zone_name}:")
            lines.append(f"        corner_numbers: [{nums}]")
            if spec.get("typology"):
                lines.append(f"        typology: \"{spec['typology']}\"")
            lines.append(
                f"        braking_distance_window: {int(spec['braking_distance_window'])}"
            )
            lines.append(f"        exit_distance_window: {int(spec['exit_distance_window'])}")
    return "\n".join(lines) + ("\n" if lines else "")


def canonical_archive_laps(laps: Dict[str, Any]) -> List[Tuple[int, float]]:
    """Vueltas que el export marca como el filtro canónico.

    ``iacc`` es IsAccurate, ``del`` es Deleted, ``status`` es TrackStatus y
    ``pin``/``pout`` son el ingreso y la salida de boxes. El archivo guarda el
    ausente como el string ``"None"``.
    """
    kept: List[Tuple[int, float]] = []
    n = len(laps.get("lap") or [])
    for i in range(n):
        if laps["iacc"][i] is not True:
            continue
        if laps["del"][i] is True:
            continue
        if str(laps["status"][i]) != "1":
            continue
        if laps["pin"][i] not in (None, "None"):
            continue
        if laps["pout"][i] not in (None, "None"):
            continue
        time = laps["time"][i]
        if time is None or not np.isfinite(float(time)):
            continue
        kept.append((int(laps["lap"][i]), float(time)))
    return kept


def _telemetry_frame(payload: Dict[str, Any]) -> Optional[pd.DataFrame]:
    tel = payload.get("tel") if isinstance(payload, dict) else None
    if not isinstance(tel, dict) or "distance" not in tel:
        return None
    return pd.DataFrame(
        {
            "Distance": tel["distance"],
            "Speed": tel.get("speed"),
            "Brake": tel.get("brake"),
            "nGear": tel.get("gear"),
            "Throttle": tel.get("throttle"),
        }
    )


def load_archive_corners(race_dir: Path) -> pd.DataFrame:
    raw = json.loads((race_dir / "corners.json").read_text(encoding="utf-8"))
    frame = pd.DataFrame(
        {
            "Number": raw["CornerNumber"],
            "Distance": raw["Distance"],
            "Angle": raw.get("Angle"),
            "X": raw.get("X"),
            "Y": raw.get("Y"),
        }
    )
    return frame.sort_values("Distance").reset_index(drop=True)


def archive_event_names(archive_root: Path) -> List[str]:
    names = []
    for child in sorted(archive_root.iterdir()):
        if (child / "Race" / "corners.json").is_file():
            names.append(child.name)
    return names


def _archive_selection(
    event_name: str,
    circuit_config: Dict[str, Any],
) -> Tuple[Optional[List[int]], str]:
    benchmark = _match_benchmark_circuit(circuit_config, event_name)
    if not benchmark or not (benchmark.get("key_corners") or {}):
        return None, ZONE_SOURCE_SPEED_FALLBACK
    numbers = key_corner_numbers(benchmark)
    return (numbers or None), ZONE_SOURCE_KEY_CORNERS


def iter_archive_frames(
    race_dir: Path,
    *,
    min_valid_laps: int = 3,
) -> Tuple[float, List[Tuple[str, int, float]], Iterable[Tuple[str, pd.DataFrame]]]:
    """Largo de pista, vueltas elegidas y un generador de telemetría.

    El largo es la distancia máxima de la vuelta canónica más rápida, el análogo
    de ``infer_track_length`` cuando la telemetría ya está cargada.
    """
    chosen: List[Tuple[str, int, float]] = []
    for driver_dir in sorted(p for p in race_dir.iterdir() if p.is_dir()):
        lap_path = driver_dir / "laptimes.json"
        if not lap_path.is_file():
            continue
        laps = json.loads(lap_path.read_text(encoding="utf-8"))
        kept = canonical_archive_laps(laps)
        if min_valid_laps and len(kept) < int(min_valid_laps):
            continue
        abbr = driver_dir.name
        for lap_number, lap_time in kept:
            chosen.append((abbr, lap_number, lap_time))
    if not chosen:
        raise FileNotFoundError(f"sin vueltas canónicas en {race_dir}")
    fastest = min(chosen, key=lambda item: item[2])
    fastest_path = race_dir / fastest[0] / f"{fastest[1]}_tel.json"
    fastest_frame = _telemetry_frame(json.loads(fastest_path.read_text(encoding="utf-8")))
    if fastest_frame is None or fastest_frame.empty:
        raise FileNotFoundError(f"sin distancia en {fastest_path}")
    track_length = float(fastest_frame["Distance"].max())

    def _frames() -> Iterable[Tuple[str, pd.DataFrame]]:
        for abbr, lap_number, _lap_time in chosen:
            path = race_dir / abbr / f"{lap_number}_tel.json"
            if not path.is_file():
                continue
            frame = _telemetry_frame(json.loads(path.read_text(encoding="utf-8")))
            if frame is None or frame.empty or "Distance" not in frame.columns:
                continue
            yield abbr, frame

    return track_length, chosen, _frames()


def diagnose_archive(
    race_dir: Path,
    event_name: str,
    circuit_config: Dict[str, Any],
    *,
    min_valid_laps: int = 3,
    extended_m: float = EXTENDED_PRE_M,
) -> Dict[str, Any]:
    corners = load_archive_corners(race_dir)
    selected, source = _archive_selection(event_name, circuit_config)
    track_length, chosen, frames = iter_archive_frames(race_dir, min_valid_laps=min_valid_laps)
    before, after = zones_before_and_after(
        corners, event_name, circuit_config, track_length, selected
    )
    pairs = consecutive_overlap_pairs(before, track_length)
    zone_stats, corner_stats = scan_telemetry(
        None,
        after,
        corners,
        track_length=track_length,
        extended_m=extended_m,
        min_valid_laps=min_valid_laps,
        apex_pre_m=pipeline_offsets(circuit_config)["apex_pre_m"],
        exit_post_m=pipeline_offsets(circuit_config)["exit_post_m"],
        frames=frames,
    )
    zone_stats.insert(0, "event", event_name)
    corner_stats.insert(0, "event", event_name)
    corner_stats.insert(1, "track_length", track_length)
    summary = circuit_summary_row(event_name, zone_stats, len(before), len(after), pairs)
    summary["zone_source"] = source
    summary["track_length"] = track_length
    summary["n_laps"] = int(len(chosen))
    summary["n_fastf1_corners"] = int(corners["Number"].nunique()) if "Number" in corners.columns else 0
    pairs_df = pd.DataFrame(pairs)
    if not pairs_df.empty:
        pairs_df.insert(0, "event", event_name)
    return {
        "summary": summary,
        "zones": zone_stats,
        "corners": corner_stats,
        "pairs": pairs_df,
        "event_name": event_name,
    }


def diagnose_session(
    session: Any,
    circuit_config: Dict[str, Any],
    *,
    push_mode: bool = False,
    min_valid_laps: int = 3,
    extended_m: float = EXTENDED_PRE_M,
) -> Dict[str, Any]:
    event_name = session_event_name(session) or ""
    selected, source = resolve_selected_corners(session, circuit_config)
    corners = session.get_circuit_info().corners.copy()
    track_length = infer_track_length(session)
    before, after = zones_before_and_after(
        corners, event_name, circuit_config, track_length, selected
    )
    pairs = consecutive_overlap_pairs(before, track_length)
    zone_stats, corner_stats = scan_telemetry(
        session,
        after,
        corners,
        track_length=track_length,
        extended_m=extended_m,
        push_mode=push_mode,
        min_valid_laps=min_valid_laps,
        apex_pre_m=pipeline_offsets(circuit_config)["apex_pre_m"],
        exit_post_m=pipeline_offsets(circuit_config)["exit_post_m"],
    )
    zone_stats.insert(0, "event", event_name)
    corner_stats.insert(0, "event", event_name)
    corner_stats.insert(1, "track_length", track_length)
    summary = circuit_summary_row(event_name, zone_stats, len(before), len(after), pairs)
    summary["zone_source"] = source
    summary["track_length"] = track_length
    summary["n_fastf1_corners"] = int(corners["Number"].nunique()) if "Number" in corners.columns else 0
    pairs_df = pd.DataFrame(pairs)
    if not pairs_df.empty:
        pairs_df.insert(0, "event", event_name)
    return {
        "summary": summary,
        "zones": zone_stats,
        "corners": corner_stats,
        "pairs": pairs_df,
        "event_name": event_name,
    }


def _fmt_pct(value: Any) -> str:
    if value is None or not np.isfinite(float(value)):
        return ""
    return f"{100.0 * float(value):.2f}".replace(".", ",")


def write_informe(
    path: Path,
    summary: pd.DataFrame,
    zones: pd.DataFrame,
    *,
    label: str,
    fastf1_version: str,
    fuente: str = "",
) -> None:
    lines = [
        f"# Diagnóstico de ventanas ZOI, 2025 ({label})",
        "",
        f"FastF1 {fastf1_version}. Carrera (`R`), vueltas canónicas, piso de 3 vueltas por piloto. "
        "La ventana extendida de 800 m solo se usa para encontrar el inicio; no entra al pipeline.",
        "",
    ]
    if fuente:
        lines.extend([fuente, ""])
    lines.extend([
        "Un inicio es la última puesta de freno (0→1) dentro de esos 800 m antes del ápice. "
        "Queda **fuera por corte** si ese inicio está antes de la ventana de frenada que el pipeline "
        "usa después de `clip_and_merge_zones`, y después del ápice de la zona anterior. "
        "Queda **fuera heredado** si cae antes de ese ápice anterior. "
        "Queda **en el borde** si está a 5 m o menos del arranque de la ventana. "
        "El porcentaje de la tabla suma los tres, sobre los inicios.",
        "",
        "La columna histórica es la de `docs/vector_por_zona_monza_2025.md`: el primer sample de la "
        "ventana ya tiene el freno puesto. En 350 m es una ventana fija, no la del YAML de cada curva.",
        "",
        "| circuito | % borde o fuera | en borde | fuera por corte | fuera heredado | inicios | pares solapados | fusiones | % histórico 350 m | % histórico pipeline |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in summary.itertuples(index=False):
        lines.append(
            "| {event} | {pct} | {borde} | {corte} | {her} | {n} | {pairs} | {merges} | {h350} | {hpipe} |".format(
                event=row.event,
                pct=_fmt_pct(row.frac_borde_o_fuera),
                borde=int(row.n_borde),
                corte=int(row.n_fuera_corte),
                her=int(row.n_fuera_heredado),
                n=int(row.n_onsets),
                pairs=int(row.n_overlap_pairs),
                merges=int(row.n_merges),
                h350=_fmt_pct(row.legacy_350_frac),
                hpipe=_fmt_pct(row.legacy_pipe_frac),
            )
        )
    lines.extend(["", "## Monza, cifras publicadas", ""])
    monza_zones = zones[zones["event"] == "Italian Grand Prix"] if "event" in zones.columns else zones.iloc[0:0]
    if monza_zones.empty:
        lines.append("Esta corrida no incluye el Gran Premio de Italia.")
    else:
        rep = monza_reproduction(monza_zones)
        med = rep["medido"]
        verb = "coinciden" if rep["coincide"] else "no coinciden"
        lines.append(
            f"Las cifras publicadas y esta corrida **{verb}**."
        )
        lines.append("")
        lines.append(
            f"Publicado, ventana de 350 m: 261/5114 (5,10 %). "
            f"Medido: {med['legacy_350_n_edge']}/{med['legacy_350_n_onsets']} "
            f"({_fmt_pct(med['legacy_350_frac'])} %)."
        )
        lines.append(
            f"Publicado, Lesmo 2 en 350 m: 250/811. "
            f"Medido: {med['lesmo2_n_edge']}/{med['lesmo2_n_onsets']}."
        )
        lines.append(
            f"Publicado, ventanas del pipeline: 13/5074 (0,26 %). "
            f"Medido: {med['legacy_pipe_n_edge']}/{med['legacy_pipe_n_onsets']} "
            f"({_fmt_pct(med['legacy_pipe_frac'])} %)."
        )
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame is None or frame.empty:
        return
    write_header = not path.exists()
    frame.to_csv(path, mode="a", header=write_header, index=False)


ARCHIVE_FUENTE = (
    "Fuente de la telemetría: export de TracingInsights-Archive/2025, carrera R. "
    "Cada archivo `{vuelta}_tel.json` es `Lap.get_telemetry()` de FastF1 (canal del auto "
    "fusionado con la posición), no `get_car_data().add_distance()`, que es lo que usa el "
    "pipeline. `corners.json` trae la distancia FastF1 de cada número. "
    "El filtro replica pick_accurate, pick_wo_box, pick_not_deleted y track status igual a 1. "
    "livetiming.formula1.com respondió 401 en este entorno y el mirror de FastF1 respondió 404, "
    "así que estas cifras no tienen por qué cerrar al entero con las publicadas para Monza."
)


def run_archive(events: Iterable[str], archive_root: Path, out_dir: Path, *, label: str) -> None:
    import fastf1 as ff1

    circuits = load_circuit_config()
    filt = load_config().get("data_filtering") or {}
    min_laps = int(filt.get("min_valid_laps_per_driver", 3))
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"{label}_summary.csv"
    zones_path = out_dir / f"{label}_zones.csv"
    corners_path = out_dir / f"{label}_corners.csv"
    pairs_path = out_dir / f"{label}_overlaps.csv"
    for path in (summary_path, zones_path, corners_path, pairs_path):
        if path.exists():
            path.unlink()
    summaries = []
    zone_frames = []
    for event in events:
        race_dir = archive_root / event / "Race"
        print(f"[archivo] {event}", flush=True)
        result = diagnose_archive(race_dir, event, circuits, min_valid_laps=min_laps)
        summaries.append(result["summary"])
        zone_frames.append(result["zones"])
        _append_csv(summary_path, pd.DataFrame([result["summary"]]))
        _append_csv(zones_path, result["zones"])
        _append_csv(corners_path, result["corners"])
        _append_csv(pairs_path, result["pairs"])
        row = result["summary"]
        print(
            f"[listo] {event} laps={row['n_laps']} borde_o_fuera={row['frac_borde_o_fuera']:.4f} "
            f"solapes={row['n_overlap_pairs']} fusiones={row['n_merges']} "
            f"hist350={row['legacy_350_n_edge']}/{row['legacy_350_n_onsets']} "
            f"histpipe={row['legacy_pipe_n_edge']}/{row['legacy_pipe_n_onsets']}",
            flush=True,
        )
    summary = pd.DataFrame(summaries)
    zones = pd.concat(zone_frames, ignore_index=True) if zone_frames else pd.DataFrame()
    write_informe(
        out_dir / f"informe_{label}.md",
        summary,
        zones,
        label=label,
        fastf1_version=ff1.__version__,
        fuente=ARCHIVE_FUENTE,
    )


def run_events(events: Iterable[str], out_dir: Path, *, year: int, label: str) -> None:
    import fastf1 as ff1

    cfg = load_config()
    circuits = load_circuit_config()
    filt = cfg.get("data_filtering") or {}
    cache = enable_cache((cfg.get("general") or {}).get("cache_dir", "cache"))
    print(f"cache {cache}", flush=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"{label}_summary.csv"
    zones_path = out_dir / f"{label}_zones.csv"
    corners_path = out_dir / f"{label}_corners.csv"
    pairs_path = out_dir / f"{label}_overlaps.csv"
    for path in (summary_path, zones_path, corners_path, pairs_path):
        if path.exists():
            path.unlink()
    summaries = []
    zone_frames = []
    for event in events:
        print(f"[cargo] {year} {event}", flush=True)
        session = ff1.get_session(year, event, "R")
        session.load(telemetry=True, weather=False, messages=False)
        print(f"[mido] {event}", flush=True)
        result = diagnose_session(
            session,
            circuits,
            push_mode=bool(filt.get("push_mode", False)),
            min_valid_laps=int(filt.get("min_valid_laps_per_driver", 3)),
        )
        summaries.append(result["summary"])
        zone_frames.append(result["zones"])
        _append_csv(summary_path, pd.DataFrame([result["summary"]]))
        _append_csv(zones_path, result["zones"])
        _append_csv(corners_path, result["corners"])
        _append_csv(pairs_path, result["pairs"])
        row = result["summary"]
        print(
            f"[listo] {event} borde_o_fuera={row['frac_borde_o_fuera']:.4f} "
            f"solapes={row['n_overlap_pairs']} fusiones={row['n_merges']} "
            f"hist350={row['legacy_350_frac']:.4f}",
            flush=True,
        )
    summary = pd.DataFrame(summaries)
    zones = pd.concat(zone_frames, ignore_index=True) if zone_frames else pd.DataFrame()
    write_informe(
        out_dir / f"informe_{label}.md",
        summary,
        zones,
        label=label,
        fastf1_version=ff1.__version__,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--event", action="append", default=None, help="Nombre FastF1. Repetible.")
    parser.add_argument("--out", default=str(_ROOT / "docs" / "zoi_diagnostico_2025"))
    parser.add_argument("--label", default="baseline")
    parser.add_argument(
        "--archive",
        default=None,
        help="Raíz del export TracingInsights-Archive/2025, con una carpeta por evento.",
    )
    args = parser.parse_args()
    if args.archive:
        root = Path(args.archive)
        events = list(args.event) if args.event else archive_event_names(root)
        run_archive(events, root, Path(args.out), label=args.label)
        return
    if args.event:
        events = list(args.event)
    else:
        import fastf1 as ff1

        enable_cache(load_config().get("general", {}).get("cache_dir", "cache"))
        events = iter_race_event_names(args.year)
        _ = ff1.__version__
    run_events(events, Path(args.out), year=args.year, label=args.label)


if __name__ == "__main__":
    main()
