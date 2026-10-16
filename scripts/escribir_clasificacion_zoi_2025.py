#!/usr/bin/env python
"""Write docs/clasificacion_pilotos_zoi_2025.md from the measured race JSON files.

Reads only files this run already wrote. Does not refit the clusters.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from f1_style_clustering.config import load_config
from f1_style_clustering.season import archetype_by_race_table, season_modal_summary, season_stability

OUT = _ROOT / "docs" / "clasificacion_pilotos_zoi_2025"
DOC = _ROOT / "docs" / "clasificacion_pilotos_zoi_2025.md"
OLD_ARCH = _ROOT / "docs" / "season_2025" / "archetype_by_race.csv"
OLD_SUMMARY = _ROOT / "docs" / "season_2025" / "driver_summary.csv"

CALENDAR = [
    "Australian Grand Prix",
    "Chinese Grand Prix",
    "Japanese Grand Prix",
    "Bahrain Grand Prix",
    "Saudi Arabian Grand Prix",
    "Miami Grand Prix",
    "Emilia Romagna Grand Prix",
    "Monaco Grand Prix",
    "Spanish Grand Prix",
    "Canadian Grand Prix",
    "Austrian Grand Prix",
    "British Grand Prix",
    "Belgian Grand Prix",
    "Hungarian Grand Prix",
    "Dutch Grand Prix",
    "Italian Grand Prix",
    "Azerbaijan Grand Prix",
    "Singapore Grand Prix",
    "United States Grand Prix",
    "Mexico City Grand Prix",
    "São Paulo Grand Prix",
    "Las Vegas Grand Prix",
    "Qatar Grand Prix",
    "Abu Dhabi Grand Prix",
]

READ = {
    "confirmed": "se confirma",
    "contradicted": "se contradice",
    "no_evidence": "no hay evidencia",
}


def _num(value, digits: int = 3) -> str:
    if value is None or value == "":
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(number):
        return ""
    text = f"{number:.{digits}f}"
    return text


def _int(value) -> str:
    if value is None or value == "":
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(number):
        return ""
    return str(int(number))


def _pct(value) -> str:
    if value is None or value == "":
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(number):
        return ""
    return f"{number:.1f}"


def _pct_cell(record: dict) -> str:
    if not record:
        return ""
    n = record.get("n")
    text = _pct(record.get("percentile"))
    if text == "":
        return f"n={_int(n)}"
    if n != 50:
        return f"{text} (n={_int(n)})"
    return text


def _load_races() -> list:
    races = []
    for path in sorted((OUT / "races").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        races.append(payload)
    order = {name: index for index, name in enumerate(CALENDAR)}
    races.sort(key=lambda race: order.get(race.get("event"), 999))
    return races


def _profiles_frame(race: dict) -> pd.DataFrame:
    rows = (race.get("clustering") or {}).get("profiles") or []
    frame = pd.DataFrame(rows)
    if frame.empty or "Driver" not in frame.columns:
        return pd.DataFrame()
    frame = frame.drop_duplicates("Driver").set_index("Driver")
    return frame


def _structure(race: dict) -> bool:
    return bool((race.get("null") or {}).get("structure"))


def _gives_classes(race: dict) -> bool:
    return bool((race.get("clustering") or {}).get("gives_classes"))


def _summaries(races: list, conclusive_only: bool) -> dict:
    out = {}
    for race in races:
        if not _gives_classes(race):
            continue
        if conclusive_only and not _structure(race):
            continue
        frame = _profiles_frame(race)
        if frame.empty or "Archetype" not in frame.columns:
            continue
        out[race["event"]] = frame
    return out


def _modal_block(races: list, min_races: int, conclusive_only: bool):
    summaries = _summaries(races, conclusive_only)
    table = archetype_by_race_table(summaries)
    summary = season_modal_summary(table, summaries, min_races)
    stability = season_stability(table, summary) if not summary.empty else pd.DataFrame()
    return table, summary, stability


def _archetype_frequency(races: list) -> pd.DataFrame:
    rows = []
    for race in races:
        if not _gives_classes(race) or not _structure(race):
            continue
        frame = _profiles_frame(race)
        if frame.empty or "Archetype" not in frame.columns:
            continue
        for driver, row in frame.iterrows():
            rows.append({"event": race["event"], "Driver": driver, "Archetype": row["Archetype"]})
    if not rows:
        return pd.DataFrame(columns=["Archetype", "celdas", "pilotos"])
    frame = pd.DataFrame(rows)
    counted = (
        frame.groupby("Archetype")
        .agg(celdas=("Driver", "size"), pilotos=("Driver", "nunique"))
        .sort_values(["celdas", "Archetype"], ascending=[False, True])
        .reset_index()
    )
    return counted


def _extremes(races: list) -> pd.DataFrame:
    rows = []
    for race in races:
        profile = race.get("profile") or {}
        scores = pd.DataFrame(profile.get("profiles") or [])
        axes = {str(axis.get("component")): axis for axis in profile.get("axes") or []}
        intervals = pd.DataFrame(profile.get("loading_intervals") or [])
        if scores.empty or "component" not in scores.columns:
            continue
        for component, block in scores.groupby("component"):
            medians = pd.to_numeric(block["median"], errors="coerce")
            if medians.notna().sum() == 0:
                continue
            high = float(medians.max())
            low = float(medians.min())
            axis = axes.get(str(component), {})
            contains_zero = ""
            if not intervals.empty and {"feature", "component", "low", "high"}.issubset(intervals.columns):
                match = intervals[
                    (intervals["component"].astype(str) == str(component))
                    & (intervals["feature"].astype(str) == str(axis.get("feature")))
                ]
                if not match.empty:
                    lo = float(match.iloc[0]["low"])
                    hi = float(match.iloc[0]["high"])
                    contains_zero = "sí" if lo <= 0.0 <= hi else "no"
            if high == low:
                rows.append(
                    {
                        "carrera": race.get("name"),
                        "event": race.get("event"),
                        "piloto": "",
                        "componente": component,
                        "extremo": "sin rango",
                        "mediana": high,
                        "feature": axis.get("feature"),
                        "carga": axis.get("loading"),
                        "signo": axis.get("sign"),
                        "intervalo_carga_incluye_0": contains_zero,
                    }
                )
                continue
            for _, row in block.iterrows():
                value = float(row["median"]) if pd.notna(row["median"]) else None
                if value is None:
                    continue
                flags = []
                if value == high:
                    flags.append("máximo")
                if value == low:
                    flags.append("mínimo")
                for flag in flags:
                    rows.append(
                        {
                            "carrera": race.get("name"),
                            "event": race.get("event"),
                            "piloto": row.get("Driver"),
                            "componente": component,
                            "extremo": flag,
                            "mediana": value,
                            "bajo": row.get("low"),
                            "alto": row.get("high"),
                            "feature": axis.get("feature"),
                            "carga": axis.get("loading"),
                            "signo": axis.get("sign"),
                            "intervalo_carga_incluye_0": contains_zero,
                        }
                    )
    return pd.DataFrame(rows)


def _ari(races: list) -> pd.DataFrame:
    old = pd.read_csv(OLD_ARCH)
    old = old.set_index("Driver")
    rows = []
    for race in races:
        event = race.get("event")
        if event not in old.columns or not _gives_classes(race):
            if event not in old.columns and _gives_classes(race):
                note = "la tabla anterior no tiene esta carrera"
            elif event in old.columns and not _gives_classes(race):
                note = "esta corrida no da clases"
            else:
                note = "sin clase en las dos corridas"
            rows.append(
                {
                    "carrera": race.get("name"),
                    "event": event,
                    "n": 0,
                    "ari": None,
                    "estructura": _structure(race),
                    "nota": note,
                }
            )
            continue
        frame = _profiles_frame(race)
        if frame.empty or "Archetype" not in frame.columns:
            continue
        new = frame["Archetype"]
        previous = old[event]
        common = sorted(set(new.dropna().index).intersection(set(previous.dropna().index)))
        if len(common) < 2:
            rows.append(
                {
                    "carrera": race.get("name"),
                    "event": event,
                    "n": len(common),
                    "ari": None,
                    "estructura": _structure(race),
                    "nota": "menos de dos pilotos en común",
                }
            )
            continue
        score = float(adjusted_rand_score(previous.loc[common].astype(str), new.loc[common].astype(str)))
        rows.append(
            {
                "carrera": race.get("name"),
                "event": event,
                "n": len(common),
                "ari": score,
                "estructura": _structure(race),
                "nota": "etiquetas modales de piloto",
            }
        )
    return pd.DataFrame(rows)


def _sign_word(sign) -> str:
    try:
        value = int(sign)
    except (TypeError, ValueError):
        return ""
    if value > 0:
        return "positiva"
    if value < 0:
        return "negativa"
    return "cero"


def _interval_cell(block: dict) -> str:
    if not block:
        return ""
    low = _num(block.get("low"), 2)
    high = _num(block.get("high"), 2)
    if low == "" or high == "":
        return ""
    return f"{low} a {high}"


def _pair_reading(block: dict) -> str:
    role = block.get("reading")
    mechanical = block.get("mechanical_reading")
    left = block.get("left_driver")
    right = block.get("right_driver")
    if role == "exploratory":
        if mechanical == "confirmed":
            detail = f"los intervalos no se tocan y {left} queda por debajo de {right}"
        elif mechanical == "contradicted":
            detail = f"los intervalos no se tocan y {right} queda por debajo de {left}"
        else:
            detail = "los intervalos se tocan"
        return f"exploratorio; {detail}. No entra en el veredicto del baseline"
    return READ.get(role, role)


def _baseline_section(race: dict) -> list:
    baseline = race.get("baseline") or {}
    lines = ["## Predicciones a priori", ""]
    lines.append(
        "Las reglas son las de `docs/temporada_2025.md` y `evaluate_baseline`. "
        "La matriz es la de la carrera suelta de Monza: conserva `fast__brake_point_rel`. "
        "(a) es Hamilton por debajo de Leclerc en `slow__brake_point_rel`, dentro de cada compuesto, en aire limpio. "
        "(b) es Leclerc por debajo de Hamilton en la mediana de la suelta de Lesmo 1, Lesmo 2 y la Parabólica. "
        "Se confirma si los intervalos no se tocan y la dirección es esa. "
        "Se contradice si no se tocan y la dirección es la opuesta. "
        "Si se tocan, no hay evidencia. Norris contra Piastri es exploratorio."
    )
    lines.append("")
    if not baseline:
        lines.append("Esta corrida no dejó el bloque de predicciones.")
        lines.append("")
        return lines
    air = baseline.get("clean_air") or {}
    lines.append(
        f"Vueltas de la matriz suelta: {_int(baseline.get('n_laps_single_race'))}. "
        f"Aire limpio: {_int(air.get('n_clean'))}. "
        f"Sin aire limpio: {_int(air.get('n_not_clean'))}. "
        f"Sin onset en la zona slow: {_int(air.get('n_excluded_no_onset'))}. "
        f"Sin vuelta en el lookup: {_int(air.get('n_missing_lap'))}."
    )
    lines.append("")
    brake = baseline.get("brake_point") or {}
    lines.append("**(a)**")
    lines.append("")
    if brake.get("error"):
        lines.append(f"El cálculo devolvió `{brake['error']}`.")
        lines.append("")
    else:
        lines.append("| compuesto | piloto | n | mediana | intervalo |")
        lines.append("| --- | --- | ---: | ---: | --- |")
        for compound in brake.get("compounds") or []:
            for key in ("HAM_LEC", "NOR_PIA"):
                block = compound.get(key) or {}
                left = block.get("left") or {}
                right = block.get("right") or {}
                if not block:
                    continue
                lines.append(
                    f"| {compound.get('compound')} | {block.get('left_driver')} | {_int(left.get('n'))} | {_num(left.get('median'), 2)} | {_interval_cell(left)} |"
                )
                lines.append(
                    f"| {compound.get('compound')} | {block.get('right_driver')} | {_int(right.get('n'))} | {_num(right.get('median'), 2)} | {_interval_cell(right)} |"
                )
        lines.append("")
        for compound in brake.get("compounds") or []:
            for key, label in (("HAM_LEC", "el baseline"), ("NOR_PIA", "Norris contra Piastri")):
                block = compound.get(key)
                if not block:
                    continue
                lines.append(f"{compound.get('compound')}, {label}: {_pair_reading(block)}.")
        lines.append("")
    release = baseline.get("release") or {}
    lines.append("**(b)**")
    lines.append("")
    if release.get("missing_zones"):
        lines.append(f"Zonas ausentes: {', '.join(release['missing_zones'])}.")
        lines.append("")
    lines.append("| piloto | n con suelta | mediana | intervalo |")
    lines.append("| --- | ---: | ---: | --- |")
    for key in ("HAM_LEC", "NOR_PIA"):
        block = release.get(key) or {}
        left = block.get("left") or {}
        right = block.get("right") or {}
        if not block:
            continue
        lines.append(
            f"| {block.get('left_driver')} | {_int(left.get('n'))} | {_num(left.get('median'), 2)} | {_interval_cell(left)} |"
        )
        lines.append(
            f"| {block.get('right_driver')} | {_int(right.get('n'))} | {_num(right.get('median'), 2)} | {_interval_cell(right)} |"
        )
    lines.append("")
    for key, label in (("HAM_LEC", "el baseline"), ("NOR_PIA", "Norris contra Piastri")):
        block = release.get(key) or {}
        if not block:
            continue
        lines.append(f"{label}: {_pair_reading(block)}.")
    canonical = release.get("n_canonical_laps") or {}
    if canonical:
        bits = [f"{driver} {_int(canonical.get(driver))}" for driver in ("HAM", "LEC", "NOR", "PIA")]
        lines.append("Vueltas canónicas: " + ", ".join(bits) + ".")
    lines.append("")
    return lines


def _edge_section(race: dict) -> list:
    rows = race.get("monza_edges") or []
    lines = ["## Borde de ventana en Monza", ""]
    lines.append(
        "La cuenta usa `scan_brake_onsets` sobre `Lap.get_car_data().add_distance()`. "
        "`edge` es verdadero cuando la primera muestra de la ventana ya está frenando. "
        "El denominador es `n_onsets`, los inicios de frenada. "
        "`n_fragments` es el número de ventanas recorridas."
    )
    lines.append("")
    lines.append(
        "Las cifras ya publicadas, con otra fuente, quedan como referencia y no se recalculan aquí. "
        "`docs/vector_por_zona_monza_2025.md`: ventana de 350 m, 261/5114 (5.10 % de los inicios); "
        "Lesmo 2, 250/811. Ventanas del pipeline, 13/5074. "
        "`docs/zoi_diagnostico_2025/informe_despues.md`, con `get_telemetry()`: 506/5141 (9.84 %)."
    )
    lines.append("")
    if not rows:
        lines.append("Esta corrida no dejó la tabla de bordes.")
        lines.append("")
        return lines
    lines.append("| ventana | zona | fragmentos | inicios | borde | a 5 m | borde / inicios |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for row in rows:
        lines.append(
            f"| {row.get('window')} | {row.get('zone')} | {_int(row.get('n_fragments'))} | "
            f"{_int(row.get('n_onsets'))} | {_int(row.get('n_edge'))} | {_int(row.get('n_within_5m'))} | "
            f"{_num(row.get('edge_frac_of_onsets'), 4)} |"
        )
    lines.append("")
    alignment = race.get("alignment") or {}
    if alignment:
        lines.append(
            f"Reloj: {alignment.get('n_laps_aligned')} vueltas alineadas, "
            f"mediana del desfase absoluto {_num(alignment.get('offset_median_abs_s'), 6)} s, "
            f"máximo {_num(alignment.get('offset_max_abs_s'), 3)} s. "
            f"t0 `{alignment.get('t0')}`."
        )
        lines.append("")
    return lines


def build(races: list) -> str:
    config = load_config()
    min_races = int((config.get("general") or {}).get("min_races_season", 8))
    complete = [race for race in races if race.get("complete")]
    by_event = {race.get("event"): race for race in complete}
    missing = [event for event in CALENDAR if event not in by_event]
    if missing:
        raise SystemExit("faltan carreras: " + ", ".join(missing))

    table_all, summary_all, stability_all = _modal_block(complete, min_races, False)
    table_ok, summary_ok, stability_ok = _modal_block(complete, min_races, True)
    frequency = _archetype_frequency(complete)
    extremes = _extremes(complete)
    ari = _ari(complete)
    old_summary = pd.read_csv(OLD_SUMMARY)

    frequency.to_csv(OUT / "frecuencia_arquetipos.csv", index=False)
    extremes.to_csv(OUT / "extremos.csv", index=False)
    ari.to_csv(OUT / "ari_por_gp.csv", index=False)

    n_classes = sum(1 for race in complete if _gives_classes(race))
    n_structure = sum(1 for race in complete if _structure(race))
    n_inconclusive = sum(1 for race in complete if _gives_classes(race) and not _structure(race))
    cells_inconclusive = 0
    for race in complete:
        if _gives_classes(race) and not _structure(race):
            cells_inconclusive += len(_profiles_frame(race))

    lines = ["# Clasificación de pilotos 2025 con las ZOI por circuito", ""]
    lines.append(
        "Misma rama `feat/zoi-por-circuito`. No se cambió el vector, el RobustScaler, el PCA automático, "
        "la regla de k, el K-means ni los defaults. La matriz de temporada saca `fast__brake_point_rel` "
        "antes del `dropna`, que es `season.exclude_columns`. La carrera suelta de Monza la conserva."
    )
    lines.append("")
    lines.append(
        "La telemetría oficial de FastF1 no carga en este entorno: `livetiming.formula1.com` responde 401 "
        "y el mirror `livetiming-mirror.fastf1.dev` responde 404. "
        "Cada vuelta entra por el canal `car_data` de OpenF1, metido en una `Session` de FastF1, "
        "y la distancia sale de `Lap.get_car_data().add_distance()`. "
        "Las banderas de vuelta y las distancias de curva salen del archivo de Tracing Insights 2025 "
        "(`laptimes.json`, `corners.json`, `drivers.json`). No se leyó `tel.json` ni se llamó a `get_telemetry()`."
    )
    lines.append("")
    lines.append(
        "El archivo de zonas anterior es `config/circuits.yaml` en `26deacd^`: solo Italia, Gran Bretaña y Mónaco "
        "tienen `key_corners`. El archivo de esta rama tiene `key_corners` en el resto de los circuitos de 2025, "
        "salvo Hungría, que sigue en el fallback de 350 m / ±60 m / 250 m. "
        "Las ventanas de Monza, Silverstone y Mónaco no se reescribieron en ese cambio."
    )
    lines.append("")
    structure_verb = "supera" if n_structure == 1 else "superan"
    lines.append(
        f"De 24 grandes premios, {n_classes} dan clases. "
        f"{n_structure} {structure_verb} los tres nulos. "
        f"{n_inconclusive} dan clases y no superan los tres: esas clases quedan como no concluyentes. "
        f"Son {cells_inconclusive} celdas piloto × GP."
    )
    lines.append("")

    italian = by_event["Italian Grand Prix"]
    lines.extend(_edge_section(italian))

    lines.append("## Vueltas y columnas")
    lines.append("")
    lines.append(
        "`vueltas` es `n_after_driver_filter`. `columnas` son las de estilo que quedan en esa matriz. "
        "`dropna` es el número de vueltas que se fueron por un valor faltante. "
        "Antes es el yaml de `26deacd^`. Después es el yaml de esta rama. "
        "Las dos matrices ya tienen fuera `fast__brake_point_rel`."
    )
    lines.append("")
    lines.append(
        "| carrera | vueltas antes | columnas antes | dropna antes | fuente antes | "
        "vueltas después | columnas después | dropna después | fuente después | clases |"
    )
    lines.append("| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |")
    for event in CALENDAR:
        race = by_event[event]
        before = race.get("before") or {}
        after = race.get("after") or {}
        lines.append(
            f"| {race.get('name')} | {_int(before.get('n_laps'))} | {_int(before.get('n_columns'))} | "
            f"{_int(before.get('n_dropped'))} | {before.get('zone_source') or ''} | "
            f"{_int(after.get('n_laps'))} | {_int(after.get('n_columns'))} | "
            f"{_int(after.get('n_dropped'))} | {after.get('zone_source') or ''} | "
            f"{'sí' if _gives_classes(race) else 'no'} |"
        )
    lines.append("")
    changed_size = []
    for event in CALENDAR:
        race = by_event[event]
        before = race.get("before") or {}
        after = race.get("after") or {}
        bits = []
        if before.get("n_laps") != after.get("n_laps"):
            bits.append(f"vueltas {_int(before.get('n_laps'))} a {_int(after.get('n_laps'))}")
        if before.get("n_columns") != after.get("n_columns"):
            bits.append(f"columnas {_int(before.get('n_columns'))} a {_int(after.get('n_columns'))}")
        if bits:
            changed_size.append(f"{race.get('name')} ({', '.join(bits)})")
    if changed_size:
        lines.append("Cambia el tamaño de la matriz en " + "; ".join(changed_size) + ".")
        lines.append("")

    lines.append("## K-means y tres nulos")
    lines.append("")
    lines.append(
        "K-means++ con semilla 42 y `n_init` 20, k elegido por la regla del pipeline. "
        "Cada nulo tiene 50 réplicas. Las semillas son 42, 43 y 44. "
        "Hay estructura si la silueta real es estrictamente mayor que el percentil 95 de la permutación por columna, "
        "del nulo gaussiano y de la cópula gaussiana. "
        "El percentil es el porcentaje de réplicas finitas menores o iguales que la real. "
        "La columna de estructura usa `beats_p95`, no el redondeo del percentil. "
        "Una carrera que da clases y no supera los tres queda como no concluyente."
    )
    lines.append("")
    lines.append(
        "| carrera | vueltas | dropna | k | regla | silueta | permutación | gaussiano | cópula | "
        "supera los tres | lectura |"
    )
    lines.append("| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |")
    for event in CALENDAR:
        race = by_event[event]
        after = race.get("after") or {}
        clustering = race.get("clustering") or {}
        null = race.get("null") or {}
        nulls = null.get("nulls") or {}
        if _gives_classes(race) and _structure(race):
            reading = "concluyente"
        elif _gives_classes(race):
            reading = "no concluyente"
        else:
            reading = "sin clases"
        lines.append(
            f"| {race.get('name')} | {_int(after.get('n_laps'))} | {_int(after.get('n_dropped'))} | "
            f"{_int(clustering.get('k'))} | {clustering.get('k_rule') or ''} | "
            f"{_num(clustering.get('silhouette'), 3)} | "
            f"{_pct_cell(nulls.get('column_permutation') or {})} | "
            f"{_pct_cell(nulls.get('gaussian') or {})} | "
            f"{_pct_cell(nulls.get('gaussian_copula') or {})} | "
            f"{'sí' if _structure(race) else 'no'} | {reading} |"
        )
    lines.append("")
    lines.append(
        "La silueta de la tabla es la del pipeline, a tres decimales. "
        "El CSV `docs/clasificacion_pilotos_zoi_2025/por_gp.csv` guarda el valor completo, "
        "el Davies-Bouldin y los tres `beats_p95`. "
        "El percentil de la tabla va a un decimal. "
        "Si al lado figura `n`, es el número de réplicas finitas: las que no eligen k quedan fuera del percentil. "
        "`n=0` quiere decir que ninguna réplica de ese nulo eligió k, y esa carrera no lo supera."
    )
    lines.append("")
    lines.append(
        f"La frecuencia de cada arquetipo cuenta celdas piloto × GP solo en las carreras que superan los tres nulos. "
        f"Las {cells_inconclusive} celdas de carreras no concluyentes no entran en este conteo."
    )
    lines.append("")
    if frequency.empty:
        lines.append("Ninguna carrera supera los tres nulos, así que no hay un arquetipo de temporada que contar.")
        lines.append("")
    else:
        lines.append("| arquetipo | celdas | pilotos |")
        lines.append("| --- | ---: | ---: |")
        for _, row in frequency.iterrows():
            lines.append(f"| {row['Archetype']} | {_int(row['celdas'])} | {_int(row['pilotos'])} |")
        lines.append("")

    lines.append("## Tabla de pilotos")
    lines.append("")
    lines.append(
        f"La clase modal usa `season_modal_summary`, con piso `min_races_season: {min_races}`. "
        "La primera moda cuenta todas las carreras que dieron clases, igual que `docs/temporada_2025.md`. "
        "Esa moda no es una conclusión cuando las carreras que la forman no superan los tres nulos. "
        "La segunda moda cuenta solo las carreras que superan los tres. "
        "El acuerdo es la fracción de esas carreras cuyo nombre coincide con la moda. "
        "Los nombres salen de `name_classes_from_medians`. No se les pone el nombre de un piloto."
    )
    lines.append("")
    lines.append(
        "| piloto | nombre | equipo | carreras con clase | moda, todas las que dan clase | acuerdo | "
        "carreras concluyentes | moda, solo concluyentes | acuerdo concluyente |"
    )
    lines.append("| --- | --- | --- | ---: | --- | ---: | ---: | --- | ---: |")

    old_by_driver = old_summary.set_index("Driver")
    drivers = sorted(set(table_all.index).union(set(old_by_driver.index)))
    compare_rows = []
    for driver in drivers:
        frame = _profiles_frame_any(complete, driver)
        n_all = int(table_all.loc[driver].dropna().shape[0]) if driver in table_all.index else 0
        n_ok = int(table_ok.loc[driver].dropna().shape[0]) if not table_ok.empty and driver in table_ok.index else 0
        mode_all = ""
        agree_all = ""
        if not summary_all.empty and driver in summary_all.index:
            mode_all = str(summary_all.loc[driver, "Archetype"])
            if driver in stability_all.index:
                agree_all = _num(stability_all.loc[driver, "agreement"], 2)
        elif n_all:
            mode_all = f"no llega a {min_races}"
        mode_ok = ""
        agree_ok = ""
        if not summary_ok.empty and driver in summary_ok.index:
            mode_ok = str(summary_ok.loc[driver, "Archetype"])
            if driver in stability_ok.index:
                agree_ok = _num(stability_ok.loc[driver, "agreement"], 2)
        elif n_ok:
            mode_ok = f"no llega a {min_races}"
        full_name = ""
        team = ""
        if not summary_all.empty and driver in summary_all.index:
            full_name = "" if pd.isna(summary_all.loc[driver, "FullName"]) else str(summary_all.loc[driver, "FullName"])
            team = "" if pd.isna(summary_all.loc[driver, "Team"]) else str(summary_all.loc[driver, "Team"])
        full_name = full_name or str(frame.get("FullName") or "")
        team = team or str(frame.get("Team") or "")
        if driver in old_by_driver.index:
            full_name = full_name or str(old_by_driver.loc[driver, "FullName"])
            team = team or str(old_by_driver.loc[driver, "Team"])
        lines.append(
            f"| {driver} | {full_name} | {team} | {n_all} | {mode_all} | {agree_all} | {n_ok} | {mode_ok} | {agree_ok} |"
        )
        previous = ""
        if driver in old_by_driver.index:
            previous = str(old_by_driver.loc[driver, "Archetype"])
        compare_rows.append(
            {
                "piloto": driver,
                "modal_anterior": previous,
                "modal_esta_corrida": mode_all,
                "modal_concluyente": mode_ok,
                "n_con_clase": n_all,
                "n_concluyentes": n_ok,
            }
        )
    lines.append("")
    lines.append(
        "La clase de cada piloto en cada GP está en `docs/clasificacion_pilotos_zoi_2025/clases_modales.csv`. "
        "`n_laps` es el total de vueltas del piloto en esa matriz y `modal_fraction` es la proporción que cae en la clase modal. "
        "Abajo queda la misma tabla partida por carrera. "
        "En una carrera no concluyente el nombre se imprime y la lectura de la carrera es no concluyente."
    )
    lines.append("")
    for event in CALENDAR:
        race = by_event[event]
        if not _gives_classes(race):
            continue
        frame = _profiles_frame(race).reset_index()
        reading = "concluyente" if _structure(race) else "no concluyente"
        lines.append(f"### {race.get('name')}")
        lines.append("")
        lines.append(f"Lectura: {reading}.")
        lines.append("")
        lines.append("| piloto | clase | vueltas | proporción en la clase |")
        lines.append("| --- | --- | ---: | ---: |")
        frame = frame.sort_values("Driver")
        for _, row in frame.iterrows():
            lines.append(
                f"| {row.get('Driver')} | {row.get('Archetype')} | {_int(row.get('n_laps'))} | {_num(row.get('modal_fraction'), 3)} |"
            )
        lines.append("")

    lines.append("## Perfil continuo")
    lines.append("")
    lines.append(
        "El camino es el de `docs/perfil_continuo_2025.md`: análisis paralelo de 50 permutaciones de columna, "
        "200 bootstraps de cargas, 2000 bootstraps del perfil estratificados por compuesto, percentiles 2.5 y 97.5, "
        "semilla 42. El signo de cada eje deja positiva la carga de mayor valor absoluto. "
        "Un eje se describe por esa feature y por el signo de su carga. "
        "Los scores no se comparan entre grandes premios."
    )
    lines.append("")
    lines.append(
        "Dentro de un GP y de un componente retenido, un piloto está en el máximo si su mediana es la mayor de ese GP, "
        "y en el mínimo si es la menor. Un empate cuenta. "
        "Si la mediana máxima y la mínima son el mismo número, ese componente no tiene extremos."
    )
    lines.append("")
    lines.append(
        "Las medianas y los intervalos de cada piloto están en `docs/clasificacion_pilotos_zoi_2025/perfiles.csv`."
    )
    lines.append("")
    lines.append("| carrera | vueltas | features | componentes | varianza acumulada |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for event in CALENDAR:
        race = by_event[event]
        profile = race.get("profile") or {}
        lines.append(
            f"| {race.get('name')} | {_int(profile.get('n_laps'))} | {_int(profile.get('n_features'))} | "
            f"{_int(profile.get('n_components'))} | {_num(profile.get('cumulative_variance'), 3)} |"
        )
    lines.append("")
    lines.append("| carrera | componente | feature | carga | signo | el intervalo de la carga incluye el 0 |")
    lines.append("| --- | --- | --- | ---: | --- | --- |")
    for event in CALENDAR:
        race = by_event[event]
        profile = race.get("profile") or {}
        intervals = pd.DataFrame(profile.get("loading_intervals") or [])
        for axis in profile.get("axes") or []:
            contains = ""
            if not intervals.empty:
                match = intervals[
                    (intervals["component"].astype(str) == str(axis.get("component")))
                    & (intervals["feature"].astype(str) == str(axis.get("feature")))
                ]
                if not match.empty:
                    lo = float(match.iloc[0]["low"])
                    hi = float(match.iloc[0]["high"])
                    contains = "sí" if lo <= 0.0 <= hi else "no"
            lines.append(
                f"| {race.get('name')} | {axis.get('component')} | `{axis.get('feature')}` | "
                f"{_num(axis.get('loading'), 4)} | {_sign_word(axis.get('sign'))} | {contains} |"
            )
    lines.append("")
    lines.append("### Extremos por piloto")
    lines.append("")
    if extremes.empty:
        lines.append("No hay perfiles.")
        lines.append("")
    else:
        drivers_ext = sorted({driver for driver in extremes["piloto"].dropna().astype(str).unique() if driver})
        for driver in drivers_ext:
            own = extremes[extremes["piloto"] == driver]
            lines.append(f"**{driver}**")
            lines.append("")
            for _, row in own.sort_values(["carrera", "componente", "extremo"]).iterrows():
                lines.append(
                    f"- {row['carrera']}, {row['componente']}, {row['extremo']} del GP "
                    f"(mediana {_num(row['mediana'], 3)}, intervalo {_num(row.get('bajo'), 3)} a {_num(row.get('alto'), 3)}). "
                    f"La carga de mayor valor absoluto es `{row['feature']}` "
                    f"({_num(row['carga'], 4)}, {_sign_word(row['signo'])})."
                )
            lines.append("")
        flat = extremes[extremes["extremo"] == "sin rango"]
        if not flat.empty:
            lines.append("Componentes en los que todas las medianas coinciden:")
            lines.append("")
            for _, row in flat.iterrows():
                lines.append(
                    f"- {row['carrera']}, {row['componente']}, mediana {_num(row['mediana'], 3)}. "
                    f"La carga de mayor valor absoluto es `{row['feature']}` "
                    f"({_num(row['carga'], 4)}, {_sign_word(row['signo'])})."
                )
            lines.append("")

    lines.append("## Comparación con la corrida anterior")
    lines.append("")
    lines.append(
        "La corrida anterior está en `docs/temporada_2025.md`, `docs/season_2025/driver_summary.csv` "
        "y `docs/season_2025/archetype_by_race.csv`, y el perfil continuo en `docs/perfil_continuo_2025.md`. "
        "Esos archivos no se reescribieron. "
        "En esa corrida los 20 pilotos que llegan al piso de 8 carreras tienen la moda «No dominant trait»."
    )
    lines.append("")
    lines.append(
        "| piloto | moda anterior | moda de esta corrida, todas las que dan clase | moda solo en carreras concluyentes |"
    )
    lines.append("| --- | --- | --- | --- |")
    compare = pd.DataFrame(compare_rows)
    compare.to_csv(OUT / "comparacion_modal.csv", index=False)
    for _, row in compare.iterrows():
        lines.append(
            f"| {row['piloto']} | {row['modal_anterior']} | {row['modal_esta_corrida']} | {row['modal_concluyente']} |"
        )
    lines.append("")
    reached = compare["modal_esta_corrida"].astype(str).str.startswith("no llega").eq(False)
    changed = compare[
        compare["modal_anterior"].astype(str).ne("")
        & reached
        & compare["modal_esta_corrida"].astype(str).ne("")
        & compare["modal_anterior"].astype(str).ne(compare["modal_esta_corrida"].astype(str))
    ]
    lines.append(
        f"Pilotos que llegan al piso de {min_races} carreras con clase y cuya moda difiere de la anterior: {len(changed)}."
    )
    lines.append("")
    lines.append(
        "El ARI compara las dos particiones de pilotos, en la intersección de quienes tienen clase en las dos corridas. "
        "El texto del arquetipo solo dice quién comparte clase dentro de una corrida. "
        "Las etiquetas de cada vuelta de la corrida anterior no están versionadas: "
        "`results/2025/italian_grand_prix/driver_laps_by_class.csv` trae conteos, no la clase de cada vuelta. "
        "Por eso el ARI de esta tabla es de pilotos, no de vueltas."
    )
    lines.append("")
    lines.append("| carrera | pilotos en común | ARI | estructura en esta corrida | nota |")
    lines.append("| --- | ---: | ---: | --- | --- |")
    for _, row in ari.iterrows():
        lines.append(
            f"| {row['carrera']} | {_int(row['n'])} | {_num(row['ari'], 3)} | "
            f"{'sí' if row['estructura'] else 'no'} | {row['nota']} |"
        )
    lines.append("")
    defined = ari[pd.to_numeric(ari["ari"], errors="coerce").notna()]
    if not defined.empty:
        lines.append(
            f"ARI definido en {len(defined)} grandes premios. "
            f"Mediana {_num(float(defined['ari'].median()), 3)}. "
            f"Mínimo {_num(float(defined['ari'].min()), 3)}. "
            f"Máximo {_num(float(defined['ari'].max()), 3)}."
        )
        lines.append("")

    lines.extend(_baseline_section(italian))
    lines.append(
        "Tablas: `docs/clasificacion_pilotos_zoi_2025/por_gp.csv`, `clases_modales.csv`, `perfiles.csv`, "
        "`monza_bordes.csv`, `frecuencia_arquetipos.csv`, `extremos.csv`, `comparacion_modal.csv`, `ari_por_gp.csv`. "
        "El JSON de cada GP está en `docs/clasificacion_pilotos_zoi_2025/races/`."
    )
    lines.append("")
    return "\n".join(lines)


def _profiles_frame_any(races: list, driver: str) -> dict:
    for race in races:
        frame = _profiles_frame(race)
        if driver in frame.index:
            return frame.loc[driver].to_dict()
    return {}


def main() -> None:
    races = _load_races()
    text = build(races)
    DOC.write_text(text, encoding="utf-8")
    print(f"wrote {DOC}", flush=True)


if __name__ == "__main__":
    argparse.ArgumentParser().parse_args()
    main()
