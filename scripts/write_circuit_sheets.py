"""Arma las fichas de docs/circuitos_2025 a partir de las fuentes y del diagnóstico.

No inventa cifras. Lo que no está en la fuente queda vacío o marcado como
medido con FastF1.

    python scripts/write_circuit_sheets.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    "zoi_window_diagnostic",
    _ROOT / "scripts" / "zoi_window_diagnostic.py",
)
diag = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(diag)

from f1_style_clustering.config import load_circuit_config  # noqa: E402

DOCS = _ROOT / "docs" / "circuitos_2025"
DIAG = _ROOT / "docs" / "zoi_diagnostico_2025"

ORDER = [
    "australian",
    "chinese",
    "japanese",
    "bahrain",
    "saudi_arabian",
    "miami",
    "emilia_romagna",
    "monaco",
    "spanish",
    "canadian",
    "austrian",
    "silverstone",
    "belgian",
    "hungarian",
    "dutch",
    "monza",
    "azerbaijan",
    "singapore",
    "united_states",
    "mexico_city",
    "sao_paulo",
    "las_vegas",
    "qatar",
    "abu_dhabi",
]

TITLES = {
    "australian": "Australia, Albert Park",
    "chinese": "China, Shanghái",
    "japanese": "Japón, Suzuka",
    "bahrain": "Baréin, Sakhir",
    "saudi_arabian": "Arabia Saudita, Yeda",
    "miami": "Miami",
    "emilia_romagna": "Emilia-Romaña, Imola",
    "monaco": "Mónaco",
    "spanish": "España, Barcelona-Catalunya",
    "canadian": "Canadá, Gilles Villeneuve",
    "austrian": "Austria, Red Bull Ring",
    "silverstone": "Gran Bretaña, Silverstone",
    "belgian": "Bélgica, Spa-Francorchamps",
    "hungarian": "Hungría, Hungaroring",
    "dutch": "Países Bajos, Zandvoort",
    "monza": "Italia, Monza",
    "azerbaijan": "Azerbaiyán, Bakú",
    "singapore": "Singapur, Marina Bay",
    "united_states": "Estados Unidos, Austin",
    "mexico_city": "Ciudad de México",
    "sao_paulo": "San Pablo, Interlagos",
    "las_vegas": "Las Vegas",
    "qatar": "Catar, Lusail",
    "abu_dhabi": "Abu Dabi, Yas Marina",
}


def _fmt(value, digits: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if not np.isfinite(number):
        return ""
    return f"{number:.{digits}f}".replace(".", ",")


def _pct(value) -> str:
    text = _fmt(100.0 * float(value), 2) if value is not None and np.isfinite(float(value)) else ""
    return text


def _bucket(speed: float, circuits: dict) -> str:
    if not np.isfinite(speed):
        return ""
    if diag._borderline_speed(float(speed)):
        return "cerca del corte; no se fija"
    name = diag.classify_speed_typology(float(speed), circuits)
    return {"slow": "lenta", "medium": "media", "fast": "rápida"}.get(name, "")


def _row(summary: pd.DataFrame, event: str):
    if summary is None or summary.empty:
        return None
    part = summary[summary["event"] == event]
    if part.empty:
        return None
    return part.iloc[0]


SOURCE_OF = {"monza": "italian", "silverstone": "british"}


def _sheet(key: str, circuits: dict, brembo: dict, fia: dict, notes: dict, baseline, despues, corners) -> str:
    source_key = SOURCE_OF.get(key, key)
    spec = (circuits.get("benchmark_circuits") or {}).get(key)
    event = {
        "hungarian": "Hungarian Grand Prix",
    }.get(key)
    if spec is not None:
        event = spec["event_name"]
    if not event:
        raise SystemExit(f"falta {key} en circuits.yaml")
    title = TITLES[key]
    lines = [
        f"# {title}, 2025",
        "",
        f"Evento FastF1: `{event}`.",
        "",
        "La numeración de la tabla medida es la de FastF1 (`CornerNumber`). "
        "Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica "
        "acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del "
        "tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice "
        "de FastF1, y no se usa para fijar la ventana.",
        "",
        "Lo que no tiene fuente queda vacío o marcado como medido con FastF1.",
        "",
        "## Documentado",
        "",
        "### Largo y frenadas",
        "",
    ]
    info = brembo[source_key]
    if info.get("url"):
        lines.append(f"Fuente: {info['url']}")
        lines.append("")
    for paragraph in info["parrafos"]:
        lines.append(paragraph)
        lines.append("")
    lines.extend(["### Zonas DRS", ""])
    lines.append(
        "Las notas del director de carrera listan paneles de luz, no el metro de detección "
        "ni el de activación. No se completa ese metro."
    )
    lines.append("")
    lines.append(f"Fuente: {fia[source_key]['fia_url']}")
    lines.append("")
    for block in fia[source_key]["drs"]:
        lines.append(f"- {block['heading']}")
        for act in block["activations"]:
            lines.append(f"  - {act}")
    lines.append("")
    lines.extend(["### Cambios de trazado 2025", ""])
    lines.append(
        "Son los ítems de «Changes to the Circuit» en la misma nota. "
        "En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido."
    )
    lines.append("")
    if not fia[source_key]["changes"]:
        lines.append("La nota no lista cambios.")
    else:
        for change in fia[source_key]["changes"]:
            lines.append(f"- {change}")
    lines.extend(["", "## Medido con FastF1", ""])
    lines.append(
        "Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. "
        "La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` "
        "y `corners.json` de FastF1, no `get_car_data().add_distance()`. "
        "livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. "
        "La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, "
        "si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. "
        "La salida es la velocidad del último sample de los 250 m posteriores al ápice. "
        "La marcha es la mediana de la marcha en el mínimo de velocidad. "
        "El p50 y el p95 son metros de ese inicio antes del ápice. "
        "El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada."
    )
    lines.append("")
    part = corners[corners["event"] == event].sort_values(["distance_m", "corner_number"])
    if part.empty:
        lines.append("Todavía no hay medición de esta carrera.")
    else:
        track = float(part["track_length"].iloc[0])
        lines.append(f"Distancia máxima de la vuelta canónica más rápida: {_fmt(track, 1)} m. No es el largo oficial.")
        lines.append("")
        lines.append(
            "| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |"
        )
        lines.append("| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
        for row in part.itertuples(index=False):
            lines.append(
                "| {n} | {d} | {ent} | {ap} | {ex} | {g} | {p50} | {p95} | {b} |".format(
                    n=int(row.corner_number),
                    d=_fmt(row.distance_m, 1),
                    ent=_fmt(row.median_entry_speed, 0),
                    ap=_fmt(row.median_apex_speed, 0),
                    ex=_fmt(row.median_exit_speed, 0),
                    g=_fmt(row.median_gear, 0),
                    p50=_fmt(row.p50_brake_m, 0),
                    p95=_fmt(row.p95_brake_m, 0),
                    b=_bucket(float(row.median_apex_speed), circuits),
                )
            )
    lines.extend(["", "## Ventanas", ""])
    base = _row(baseline, event)
    after = _row(despues, event)
    if base is not None:
        lines.append(
            f"Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): "
            f"{_pct(base.frac_borde_o_fuera)} % de inicios en el borde o afuera "
            f"({int(base.n_borde)} en el borde, {int(base.n_fuera_corte)} por corte, "
            f"{int(base.n_fuera_heredado)} heredados, {int(base.n_onsets)} inicios). "
            f"Pares solapados: {int(base.n_overlap_pairs)}. Fusiones: {int(base.n_merges)}. "
            f"Definición histórica de 350 m: {_pct(base.legacy_350_frac)} %. "
            f"Definición histórica del pipeline: {_pct(base.legacy_pipe_frac)} %."
        )
        lines.append("")
    if after is not None:
        lines.append(
            f"Después de las ventanas de esta ficha: "
            f"{_pct(after.frac_borde_o_fuera)} % en el borde o afuera "
            f"({int(after.n_borde)} en el borde, {int(after.n_fuera_corte)} por corte, "
            f"{int(after.n_fuera_heredado)} heredados, {int(after.n_onsets)} inicios). "
            f"Pares solapados: {int(after.n_overlap_pairs)}. Fusiones: {int(after.n_merges)}."
        )
        lines.append("")
    if event in diag.PROTECTED_EVENTS:
        lines.append(
            "Monza, Silverstone y Mónaco no se reescribieron. La tabla de abajo es la que ya estaba."
        )
        lines.append("")
    elif spec is None:
        lines.append(
            "Este circuito sigue en el fallback de 350 m, ±60 m y 250 m. No entró a `key_corners`."
        )
        lines.append("")
    zones = ((spec or {}).get("key_corners") or {})
    if zones:
        lines.append("| zona | números | frenada (m) | salida (m) |")
        lines.append("| --- | --- | ---: | ---: |")
        for name, zone in zones.items():
            nums = ", ".join(str(n) for n in zone.get("corner_numbers") or [])
            brake = zone.get("braking_distance_window", "")
            exit_m = zone.get("exit_distance_window", "")
            lines.append(f"| {name} | {nums} | {brake} | {exit_m} |")
        lines.append("")
        lines.append(
            "Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos."
        )
        lines.append("")
    item_notes = notes.get(event) or []
    if item_notes:
        lines.append(
            "La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape."
        )
        lines.append("")
        lines.append("Notas de la propuesta, para revisar:")
        lines.append("")
        for note in item_notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    circuits = load_circuit_config()
    brembo = json.loads((DOCS / "fuentes_brembo.json").read_text(encoding="utf-8"))
    fia = json.loads((DOCS / "fuentes_fia.json").read_text(encoding="utf-8"))
    notes_path = DIAG / "propuesta_notas.json"
    notes = {}
    if notes_path.exists():
        for item in json.loads(notes_path.read_text(encoding="utf-8")):
            notes[item["event_name"]] = item.get("notas") or []
    baseline = pd.read_csv(DIAG / "baseline_summary.csv")
    corners = pd.read_csv(DIAG / "baseline_corners.csv")
    despues_path = DIAG / "despues_summary.csv"
    despues = pd.read_csv(despues_path) if despues_path.exists() else pd.DataFrame()
    index = [
        "# Circuitos 2025",
        "",
        "Una ficha por gran premio. Lo documentado cita a Brembo o a la nota del director de carrera de la FIA. "
        "Lo medido sale de la telemetría FastF1 de la carrera, vía el export de TracingInsights-Archive/2025. "
        "La distancia de frenada de Brembo no es la ventana hasta el ápice de FastF1.",
        "",
        "El diagnóstico está en `docs/zoi_diagnostico_2025/`.",
        "",
    ]
    for key in ORDER:
        text = _sheet(key, circuits, brembo, fia, notes, baseline, despues, corners)
        (DOCS / f"{key}.md").write_text(text, encoding="utf-8")
        bench = circuits["benchmark_circuits"].get(key) or {}
        event = bench.get("event_name") or "Hungarian Grand Prix"
        index.append(f"- [{TITLES[key]}]({key}.md) (`{event}`)")
    index.append("")
    (DOCS / "indice.md").write_text("\n".join(index), encoding="utf-8")
    print(f"fichas: {len(ORDER)}", flush=True)


if __name__ == "__main__":
    main()
