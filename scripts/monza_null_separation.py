"""Silueta de Monza 2025 contra un nulo de columnas permutadas.

Misma corrida que::

    python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R

Para cada k de 2 a 7 compara la silueta del K-means++ del pipeline (RobustScaler,
PCA auto, ``n_init`` y semilla de la config) con ~200 permutaciones independientes
de las columnas ya normalizadas. Escribe el percentil de la silueta real, la
misma tabla sin las columnas de IQR 0 o casi constantes, y un diagnóstico por
columna. No cambia el camino por defecto.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from f1_style_clustering.analysis.null_separation import (  # noqa: E402
    column_diagnostics,
    sensitivity_column_sets,
    silhouette_against_column_null,
)
from f1_style_clustering.config import load_circuit_config, load_config  # noqa: E402
from f1_style_clustering.data.loader import enable_cache, load_session  # noqa: E402
from f1_style_clustering.features.preprocessor import separate_metadata  # noqa: E402
from f1_style_clustering.pipeline import run_pipeline  # noqa: E402
from f1_style_clustering.season import resolve_event_name, session_output_dir, write_session_outputs  # noqa: E402


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


def _pipeline_settings(cfg: dict) -> dict:
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


def _check_matches_pipeline(summary: pd.DataFrame, eval_df: pd.DataFrame) -> float:
    if eval_df is None or eval_df.empty:
        return float("nan")
    merged = summary.merge(eval_df[["k", "silhouette"]], on="k", suffixes=("_null", "_pipeline"))
    if merged.empty:
        return float("nan")
    return float((merged["silhouette_null"] - merged["silhouette_pipeline"]).abs().max())


def _variant_block(summary: pd.DataFrame) -> str:
    show = summary.copy()
    show["separa"] = np.where(show["separates"], "sí", "no")
    show = show[
        ["k", "silhouette", "null_mean", "null_p50", "null_p95", "percentile", "separa", "n_perm", "n_components"]
    ]
    show.columns = [
        "k",
        "silueta",
        "nulo media",
        "nulo p50",
        "nulo p95",
        "percentil",
        "separa del nulo",
        "permutaciones",
        "PCs",
    ]
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


def _options_paragraph(chosen_separates: bool) -> str:
    if chosen_separates:
        return (
            "La silueta del k que elige la regla queda por encima del percentil 95 del nulo. "
            "Ese corte es un criterio de lectura declarado, no una propiedad medida de los datos."
        )
    return "\n".join(
        [
            "La silueta real no se separa del nulo en el k que elige la regla: cae en el cuerpo de la distribución de las permutaciones, o no llega al percentil 95. El mismo K-means, con las mismas marginales y sin la estructura conjunta, alcanza una silueta parecida. Las clases describen un reparto de la sesión; no son modos que el algoritmo distinga de ese nulo.",
            "",
            "Opciones, sin cambiar el algoritmo por defecto:",
            "",
            "1. **Partición descriptiva.** Conservar las clases como resumen de la sesión y no leerlas como estilos separados del nulo.",
            "2. **Perfil continuo por piloto.** Usar los scores de las PC del espacio de ajuste (por ejemplo la media de cada piloto) en lugar de asignar una clase.",
            "3. **Asignación blanda.** Dar, por vuelta, una probabilidad de cada clase. No está implementada.",
        ]
    )


def write_report(
    path: Path,
    *,
    year: int,
    event: str,
    session_type: str,
    result: dict,
    summary: pd.DataFrame,
    reduced: pd.DataFrame | None,
    sets: dict,
    diagnostics: pd.DataFrame,
    match_delta: float,
    n_perm: int,
) -> None:
    raw = result["df_raw"]
    info = result.get("pca_fit_info") or {}
    n_drivers = int(raw["Driver"].nunique()) if "Driver" in raw.columns else 0
    style_n = int(summary["n_components"].iloc[0]) if len(summary) else 0
    # n_components in the summary is the PCA count, not the column count.
    n_cols = int(diagnostics.shape[0])
    chosen = result.get("k_used")
    rule = result.get("k_rule")
    chosen_row = summary.loc[summary["k"] == chosen]
    chosen_sep = bool(chosen_row["separates"].iloc[0]) if len(chosen_row) else False
    any_sep = bool(summary["separates"].any())
    lines = [
        "# Separación contra un nulo de columnas permutadas (Monza 2025)",
        "",
        "Corrida: `python scripts/run_pipeline.py --year "
        f"{year} --circuit \"{event}\" --session {session_type}`.",
        "",
        "La matriz es la del pipeline con la configuración por defecto: mediana de sesión por tipología, mediana del campo en la misma vuelta, ajuste de compuesto y vida dentro de piloto, y las columnas de estilo que entran al K-means (onset apagado, sin `fast__throttle_attack`). El espacio de la silueta es el de ajuste: RobustScaler y PCA automático al 85 % de varianza, K-means++ con la semilla y el `n_init` de `config/pipeline_config.yaml`. Cada réplica del nulo permuta cada columna por su cuenta y vuelve a ajustar el escalador y el PCA. Se conservan las marginales (empates, ceros, colas) y se rompe la relación entre columnas.",
        "",
        f"Vueltas: {len(raw)}. Pilotos: {n_drivers}. Columnas: {n_cols}. "
        f"Componentes en el ajuste: {info.get('n_components', style_n)}. "
        f"Varianza acumulada: {_fmt(info.get('cumulative_variance'), 4)}. "
        f"k elegido: {chosen} (regla `{rule}`).",
        "",
        f"La silueta observada de esta tabla y la de `eval_df` del pipeline difieren a lo sumo en {_fmt(match_delta, 6)} "
        "(mismo espacio y el mismo K-means).",
        "",
        "## Percentil de la silueta real",
        "",
        f"Nulo: {n_perm} permutaciones pedidas. El percentil es el porcentaje de siluetas nulas menores o iguales que la real. "
        "Criterio de lectura declarado, no medido: la real se separa del nulo en un k si ese percentil es mayor que 95.",
        "",
        _variant_block(summary),
        "",
    ]
    if not any_sep:
        lines.append("En ningún k de 2 a 7 la silueta real supera el percentil 95 del nulo.")
    elif not chosen_sep:
        which = ", ".join(str(int(k)) for k in summary.loc[summary["separates"], "k"])
        lines.append(
            f"El k de la regla no se separa del nulo. Sí lo hacen, con el mismo criterio declarado, los k: {which}."
        )
    else:
        lines.append("El k de la regla se separa del nulo según el criterio declarado.")
    lines.extend(["", _options_paragraph(chosen_sep), ""])

    lines.extend(["## Sensibilidad sin columnas de IQR 0 o casi constantes", ""])
    lines.append(
        "RobustScaler sustituye una escala 0 por 1. Una columna con IQR 0 entra a la distancia con esa escala. "
        "«Casi constantes» son las de `near_constant_columns`: más del 90 % de ceros, o menos de 3 valores distintos. "
        "Sacarlas es solo esta comparación. El vector por defecto no cambia."
    )
    lines.append("")
    if sets["dropped"]:
        reasons = []
        zero = set(sets["zero_iqr"])
        near = set(sets["near_constant"])
        for col in sets["dropped"]:
            why = []
            if col in zero:
                why.append("IQR 0")
            if col in near:
                why.append("casi constante")
            reasons.append(f"`{col}` ({', '.join(why)})")
        lines.append("Columnas apartadas: " + "; ".join(reasons) + ".")
    else:
        lines.append("Ninguna columna tiene IQR 0 ni entra en `near_constant_columns`. No hay segunda tabla.")
    lines.append("")
    if reduced is not None and not reduced.empty:
        kept_n = len(sets["kept"])
        lines.append(f"Columnas que quedan: {kept_n}. Misma regla de lectura.")
        lines.append("")
        lines.append(_variant_block(reduced))
        red_chosen = reduced.loc[reduced["k"] == chosen]
        if len(red_chosen):
            sep = "sí" if bool(red_chosen["separates"].iloc[0]) else "no"
            lines.append("")
            lines.append(
                f"En el k={chosen} de la regla, sin esas columnas, el percentil es "
                f"{_fmt(red_chosen['percentile'].iloc[0], 1)} y el criterio declarado dice que {sep} se separa."
            )
    lines.extend(["", "## Diagnóstico por columna", ""])
    lines.append(
        "Sobre la matriz ya normalizada, antes del escalador. "
        "`var_within` es la varianza agrupada dentro de piloto (MSW). "
        "`var_between` es la varianza, sin ponderar por vueltas, de las medias de cada piloto. "
        "`identical_frac` es la fracción de valores finitos iguales al valor más repetido. "
        "`peso_pc_share` es la suma de cargas al cuadrado por la varianza explicada de cada PC usada, renormalizada para que las columnas sumen 1. "
        "`scaler_scale` es la escala que ajustó RobustScaler; en una columna de IQR 0 esa escala queda en 1."
    )
    lines.append("")
    diag = diagnostics.sort_values("peso_pc_share", ascending=False).copy()
    diag["zero_iqr"] = np.where(diag["zero_iqr"], "sí", "no")
    show = diag[
        [
            "feature",
            "var_within",
            "var_between",
            "ratio_between_within",
            "identical_frac",
            "n_unique",
            "iqr",
            "scaler_scale",
            "zero_iqr",
            "peso_pc_share",
        ]
    ].rename(
        columns={
            "feature": "columna",
            "ratio_between_within": "entre/dentro",
            "identical_frac": "idénticos",
            "n_unique": "valores",
            "scaler_scale": "escala",
            "zero_iqr": "IQR 0",
            "peso_pc_share": "peso PC",
        }
    )
    lines.append(
        _md_table(
            show,
            {
                "var_within": 6,
                "var_between": 6,
                "entre/dentro": 3,
                "idénticos": 3,
                "valores": "int",
                "iqr": 6,
                "escala": 4,
                "peso PC": 4,
            },
        )
    )
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--circuit", default="Italian Grand Prix")
    ap.add_argument("--session", default="R")
    ap.add_argument("--n-perm", type=int, default=200)
    ap.add_argument("--doc", default=str(_ROOT / "docs" / "separacion_nulo_monza_2025.md"))
    ap.add_argument("--tables", default=str(_ROOT / "docs" / "monza_2025_methodology"))
    args = ap.parse_args()

    cfg = load_config()
    circuits = load_circuit_config()
    event = resolve_event_name(args.circuit, circuits)
    enable_cache((cfg.get("general") or {}).get("cache_dir", "cache"))
    session = load_session(year=args.year, grand_prix=event, session_type=args.session)
    print(f"[1] {args.year} {event} {args.session}", flush=True)
    result = run_pipeline(session, config=cfg, circuit_config=circuits)
    if result.get("error"):
        raise SystemExit(result["error"])
    dest = session_output_dir(_ROOT / "results", args.year, event)
    write_session_outputs(result, dest, save_plots=True)
    print(f"[2] pipeline k={result.get('k_used')} regla={result.get('k_rule')} -> {dest}", flush=True)

    settings = _pipeline_settings(cfg)
    raw = result["df_raw"]
    numeric, _meta = separate_metadata(raw)
    print(f"[3] nulo columnas={numeric.shape[1]} vueltas={len(numeric)} perm={args.n_perm}", flush=True)
    summary, scores = silhouette_against_column_null(
        numeric,
        k_range=range(2, 8),
        n_perm=args.n_perm,
        progress_every=25,
        **settings,
    )
    match_delta = _check_matches_pipeline(summary, result.get("eval_df"))
    print(f"    |silueta - eval_df| max = {match_delta}", flush=True)
    if not np.isfinite(match_delta) or match_delta > 1e-8:
        raise SystemExit(f"la silueta del nulo no reproduce eval_df (delta={match_delta})")

    sets = sensitivity_column_sets(raw, list(numeric.columns))
    reduced = None
    reduced_scores: dict = {}
    if len(sets["kept"]) >= 2 and sets["dropped"]:
        print(f"[4] sensibilidad sin {sets['dropped']}", flush=True)
        reduced, reduced_scores = silhouette_against_column_null(
            numeric[sets["kept"]],
            k_range=range(2, 8),
            n_perm=args.n_perm,
            progress_every=25,
            **settings,
        )
    else:
        print("[4] sin columnas para apartar", flush=True)

    from f1_style_clustering.features.preprocessor import standardize_features
    from f1_style_clustering.models.dimensionality import pca_for_clustering

    scaled, _, scaler = standardize_features(numeric, scaler_type=settings["scaler_type"])
    _fit, pca, _info = pca_for_clustering(
        scaled,
        variance_threshold=settings["variance_threshold"],
        max_features_direct=settings["max_features_direct"],
        force=settings["force_pca"],
        random_state=settings["random_state"],
    )
    diag_source = raw.loc[scaled.index, ["Driver", *scaled.columns]]
    diagnostics = column_diagnostics(
        diag_source,
        feature_cols=list(scaled.columns),
        pca_model=pca,
        scaler=scaler,
    )

    tables = Path(args.tables)
    tables.mkdir(parents=True, exist_ok=True)
    summary.to_csv(tables / "null_separation_all.csv", index=False)
    if reduced is not None:
        reduced.to_csv(tables / "null_separation_no_iqr0.csv", index=False)
    diagnostics.to_csv(tables / "column_diagnostics.csv", index=False)
    long_rows = [{"variant": "all", "k": k, "rep": i, "silhouette": s} for k, vals in scores.items() for i, s in enumerate(vals)]
    long_rows += [
        {"variant": "no_iqr0", "k": k, "rep": i, "silhouette": s}
        for k, vals in reduced_scores.items()
        for i, s in enumerate(vals)
    ]
    pd.DataFrame(long_rows).to_csv(tables / "null_silhouette_replicates.csv", index=False)

    doc = Path(args.doc)
    write_report(
        doc,
        year=args.year,
        event=event,
        session_type=args.session,
        result=result,
        summary=summary,
        reduced=reduced,
        sets=sets,
        diagnostics=diagnostics,
        match_delta=match_delta,
        n_perm=args.n_perm,
    )
    print(f"[5] {doc}", flush=True)
    print(summary.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
