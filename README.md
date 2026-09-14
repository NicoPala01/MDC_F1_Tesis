# Los datos al volante: Clasificación de pilotos de Fórmula 1 mediante clustering de estilos de conducción

**Tesis de Maestría en Ciencia de Datos — Universidad Austral**  
**Autor:** Nicolás Palavecino  
**Tutor:** Ezequiel Nuske  
**Rama:** `refactor/pipeline-b-typology-median` (Pipeline B; base `refactor/ag-version`)

---

## 🏎️ Descripción del Proyecto

Este repositorio contiene la arquitectura de software, algoritmos y notebooks de investigación aplicados a la clasificación objetiva de estilos de conducción de pilotos de Fórmula 1 mediante técnicas de **Aprendizaje No Supervisado (Clustering)** e **Ingeniería de Características** sobre señales de telemetría de alta frecuencia (**FastF1**).

### Pipeline B (camino principal)

El clustering **no** se hace sobre una matriz frágil de una columna por curva numerada. El camino aprobado por el comité es:

**features por vuelta** → **normalización relativa tipología × sesión** (restar la mediana del grid) → **agregación mediana por piloto** (`n_laps`) → **PCA opcional en el espacio de ajuste** (umbral de varianza ~0.80–0.85; con 6–8 features se clusteriza directo sobre RobustScaler) → **K-means++ con k por reglas** (barrido; silueta ≥ 0.25 o si no mínimo Davies-Bouldin; tamaño mínimo de clúster ≥ 3) → **nombres de arquetipo mutuamente excluyentes** sobre esas 6–8 features (el radar usa el mismo espacio).

Features (calidad > forzar 10), en ZOI disjuntas (frenado | vértice | salida), preferentemente por (piloto × vuelta × tipología slow/medium/fast):

1. `brake_point_rel`
2. `trail_brake_frac` (fracción espacial con `Brake==True`; en FastF1 `Brake` es bool)
3. `apex_speed_rel` (mín. Speed en ventana de apex; apex cinemático = argmin Speed)
4. `throttle_attack` (p95 ThrottleRate en salida, suavizado)
5. `coast_frac`
6. `full_throttle_frac`
7. `throttle_onset_rel` (opcional; la ventana incluye pre-apex)
8. `brake_point_iqr` (opcional, post-agregación)

`config/circuits.yaml` alimenta las ZOI (offsets, wrap-around en T1/última curva, buckets de tipología). `pick_quicklaps` es un **push mode** explícito, no el filtro canónico por defecto (`pick_accurate ∩ pick_wo_box ∩ pick_not_deleted ∩ pick_track_status` verde). Media vs mediana es un switch de sensibilidad sobre la misma matriz.

Pipeline C (clustering por vuelta) queda como stub de apéndice y **no** reemplaza este camino.

### Objetivos Principales
1. **Caracterización Objetiva**: Desplazar la subjetividad de etiquetas tradicionales (*"agresivo"*, *"suave"*, *"técnico"*) por vectores cuantitativos reproducibles (Puntos de frenado normalizados, velocidad en vértice, tasa de aceleración, *trail braking*).
2. **Comparación Intra-Equipo (*Teammates*)**: Comparar pilotos con monoplazas técnicamente idénticos para aislar el factor humano y orientar configuraciones (*setups*) personalizadas.
3. **Optimización del Desarrollo y Sinergia de Neumáticos**: Evaluar la compatibilidad del monoplaza y la gestión térmica/degradación de gomas según el estilo del piloto.
4. **Scouting y Compatibilidad**: Marco analítico para evaluar contrataciones alineadas a la filosofía técnica de la escudería.

---

## 📁 Estructura del Repositorio

```text
MDC_F1_Tesis/
├── pyproject.toml                     # Configuración de paquete Python y dependencias (uv / pip)
├── requirements.txt                   # Congelado de dependencias
├── config/
│   ├── circuits.yaml                  # Definición de tipologías de curva y circuitos de prueba
│   └── pipeline_config.yaml           # Parámetros del pipeline (filtros, ZOI, clustering)
│
├── src/
│   └── f1_style_clustering/           # Paquete Python modular principal
│       ├── config.py                  # Gestor de configuraciones YAML
│       ├── data/
│       │   ├── loader.py              # Ingesta FastF1, cache y derivadas cinemáticas
│       │   └── filters.py             # Filtrado de vueltas limpias (quicklaps, banderas, outlaps)
│       ├── features/
│       │   ├── zoi.py                 # Extracción de Zonas de Interés (Braking, Apex, Exit)
│       │   ├── metrics.py             # Cálculo de métricas (BrakingDist, Decel, ApexSpeed, ThrottleRate)
│       │   ├── aggregators.py         # Agregación por piloto y matrices de sesión
│       │   └── preprocessor.py        # Normalización respecto a media y estandarización Z-score
│       ├── models/
│       │   ├── dimensionality.py      # PCA (varianza explicada, loadings) y t-SNE
│       │   ├── clustering.py          # K-Means, Clustering Jerárquico, GMM, DBSCAN
│       │   └── evaluation.py          # Silueta, Inercia / Codo, Davies-Bouldin, Calinski-Harabasz
│       ├── analysis/
│       │   ├── archetypes.py          # Caracterización y perfilado de clústeres
│       │   ├── teammates.py           # Comparación de compañeros de equipo (hardware idéntico)
│       │   └── tire_synergy.py        # Correlación estilo vs degradación de neumáticos en carrera
│       └── visualization/
│           ├── telemetry_plots.py     # Trazas sincronizadas multicanal (Velocidad, Freno, Throttle)
│           ├── radar_charts.py        # Gráficos de radar para arquetipos de estilo
│           ├── cluster_plots.py       # Scatter 2D/3D (PCA, t-SNE) y curvas de validación (Codo/Silueta)
│           └── corner_maps.py         # Visualización de trazadas y vértices de circuito
│
├── notebooks/                         # Serie de notebooks reproducibles paso a paso
│   ├── 01_data_acquisition_and_exploration.ipynb
│   ├── 02_feature_engineering_and_zoi.ipynb
│   ├── 03_dimensionality_reduction_pca_tsne.ipynb
│   ├── 04_driver_clustering_and_archetypes.ipynb
│   ├── 05_teammate_and_strategy_applications.ipynb
│   └── archive/                       # Notebooks exploratorios preexistentes archivados
│
├── scripts/
│   ├── run_pipeline.py                # Pipeline B CLI (tipología × mediana, k por reglas)
│   ├── generate_notebooks.py          # Generador/actualizador de notebooks
│   └── export_results.py              # Exportador de reportes ejecutivos
│
└── tests/                             # Suite de pruebas unitarias automatizadas (pytest)
    ├── test_features.py               # Tests para métricas cinemáticas y preprocesamiento
    ├── test_models.py                 # Tests para PCA, t-SNE, K-Means, GMM y Teammates
    └── test_pipeline_b.py             # Tests Pipeline B (ZOI, filtros, k, namer; sin red FastF1)
```

---

## ⚙️ Instalación y Configuración del Entorno

El proyecto es totalmente compatible tanto con **`uv`** (recomendado por rendimiento) como con **`pip`**.

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

## 🚀 Ejecución del Pipeline

### 1. Ejecutar Pipeline Completo (CLI)
Para ejecutar la ingesta, ingeniería de características, reducción dimensional, clustering, análisis de *teammates* y generación de gráficos:

```bash
# Pipeline B: k se elige por reglas salvo --k-clusters
python scripts/run_pipeline.py --season 2025 --circuit "Italian Grand Prix" --session R

# Sensibilidad media vs mediana (misma matriz) y override de k
python scripts/run_pipeline.py --season 2025 --circuit "Italian Grand Prix" --session R --aggregator mean
python scripts/run_pipeline.py --season 2025 --circuit "Italian Grand Prix" --session R --k-clusters 3
```

Los resultados numéricos (`.csv`) y figuras de alta resolución (`.png`) se guardarán en la carpeta `results/`.

### 2. Ejecutar la Suite de Pruebas Unitarias
```bash
python -m pytest -v
```

### 3. Explorar en Jupyter Notebooks
Inicia Jupyter y navega por la serie ordenada:
```bash
jupyter lab
# o jupyter notebook
```
- **`01_data_acquisition_and_exploration.ipynb`**: Carga y validación de vueltas de telemetría.
- **`02_feature_engineering_and_zoi.ipynb`**: ZOI disjuntas, features Pipeline B y normalización tipología×sesión.
- **`03_dimensionality_reduction_pca_tsne.ipynb`**: PCA como espacio de ajuste (umbral de varianza) y t-SNE para visualización.
- **`04_driver_clustering_and_archetypes.ipynb`**: K-means++ con k por reglas, arquetipos mutuamente excluyentes, radar 6–8.
- **`05_teammate_and_strategy_applications.ipynb`**: Comparación intra-equipo sobre el mismo espacio de features.
