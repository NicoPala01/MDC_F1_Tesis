"""Read saved session CSVs for the lap-profile dashboard."""

from pathlib import Path
from typing import Dict, List

import pandas as pd

METRIC_LABELS = {
    "brake_point_rel": "Punto de frenado (relativo)",
    "trail_brake_frac": "Trail braking",
    "apex_speed_rel": "Velocidad en el vértice (relativa)",
    "throttle_attack": "Ataque de acelerador",
    "coast_frac": "Costa",
    "full_throttle_frac": "Full throttle",
    "throttle_onset_rel": "Onset de acelerador",
}


def discover_sessions(results_root: Path) -> List[Dict[str, str]]:
    """Session folders that already contain a driver profile and a lap distribution."""
    sessions: List[Dict[str, str]] = []
    root = Path(results_root)
    if not root.exists():
        return sessions
    for year_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for event_dir in sorted(p for p in year_dir.iterdir() if p.is_dir()):
            if event_dir.name == "season":
                continue
            profiles = event_dir / "driver_profiles.csv"
            distribution = event_dir / "driver_lap_distribution.csv"
            if not profiles.exists() or not distribution.exists():
                continue
            pretty = event_dir.name.replace("_", " ").title()
            sessions.append(
                {
                    "year": year_dir.name,
                    "event": event_dir.name,
                    "label": f"{year_dir.name} · {pretty}",
                    "profiles": str(profiles),
                    "distribution": str(distribution),
                }
            )
    return sessions


def load_session_tables(session: Dict[str, str]) -> tuple:
    """Return ``(profiles, distribution)`` for one saved Grand Prix."""
    profiles = pd.read_csv(session["profiles"])
    distribution = pd.read_csv(session["distribution"])
    if "Driver" not in profiles.columns and profiles.index.name == "Driver":
        profiles = profiles.reset_index()
    return profiles, distribution


def metric_table(profile_row: pd.Series) -> pd.DataFrame:
    """Median style features for one driver, with display labels."""
    rows = []
    for col, label in METRIC_LABELS.items():
        if col not in profile_row.index or pd.isna(profile_row[col]):
            continue
        rows.append({"Métrica": label, "Mediana de las vueltas": float(profile_row[col])})
    return pd.DataFrame(rows)
