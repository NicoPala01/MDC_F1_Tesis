"""Simple dashboard: pick a Grand Prix and a driver, read the lap-class profile.

Run from the repo root after a pipeline session has written ``results/``::

    streamlit run app/dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402

from f1_style_clustering.analysis.dashboard_data import (  # noqa: E402
    discover_sessions,
    load_session_tables,
    metric_table,
)

DEFAULT_RESULTS = ROOT / "results"


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Perfil de vueltas", layout="centered")
    st.title("Perfil de vueltas")
    st.caption("La tendencia del piloto en el Gran Premio es la clase más frecuente de sus vueltas.")

    sessions = discover_sessions(DEFAULT_RESULTS)
    if not sessions:
        st.info(
            "No hay resultados para mostrar. Corré una sesión primero, por ejemplo "
            "`python scripts/run_pipeline.py --smoke`, y volvé a abrir este tablero."
        )
        return

    labels = [s["label"] for s in sessions]
    choice = st.selectbox("Circuito", labels, index=0)
    session = sessions[labels.index(choice)]
    profiles, distribution = load_session_tables(session)
    if profiles.empty or "Driver" not in profiles.columns:
        st.warning("Ese Gran Premio no tiene perfiles de piloto.")
        return

    driver_labels = []
    for _, row in profiles.iterrows():
        name = row["FullName"] if "FullName" in profiles.columns and pd.notna(row.get("FullName")) else row["Driver"]
        driver_labels.append(f"{name} ({row['Driver']})")
    picked = st.selectbox("Piloto", driver_labels, index=0)
    driver = profiles.iloc[driver_labels.index(picked)]
    code = driver["Driver"]

    full_name = driver["FullName"] if "FullName" in driver.index and pd.notna(driver.get("FullName")) else code
    team = driver["Team"] if "Team" in driver.index and pd.notna(driver.get("Team")) else "—"
    archetype = driver["Archetype"] if "Archetype" in driver.index else "—"
    modal_fraction = float(driver["modal_fraction"]) if "modal_fraction" in driver.index else float("nan")
    n_laps = int(driver["n_laps"]) if "n_laps" in driver.index and pd.notna(driver.get("n_laps")) else 0

    st.subheader(str(full_name))
    st.write(f"**Equipo:** {team}")
    st.write(f"**Gran Premio:** {session['label']}")
    st.write(f"**Perfil:** {archetype}")
    if pd.notna(modal_fraction):
        st.write(f"**Tendencia:** {modal_fraction:.0%} de {n_laps} vueltas clasificadas")

    dist = distribution[distribution["Driver"] == code].copy() if "Driver" in distribution.columns else pd.DataFrame()
    st.markdown("**Distribución de vueltas**")
    if dist.empty:
        st.write("Sin vueltas clasificadas para este piloto.")
    else:
        chart = dist.set_index("Archetype")["fraction"] * 100
        chart.name = "Porcentaje de vueltas"
        st.bar_chart(chart)
        show = dist[["Archetype", "n_laps_in_class", "fraction"]].copy()
        show["fraction"] = show["fraction"].map(lambda v: f"{v:.0%}")
        show = show.rename(
            columns={
                "Archetype": "Clase",
                "n_laps_in_class": "Vueltas",
                "fraction": "Fracción",
            }
        )
        st.dataframe(show, hide_index=True, use_container_width=True)

    metrics = metric_table(driver)
    st.markdown("**Métricas**")
    if metrics.empty:
        st.write("Este resultado no guardó medianas de telemetría.")
    else:
        st.dataframe(metrics, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
