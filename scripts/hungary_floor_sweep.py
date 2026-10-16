#!/usr/bin/env python
"""Hungary class-size floors. Runs only after that race's null file exists."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd

from f1_style_clustering.analysis.null_separation import _fit_space
from f1_style_clustering.analysis.round2 import jsonable, sweep_floors
from f1_style_clustering.analysis.season_checks import style_columns
from f1_style_clustering.config import load_config


def main() -> None:
    runs = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/season_2025/runs")
    matrix_path = runs / "hungarian_grand_prix_included_matrix.csv"
    candidates = [
        runs / "hungarian_grand_prix_triple.json",
        runs / "hungarian_grand_prix.json",
    ]
    null_path = next((path for path in candidates if path.exists()), None)
    if null_path is None:
        sys.exit("El barrido espera el nulo de Hungría.")
    null_payload = json.loads(null_path.read_text(encoding="utf-8"))
    if not null_payload.get("null_done"):
        sys.exit("El nulo de Hungría todavía no está escrito.")
    if not matrix_path.exists():
        sys.exit("Falta la matriz de Hungría con la columna incluida.")
    frame = pd.read_csv(matrix_path)
    numeric = frame[style_columns(frame)].apply(pd.to_numeric, errors="coerce")
    config = load_config()
    seed = int((config.get("general") or {}).get("random_state", 42))
    pca_cfg = (config.get("dimensionality_reduction") or {}).get("pca") or {}
    fit, _pca, _info, _scaler = _fit_space(
        numeric,
        "robust",
        float(pca_cfg.get("variance_threshold", 0.85)),
        8,
        False,
        seed,
    )
    rows = sweep_floors(fit, config, n_laps=len(numeric))
    out = {
        "event": "Hungarian Grand Prix",
        "matrix": "column included, the one with the size-2 class",
        "n_laps": int(len(numeric)),
        "after_null": str(null_path),
        "floors": rows,
    }
    dest = runs / "hungary_floor_sweep.json"
    dest.write_text(json.dumps(jsonable(out), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {dest}", flush=True)


if __name__ == "__main__":
    main()
