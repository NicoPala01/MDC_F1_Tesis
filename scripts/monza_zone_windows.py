"""Vector por zona y borde de la ventana de frenado, Monza 2025.

La corrida por defecto no cambia (``vector_unit: typology``, ventanas del YAML).
Esta corrida arma el vector por zona, con las columnas de frenada omitidas donde
no hay frenada, y mide en cuántos inicios de frenada el primer sample de una
ventana de 350 m ya está frenando (issue #10).

    python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from f1_style_clustering.analysis.null_separation import silhouette_against_column_null  # noqa: E402
from f1_style_clustering.config import load_circuit_config, load_config  # noqa: E402
from f1_style_clustering.data.loader import enable_cache, load_session  # noqa: E402
from f1_style_clustering.features.brake_windows import (  # noqa: E402
    braking_pre_apex_m,
    median_entry_speed_by_zone,
    scale_braking_distance,
    scan_brake_onsets,
    summarize_onsets,
)
from f1_style_clustering.features.preprocessor import separate_metadata  # noqa: E402
from f1_style_clustering.features.zoi import extract_circuit_zones, resolve_selected_corners  # noqa: E402
from f1_style_clustering.pipeline import run_pipeline  # noqa: E402
from f1_style_clustering.season import resolve_event_name  # noqa: E402


def _fmt(value, digits=4) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return ""
    return f"{float(value):.{digits}f}"


def _md_table(frame: pd.DataFrame, digits: dict) -> str:
    headers = list(frame.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for _, row in frame.iterrows():
        cells = []
        for col in headers:
            spec = digits.get(col)
            val = row[col]
            if spec is None:
                cells.append(str(val))
            elif spec == "int":
                cells.append(str(int(val)) if pd.notna(val) else "")
            else:
                cells.append(_fmt(val, int(spec)))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _settings(cfg: dict) -> dict:
    feat = cfg.get("features") or {}
    clus = cfg.get("clustering") or {}
    pca = (cfg.get("dimensionality_reduction") or {}).get("pca") or {}
    mode = str(pca.get("use_as_clustering_input", "auto")).lower()
    return {
        "scaler_type": str(feat.get("standardization", "robust")),
        "variance_threshold": float(pca.get("variance_threshold", 0.85)),
        "max_features_direct": 8,
        "force_pca": mode in {"true", "always", "1", "yes"},
        "random_state": int((cfg.get("general") or {}).get("random_state", 42)),
        "n_init": int((clus.get("kmeans") or {}).get("n_init", 20)),
    }


def _sep_table(summary: pd.DataFrame) -> str:
    show = summary.copy()
    show["separa"] = np.where(show["separates"], "sí", "no")
    show = show[["k", "silhouette", "null_mean", "null_p50", "null_p95", "percentile", "separa", "n_perm", "n_components"]]
    show.columns = ["k", "silueta", "nulo media", "nulo p50", "nulo p95", "percentil", "separa del nulo", "permutaciones", "PCs"]
    return _md_table(
        show,
        {
            "k": "int",
            "silueta": 4,
            "nulo media": 4,
            "nulo p50": 4,
            "nulo p95": 4,
            "percentil": 1,
            "permutaciones": "int",
            "PCs": "int",
        },
    )


def write_report(path: Path, payload: dict) -> None:
    edges = payload["edges"]
    total_350 = edges[(edges["window"] == "350m") & (edges["zone"] == "TOTAL")].iloc[0]
    total_pipe = edges[(edges["window"] == "pipeline") & (edges["zone"] == "TOTAL")].iloc[0]
    by_zone = edges[edges["zone"] != "TOTAL"].copy()
    show_edge = by_zone.rename(
        columns={
            "window": "ventana",
            "zone": "zona",
            "n_fragments": "fragmentos",
            "n_onsets": "inicios",
            "n_edge": "en el borde",
            "edge_frac_of_onsets": "fracción borde",
            "within_5m_frac_of_onsets": "fracción a ≤5 m",
            "median_entry_speed": "velocidad de entrada",
        }
    )[
        [
            "ventana",
            "zona",
            "fragmentos",
            "inicios",
            "en el borde",
            "fracción borde",
            "fracción a ≤5 m",
            "velocidad de entrada",
        ]
    ]
    scales = payload["scales"]
    show_scale = scales.rename(
        columns={
            "zone": "zona",
            "pre_apex_m": "metros actuales",
            "entry_speed": "velocidad de entrada",
            "scaled_pre_m": "metros escalados",
        }
    )
    summary = payload["summary"]
    chosen = payload["k_used"]
    chosen_row = summary.loc[summary["k"] == chosen]
    chosen_sep = bool(chosen_row["separates"].iloc[0]) if len(chosen_row) else False
    report = payload["zone_report"]
    lines = [
        "# Vector por zona y ventanas de frenado (Monza 2025)",
        "",
        "Corrida de referencia, configuración por defecto: "
        '`python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R`.',
        "",
        "El vector por zona y las ventanas escaladas por velocidad están apagados en "
        "`config/pipeline_config.yaml` (`vector_unit: typology`, `speed_scaled_windows: false`). "
        "Los números de este documento salen de una corrida aparte con `vector_unit: zone` y de un "
        "recorrido de la telemetría canónica. El K-means, el RobustScaler, el PCA automático y la regla de k no cambian.",
        "",
        "## Issue #10: inicios de frenada en el borde de 350 m",
        "",
        "Definición medida: un inicio cae en el borde si el primer sample dentro de la ventana ya tiene el freno puesto. "
        "La ventana de 350 m empieza 350 m antes del ápice y termina donde empieza la ventana de ápice. "
        "No es la ventana que usa el YAML de Monza en cada curva (Curva Grande está en 180 m, Lesmo 2 en 200 m, Rettifilo en 350 m). "
        "La otra definición, también medida, cuenta un inicio si está a 5 m o menos del arranque geométrico de la ventana.",
        "",
        f"Ventana de 350 m, todas las zonas: {int(total_350['n_onsets'])} inicios en {int(total_350['n_fragments'])} fragmentos. "
        f"En el borde: {int(total_350['n_edge'])} ({_fmt(100 * total_350['edge_frac_of_onsets'], 2)} % de los inicios). "
        f"A 5 m o menos: {int(total_350['n_within_5m'])} ({_fmt(100 * total_350['within_5m_frac_of_onsets'], 2)} % de los inicios).",
        "",
        f"Ventanas que realmente usa el pipeline en Monza: {int(total_pipe['n_onsets'])} inicios, "
        f"{int(total_pipe['n_edge'])} en el borde ({_fmt(100 * total_pipe['edge_frac_of_onsets'], 2)} % de los inicios), "
        f"{int(total_pipe['n_within_5m'])} a 5 m o menos ({_fmt(100 * total_pipe['within_5m_frac_of_onsets'], 2)} %).",
        "",
        "Se esperaba, antes de medir, menos del 0.2 % en el borde de 350 m. El porcentaje de arriba es el medido, no ese objetivo.",
        "",
        _md_table(
            show_edge,
            {
                "fragmentos": "int",
                "inicios": "int",
                "en el borde": "int",
                "fracción borde": 4,
                "fracción a ≤5 m": 4,
                "velocidad de entrada": 1,
            },
        ),
        "",
        "### Riesgo fuera de Monza",
        "",
        "No se midió otro circuito. Lo que el código hace, y el riesgo que eso deja abierto:",
        "",
        "- Monza, Silverstone y Mónaco usan `key_corners`. El resto de la temporada cae en `_zones_from_speed_threshold_fallback`: una zona por curva de FastF1, con los 350 m / ±60 m / 250 m de `default_zoi_offsets`.",
        "- En una frenada larga después de una recta larga, 350 m pueden abrir la ventana después del inicio real. `brake_point_rel` mediría un onset cortado. En Monza, con la definición de arriba, la fracción en el borde de 350 m es la de la tabla.",
        "- En sectores trabados (Mónaco, y el fallback cuando dos curvas quedan cerca) las ventanas se solapan y `clip_and_merge_zones` las recorta. Ese recorte no está contado en esta corrida.",
        "- La intensidad de frenado no entra al vector. `get_max_deceleration` existe y no se usa.",
        "",
        "### Ventanas escaladas por velocidad (apagadas)",
        "",
        "La opción `speed_scaled_windows` multiplica los metros pre-ápice de cada zona por `(velocidad de entrada / 300 km/h)^2`, con piso 80 m y techo 700 m. "
        "La velocidad de entrada es la mediana de la velocidad del primer sample de la ventana que el pipeline usa hoy. "
        "Esta tabla es esa cuenta. No se volvió a clusterizar con las ventanas escaladas.",
        "",
        _md_table(
            show_scale,
            {"metros actuales": 1, "velocidad de entrada": 1, "metros escalados": 1},
        ),
        "",
        "## Vector por zona",
        "",
        "Hoy el bloque `medium` junta Lesmo 1, Lesmo 2, la Parabólica y la Roggia. "
        "Con `vector_unit: zone` hay un bloque por curva. La mediana de sesión se resta dentro de la zona, no de la tipología. "
        "Después siguen la mediana del campo en la misma vuelta, el ajuste de compuesto y vida, el RobustScaler, el PCA automático y el K-means.",
        "",
        "Regla declarada, no medida: una columna de frenada (`brake_point_rel`, `trail_brake_frac`) entra solo si al menos el "
        f"{_fmt(100 * report.get('min_brake_coverage', 0.95), 0)} % de las vueltas tiene valor. "
        "Por debajo de eso no se inventa una distancia. Si frenó entre el 2 % y ese piso, la columna `{zona}__braked` vale 1 o 0. "
        "Si no frena casi nadie, no se agrega ni esa columna: sería otra columna de IQR 0.",
        "",
        f"Vueltas que sobrevivirían a `dropna(how='any')` con todas las columnas de frenada: {report.get('naive_complete_laps')}. "
        f"Vueltas que quedan con la regla de arriba: {report.get('n_laps')}. "
        f"Vueltas que entran al K-means después del filtro de pilotos: {payload['n_laps']}. "
        f"Columnas: {payload['n_cols']}. Pilotos: {payload['n_drivers']}. "
        f"k elegido: {chosen} (regla `{payload['k_rule']}`). "
        f"PCA: {payload['n_components']} componentes, varianza {_fmt(payload['cumulative'], 4)}.",
        "",
        "Cobertura de `brake_point_rel` por zona (fracción de vueltas con onset, antes de omitir columnas):",
        "",
    ]
    cov = report.get("brake_coverage") or {}
    if cov:
        cov_df = pd.DataFrame([{"zona": k, "cobertura": v} for k, v in cov.items()])
        lines.append(_md_table(cov_df, {"cobertura": 3}))
        lines.append("")
    omitted = report.get("omitted_columns") or []
    lines.append("Columnas de frenada omitidas: " + (", ".join(f"`{c}`" for c in omitted) if omitted else "ninguna") + ".")
    braked = report.get("braked_columns") or []
    lines.append("Columnas `braked`: " + (", ".join(f"`{c}`" for c in braked) if braked else "ninguna") + ".")
    lines.extend(
        [
            "",
            "## Separación del vector por zona",
            "",
            "El mismo nulo que en `docs/separacion_nulo_monza_2025.md`: columnas permutadas una por una, escalador y PCA reajustados, "
            f"{payload['n_perm']} permutaciones, k de 2 a 7. "
            "Criterio de lectura declarado: la real se separa si el percentil es mayor que 95.",
            "",
            _sep_table(summary),
            "",
        ]
    )
    if not chosen_sep:
        lines.extend(
            [
                "En el k que elige la regla, la silueta real no se separa del nulo.",
                "",
                "Opciones, sin cambiar el algoritmo por defecto:",
                "",
                "1. **Partición descriptiva.** Conservar las clases como resumen de la sesión.",
                "2. **Perfil continuo por piloto.** Usar los scores de las PC del espacio de ajuste en lugar de una clase.",
                "3. **Asignación blanda.** Probabilidad de clase por vuelta. No está implementada.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "En el k que elige la regla, la silueta real se separa del nulo según el criterio declarado. "
                "La asignación blanda no está implementada.",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--circuit", default="Italian Grand Prix")
    ap.add_argument("--session", default="R")
    ap.add_argument("--n-perm", type=int, default=200)
    ap.add_argument("--doc", default=str(_ROOT / "docs" / "vector_por_zona_monza_2025.md"))
    ap.add_argument("--tables", default=str(_ROOT / "docs" / "monza_2025_methodology"))
    args = ap.parse_args()

    cfg = load_config()
    circuits = load_circuit_config()
    event = resolve_event_name(args.circuit, circuits)
    enable_cache((cfg.get("general") or {}).get("cache_dir", "cache"))
    print(f"[1] cargo {args.year} {event}", flush=True)
    session = load_session(year=args.year, grand_prix=event, session_type=args.session)
    selected, _source = resolve_selected_corners(session, circuits)
    zones = extract_circuit_zones(session, circuit_config=circuits, selected_corners=selected)
    filt = cfg.get("data_filtering") or {}
    print("[2] bordes de frenada", flush=True)
    records = scan_brake_onsets(
        session,
        zones,
        fixed_pre_m=350.0,
        push_mode=bool(filt.get("push_mode", False)),
        min_valid_laps=int(filt.get("min_valid_laps_per_driver", 3)),
    )
    edges = summarize_onsets(records)
    speeds = median_entry_speed_by_zone(records, window="pipeline")
    ref = float((cfg.get("features") or {}).get("speed_scaled_ref_kmh", 300.0))
    scale_rows = []
    for name, zone in zones.items():
        base = braking_pre_apex_m(zone)
        speed = speeds.get(name, float("nan"))
        scale_rows.append(
            {
                "zone": name,
                "pre_apex_m": base,
                "entry_speed": speed,
                "scaled_pre_m": scale_braking_distance(base, speed, ref_kmh=ref),
            }
        )
    scales = pd.DataFrame(scale_rows)

    cfg_zone = copy.deepcopy(cfg)
    cfg_zone.setdefault("features", {})
    cfg_zone["features"]["vector_unit"] = "zone"
    cfg_zone["features"]["speed_scaled_windows"] = False
    print("[3] pipeline vector_unit=zone", flush=True)
    result = run_pipeline(session, config=cfg_zone, circuit_config=circuits)
    if result.get("error"):
        raise SystemExit(result["error"])
    raw = result["df_raw"]
    numeric, _meta = separate_metadata(raw)
    settings = _settings(cfg_zone)
    print(f"[4] nulo columnas={numeric.shape[1]} vueltas={len(numeric)}", flush=True)
    summary, scores = silhouette_against_column_null(
        numeric,
        k_range=range(2, 8),
        n_perm=args.n_perm,
        progress_every=25,
        **settings,
    )
    info = result.get("pca_fit_info") or {}
    payload = {
        "edges": edges,
        "scales": scales,
        "summary": summary,
        "zone_report": result.get("zone_vector") or {},
        "k_used": result.get("k_used"),
        "k_rule": result.get("k_rule"),
        "n_laps": int(len(raw)),
        "n_drivers": int(raw["Driver"].nunique()) if "Driver" in raw.columns else 0,
        "n_cols": int(numeric.shape[1]),
        "n_components": info.get("n_components"),
        "cumulative": info.get("cumulative_variance"),
        "n_perm": args.n_perm,
    }
    tables = Path(args.tables)
    tables.mkdir(parents=True, exist_ok=True)
    edges.to_csv(tables / "brake_window_edges.csv", index=False)
    scales.to_csv(tables / "speed_scaled_windows.csv", index=False)
    summary.to_csv(tables / "null_separation_zone.csv", index=False)
    pd.DataFrame(
        [{"k": k, "rep": i, "silhouette": s} for k, vals in scores.items() for i, s in enumerate(vals)]
    ).to_csv(tables / "null_silhouette_replicates_zone.csv", index=False)
    doc = Path(args.doc)
    write_report(doc, payload)
    print(edges[edges["zone"] == "TOTAL"].to_string(index=False), flush=True)
    print(summary.to_string(index=False), flush=True)
    print(f"[5] {doc}", flush=True)
    print("zone_vector", result.get("zone_vector"), flush=True)


if __name__ == "__main__":
    main()
