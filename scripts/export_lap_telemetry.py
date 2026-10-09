"""Export the raw telemetry of the canonical laps of one session for offline feature work.

Writes, under ``cache/derived/<year>_<event_slug>_<session>/`` (gitignored):

- ``lap_matrix.csv``: the lap × style matrix from ``build_lap_style_matrix`` (Driver, LapNumber, 17 style
  columns, metadata), relative to the session median per typology; ``run_pipeline`` then applies the
  lap-synchronous centring and tyre effects on top.
- ``car.pkl``: ``prepare_lap_telemetry`` per lap (car data at native ~4 Hz, Distance, Acceleration,
  ThrottleRate), with ``Driver`` and ``LapNumber`` columns. Same samples the pipeline uses.
- ``tel.pkl``: ``lap.get_telemetry()`` per lap (car + position merged and interpolated: X, Y, Z,
  Distance, Speed, Throttle, Brake, nGear, RPM, DRS), with ``Driver`` and ``LapNumber``.
- ``laps.csv``: FastF1 lap fields for those laps (LapTime, sectors, speed traps, Compound, TyreLife,
  Stint, Position, TrackStatus, Team).
- ``zones.json``: the analysis zones (braking | apex | exit windows in metres, typology, apex distance).
- ``corners.csv``: ``session.get_circuit_info().corners`` (X, Y, Number, Letter, Angle, Distance).
- ``weather.csv``: session weather samples.

Usage (repo root, FastF1 cache available):

    python scripts/export_lap_telemetry.py --year 2025 --circuit "Italian Grand Prix" --session R
"""

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from f1_style_clustering.config import load_circuit_config, load_config  # noqa: E402
from f1_style_clustering.data.loader import enable_cache, load_session, prepare_lap_telemetry  # noqa: E402
from f1_style_clustering.features.aggregators import build_lap_style_matrix  # noqa: E402
from f1_style_clustering.features.zoi import extract_circuit_zones, resolve_selected_corners  # noqa: E402

warnings.filterwarnings("ignore")

LAP_FIELDS = [
    "Driver", "Team", "LapNumber", "LapTime", "Sector1Time", "Sector2Time", "Sector3Time",
    "SpeedI1", "SpeedI2", "SpeedFL", "SpeedST", "Compound", "TyreLife", "FreshTyre", "Stint",
    "Position", "TrackStatus", "IsPersonalBest", "LapStartTime",
]


def _jsonable(value):
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return value


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--circuit", default="Italian Grand Prix")
    ap.add_argument("--session", default="R")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    slug = f"{args.year}_{args.circuit.lower().replace(' ', '_')}_{args.session.lower()}"
    out = Path(args.out) if args.out else _ROOT / "cache" / "derived" / slug
    out.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    circuits = load_circuit_config()
    enable_cache((cfg.get("general") or {}).get("cache_dir", "cache"))
    session = load_session(year=args.year, grand_prix=args.circuit, session_type=args.session)
    selected, zone_source = resolve_selected_corners(session, circuits)
    zones = extract_circuit_zones(session, circuit_config=circuits, selected_corners=selected)
    feat_cfg = cfg.get("features") or {}
    matrix = build_lap_style_matrix(
        session,
        analysis_zones=zones,
        circuit_config=circuits,
        push_mode=bool((cfg.get("data_filtering") or {}).get("push_mode", False)),
        min_valid_laps=int((cfg.get("data_filtering") or {}).get("min_valid_laps_per_driver", 3)),
        include_throttle_onset=bool(feat_cfg.get("include_throttle_onset", True)),
    )
    matrix.attrs = {}
    matrix.to_csv(out / "lap_matrix.csv", index=False)
    print(f"lap matrix {matrix.shape} zone_source={zone_source}")

    keys = set(zip(matrix["Driver"].astype(str), matrix["LapNumber"].astype(int)))
    laps = session.laps
    car_frames, tel_frames, lap_rows = [], [], []
    for _, lap in laps.iterlaps():
        key = (str(lap["Driver"]), int(lap["LapNumber"]))
        if key not in keys:
            continue
        car = prepare_lap_telemetry(lap)
        if car is not None and not car.empty:
            car = car.copy()
            car["Driver"], car["LapNumber"] = key
            car_frames.append(car)
        try:
            tel = lap.get_telemetry()
            tel = pd.DataFrame(tel).copy()
            tel["Driver"], tel["LapNumber"] = key
            tel_frames.append(tel)
        except Exception as exc:  # position data can be missing for a lap
            print(f"no merged telemetry for {key}: {exc}")
        lap_rows.append({f: lap.get(f) if hasattr(lap, "get") else None for f in LAP_FIELDS})

    car_all = pd.concat(car_frames, ignore_index=True)
    tel_all = pd.concat(tel_frames, ignore_index=True)
    car_all.attrs, tel_all.attrs = {}, {}
    car_all.to_pickle(out / "car.pkl")
    tel_all.to_pickle(out / "tel.pkl")
    lap_df = pd.DataFrame(lap_rows)
    for c in [c for c in lap_df.columns if c.endswith("Time")]:
        lap_df[c] = pd.to_timedelta(lap_df[c]).dt.total_seconds()
    lap_df.to_csv(out / "laps.csv", index=False)

    (out / "zones.json").write_text(json.dumps(_jsonable(zones), indent=2))
    corners = session.get_circuit_info().corners
    corners.to_csv(out / "corners.csv", index=False)
    if getattr(session, "weather_data", None) is not None:
        weather = session.weather_data.copy()
        weather["Time"] = pd.to_timedelta(weather["Time"]).dt.total_seconds()
        weather.to_csv(out / "weather.csv", index=False)
    print(f"car {car_all.shape} tel {tel_all.shape} laps {lap_df.shape} -> {out}")


if __name__ == "__main__":
    main()
