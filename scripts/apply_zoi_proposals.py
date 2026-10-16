"""Arma ``key_corners`` a partir del diagnóstico y los escribe en el YAML.

No toca Monza, Silverstone ni Mónaco. No escribe ``typology``: el cubo lo
sigue eligiendo la sesión. El ápice queda en los ±60 m del default.

    python scripts/apply_zoi_proposals.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

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

MARKER = "  # Ventanas medidas en la carrera 2025."
DIAG = _ROOT / "docs" / "zoi_diagnostico_2025"
YAML_PATH = _ROOT / "config" / "circuits.yaml"

# official_name sale de la ficha Brembo 2025, salvo Catar: esa página respondió 404.
META = [
    ("australian", "Albert Park GP Circuit", "Australian Grand Prix"),
    ("chinese", "Shanghai International Circuit", "Chinese Grand Prix"),
    ("japanese", "Suzuka Circuit", "Japanese Grand Prix"),
    ("bahrain", "Bahrain International Circuit", "Bahrain Grand Prix"),
    ("saudi_arabian", "Jeddah Corniche Circuit", "Saudi Arabian Grand Prix"),
    ("miami", "Miami International Autodrome", "Miami Grand Prix"),
    ("emilia_romagna", "Autodromo Internazionale Enzo e Dino Ferrari", "Emilia Romagna Grand Prix"),
    ("spanish", "Circuit de Barcelona-Catalunya", "Spanish Grand Prix"),
    ("canadian", "Circuit Gilles-Villeneuve", "Canadian Grand Prix"),
    ("austrian", "Red Bull Ring", "Austrian Grand Prix"),
    ("belgian", "Circuit de Spa-Francorchamps", "Belgian Grand Prix"),
    ("hungarian", "Hungaroring", "Hungarian Grand Prix"),
    ("dutch", "Circuit Zandvoort", "Dutch Grand Prix"),
    ("azerbaijan", "Baku City Circuit", "Azerbaijan Grand Prix"),
    ("singapore", "Marina Bay Street Circuit", "Singapore Grand Prix"),
    ("united_states", "Circuit of the Americas", "United States Grand Prix"),
    ("mexico_city", "Autódromo Hermanos Rodríguez", "Mexico City Grand Prix"),
    ("sao_paulo", "Autódromo José Carlos Pace", "São Paulo Grand Prix"),
    ("las_vegas", "Las Vegas Strip Circuit", "Las Vegas Grand Prix"),
    ("qatar", "Qatar Grand Prix", "Qatar Grand Prix"),
    ("abu_dhabi", "Yas Marina Circuit", "Abu Dhabi Grand Prix"),
]


def build_entries(circuits: dict) -> tuple[list[dict], list[dict]]:
    summary = pd.read_csv(DIAG / "baseline_summary.csv")
    corners = pd.read_csv(DIAG / "baseline_corners.csv")
    zones = pd.read_csv(DIAG / "baseline_zones.csv")
    entries = []
    notes = []
    for key, official, event in META:
        row = summary[summary["event"] == event]
        if row.empty:
            raise SystemExit(f"falta {event} en baseline_summary.csv")
        rec = row.iloc[0]
        proposal = diag.propose_key_corners(
            corners[corners["event"] == event],
            zones[zones["event"] == event],
            track_length=float(rec["track_length"]),
            n_overlap_pairs=int(rec["n_overlap_pairs"]),
            n_merges=int(rec["n_merges"]),
            event_name=event,
            circuit_config=circuits,
        )
        measured_rows = [int(n) for n in corners.loc[corners["event"] == event, "corner_number"]]
        measured = sorted(set(measured_rows))
        item = {
            "key": key,
            "official_name": official,
            "event_name": event,
            "notas": [],
            "key_corners": None,
        }
        if len(measured_rows) != len(measured):
            repeated = sorted({n for n in measured_rows if measured_rows.count(n) > 1})
            item["notas"].append(
                "FastF1 repite el Number "
                + ", ".join(str(n) for n in repeated)
                + ". `key_corners` se queda con la primera distancia y el fallback pisa `Turn_N` y se queda con la última. "
                "No se escribe ficha para no mover el ápice sin cambiar el algoritmo."
            )
            notes.append(item)
            continue
        if proposal is None:
            item["notas"].append(
                "El diagnóstico no justificó una ficha propia: sin solapes, sin fusiones y con menos del 5 % de inicios en el borde o afuera."
            )
        else:
            spec = {}
            for name, zone in proposal["key_corners"].items():
                zone = dict(zone)
                zone.pop("typology", None)
                spec[name] = zone
            listed = []
            for zone in spec.values():
                listed.extend(int(n) for n in zone["corner_numbers"])
            if listed != measured:
                raise SystemExit(f"{event}: la propuesta no cubre los números FastF1 {measured} vs {listed}")
            item["key_corners"] = spec
            item["notas"].extend(proposal.get("notes") or [])
        notes.append(item)
        if item["key_corners"]:
            entries.append(
                {
                    "key": key,
                    "official_name": official,
                    "event_name": event,
                    "key_corners": item["key_corners"],
                }
            )
    return entries, notes


def splice(text: str, block: str) -> str:
    if MARKER in text:
        text = text[: text.index(MARKER)].rstrip() + "\n"
    return text.rstrip() + "\n\n" + MARKER + "\n" + block


def main() -> None:
    circuits = load_circuit_config()
    entries, notes = build_entries(circuits)
    block = diag.render_circuit_yaml(entries)
    original = YAML_PATH.read_text(encoding="utf-8")
    for event in diag.PROTECTED_EVENTS:
        if event not in original:
            raise SystemExit(f"el YAML no contiene {event}")
    updated = splice(original, block)
    for event in diag.PROTECTED_EVENTS:
        # El bloque viejo tiene que seguir igual, carácter por carácter, hasta el marcador.
        old_head = original.split(MARKER)[0] if MARKER in original else original
        new_head = updated.split(MARKER)[0]
        if old_head != new_head and MARKER not in original:
            # La primera vez el head es el archivo entero, y el nuevo le agrega un salto.
            if new_head.rstrip() + "\n" != old_head.rstrip() + "\n" and new_head != old_head:
                pass
        if event not in updated.split(MARKER)[0]:
            raise SystemExit(f"se perdió {event}")
    # El tramo anterior al marcador, sin el salto final, tiene que ser el YAML original.
    head = updated.split(MARKER)[0].rstrip() + "\n"
    old = original.rstrip() + "\n"
    if head != old:
        raise SystemExit("el tramo de Monza, Silverstone y Mónaco cambió")
    YAML_PATH.write_text(updated, encoding="utf-8")
    (DIAG / "propuesta_notas.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"circuitos escritos: {len(entries)}", flush=True)
    for item in notes:
        n = 0 if not item["key_corners"] else len(item["key_corners"])
        print(f"  {item['event_name']}: {n} zonas, {len(item['notas'])} notas", flush=True)


if __name__ == "__main__":
    main()
