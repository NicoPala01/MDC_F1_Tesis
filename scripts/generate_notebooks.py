"""Script to generate thesis jupyter notebooks (02 to 05) aligned with Pipeline B.

Live FastF1 cells are optional (need a local cache). CI does not re-download telemetry.
"""

import nbformat as nbf
from pathlib import Path


def create_notebook_02():
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    cells = []

    cells.append(nbf.v4.new_markdown_cell("""# 02 - Ingeniería de Características (Pipeline B) y ZOI disjuntas
**Tesis de Maestría en Ciencia de Datos - Universidad Austral**  
*Autor: Nicolás Palavecino | Tutor: Ezequiel Nuske*

---

## 1. Pipeline B (camino principal)
El comité de tesis aprobó **Pipeline B** frente a una matriz frágil *una columna por curva numerada* (p ≫ n):

1. Features **por vuelta** en ZOI disjuntas (frenado | vértice | salida), con wrap-around en T1 / última curva.
2. Unidad de normalización: **tipología × sesión** (slow / medium / fast). Se resta la **mediana** del grid en esa celda.
3. Agregación **mediana** por piloto (media disponible como switch de sensibilidad). Se reporta `n_laps`.
4. Conjunto de 6–8 features (calidad > forzar 10): `brake_point_rel`, `trail_brake_frac`, `apex_speed_rel`, `throttle_attack`, `coast_frac`, `full_throttle_frac`, más `throttle_onset_rel` (ventana pre-apex) y `brake_point_iqr` post-agregación.

`config/circuits.yaml` deja de ser un archivo muerto: alimenta offsets ZOI, buckets de tipología y curvas clave.

Filtros canónicos FastF1: `pick_accurate ∩ pick_wo_box ∩ pick_not_deleted ∩ pick_track_status('1')`.  
`pick_quicklaps` es **push mode** explícito, no la definición por defecto de vuelta limpia.

*Las celdas de carga FastF1 requieren cache local; no se re-descarga telemetría en CI.*
"""))

    cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from f1_style_clustering.config import load_config, load_circuit_config
from f1_style_clustering.data.loader import load_session, enable_cache
from f1_style_clustering.features.zoi import extract_circuit_zones, disjoint_zone_bounds
from f1_style_clustering.features.aggregators import (
    build_pipeline_b_feature_matrix,
    CORE_STYLE_FEATURES,
)
from f1_style_clustering.features.preprocessor import standardize_features, separate_metadata
from f1_style_clustering.visualization.telemetry_plots import plot_corner_telemetry_comparison

cfg = load_config()
circuits = load_circuit_config()
print('Pipeline:', cfg['pipeline']['name'], '| aggregation:', cfg['features']['aggregation'])
print('ZOI offsets:', circuits['default_zoi_offsets'])
print('Core features:', CORE_STYLE_FEATURES)

# Opcional: descomentar con cache FastF1 local
# enable_cache('cache')
# session = load_session(year=2025, grand_prix='Italian Grand Prix', session_type='R')
# print('Sesión cargada:', session.event.EventName)
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 2. ZOI disjuntas y wrap-around
Las ventanas ya no se solapan (el frenado termina donde empieza el apex). T1 usa distancia de pista modular.
"""))
    cells.append(nbf.v4.new_code_cell("""# Demostración sin FastF1: T1 cerca de la línea de meta
bounds = disjoint_zone_bounds(
    apex_distance=40.0,
    braking_pre_m=350.0,
    apex_pre_m=60.0,
    apex_post_m=60.0,
    exit_post_m=250.0,
    track_length=5000.0,
)
print(bounds)

# Con sesión FastF1 en cache:
# analysis_zones = extract_circuit_zones(session, circuit_config=circuits)
# print(f'Total de curvas: {len(analysis_zones)}')
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 3. Matriz Pipeline B (6–8 features relativas)
`build_pipeline_b_feature_matrix` aplica filtros canónicos, features por (vuelta × curva × tipología), resta la mediana tipología×sesión y agrega por piloto.
"""))
    cells.append(nbf.v4.new_code_cell("""# Con sesión en cache:
# df_raw = build_pipeline_b_feature_matrix(session, circuit_config=circuits, aggregation='median')
# print(df_raw.shape)
# display(df_raw.head())
# df_scaled, df_meta, scaler = standardize_features(df_raw, scaler_type='robust')
print('Ver tests/test_pipeline_b.py para el contrato de features sin red.')
"""))

    nb.cells = cells
    with open("notebooks/02_feature_engineering_and_zoi.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb, f)


def create_notebook_03():
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    cells = []

    cells.append(nbf.v4.new_markdown_cell("""# 03 - Reducción de Dimensionalidad (PCA de ajuste y t-SNE)
**Tesis de Maestría en Ciencia de Datos - Universidad Austral**  
*Autor: Nicolás Palavecino | Tutor: Ezequiel Nuske*

---

## 1. PCA como espacio de *fit*, no solo como gráfico 2D
Con **≤ 8 features estables** (Pipeline B) se clusteriza directo sobre RobustScaler / z-score.  
PCA entra al clustering **cuando hace falta** (umbral de varianza ~0.80–0.85), no como único mapa 2D de exhibición.

t-SNE sigue siendo una proyección no lineal **para visualización**, no para ajustar K-means.
"""))

    cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np

from f1_style_clustering.models.dimensionality import pca_for_clustering, perform_pca, perform_tsne

# Ilustración offline: 6 features → PCA de fit desactivado; 12 features + force → fit space
rng = np.random.default_rng(0)
df6 = pd.DataFrame(rng.normal(size=(20, 6)), columns=list('abcdef'))
fit6, _, info6 = pca_for_clustering(df6, variance_threshold=0.85)
print('≤8 features, PCA used:', info6['used'], 'shape', fit6.shape)

df12 = pd.DataFrame(rng.normal(size=(20, 12)), columns=[f'f{i}' for i in range(12)])
fit12, _, info12 = pca_for_clustering(df12, variance_threshold=0.80, force=True)
print('forced PCA used:', info12['used'], 'n_components', info12['n_components'], 'var', info12['cumulative_variance'])
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 2. Sesión FastF1 (opcional, requiere cache)
No re-ejecutar descargas en CI. Con cache local:

```python
from f1_style_clustering.pipeline import run_pipeline_b
from f1_style_clustering.data.loader import load_session, enable_cache
enable_cache('cache')
session = load_session(2025, 'Italian Grand Prix', 'R')
out = run_pipeline_b(session)
print(out['pca_fit_info'])
```
"""))

    nb.cells = cells
    with open("notebooks/03_dimensionality_reduction_pca_tsne.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb, f)


def create_notebook_04():
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    cells = []

    cells.append(nbf.v4.new_markdown_cell("""# 04 - Clustering Pipeline B y arquetipos mutuamente excluyentes
**Tesis de Maestría en Ciencia de Datos - Universidad Austral**  
*Autor: Nicolás Palavecino | Tutor: Ezequiel Nuske*

---

## 1. K-means++ con k por reglas (no `K_OPTIMAL = 3` como único camino)

- Barrido de k (YAML `k_range`, p.ej. 2–7).
- Si la silueta máxima **≥ 0.25** → ese k; si no → **mínimo Davies-Bouldin**.
- Tamaño mínimo de clúster **≥ 3**.
- DBSCAN solo como **prefiltro de outliers** opcional, no como partición principal.
- Nombres de arquetipo: reglas mutuamente excluyentes sobre las **6–8 features agregadas / centroides**.
- El **radar usa el mismo espacio** que el ajuste por defecto (no top-2 de ~60 columnas).
"""))

    cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
from sklearn.datasets import make_blobs

from f1_style_clustering.models.evaluation import select_k_rule_based
from f1_style_clustering.models.clustering import fit_kmeans
from f1_style_clustering.analysis.archetypes import (
    characterize_clusters,
    assign_archetype_names,
    radar_feature_list,
)

X, _ = make_blobs(n_samples=18, centers=3, cluster_std=0.25, random_state=0)
df = pd.DataFrame(X, columns=['brake_point_rel', 'apex_speed_rel'])
# Completar el espacio Pipeline B sintético
for col in ['trail_brake_frac', 'throttle_attack', 'coast_frac', 'full_throttle_frac']:
    df[col] = np.random.default_rng(0).normal(size=len(df))

k_star, eval_df, rule = select_k_rule_based(df, k_min=2, k_max=5, silhouette_threshold=0.25, min_cluster_size=3)
print('k* =', k_star, 'rule =', rule)
display(eval_df)

labels, _ = fit_kmeans(df, n_clusters=k_star)
profiles = characterize_clusters(df, labels)
names = assign_archetype_names(profiles)
print(names)
print('Radar features:', radar_feature_list(df))
assert len(set(names.values())) == len(names)
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 2. Ejecución completa con FastF1 (cache local, no CI)

```python
from f1_style_clustering.pipeline import run_pipeline_b
out = run_pipeline_b(session)  # k por reglas
print(out['k_used'], out['k_rule'], out['archetype_names'])
```

Override explícito: `run_pipeline_b(session, k_clusters=3)` o `--k-clusters 3` en el CLI.
"""))

    nb.cells = cells
    with open("notebooks/04_driver_clustering_and_archetypes.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb, f)


def create_notebook_05():
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    cells = []

    cells.append(nbf.v4.new_markdown_cell("""# 05 - Aplicaciones: teammates y estrategia (espacio Pipeline B)
**Tesis de Maestría en Ciencia de Datos - Universidad Austral**  
*Autor: Nicolás Palavecino | Tutor: Ezequiel Nuske*

---

Comparaciones intra-equipo y matrices de distancia se calculan sobre las **mismas 6–8 features relativas** usadas para clusterizar, no sobre un radar de columnas por curva.

Pipeline C (clustering de vueltas) permanece como stub de apéndice (`analysis/pipeline_c.py`) y no sustituye este camino.
"""))

    cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np

from f1_style_clustering.analysis.teammates import compare_teammates, compute_intra_team_deltas
from f1_style_clustering.visualization.radar_charts import plot_driver_radar_comparison

df = pd.DataFrame({
    'brake_point_rel': [0.4, -0.3, 0.1, -0.2],
    'trail_brake_frac': [0.2, -0.1, 0.0, 0.1],
    'apex_speed_rel': [-0.2, 0.5, 0.1, 0.0],
    'throttle_attack': [0.3, 0.1, -0.4, 0.2],
    'coast_frac': [0.0, -0.1, 0.2, 0.0],
    'full_throttle_frac': [0.2, 0.0, -0.3, 0.1],
}, index=['VER', 'PER', 'NOR', 'PIA'])
meta = pd.DataFrame({'Team': ['Red Bull', 'Red Bull', 'McLaren', 'McLaren']}, index=df.index)

pairs = compare_teammates(df, meta)
display(pairs[['Team', 'Driver_1', 'Driver_2', 'Style_Euclidean_Distance']])
display(compute_intra_team_deltas(df, 'NOR', 'PIA').head())
"""))

    cells.append(nbf.v4.new_markdown_cell("""## FastF1 (opcional)
Con cache local, `run_pipeline_b(session)` expone `df_scaled` y `df_meta` para `compare_teammates`. No re-descargar en CI.
"""))

    nb.cells = cells
    with open("notebooks/05_teammate_and_strategy_applications.ipynb", "w", encoding="utf-8") as f:
        nbf.write(nb, f)


def main():
    Path("notebooks").mkdir(parents=True, exist_ok=True)
    create_notebook_02()
    create_notebook_03()
    create_notebook_04()
    create_notebook_05()
    print("Notebooks 02–05 aligned with Pipeline B.")


if __name__ == "__main__":
    main()
