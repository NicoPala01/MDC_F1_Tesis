# Los datos al volante

Tesis de Maestría en Ciencia de Datos — Universidad Austral  
Autor: Nicolás Palavecino  
Tutor: Ezequiel Nuske

Clustering no supervisado de **perfiles observables** de telemetría FastF1. Los clústeres describen patrones de una sesión; no aíslan estilo causal (FastF1 no trae carga de combustible ni setup). Team / Compound / TyreLife se residualizan cuando existen.

## Qué calcula

1. **Por carrera:** vueltas canónicas → ventanas ZOI en las curvas clave (frenado | vértice | salida) → features por fragmento, relativas a la mediana de la sesión por tipología → **un vector por vuelta** → K-means++ de las vueltas. El perfil del piloto es la **clase modal**: la que concentra más vueltas suyas. `driver_lap_distribution.csv` es el reparto.
2. **Temporada:** el mismo análisis en cada GP. La tendencia de temporada es el arquetipo modal más frecuente entre las carreras. `stability.csv` mide en cuántas el piloto coincide con esa tendencia. No hay un segundo clustering de vectores medianos.

Circuito de prueba: **Monza** (`Italian Grand Prix`). El resto de la temporada usa `key_corners` si el evento está en `config/circuits.yaml`; si no, fallback por curva FastF1 y colapso a slow/medium/fast.

## Instalación

Desde la raíz del repo (no desde `scripts/`). El paquete vive en `src/`; hay que instalarlo en el entorno activo:

```bash
python -m pip install -e ".[dev]"
```

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Corrida

```bash
# Monza 2025, una sesión
python scripts/run_pipeline.py --smoke

# Todas las carreras 2025 + clustering global
python scripts/run_pipeline.py --season 2025
```

Salida: `results/2025/italian_grand_prix/` (`lap_classifications.csv`, `driver_lap_distribution.csv`, `driver_profiles.csv`) y `results/2025/season/`.

Un GP suelto: `python scripts/run_pipeline.py --circuit "British Grand Prix"`.

Tablero (circuito y piloto, distribución y perfil del GP):

```bash
python -m pip install -e ".[dashboard]"
streamlit run app/dashboard.py
```

Tests (sintéticos, sin red): `python -m pytest -v`.

## Separación: algoritmos y métricas alternativas

`docs/separacion_algoritmos_metricas.md` compara, sobre la matriz de vueltas de Monza 2025, conjuntos de features (todas / sin casi-constantes / seleccionadas por ICC entre pilotos), escalados, unidad de muestra (vuelta / bloque de 5 vueltas) y algoritmos (K-means, k-medianas, k-medoides, GMM, Ward, enlace promedio coseno, espectral, HDBSCAN), con métricas que van más allá de silueta / Davies-Bouldin: silueta contra un nulo de columnas permutadas, estadístico gap, prediction strength, BIC/ICL, Dunn, AMI con piloto / equipo / compuesto, y estabilidad bootstrap.

```bash
python scripts/monza_separation_benchmark.py            # escribe results/2025/italian_grand_prix/separation/
python scripts/monza_separation_benchmark.py --quick    # sólo z-score, tres algoritmos
```

Código: `features/screening.py` (ICC, casi-constantes, bloques), `models/separation.py` (métricas), `models/alternatives.py` (algoritmos y benchmark).

## Métricas de telemetría y normalización

`docs/metricas_telemetria.md` evalúa cada métrica por lo que necesita una métrica de estilo: que separe a compañeros de equipo (mismo auto), que dé el mismo orden en las dos mitades de la carrera, y que no siga al compuesto, a la vida del neumático ni al número de vuelta. Hallazgo principal: con la mediana de sesión, las clases de Monza separan primera y segunda mitad de carrera, porque la velocidad de ápice y el punto de frenado siguen el combustible. Restar la mediana del campo en la misma vuelta lo corrige.

La normalización por vuelta sincronizada es la configuración principal. Valores por defecto en `config/pipeline_config.yaml`:

```yaml
features:
  lap_synchronous: true              # mediana del campo en la misma vuelta
  within_driver_tyre_effects: true   # compuesto y vida del neumático, estimados dentro de cada piloto
  extended_metrics: false            # liberación de freno → pleno, ápice → pleno, modulación, lift-and-coast
  feature_screening:                 # variante evaluada; la corrida principal usa las 17 columnas
    drop_near_constant: false
    min_icc: null
```

Resultado de Monza 2025 con esa configuración: `docs/monza_2025_throttle_onset_off.md` (k=3 por Davies-Bouldin). La corrida anterior, sólo con la mediana de sesión, separaba fase de carrera.

Con `extended_metrics: true`, las métricas extendidas van al perfil del piloto (`driver_extended_profile`), no a la matriz del K-means.

```bash
python scripts/export_lap_telemetry.py                        # telemetría de las vueltas canónicas en cache/derived/
python scripts/evaluate_candidate_features.py candidatas.csv  # puntaje de columnas nuevas (Driver, LapNumber, ...)
python experiments/telemetry_candidates/integrated/run.py     # comparación de normalizaciones y conjuntos
```

Los cinco estudios por familia (frenada, trazada X/Y, acelerador y marcha, normalización, granularidad y consistencia) están en `experiments/telemetry_candidates/<familia>/REPORT.md`.

## Notebooks

Ejecutar en orden con cache FastF1 local. El 04 solo lee resultados del CLI de temporada.

- `01_monza_laps_and_zoi.ipynb` — filtro, mapa ZOI, telemetría partida
- `02_monza_lap_profiles.ipynb` — tabla larga de features por zona
- `03_monza_clustering.ipynb` — exploración de k, PCA y radar
- `04_season_results.ipynb` — tendencia modal por GP y heatmap piloto × GP
