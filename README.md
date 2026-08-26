# Los datos al volante: Clasificación de pilotos de Fórmula 1 mediante clustering de estilos de conducción

**Tesis de Maestría en Ciencia de Datos — Universidad Austral**  
**Autor:** Nicolás Palavecino  
**Tutor:** Ezequiel Nuske  
**Rama:** `refactor/ag-version`

---

## 🏎️ Descripción del Proyecto

Este repositorio contiene la arquitectura de software, algoritmos y notebooks de investigación aplicados a la clasificación objetiva de estilos de conducción de pilotos de Fórmula 1 mediante técnicas de **Aprendizaje No Supervisado (Clustering)** e **Ingeniería de Características** sobre señales de telemetría de alta frecuencia (**FastF1**).

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
│   ├── run_pipeline.py                # Pipeline CLI ejecutable de punta a punta
│   ├── generate_notebooks.py          # Generador/actualizador de notebooks
│   └── export_results.py              # Exportador de reportes ejecutivos
│
└── tests/                             # Suite de pruebas unitarias automatizadas (pytest)
    ├── test_features.py               # Tests para métricas cinemáticas y preprocesamiento
    └── test_models.py                 # Tests para PCA, t-SNE, K-Means, GMM y Teammates
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
# Ejemplo: Temporada 2025 - Gran Premio de Italia (Carrera) con k=3 clústeres
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
- **`02_feature_engineering_and_zoi.ipynb`**: Extracción de Zonas de Interés (ZOI) y cálculo de Z-scores.
- **`03_dimensionality_reduction_pca_tsne.ipynb`**: PCA, loadings factoriales y t-SNE.
- **`04_driver_clustering_and_archetypes.ipynb`**: K-Means, GMM, métricas de silueta y radares de estilo.
- **`05_teammate_and_strategy_applications.ipynb`**: Comparación intra-equipo y matrices de compatibilidad.
