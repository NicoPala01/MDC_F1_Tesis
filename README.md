# Los datos al volante: Clasificación de pilotos de Fórmula 1 mediante clustering de perfiles observables

**Tesis de Maestría en Ciencia de Datos — Universidad Austral**  
**Autor:** Nicolás Palavecino  
**Tutor:** Ezequiel Nuske  
**Rama de trabajo:** `new-method` (Pipeline B; no causal)

---

## Descripción del Proyecto

Este repositorio contiene la arquitectura de software, algoritmos y notebooks de investigación para **describir perfiles / patrones observables** de telemetría de pilotos de Fórmula 1 mediante **clustering no supervisado** e **ingeniería de características** sobre señales de alta frecuencia (**FastF1**).

Los clústeres **no** son estilos causales. No se identifican autos idénticos, sinergia de neumáticos, *fit* auto–piloto ni decisiones de *scouting*/contratación. FastF1 **no** aporta carga de combustible ni *setup*; Team / Compound / TyreLife se residualizan cuando existen en el grano disponible y el resto se declara como confusor.

### Pipeline B (camino principal)

El clustering **no** se hace sobre una matriz frágil de una columna por curva numerada. El camino de método es:

**features por vuelta** → **normalización relativa tipología × sesión** (restar la mediana del grid por *slow/medium/fast*) → **agregación mediana por piloto** (`n_laps`; la media es un switch de sensibilidad) → **residualización Team (FE / *teammate-relative*) y Compound/TyreLife si hay columnas** → **espacio de ajuste**: 6–8 features con RobustScaler, o PCA de ajuste si se fuerza / hay más columnas (el PCA 2D es **solo visualización**) → **K-means++ con k por reglas** (solo el *pool* con `min_cluster_size`; silueta ≥ 0.25 o si no mínimo Davies-Bouldin) → **nombres de arquetipo mutuamente excluyentes** sobre el **mismo** espacio de ajuste.

Estabilidad adicional (no sustituye la de semillas):

- **Seed stability:** ARI medio entre inicializaciones K-means++.
- **Driver bootstrap / LOO:** re-muestreo o leave-one-out de **pilotos** (`n_eff ≈ n_drivers`), re-ajuste con el mismo `k_used`, ARI medio/std (y concordancia de perfiles opcional).
- **ΔARI mediana vs media:** misma sesión/filtros, *k* alineado; **no** es validación con compuesto Medium.

Features (calidad > forzar 10), en ZOI disjuntas (frenado | vértice | salida), unidad (piloto × vuelta × tipología):

1. `brake_point_rel`
2. `trail_brake_frac` (fracción espacial con `Brake==True`; en FastF1 `Brake` es bool)
3. `apex_speed_rel` (mín. Speed en ventana de apex; apex cinemático = argmin Speed)
4. `throttle_attack` (p95 ThrottleRate en salida, suavizado)
5. `coast_frac`
6. `full_throttle_frac`
7. `throttle_onset_rel` (opcional; la ventana incluye pre-apex)
8. `brake_point_iqr` (opcional, post-agregación)

`config/circuits.yaml` alimenta las ZOI (offsets, wrap-around en T1/última curva, buckets de tipología). `pick_quicklaps` es **solo push mode** (`--push-mode`), no el filtro canónico (`pick_accurate ∩ pick_wo_box ∩ pick_not_deleted ∩ pick_track_status` verde).

Pipeline C (clustering por vuelta) queda como stub de apéndice y **no** reemplaza este camino.

### Qué hace (y qué no hace) este pipeline

1. **Perfiles observables:** vectores cuantitativos reproducibles (punto de frenado relativo, velocidad en vértice, *trail braking*, ataque de acelerador) para describir patrones en telemetría de una sesión.
2. **Comparación intra-equipo:** distancias entre compañeros sobre el mismo espacio de features. Es descriptiva; **no** aísla un factor humano causal (el hardware no está identificado como idéntico; faltan *setup* y combustible).
3. **Sensibilidad estadística:** mediana vs media (ΔARI), bootstrap de pilotos, residualización parcial Team/Compound/TyreLife. **No** hay validación por compuesto Medium.
4. **Trabajo futuro (sin soporte actual):** estrategia de carrera, *scouting*/contratación, *car–driver fit*, sinergia de neumáticos. Esas aplicaciones no están identificadas en este código.

---

## Estructura del Repositorio

```text
MDC_F1_Tesis/
├── pyproject.toml                     # Configuración de paquete Python y dependencias (uv / pip)
├── requirements.txt                   # Congelado de dependencias
├── config/
│   ├── circuits.yaml                  # Tipologías de curva, ZOI y circuitos
│   └── pipeline_config.yaml           # Filtros, agregación mediana, k por reglas, bootstrap
│
├── src/
│   └── f1_style_clustering/           # Paquete Python modular principal
│       ├── config.py
│       ├── pipeline.py                # Orquestador Pipeline B + ΔARI + bootstrap + declaración
│       ├── data/
│       │   ├── loader.py              # Ingesta FastF1, cache y derivadas cinemáticas
│       │   └── filters.py             # Canónico verde; pick_quicklaps = push_mode
│       ├── features/
│       │   ├── zoi.py                 # Zonas de Interés disjuntas (Braking, Apex, Exit)
│       │   ├── metrics.py             # Métricas Pipeline B (relativas, trail espacial)
│       │   ├── aggregators.py         # Unidad tipología × sesión; mediana/media por piloto
│       │   └── preprocessor.py        # Tipología×sesión, residualización Team/tyre, RobustScaler
│       ├── models/
│       │   ├── dimensionality.py      # PCA de ajuste (umbral) vs PCA 2D de gráfico
│       │   ├── clustering.py          # K-Means++ ; seed stability + driver bootstrap/LOO
│       │   └── evaluation.py          # Silueta, DB, k por reglas, mean_median_kmeans_ari
│       ├── analysis/
│       │   ├── archetypes.py          # Namer if/elif sobre el espacio de ajuste
│       │   ├── teammates.py           # Distancias intra-equipo (descriptivo, no causal)
│       │   └── tire_synergy.py        # Exploratorio; no es validación del clustering
│       └── visualization/
│           ├── telemetry_plots.py
│           ├── radar_charts.py        # Radar = mismas 6–8 features de ajuste
│           ├── cluster_plots.py       # Scatter PCA 2D de visualización
│           └── corner_maps.py
│
├── notebooks/                         # Serie paso a paso (perfiles observables)
│   ├── 01_data_acquisition_and_exploration.ipynb
│   ├── 02_feature_engineering_and_zoi.ipynb
│   ├── 03_dimensionality_reduction_pca_tsne.ipynb
│   ├── 04_driver_clustering_and_archetypes.ipynb
│   ├── 05_teammate_and_strategy_applications.ipynb
│   └── archive/
│
├── scripts/
│   ├── run_pipeline.py                # CLI Pipeline B (bootstrap y ΔARI por defecto)
│   ├── generate_notebooks.py
│   └── export_results.py
│
└── tests/                             # pytest sintético (sin red FastF1; README no requerido)
    ├── test_features.py
    ├── test_models.py
    └── test_pipeline_b.py
```

---

## Instalación y Configuración del Entorno

El proyecto es compatible tanto con **`uv`** (recomendado) como con **`pip`**.

### Opción 1: Con `uv` (Recomendada)
```bash
# Crear entorno virtual e instalar dependencias en modo editable
uv venv
source .venv/bin/activate  # En Linux/macOS
# o en Windows PowerShell:
.venv\Scripts\activate

uv pip install -e ".[dev]"
```

### Opción 2: Con `pip` estándar
```bash
python -m venv .venv
.venv\Scripts\activate      # Windows

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

---

## Ejecución del Pipeline

### 1. Ejecutar Pipeline Completo (CLI)

Ingesta FastF1, features Pipeline B, clustering, bootstrap de pilotos, ΔARI mediana/media y gráficos. **No** descarga resultados inventados: hace falta cache/red FastF1 para una sesión real.

```bash
# Pipeline B: k por reglas; mediana por defecto; bootstrap de pilotos y ΔARI ON
python scripts/run_pipeline.py --season 2025 --circuit "Italian Grand Prix" --session R

# Sensibilidad media (misma sesión/filtros; k del run primario se alinea en ΔARI)
python scripts/run_pipeline.py --season 2025 --circuit "Italian Grand Prix" --session R --aggregator mean

# Override de k; push mode = pick_quicklaps (no es el filtro canónico)
python scripts/run_pipeline.py --season 2025 --circuit "Italian Grand Prix" --session R --k-clusters 3 --push-mode

# PCA como espacio de ajuste (distinto del PCA 2D de los plots)
python scripts/run_pipeline.py --season 2025 --circuit "Italian Grand Prix" --session R --pca-fit

# Apagar checks Sigma (siguen existiendo seed stability)
python scripts/run_pipeline.py --season 2025 --circuit "Italian Grand Prix" --session R \
  --no-driver-bootstrap --no-mean-median-ari --no-residualize
```

Salida esperada en consola (además de silueta / Davies-Bouldin / seed ARI):

- `Driver bootstrap (n_eff=…) mean ARI: …`
- `Mean vs median ΔARI (aligned k=…): …`
- `Confounding: residualized=[…]; fuel load and car setup are not in FastF1.`

Los CSV y figuras van a `results/`. No hay *hold-out* Medium como validación.

### 2. Ejecutar la Suite de Pruebas Unitarias
```bash
python -m pytest -v
```

Las pruebas son **sintéticas** (sin descargas FastF1). El README no forma parte de pytest.

### 3. Explorar en Jupyter Notebooks
```bash
jupyter lab
# o jupyter notebook
```
- **`01_data_acquisition_and_exploration.ipynb`**: Carga y validación de vueltas de telemetría.
- **`02_feature_engineering_and_zoi.ipynb`**: ZOI disjuntas, features Pipeline B y normalización tipología×sesión.
- **`03_dimensionality_reduction_pca_tsne.ipynb`**: PCA de **ajuste** (umbral de varianza) vs PCA/t-SNE de **visualización**.
- **`04_driver_clustering_and_archetypes.ipynb`**: K-means++ con k por reglas, arquetipos, radar 6–8, bootstrap.
- **`05_teammate_and_strategy_applications.ipynb`**: Comparación intra-equipo descriptiva (no estrategia causal).
