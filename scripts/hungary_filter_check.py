#!/usr/bin/env python
"""Run the Hungary filter check on its own. Does not trim and does not sweep floors."""

from __future__ import annotations

import os

os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path

from f1_style_clustering.analysis.hungary_laps import run_hungary_filter_check
from f1_style_clustering.config import load_circuit_config, load_config
from f1_style_clustering.data.loader import load_session


def main() -> None:
    config = load_config()
    cache = (config.get("general") or {}).get("cache_dir", "cache")
    session = load_session(year=2025, grand_prix="Hungarian Grand Prix", session_type="R", cache_dir=cache)
    payload = run_hungary_filter_check(session, config, load_circuit_config(), Path("docs/season_2025/runs"))
    print(
        "confirmed", payload.get("note_confirmed"),
        "filter_failure", payload.get("filter_failure"),
        "inconclusive", payload.get("filter_inconclusive"),
        "evaluate_trim", payload.get("evaluate_outlier_trim"),
        flush=True,
    )


if __name__ == "__main__":
    main()
