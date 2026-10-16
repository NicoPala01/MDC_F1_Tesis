#!/usr/bin/env python
"""Evaluate the 2026-10-14 baseline predictions on Monza 2025 R.

The prediction text is already in ``docs/temporada_2025.md``. This script only
writes the measured intervals. It does not change that text and it does not
change the clustering path. The single-race matrix keeps ``fast__brake_point_rel``.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

from f1_style_clustering.analysis.baseline_predictions import evaluate_baseline
from f1_style_clustering.analysis.round2 import jsonable, prepare_style_matrix
from f1_style_clustering.config import load_circuit_config, load_config
from f1_style_clustering.data.loader import load_session


def main() -> None:
    config = load_config()
    circuits = load_circuit_config()
    cache = (config.get("general") or {}).get("cache_dir", "cache")
    session = load_session(year=2025, grand_prix="Italian Grand Prix", session_type="R", cache_dir=cache)
    prepared = prepare_style_matrix(session, config, circuits, exclude_columns=[], speed_scaled=False)
    frame = prepared["frame"]
    result = evaluate_baseline(session, frame, prepared["zones"])
    result["event"] = "Italian Grand Prix"
    result["year"] = 2025
    result["zone_source"] = prepared["zone_source"]
    result["n_laps_in_matrix"] = 0 if frame is None else int(len(frame))
    dest = Path("docs/season_2025/runs/monza_baseline_predictions.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        __import__("json").dumps(jsonable(result), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"wrote {dest}", flush=True)


if __name__ == "__main__":
    main()
