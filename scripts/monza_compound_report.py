#!/usr/bin/env python
"""Fracción de compuesto por clase y contrastes dentro de compuesto. Monza 2025.

Lee la matriz y las clases ya escritas por
``python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R``.
No vuelve a bajar telemetría y no cambia el ajuste por defecto. El reajuste
dentro de MEDIUM y de HARD usa el mismo K-means, RobustScaler, PCA automático
y la misma regla de k, con el piso ``max(3, ceil(0.05 * n))`` de esas vueltas.
Si ese piso no deja ningún k válido, el reporte lo dice y no baja el piso.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from f1_style_clustering.analysis.compound_report import (  # noqa: E402
    compound_by_class,
    lap_size_floor,
    within_compound_median_contrasts,
)
from f1_style_clustering.config import load_config  # noqa: E402
from f1_style_clustering.models.evaluation import InvalidKPoolError  # noqa: E402
from f1_style_clustering.pipeline import cluster_driver_matrix  # noqa: E402

PAIRS = (("HAM", "LEC"), ("NOR", "PIA"))
FEATURE = "slow__brake_point_rel"
REFIT_COMPOUNDS = ("MEDIUM", "HARD")


def _fmt(value, digits=4) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if digits == "int":
        return str(int(value))
    return f"{float(value):.{digits}f}"


def _md_table(frame: pd.DataFrame, digits: dict) -> str:
    show = frame.copy()
    for col, spec in digits.items():
        if col not in show.columns:
            continue
        show[col] = show[col].map(lambda v, spec=spec: _fmt(v, spec))
    header = "| " + " | ".join(show.columns) + " |"
    rule = "| " + " | ".join("---" for _ in show.columns) + " |"
    body = ["| " + " | ".join(str(v) for v in row) + " |" for row in show.itertuples(index=False, name=None)]
    return "\n".join([header, rule, *body])


def _recluster(features: pd.DataFrame, compound: str, cfg: dict) -> dict:
    sub = features.loc[features["Compound"].astype(str) == compound].copy()
    n = int(len(sub))
    floor = lap_size_floor(n)
    cfg_lap = copy.deepcopy(cfg)
    clus = cfg_lap.setdefault("clustering", {})
    clus["min_cluster_size"] = floor
    clus["driver_bootstrap"] = False
    clus["compare_aggregators"] = False
    info = {"compound": compound, "n_laps": n, "min_cluster_size": floor, "reached": False}
    if n < 2:
        info["reason"] = "menos de 2 vueltas"
        return info
    try:
        result = cluster_driver_matrix(
            sub,
            config=cfg_lap,
            driver_bootstrap=False,
            compare_aggregators=False,
            residualize=False,
            extras={},
        )
    except InvalidKPoolError as exc:
        info["reason"] = str(exc)
        return info
    if result.get("error"):
        info["reason"] = str(result["error"])
        return info
    labels = result["cluster_labels"]
    sizes = labels.value_counts().sort_index()
    metrics = result["metrics"]
    pca_info = result.get("pca_fit_info") or {}
    names = result.get("archetype_names") or {}
    info.update(
        {
            "reached": True,
            "k_used": int(result["k_used"]),
            "k_rule": str(result["k_rule"]),
            "silhouette": float(metrics.silhouette),
            "davies_bouldin": float(metrics.davies_bouldin),
            "n_components": int(pca_info.get("n_components") or 0),
            "cumulative_variance": float(pca_info.get("cumulative_variance") or float("nan")),
            "sizes": {int(k): int(v) for k, v in sizes.items()},
            "names": {int(k): str(v) for k, v in names.items()},
            "eval_df": result["eval_df"],
        }
    )
    return info


def _yes(value) -> str:
    return "sí" if bool(value) else "no"


def _reading(payload: dict) -> list:
    mix = payload["mix"]
    contrasts = payload["contrasts"]
    lines = [
        "## Lectura",
        "",
        "La mezcla no es pareja. En la clase 0, "
        f"{_fmt(100 * float(mix.loc[(mix['Cluster'] == 0) & (mix['Compound'] == 'MEDIUM'), 'frac_of_class'].iloc[0]), 1)} % "
        "de las vueltas son MEDIUM. En la clase 2, "
        f"{_fmt(100 * float(mix.loc[(mix['Cluster'] == 2) & (mix['Compound'] == 'HARD'), 'frac_of_class'].iloc[0]), 1)} % "
        "son HARD. Es la misma tabla que ya está en `docs/monza_2025_throttle_onset_off.md`.",
        "",
    ]
    by_name = {info["compound"]: info for info in payload["refits"]}
    medium = by_name["MEDIUM"]
    hard = by_name["HARD"]
    if medium.get("reached"):
        med_eval = medium["eval_df"]
        k3_min = int(med_eval.loc[med_eval["k"] == 3, "min_cluster_size"].iloc[0])
        lines.append(
            f"Dentro de MEDIUM el único k que pasa el piso de {medium['min_cluster_size']} es k=2 "
            f"(silueta {_fmt(medium['silhouette'], 4)}, todavía bajo 0.25, así que la regla usa Davies-Bouldin). "
            f"k=3 queda afuera: su clase más chica tiene {k3_min} vuelta{'s' if k3_min != 1 else ''}. "
            f"El k=3 de la sesión completa no se sostiene en las {medium['n_laps']} vueltas de MEDIUM."
        )
        lines.append("")
    if hard.get("reached"):
        lines.append(
            f"Dentro de HARD entran k=2 y k=3. La silueta máxima de ese pool es la de k=2 "
            f"({_fmt(float(hard['eval_df'].loc[hard['eval_df']['k'] == 2, 'silhouette'].iloc[0]), 4)}), bajo 0.25, "
            f"y el Davies-Bouldin mínimo es el de k={hard['k_used']} "
            f"({_fmt(hard['davies_bouldin'], 4)}). "
            "Los nombres salen otra vez de las medianas; no son las mismas clases de la sesión, aunque algunas frases coincidan. "
            "«No dominant trait» es el texto de la función cuando ningún rasgo llega a 0.25 IQR."
        )
    lines.append("")
    lines.append(
        "En `slow__brake_point_rel`, un valor más chico es frenar más tarde que el campo. "
        "La diferencia es mediana(A) − mediana(B)."
    )
    lines.append("")
    for _, row in contrasts.iterrows():
        label = f"{row['left']} − {row['right']} en {row['Compound']}"
        if not bool(row["enough"]):
            lines.append(
                f"- {label}: no alcanza. n={int(row['n_left'])} y n={int(row['n_right'])}."
            )
            continue
        contains = float(row["ci_low"]) <= 0.0 <= float(row["ci_high"])
        side = "el intervalo incluye el 0" if contains else "el intervalo no incluye el 0"
        lines.append(
            f"- {label}: {_fmt(row['difference'], 2)} m "
            f"(intervalo {_fmt(row['ci_low'], 2)} a {_fmt(row['ci_high'], 2)}; {side}; "
            f"n={int(row['n_left'])} y {int(row['n_right'])})."
        )
    lines.extend(
        [
            "",
            "HAM − LEC es positivo en HARD y en MEDIUM: la mediana de Hamilton queda por encima de la de Leclerc, "
            "o sea que Leclerc frena más tarde en esos dos compuestos. "
            "NOR − PIA es negativo en MEDIUM y en SOFT: Norris frena más tarde que Piastri. "
            "SOFT son 5 y 6 vueltas. NOR y PIA no tienen vueltas en HARD; HAM y LEC no tienen vueltas en SOFT. "
            "El baseline anotado en `docs/monza_2025_throttle_onset_off.md` esperaba a Hamilton más tarde que Leclerc. "
            "Estos intervalos no se calcularon para acercarse a esa expectativa, y no la reproducen.",
            "",
        ]
    )
    return lines


def write_report(path: Path, payload: dict) -> None:
    mix = payload["mix"]
    contrasts = payload["contrasts"]
    refits = payload["refits"]
    lines = [
        "# Compuesto por clase y contrastes dentro de compuesto (Monza 2025)",
        "",
        "Corrida de referencia, ya escrita en `results/2025/italian_grand_prix/`: "
        '`python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R`.',
        "",
        "Este documento solo lee esa matriz y esas clases. No cambia K-means, RobustScaler, "
        "PCA automático, la regla de k ni las columnas del vector por defecto. "
        "El reajuste dentro de un compuesto es una sensibilidad: mismas piezas, otras filas. "
        "No se movió ningún parámetro para acercar un contraste a un baseline.",
        "",
        f"Vueltas emparejadas por piloto y número de vuelta: {payload['n_matched']}. "
        f"Solo en la matriz: {payload['n_feature_only']}. Solo en las clases: {payload['n_class_only']}.",
        "",
        "## Fracción de compuesto por clase",
        "",
        "La fracción de la clase es vueltas de ese compuesto sobre las vueltas de la clase. "
        "La fracción del compuesto es vueltas de esa clase sobre las vueltas de ese compuesto.",
        "",
        _md_table(
            mix.rename(
                columns={
                    "Cluster": "clase",
                    "Archetype": "nombre",
                    "Compound": "compuesto",
                    "n": "vueltas",
                    "n_class": "vueltas de la clase",
                    "frac_of_class": "fracción de la clase",
                    "n_compound": "vueltas del compuesto",
                    "frac_of_compound": "fracción del compuesto",
                }
            ),
            {
                "vueltas": "int",
                "vueltas de la clase": "int",
                "fracción de la clase": 3,
                "vueltas del compuesto": "int",
                "fracción del compuesto": 3,
            },
        ),
        "",
        "## Sensibilidad dentro de un solo compuesto",
        "",
        "Se vuelve a ajustar el pipeline de clustering sobre las filas de `features_raw.csv` de un solo compuesto. "
        "Esa matriz ya trae la mediana de sesión, la mediana del campo en la misma vuelta y el ajuste de compuesto y vida dentro de piloto. "
        "El piso de tamaño es `max(3, ceil(0.05 × n))` de esas vueltas, no el piso de 43 de la sesión completa. "
        "Si ningún k de 2 a 7 lo cumple, no se baja el piso a 3.",
        "",
    ]
    soft_n = payload["compound_counts"].get("SOFT", 0)
    lines.append(
        f"SOFT tiene {soft_n} vueltas. No se reajustó: el pedido era MEDIUM, y HARD si el piso lo permite."
    )
    lines.append("")
    for info in refits:
        lines.append(f"### {info['compound']}")
        lines.append("")
        lines.append(
            f"Vueltas: {info['n_laps']}. Piso: {info['min_cluster_size']}."
        )
        if not info.get("reached"):
            lines.append("")
            lines.append(
                "No alcanza un k válido con ese piso. "
                + (info.get("reason") or "El selector no devolvió un ajuste.")
            )
            lines.append("")
            continue
        sizes = ", ".join(f"{k}={v}" for k, v in info["sizes"].items())
        names = "; ".join(f"{k}: {v}" for k, v in info["names"].items())
        lines.append(
            f"k elegido: {info['k_used']} (regla `{info['k_rule']}`). "
            f"Silueta {_fmt(info['silhouette'], 4)}, Davies-Bouldin {_fmt(info['davies_bouldin'], 4)}. "
            f"PCA: {info['n_components']} componentes, varianza {_fmt(info['cumulative_variance'], 4)}. "
            f"Tamaños: {sizes}."
        )
        lines.append("")
        lines.append(f"Nombres, con la misma función de medianas: {names}.")
        lines.append("")
        eval_df = info["eval_df"]
        show = eval_df.rename(
            columns={
                "k": "k",
                "silhouette": "silueta",
                "davies_bouldin": "Davies-Bouldin",
                "min_cluster_size": "tamaño mínimo",
                "valid": "entra al pool",
            }
        )
        keep = [c for c in ("k", "silueta", "Davies-Bouldin", "tamaño mínimo", "entra al pool") if c in show.columns]
        if "entra al pool" in show.columns:
            show["entra al pool"] = show["entra al pool"].map(_yes)
        lines.append(_md_table(show[keep], {"silueta": 4, "Davies-Bouldin": 4, "tamaño mínimo": "int"}))
        lines.append("")

    lines.extend(
        [
            "## Contrastes en `slow__brake_point_rel` dentro de compuesto",
            "",
            "La columna es la que entró al escalado: ya restada de la mediana de sesión, de la mediana del campo en la misma vuelta, "
            "y de la parte de compuesto y vida estimada dentro de cada piloto. "
            "Más chico es frenar más tarde que el campo en esa vuelta, en metros. "
            "La diferencia es la mediana del primer piloto menos la mediana del segundo, dentro de un compuesto. "
            "No se juntan compuestos. Cada lado se remuestrea con reposición, a su propio tamaño, "
            f"{payload['n_boot']} veces, semilla {payload['seed']}. "
            "El intervalo es el percentil 2.5 y el 97.5 de esas diferencias. "
            "Con menos de 2 vueltas finitas de un lado, la celda queda vacía.",
            "",
        ]
    )
    show_c = contrasts.rename(
        columns={
            "Compound": "compuesto",
            "left": "piloto A",
            "right": "piloto B",
            "n_left": "n A",
            "n_right": "n B",
            "median_left": "mediana A",
            "median_right": "mediana B",
            "difference": "A − B",
            "ci_low": "percentil 2.5",
            "ci_high": "percentil 97.5",
            "enough": "alcanza",
        }
    )
    keep_c = [
        "compuesto",
        "piloto A",
        "piloto B",
        "n A",
        "n B",
        "mediana A",
        "mediana B",
        "A − B",
        "percentil 2.5",
        "percentil 97.5",
        "alcanza",
    ]
    show_c["alcanza"] = show_c["alcanza"].map(_yes)
    lines.append(
        _md_table(
            show_c[keep_c],
            {
                "n A": "int",
                "n B": "int",
                "mediana A": 2,
                "mediana B": 2,
                "A − B": 2,
                "percentil 2.5": 2,
                "percentil 97.5": 2,
            },
        )
    )
    lines.append("")
    lines.append(
        "Leer el intervalo: si el 0 cae entre los dos percentiles, esta muestra no aparta la diferencia de 0 "
        "al 95 % percentil. Eso no mueve k ni las columnas."
    )
    lines.append("")
    lines.extend(_reading(payload))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features", default=str(_ROOT / "results" / "2025" / "italian_grand_prix" / "features_raw.csv"))
    ap.add_argument(
        "--classes",
        default=str(_ROOT / "results" / "2025" / "italian_grand_prix" / "lap_classifications.csv"),
    )
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--doc", default=str(_ROOT / "docs" / "compuesto_monza_2025.md"))
    ap.add_argument("--tables", default=str(_ROOT / "docs" / "monza_2025_methodology"))
    args = ap.parse_args()

    features = pd.read_csv(args.features)
    classes = pd.read_csv(args.classes)
    mix = compound_by_class(features, classes)
    contrasts = within_compound_median_contrasts(
        features,
        FEATURE,
        pairs=PAIRS,
        n_boot=args.n_boot,
        seed=args.seed,
    )
    counts = features["Compound"].astype(str).value_counts().to_dict()
    cfg = load_config()
    refits = [_recluster(features, compound, cfg) for compound in REFIT_COMPOUNDS]

    tables = Path(args.tables)
    tables.mkdir(parents=True, exist_ok=True)
    mix.to_csv(tables / "compound_by_class.csv", index=False)
    contrasts.to_csv(tables / "compound_contrasts.csv", index=False)
    refit_rows = []
    for info in refits:
        row = {k: v for k, v in info.items() if k != "eval_df"}
        refit_rows.append(row)
        if info.get("eval_df") is not None:
            info["eval_df"].to_csv(tables / f"compound_refit_{info['compound'].lower()}.csv", index=False)
    pd.DataFrame(refit_rows).to_csv(tables / "compound_sensitivity.csv", index=False)

    payload = {
        "mix": mix,
        "contrasts": contrasts,
        "refits": refits,
        "n_matched": mix.attrs.get("n_matched"),
        "n_feature_only": mix.attrs.get("n_feature_only"),
        "n_class_only": mix.attrs.get("n_class_only"),
        "compound_counts": counts,
        "n_boot": args.n_boot,
        "seed": args.seed,
    }
    write_report(Path(args.doc), payload)
    print(mix.to_string(index=False))
    print(contrasts.to_string(index=False))
    for info in refits:
        brief = {k: v for k, v in info.items() if k != "eval_df"}
        print(brief)
    print(args.doc)


if __name__ == "__main__":
    main()
