"""Team-weight layer on three 2025 races drawn before the run.

The draw, the floors and the structure gate live in
``f1_style_clustering.analysis.team_weight`` and are not changed after a
percentile is seen. This script writes summary tables only. The FastF1 cache
stays under ``cache/`` and is not part of the result.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from f1_style_clustering.analysis.team_weight import (  # noqa: E402
    BOOT_SEED,
    CALIBRATION_SEED,
    DRAW_SEED,
    DRIVER_EFFECT_NOTE,
    MIN_CLEAN_LAPS,
    MIN_STINTS,
    N_BOOT,
    N_DRAW,
    N_FAKE_PAIRS,
    N_NULL,
    N_PERM,
    PAIR_COLUMNS,
    PERM_SEED,
    STRUCTURE_GATE_RULE,
    artifact_control,
    association_reason,
    association_statistics,
    attach_association,
    bootstrap_v_interval,
    build_pair_rows,
    calibration_fake_teams,
    class_structure_reason,
    common_columns,
    draw_races,
    driver_medians,
    family_summary,
    feature_family,
    iqr_variants,
    lawson_tsunoda_control,
    pace_by_class,
    pair_deltas,
    permutation_percentile,
    retention_table,
    small_class_mask,
    variance_table,
)
from f1_style_clustering.analysis.season_checks import five_percent_floor  # noqa: E402
from f1_style_clustering.analysis.triple_null import run_triple_null  # noqa: E402
from f1_style_clustering.config import load_circuit_config, load_config  # noqa: E402
from f1_style_clustering.data.loader import enable_cache, load_session  # noqa: E402
from f1_style_clustering.pipeline import (  # noqa: E402
    _lap_min_cluster_size,
    cluster_driver_matrix,
    run_pipeline,
)
from f1_style_clustering.season import iter_race_event_names, season_exclude_columns  # noqa: E402

DOCS = _ROOT / "docs" / "peso_equipo_2025"
WORK = Path("/tmp/peso_equipo")


def _style_columns(frame: pd.DataFrame) -> list:
    return [
        column
        for column in frame.columns
        if "__" in str(column) and pd.api.types.is_numeric_dtype(frame[column])
    ]


def _rainfall_for_laps(session, laps: pd.DataFrame):
    weather = getattr(session, "weather_data", None)
    if (
        weather is None
        or len(getattr(weather, "index", [])) == 0
        or "Rainfall" not in weather.columns
        or "SessionTime" not in getattr(weather, "columns", [])
        or "SessionTime" not in laps.columns
    ):
        return None
    try:
        right = weather[["SessionTime", "Rainfall"]].dropna(subset=["SessionTime"]).sort_values("SessionTime")
        left = laps[["SessionTime"]].sort_values("SessionTime")
        aligned = pd.merge_asof(left, right, on="SessionTime", direction="nearest")
        flags = aligned["Rainfall"].fillna(False).astype(bool)
        return flags.reindex(laps.index).fillna(False)
    except (ValueError, TypeError):
        return None


def race_retention(session) -> dict:
    laps = session.laps
    if laps is None or len(laps) == 0 or "TrackStatus" not in laps.columns:
        return {
            "n_vueltas": 0 if laps is None else int(len(laps)),
            "share_conservada": float("nan"),
            "excluida": False,
            "motivo": "",
            "nota": "sin TrackStatus; la carrera no se excluye por esta regla",
        }
    work = laps
    if "PitInTime" in work.columns and "PitOutTime" in work.columns:
        pit = work["PitInTime"].notna() | work["PitOutTime"].notna()
        work = work.loc[~pit]
    rain = _rainfall_for_laps(session, work)
    report = retention_table(work["TrackStatus"].tolist(), None if rain is None else rain.tolist())
    report["nota"] = "" if rain is not None else "sin lluvia alineada al reloj; solo SC y VSC"
    return report


def _load_race(event: str, cfg: dict):
    """FastF1 when an F1 account is configured. Otherwise the public OpenF1 path.

    ``Session.load`` prompts for an F1 email when ``F1_USERNAME`` and
    ``F1_PASSWORD`` are missing, and a tty blocks there. This function does
    not call that prompt.
    """
    import os

    cache_dir = (cfg.get("general") or {}).get("cache_dir", "cache")
    enable_cache(cache_dir)
    if os.environ.get("F1_USERNAME") and os.environ.get("F1_PASSWORD"):
        session = load_session(year=2025, grand_prix=event, session_type="R", cache_dir=cache_dir)
        return session, "fastf1"
    from openf1_public_session import load_public_session

    session, note = load_public_session(event)
    session._openf1_note = note
    return session, "openf1"


def _analysis_frame(result: dict, session) -> pd.DataFrame:
    raw = result["df_raw"].copy()
    labels = result.get("cluster_labels")
    if labels is not None:
        raw["Cluster"] = labels.reindex(raw.index)
    frame = raw.reset_index(drop=True)
    frame["Driver"] = frame["Driver"].astype(str)
    frame["LapNumber"] = pd.to_numeric(frame["LapNumber"], errors="coerce")
    laps = session.laps
    keep = [column for column in ("Driver", "LapNumber", "Stint", "LapTime") if column in laps.columns]
    meta = laps[keep].copy()
    meta["Driver"] = meta["Driver"].astype(str)
    meta["LapNumber"] = pd.to_numeric(meta["LapNumber"], errors="coerce")
    meta = meta.drop_duplicates(["Driver", "LapNumber"])
    frame = frame.merge(meta, on=["Driver", "LapNumber"], how="left")
    if "LapTime" in frame.columns:
        if pd.api.types.is_timedelta64_dtype(frame["LapTime"]):
            frame["LapTimeSeconds"] = frame["LapTime"].dt.total_seconds()
        else:
            frame["LapTimeSeconds"] = pd.to_numeric(frame["LapTime"], errors="coerce")
    results = getattr(session, "results", None)
    if results is not None and "Abbreviation" in results.columns and "TeamName" in results.columns:
        teams = results.dropna(subset=["Abbreviation"]).drop_duplicates("Abbreviation")
        team_map = teams.set_index(teams["Abbreviation"].astype(str))["TeamName"].astype(str)
        mapped = frame["Driver"].map(team_map)
        frame["Team"] = mapped.where(mapped.notna(), frame["Team"] if "Team" in frame.columns else np.nan)
        if "GridPosition" in results.columns:
            grid = teams.set_index(teams["Abbreviation"].astype(str))["GridPosition"]
            frame["GridPosition"] = pd.to_numeric(frame["Driver"].map(grid), errors="coerce")
    return frame


def _slim_null(result: dict) -> dict:
    if not isinstance(result, dict):
        return {"error": str(result)}
    nulls = {}
    for name, record in (result.get("nulls") or {}).items():
        if not isinstance(record, dict):
            continue
        kept = {key: value for key, value in record.items() if key != "values"}
        score = kept.get("name_score")
        if isinstance(score, dict):
            kept["name_score"] = {key: value for key, value in score.items() if key != "values"}
        nulls[name] = kept
    real = dict(result.get("real") or {})
    real.pop("labels", None)
    return {
        "error": result.get("error"),
        "structure": bool(result.get("structure")),
        "n_laps": result.get("n_laps"),
        "n_columns": result.get("n_columns"),
        "real": {key: real.get(key) for key in ("k", "k_rule", "silhouette", "error", "floor")},
        "nulls": nulls,
    }


def _recluster(frame: pd.DataFrame, columns: list, cfg: dict) -> pd.Series:
    import copy

    # Pace and grid stay out of the fit. They are numeric and are not style columns.
    meta = [
        column
        for column in ("Driver", "Team", "FullName", "LapNumber", "Stint", "Compound", "TyreLife", "FreshTyre")
        if column in frame.columns
    ]
    reduced = frame[meta + columns].copy()
    local = copy.deepcopy(cfg)
    local.setdefault("clustering", {})
    local["clustering"]["min_cluster_size"] = _lap_min_cluster_size(len(reduced))
    local["clustering"]["driver_bootstrap"] = False
    local["clustering"]["compare_aggregators"] = False
    fitted = cluster_driver_matrix(
        reduced,
        config=local,
        residualize=False,
        driver_bootstrap=False,
        compare_aggregators=False,
    )
    if fitted.get("error"):
        raise RuntimeError(fitted["error"])
    return fitted["cluster_labels"]


def _one_variant(frame, columns, labels, race, structure, results: pd.DataFrame) -> dict:
    del columns
    work = frame.copy()
    if isinstance(labels, pd.Series):
        work["Cluster"] = labels.reindex(work.index).to_numpy()
    else:
        work["Cluster"] = np.asarray(labels)
    class_reason = class_structure_reason(work["Cluster"])
    reason = association_reason(bool(structure), class_reason)
    pairs = build_pair_rows(work, results, race, class_reason)
    stats = association_statistics(work["Cluster"], work["Driver"], work["Team"])
    perm = {"percentil_midrank": float("nan"), "percentil_le": float("nan"), "n_perm": 0}
    lo = hi = float("nan")
    if reason == "":
        perm = permutation_percentile(
            work["Cluster"], work["Driver"], work["Team"], n_perm=N_PERM, seed=PERM_SEED
        )
        lo, hi = bootstrap_v_interval(work, N_BOOT, BOOT_SEED)
    attached = attach_association(pairs, stats, perm, reason)
    attached["ic_v_bajo"] = lo
    attached["ic_v_alto"] = hi
    attached["estructura_supera_nulo"] = bool(structure)
    attached["clases_chicas"] = "con"
    floor = five_percent_floor(len(work))
    mask = small_class_mask(work["Cluster"], floor).to_numpy()
    kept = work.loc[~mask].copy()
    kept_class = class_structure_reason(kept["Cluster"]) if len(kept) else "sin_clases"
    kept_reason = association_reason(bool(structure), kept_class)
    kept_pairs = build_pair_rows(kept if len(kept) else work.iloc[0:0], results, race, kept_class)
    kept_stats = association_statistics(kept["Cluster"], kept["Driver"], kept["Team"]) if len(kept) else {}
    kept_perm = {"percentil_midrank": float("nan"), "percentil_le": float("nan"), "n_perm": 0}
    if kept_reason == "" and len(kept):
        kept_perm = permutation_percentile(
            kept["Cluster"], kept["Driver"], kept["Team"], n_perm=N_PERM, seed=PERM_SEED + 1
        )
    kept_attached = attach_association(kept_pairs, kept_stats, kept_perm, kept_reason)
    kept_attached["estructura_supera_nulo"] = bool(structure)
    kept_attached["clases_chicas"] = "sin"
    kept_attached["piso_clase"] = int(floor)
    attached["piso_clase"] = int(floor)
    return {
        "pares": pd.concat([attached, kept_attached], ignore_index=True),
        "class_reason": class_reason,
        "reason": reason,
        "floor": int(floor),
        "n_small": int(mask.sum()) if len(mask) else 0,
    }


def _results_table(session) -> pd.DataFrame:
    results = getattr(session, "results", None)
    if results is None or "Abbreviation" not in results.columns or "TeamName" not in results.columns:
        return pd.DataFrame(columns=["Abbreviation", "TeamName"])
    columns = [column for column in ("Abbreviation", "TeamName", "Status", "Position", "GridPosition") if column in results.columns]
    return results[columns].copy()


def analyse_loaded_race(event: str, session, source: str, cfg: dict) -> dict:
    retention = race_retention(session)
    retention["race"] = event
    retention["fuente"] = source
    note = getattr(session, "_openf1_note", None)
    if isinstance(note, dict):
        retention["track_status_nota"] = note.get("track_status")
        retention["is_accurate_nota"] = note.get("is_accurate")
        retention["reference_lap"] = note.get("reference_lap")
        retention["reference_driver"] = note.get("reference_driver")
    if retention.get("excluida"):
        return {"race": event, "retention": retention, "skipped": "lluvia_sc_vsc"}
    print(f"[pipeline] {event}", flush=True)
    result = run_pipeline(
        session,
        config=cfg,
        circuit_config=load_circuit_config(),
        residualize=False,
        exclude_columns=season_exclude_columns(cfg),
        driver_bootstrap=False,
        compare_aggregators=False,
    )
    if result.get("error"):
        return {"race": event, "retention": retention, "error": str(result["error"])}
    frame = _analysis_frame(result, session)
    results = _results_table(session)
    columns = _style_columns(frame)
    split = iqr_variants(frame, columns)
    numeric = frame[split["con_iqr0"]].apply(pd.to_numeric, errors="coerce")
    print(f"[nulo] {event} columnas={numeric.shape[1]} vueltas={len(numeric)}", flush=True)
    null = run_triple_null(
        numeric,
        cfg,
        n_replicates=N_NULL,
        seed=42,
        progress=event,
        drivers=frame["Driver"].astype(str).tolist(),
        teams=frame.groupby(frame["Driver"].astype(str))["Team"].first(),
    )
    structure = bool(null.get("structure"))
    primary = _one_variant(frame, split["con_iqr0"], frame["Cluster"], event, structure, results)
    official = build_pair_rows(frame, results, event, primary["class_reason"])
    primary["pares"]["variante_iqr"] = "con_iqr0"
    print(f"[varianza] {event}", flush=True)
    components = variance_table(frame, split["con_iqr0"], event, n_boot=N_BOOT, seed=BOOT_SEED, variante_iqr="con_iqr0")
    deltas = pair_deltas(frame, primary["pares"].loc[primary["pares"]["clases_chicas"] == "con"], split["con_iqr0"], n_boot=N_BOOT, seed=BOOT_SEED)
    pace = pace_by_class(frame, event)
    artifacts = []
    seen = set()
    for pair in official.to_dict(orient="records"):
        key = (pair["team"], pair["driver_a"], pair["driver_b"])
        if not pair["driver_b"] or key in seen:
            continue
        seen.add(key)
        control = artifact_control(frame, split["con_iqr0"], pair["driver_a"], pair["driver_b"])
        control.update(race=event, team=pair["team"])
        artifacts.append(control)
    calibration = pd.DataFrame()
    if frame["Cluster"].nunique(dropna=True) >= 2:
        calibration = calibration_fake_teams(
            frame["Cluster"], frame["Driver"], n_fake=N_FAKE_PAIRS, n_perm=N_PERM, seed=CALIBRATION_SEED
        )
        if len(calibration):
            calibration.insert(0, "race", event)
    extra = {"variante": "sin_iqr0", "pares": pd.DataFrame(), "components": pd.DataFrame(), "null": None}
    if split["iqr0"] and len(split["sin_iqr0"]) >= 2:
        print(f"[nulo sin iqr0] {event} drop={split['iqr0']}", flush=True)
        labels = _recluster(frame, split["sin_iqr0"], cfg)
        reduced = frame[split["sin_iqr0"]].apply(pd.to_numeric, errors="coerce")
        null_drop = run_triple_null(
            reduced,
            cfg,
            n_replicates=N_NULL,
            seed=42,
            progress=f"{event} sin_iqr0",
            drivers=frame["Driver"].astype(str).tolist(),
            teams=frame.groupby(frame["Driver"].astype(str))["Team"].first(),
        )
        variant = _one_variant(
            frame,
            split["sin_iqr0"],
            labels.reindex(frame.index),
            event,
            bool(null_drop.get("structure")),
            results,
        )
        variant["pares"]["variante_iqr"] = "sin_iqr0"
        extra = {
            "variante": "sin_iqr0",
            "pares": variant["pares"],
            "components": variance_table(
                frame, split["sin_iqr0"], event, n_boot=N_BOOT, seed=BOOT_SEED + 7, variante_iqr="sin_iqr0"
            ),
            "null": _slim_null(null_drop),
        }
    medians = driver_medians(frame, [column for column in split["con_iqr0"] if feature_family(column) == "estilo"])
    teams = frame.groupby(frame["Driver"].astype(str))["Team"].first().to_dict()
    mates = {}
    for pair in official.to_dict(orient="records"):
        if pair["driver_b"]:
            mates[pair["driver_a"]] = pair["driver_b"]
            mates[pair["driver_b"]] = pair["driver_a"]
    return {
        "race": event,
        "retention": retention,
        "skipped": "",
        "columns": split,
        "null": _slim_null(null),
        "pares": pd.concat([primary["pares"], extra["pares"]], ignore_index=True),
        "components": pd.concat([components, extra["components"]], ignore_index=True),
        "deltas": deltas,
        "pace": pace,
        "artifacts": pd.DataFrame(artifacts),
        "calibration": calibration,
        "null_sin_iqr0": extra["null"],
        "profile": {"teams": teams, "mates": mates, "medians": medians},
        "n_laps": int(len(frame)),
        "k": None if null.get("real") is None else (null.get("real") or {}).get("k"),
    }


def _jsonable(value):
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.floating, float)):
        if not np.isfinite(value):
            return None
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _write_table(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame is None or len(frame) == 0:
        pd.DataFrame().to_csv(path, index=False)
        return
    frame.to_csv(path, index=False)


def _fmt(value, digits=3):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(number):
        return "—"
    return f"{number:.{digits}f}"


def render_markdown(payload: dict, path: Path) -> None:
    lines = [
        "# Peso del equipo y compañeros, tres GP de 2025",
        "",
        "La base del código es `feat/zoi-por-circuito` (PR 13). `main` no tiene esas ventanas ni la corrida OpenF1. `monza-test` está contenido en `main`. El nulo del PR 11 ya está en esa base.",
        "",
        "## Reglas, anteriores a la corrida",
        "",
        STRUCTURE_GATE_RULE,
        "",
        DRIVER_EFFECT_NOTE,
        "",
        f"Semilla del sorteo: `{payload['seed']}`. Se sortean `{payload['n_draw']}` carreras de `iter_race_event_names(2025)`, en el orden del calendario, con `numpy.random.Generator.choice` sin reposición. Numpy `{payload['numpy']}`.",
        "",
        f"Piso de un par: `{MIN_CLEAN_LAPS}` vueltas limpias y `{MIN_STINTS}` stints. Una carrera con menos del 50 % de vueltas conservadas por safety car, VSC o lluvia sale de la capa. No se filtra por `Status` ni por posición.",
        "",
        f"Permutación de pilotos: `{N_PERM}` réplicas, semilla `{PERM_SEED}`. Bootstrap por stint: `{N_BOOT}`, semilla `{BOOT_SEED}`. El percentil del test es el rango medio. El nulo de silueta del PR 11 sigue usando la proporción de réplicas menores o iguales.",
        "",
        "Familia auto: `brake_point_rel`, `apex_speed_rel`, `full_throttle_frac`. Familia estilo: tasas y transiciones (`throttle_attack`, `trail_brake_frac`, `coast_frac`, `throttle_onset_rel` y las métricas de tiempo). Una columna de otro stem se reporta como `otra`. No se borra ninguna.",
        "",
        "## Sorteo",
        "",
        "Población:",
        "",
    ]
    for name in payload["population"]:
        mark = " ← sorteado" if name in payload["drawn"] else ""
        lines.append(f"- {name}{mark}")
    lines.extend(["", "Sorteados, en el orden que devolvió el generador:", ""])
    for name in payload["drawn"]:
        lines.append(f"- {name}")
    lines.extend(["", "## Resultados", ""])
    if not payload.get("ran"):
        lines.append("La corrida todavía no está. Este archivo no contiene cifras de telemetría.")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    ret = payload["retention"]
    if len(ret):
        lines.append("Retención (safety car, VSC, lluvia):")
        lines.append("")
        for _, row in ret.iterrows():
            lines.append(
                f"- {row['race']}: conservada {_fmt(row.get('share_conservada'))}, "
                f"excluida {bool(row.get('excluida'))}, motivo `{row.get('motivo') or '—'}`, "
                f"SC {row.get('n_sc')}, VSC {row.get('n_vsc')}, lluvia no verde {row.get('n_lluvia_no_verde')}."
            )
        lines.append("")
    if payload.get("failures"):
        lines.append("Carreras de la muestra que no produjeron matriz:")
        lines.append("")
        for item in payload["failures"]:
            lines.append(f"- {item['race']}: {item['error']}")
        lines.append("")
    nulls = payload["nulls"]
    if len(nulls):
        lines.extend(["Estructura frente al nulo triple:", ""])
        for _, row in nulls.iterrows():
            lines.append(
                f"- {row['race']} ({row['variante']}): structure {bool(row['structure'])}, "
                f"k {_fmt(row.get('k'), 0)}, silueta {_fmt(row.get('silhouette'))}, "
                f"percentil permutación {_fmt(row.get('pct_perm'), 1)}, "
                f"gaussiano {_fmt(row.get('pct_gauss'), 1)}, cópula {_fmt(row.get('pct_copula'), 1)}."
            )
        lines.append("")
    lines.append("Pares. `V_cramer_bc`, `AMI` y `ARI` son de la carrera (clase × escudería, nivel vuelta) y se repiten en cada fila. El AMI de la columna `AMI` es clase contra escudería. `AMI_clase_piloto` es clase contra piloto.")
    lines.append("")
    pares = payload["pares"]
    if len(pares):
        show = pares.loc[pares["clases_chicas"] == "con"] if "clases_chicas" in pares.columns else pares
        for _, row in show.iterrows():
            lines.append(
                f"- {row['race']} / {row['team']} / {row['driver_a']}-{row['driver_b'] or '—'} / {row['estrato']} / {row['variante_iqr']}: "
                f"n {row['n_a']}/{row['n_b']}, motivo `{row['motivo_NA'] or '—'}`, "
                f"compuesto `{row['compuesto_comun'] or '—'}`, V {_fmt(row['V_cramer_bc'])} "
                f"[{_fmt(row.get('ic_v_bajo'))}, {_fmt(row.get('ic_v_alto'))}], "
                f"AMI {_fmt(row['AMI'])}, ARI {_fmt(row['ARI'])}, "
                f"percentil {_fmt(row['pct_null_permutacion_piloto'], 1)}, "
                f"asociación `{row.get('motivo_asociacion') or '—'}`, "
                f"V modal {_fmt(row.get('V_cramer_bc_piloto_modal'))}, "
                f"AMI piloto {_fmt(row.get('AMI_clase_piloto'))}."
            )
        lines.append("")
    discarded = payload["discarded"]
    lines.append(f"Pares con motivo de NA: {len(discarded)}.")
    if len(discarded):
        lines.append("")
        for _, row in discarded.iterrows():
            lines.append(
                f"- {row['race']} {row['team']} {row['driver_a']}-{row['driver_b'] or '—'} "
                f"{row['estrato']}: `{row['motivo_NA']}` ({row.get('detalle_NA') or ''})."
            )
    lines.append("")
    lines.append("Proporción de varianza del piloto dentro del equipo, por feature. El intervalo es el bootstrap por stint.")
    lines.append("")
    comp = payload["components"]
    if len(comp):
        view = comp.loc[comp["componente"] == "piloto_dentro_de_equipo"]
        for _, row in view.iterrows():
            lines.append(
                f"- {row['race']} {row['feature']} ({row['familia']}, {row['variante_iqr']}): "
                f"piloto {_fmt(row['proporcion'])} [{_fmt(row['ic_bajo'])}, {_fmt(row['ic_alto'])}], "
                f"equipo {_fmt(_component(comp, row, 'equipo'))}, "
                f"stint {_fmt(_component(comp, row, 'stint'))}, "
                f"residual {_fmt(_component(comp, row, 'residual'))}, "
                f"R² fijos {_fmt(row['r2_fijos'])}."
            )
        lines.append("")
    fam = payload["families"]
    if len(fam):
        lines.append("Media no ponderada de esas proporciones, por familia. No es un modelo conjunto.")
        lines.append("")
        for _, row in fam.iterrows():
            lines.append(
                f"- {row['race']} {row['familia']} ({row['variante_iqr']}): "
                f"piloto {_fmt(row.get('proporcion_piloto_media'))}, "
                f"equipo {_fmt(row.get('proporcion_equipo_media'))}, "
                f"features {row.get('n_features')}."
            )
        lines.append("")
    pace = payload["pace"]
    if len(pace):
        lines.append("Ritmo. η² del tiempo de vuelta sobre la clase, y de la posición de grilla sobre la clase modal.")
        lines.append("")
        for _, row in pace.iterrows():
            lines.append(f"- {row['race']} {row['ritmo']} {row['nivel']}: {_fmt(row['eta2'])} (n {row['n']}).")
        lines.append("")
    cal = payload["calibration"]
    if len(cal):
        lines.append(
            f"Calibración, {N_FAKE_PAIRS} emparejamientos falsos. "
            f"Media del percentil: {_fmt(cal['percentil_midrank'].mean(), 1)}."
        )
        lines.append("")
    art = payload["artifacts"]
    if len(art):
        lines.append("Control del residuo de equipo. La simetría en datos permutados es el artefacto. La tasa del intervalo es el método de este módulo.")
        lines.append("")
        for _, row in art.iterrows():
            lines.append(
                f"- {row.get('race')} {row.get('team')} {row.get('driver_a')}-{row.get('driver_b')}: "
                f"simetría {_fmt(row.get('simetria_abs'), 4)}, "
                f"separa residuos {row.get('separa_kmeans_residuo')}, "
                f"tasa separa permutada {_fmt(row.get('tasa_separa_permutada'))}, "
                f"tasa IC excluye 0 en la permutación {_fmt(row.get('tasa_ic_excluye_cero_permutada'))}."
            )
        lines.append("")
    law = payload["lawson"]
    if len(law):
        lines.append("Lawson y Tsunoda. Si la muestra no cruza el cambio de equipo, la función queda en no aplica.")
        lines.append("")
        for _, row in law.iterrows():
            lines.append("- " + ", ".join(f"{column}={row[column]}" for column in law.columns if pd.notna(row[column])))
        lines.append("")
    lines.append("Las cifras de esta sección salen de los CSV de este directorio, escritos por la misma corrida.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _component(table: pd.DataFrame, row: pd.Series, name: str) -> float:
    match = table.loc[
        (table["race"] == row["race"])
        & (table["feature"] == row["feature"])
        & (table["variante_iqr"] == row["variante_iqr"])
        & (table["componente"] == name),
        "proporcion",
    ]
    if match.empty:
        return float("nan")
    return float(match.iloc[0])


def _null_row(event: str, variante: str, slim: dict) -> dict:
    nulls = (slim or {}).get("nulls") or {}
    def pct(name):
        record = nulls.get(name) or {}
        return record.get("percentile")
    real = (slim or {}).get("real") or {}
    return {
        "race": event,
        "variante": variante,
        "structure": bool((slim or {}).get("structure")),
        "k": real.get("k"),
        "silhouette": real.get("silhouette"),
        "pct_perm": pct("column_permutation"),
        "pct_gauss": pct("gaussian"),
        "pct_copula": pct("gaussian_copula"),
        "error": (slim or {}).get("error"),
    }


def run(draw_only: bool = False) -> dict:
    import fastf1

    fastf1.set_log_level("WARNING")
    cfg = load_config()
    population = iter_race_event_names(2025)
    drawn = draw_races(population, seed=DRAW_SEED, n=N_DRAW)
    print("sorteo", DRAW_SEED, drawn, flush=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": DRAW_SEED,
        "n_draw": N_DRAW,
        "numpy": np.__version__,
        "population": population,
        "drawn": drawn,
        "ran": False,
    }
    (DOCS / "sorteo.json").write_text(json.dumps(_jsonable(payload), indent=2), encoding="utf-8")
    if draw_only:
        render_markdown(payload, DOCS / "README.md")
        return payload
    WORK.mkdir(parents=True, exist_ok=True)
    retentions = []
    failures = []
    null_rows = []
    pares = []
    components = []
    deltas = []
    paces = []
    artifacts = []
    calibrations = []
    profiles = []
    column_sets = []
    iqr_rows = []
    for event in drawn:
        try:
            session, source = _load_race(event, cfg)
            print(f"[fuente] {event} {source}", flush=True)
            outcome = analyse_loaded_race(event, session, source, cfg)
        except Exception:
            text = traceback.format_exc()
            print(text, flush=True)
            failures.append({"race": event, "error": text.strip().splitlines()[-1]})
            continue
        retentions.append(outcome["retention"])
        if outcome.get("skipped") or outcome.get("error"):
            failures.append({"race": event, "error": outcome.get("error") or outcome.get("skipped")})
            continue
        null_rows.append(_null_row(event, "con_iqr0", outcome["null"]))
        if outcome.get("null_sin_iqr0"):
            null_rows.append(_null_row(event, "sin_iqr0", outcome["null_sin_iqr0"]))
        pares.append(outcome["pares"])
        components.append(outcome["components"])
        deltas.append(outcome["deltas"])
        paces.append(outcome["pace"])
        artifacts.append(outcome["artifacts"])
        calibrations.append(outcome["calibration"])
        profiles.append({"race": event, **{key: outcome["profile"][key] for key in ("teams", "mates")}, "medians": outcome["profile"]["medians"]})
        column_sets.append(outcome["columns"]["con_iqr0"])
        for column in outcome["columns"]["iqr0"]:
            iqr_rows.append({"race": event, "column": column})
        (WORK / f"{event}.json").write_text(
            json.dumps(_jsonable({"null": outcome["null"], "n_laps": outcome["n_laps"]})),
            encoding="utf-8",
        )
    common = common_columns(column_sets)
    common_components = []
    # Recompute on the stored per-race frames only through the already-fitted
    # components: keep the rows whose feature is in the intersection.
    if components and common:
        stacked = pd.concat(components, ignore_index=True)
        common_components.append(stacked.loc[stacked["feature"].isin(common)].copy())
    pare_table = pd.concat(pares, ignore_index=True) if pares else pd.DataFrame(columns=list(PAIR_COLUMNS))
    component_table = pd.concat(components, ignore_index=True) if components else pd.DataFrame()
    discarded = pare_table.loc[pare_table["motivo_NA"].astype(str) != ""] if len(pare_table) and "motivo_NA" in pare_table.columns else pd.DataFrame()
    families = family_summary(component_table) if len(component_table) else pd.DataFrame()
    common_table = pd.concat(common_components, ignore_index=True) if common_components else pd.DataFrame()
    common_families = family_summary(common_table) if len(common_table) else pd.DataFrame()
    if len(common_families):
        common_families.insert(0, "columnas", "comunes")
    lawson = lawson_tsunoda_control(
        [
            {
                "race": item["race"],
                "team_of": item["teams"],
                "teammate_of": item["mates"],
                "medians": item["medians"],
            }
            for item in profiles
        ],
        common or [],
    )
    payload.update(
        ran=True,
        retention=pd.DataFrame(retentions),
        failures=failures,
        nulls=pd.DataFrame(null_rows),
        pares=pare_table,
        discarded=discarded,
        components=component_table,
        families=pd.concat([families, common_families], ignore_index=True) if len(common_families) else families,
        pace=pd.concat(paces, ignore_index=True) if paces else pd.DataFrame(),
        calibration=pd.concat([item for item in calibrations if item is not None and len(item)], ignore_index=True) if any(len(item) for item in calibrations if item is not None) else pd.DataFrame(),
        artifacts=pd.concat([item for item in artifacts if item is not None and len(item)], ignore_index=True) if artifacts else pd.DataFrame(),
        lawson=lawson,
        common_columns=common,
    )
    _write_table(payload["retention"], DOCS / "retencion.csv")
    _write_table(payload["nulls"], DOCS / "nulo_estructura.csv")
    _write_table(pare_table, DOCS / "pares.csv")
    _write_table(discarded, DOCS / "pares_descartados.csv")
    _write_table(component_table, DOCS / "varianza_por_feature.csv")
    _write_table(payload["families"], DOCS / "varianza_por_familia.csv")
    _write_table(common_table, DOCS / "varianza_columnas_comunes.csv")
    _write_table(payload["pace"], DOCS / "ritmo_por_clase.csv")
    _write_table(payload["calibration"], DOCS / "calibracion.csv")
    _write_table(payload["artifacts"], DOCS / "control_artefacto.csv")
    _write_table(lawson, DOCS / "lawson_tsunoda.csv")
    _write_table(pd.concat(deltas, ignore_index=True) if deltas else pd.DataFrame(), DOCS / "diferencias_par.csv")
    _write_table(pd.DataFrame(iqr_rows), DOCS / "columnas_iqr0.csv")
    (DOCS / "columnas_comunes.json").write_text(json.dumps(common, indent=2), encoding="utf-8")
    (DOCS / "fallos.json").write_text(json.dumps(failures, indent=2), encoding="utf-8")
    render_markdown(payload, DOCS / "README.md")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draw-only", action="store_true")
    args = parser.parse_args()
    run(draw_only=args.draw_only)


if __name__ == "__main__":
    main()
