#!/usr/bin/env python
"""Apply the declared robust-z cap on every saved race matrix.

Runs only when the Hungary filter check says the named laps are not a filter
failure and the check is conclusive. The cap is 10 on every race.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from f1_style_clustering.analysis.round2 import jsonable
from f1_style_clustering.analysis.season_checks import DECLARED_ROBUST_Z_MAX, outlier_mask, style_columns


def _one(path: Path) -> dict:
    frame = pd.read_csv(path)
    mask, detail = outlier_mask(frame, max_z=DECLARED_ROBUST_Z_MAX)
    return {
        "matrix": path.name,
        "n": int(len(frame)),
        "n_flagged": int(mask.sum()),
        "max_z": DECLARED_ROBUST_Z_MAX,
        "columns": detail.to_dict(orient="records"),
    }


def main() -> None:
    runs = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/season_2025/runs")
    check_path = runs / "hungary_filter_check.json"
    if not check_path.exists():
        sys.exit("El recorte espera el chequeo de filtro de Hungría.")
    check = json.loads(check_path.read_text(encoding="utf-8"))
    dest = runs / "outlier_trim_eval.json"
    if not check.get("evaluate_outlier_trim"):
        payload = {
            "applied": False,
            "reason": "El chequeo no habilitó el recorte.",
            "filter_failure": check.get("filter_failure"),
            "filter_inconclusive": check.get("filter_inconclusive"),
            "note_confirmed": check.get("note_confirmed"),
        }
        dest.write_text(json.dumps(jsonable(payload), indent=2, ensure_ascii=False), encoding="utf-8")
        print(payload["reason"], flush=True)
        return
    rows = []
    for path in sorted(runs.glob("*_matrix.csv")):
        rows.append(_one(path))
    included = runs / "hungarian_grand_prix_included_matrix.csv"
    if included.exists():
        rows.append(_one(included))
    payload = {"applied": True, "max_z": DECLARED_ROBUST_Z_MAX, "races": rows}
    dest.write_text(json.dumps(jsonable(payload), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {dest}", flush=True)


if __name__ == "__main__":
    main()
