"""Script to generate thesis jupyter notebooks (01 to 05)."""

import nbformat as nbf
from pathlib import Path


def create_notebook_02():
    nb = nbf.v4.new_notebook()
    nb.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
    cells = []

    cells.append(nbf.v4.new_markdown_cell("""# 02 - Ingeniería de Características y Segmentación por Zonas de Interés (ZOI)
**Tesis de Maestría en Ciencia de Datos - Universidad Austral**  
*Autor: Nicolás Palavecino | Tutor: Ezequiel Nuske*

---

## 1. Fundamento Teórico de la Ingeniería de Características
Para superar la subjetividad de etiquetas como *agresivo* o *suave*, descomponemos cada curva del circuito en tres **Zonas de Interés (ZOI)**:
1. **Fase de Frenado (*Braking Zone*)**: Desde la iniciación de la presión de freno hasta el vértice.
   - *Métricas*: Distancia de inicio de frenado al vértice ($m$), Máxima desaceleración longitudinal ($m/s^2$).
2. **Fase de Vértice (*Apex Zone*)**: Ventana espacial inmediata alrededor del punto de mínima distancia angular.
   - *Métricas*: Velocidad mínima en vértice ($km/h$), Nivel de *Trail Braking* (frenado en rotación).
3. **Fase de Salida (*Exit Zone*)**: Región de reaplicación del acelerador y tracción.
   - *Métricas*: Tasa máxima de aplicación del acelerador ($\\%/s$), Distancia al inicio de potencia positiva ($m$).

Posteriormente, aplicamos **Estandarización Z-score** para nivelar las magnitudes físicas y permitir la comparabilidad multidimensional.
"""))

    cells.append(nbf.v4.new_code_cell("""import fastf1 as ff1
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from f1_style_clustering.data.loader import load_session, enable_cache
from f1_style_clustering.features.zoi import extract_circuit_zones, get_corner_fragments
from f1_style_clustering.features.aggregators import build_session_feature_matrix
from f1_style_clustering.features.preprocessor import normalize_relative_to_mean, standardize_features
from f1_style_clustering.visualization.telemetry_plots import plot_corner_telemetry_comparison

enable_cache('cache')
session = load_session(year=2025, grand_prix='Italian Grand Prix', session_type='R')
print('Sesión cargada:', session.event.EventName)
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 2. Extracción Dinámica de Zonas de Interés (ZOI)"""))
    cells.append(nbf.v4.new_code_cell("""# Extraer ZOIs para todas las curvas del circuito
analysis_zones = extract_circuit_zones(session)
print(f'Total de curvas extraídas: {len(analysis_zones)}')
for c_name, z_info in list(analysis_zones.items())[:3]:
    print(f"{c_name}: Frenado {z_info['braking']}, Vértice {z_info['apex']}, Salida {z_info['exit']}")
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 3. Visualización de Perfiles Telemétricos en Curvas Clave"""))
    cells.append(nbf.v4.new_code_cell("""# Curva 1 (Variante del Rettifilo)
t1_zone = analysis_zones['Turn_1']
fig_t1 = plot_corner_telemetry_comparison(session, t1_zone, corner_title='Turn 1 - Rettifilo')
plt.show()
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 4. Construcción de la Matriz de Características de Pilotos"""))
    cells.append(nbf.v4.new_code_cell("""# Construir matriz de features agregada para toda la sesión
df_raw = build_session_feature_matrix(session, analysis_zones=analysis_zones)
print(f'Matriz de features crudas: {df_raw.shape[0]} pilotos x {df_raw.shape[1]} columnas')
display(df_raw.head())
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 5. Normalización y Estandarización a Z-Scores"""))
    cells.append(nbf.v4.new_code_cell("""# 1. Desviación relativa respecto a la media de la sesión
df_norm, df_meta = normalize_relative_to_mean(df_raw)

# 2. Estandarización Z-score (Media = 0, Desv. Est. = 1)
df_standardized, _, scaler = standardize_features(df_norm)

print('--- Matriz Estandarizada (Z-Scores) lista para Reducción y Clustering ---')
display(df_standardized.head())
"""))

    cells.append(nbf.v4.new_code_cell("""# Mapa de calor de características estandarizadas
plt.figure(figsize=(14, 7))
sns.heatmap(df_standardized.iloc[:, :12], cmap='coolwarm', center=0, annot=True, fmt='.2f', linewidths=0.5)
plt.title('Mapa de Calor de Z-Scores de Estilo de Conducción (Pilotos vs Métricas de Curva)', fontsize=12, fontweight='bold')
plt.xlabel('Métricas de Telemetría (Z-score)')
plt.ylabel('Piloto')
plt.tight_layout()
plt.show()
"""))

    nb.cells = cells
    with open('notebooks/02_feature_engineering_and_zoi.ipynb', 'w', encoding='utf-8') as f:
        nbf.write(nb, f)


def create_notebook_03():
    nb = nbf.v4.new_notebook()
    nb.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
    cells = []

    cells.append(nbf.v4.new_markdown_cell("""# 03 - Reducción de Dimensionalidad (PCA y t-SNE)
**Tesis de Maestría en Ciencia de Datos - Universidad Austral**  
*Autor: Nicolás Palavecino | Tutor: Ezequiel Nuske*

---

## 1. Fundamentos Matemáticos de la Reducción de Dimensionalidad
Dado que la ingeniería de características genera un espacio de alta dimensionalidad (múltiples curvas $\\times$ múltiples fases ZOI), el análisis enfrenta el riesgo del ruido y la multicolinealidad.
- **Análisis de Componentes Principales (PCA)**: Técnica lineal ortogonal que proyecta el espacio de características en direcciones de máxima varianza (autovectores de la matriz de covarianza), permitiendo evaluar la contribución (*loadings*) de cada señal.
- **t-Distributed Stochastic Neighbor Embedding (t-SNE)**: Técnica no lineal probabilística para preservar la estructura de vecindad local en bajas dimensiones.
"""))

    cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from f1_style_clustering.data.loader import load_session, enable_cache
from f1_style_clustering.features.zoi import extract_circuit_zones
from f1_style_clustering.features.aggregators import build_session_feature_matrix
from f1_style_clustering.features.preprocessor import normalize_relative_to_mean, standardize_features
from f1_style_clustering.models.dimensionality import perform_pca, compute_pca_loadings, perform_tsne
from f1_style_clustering.visualization.cluster_plots import plot_pca_biplot

enable_cache('cache')
session = load_session(year=2025, grand_prix='Italian Grand Prix', session_type='R')
analysis_zones = extract_circuit_zones(session)
df_raw = build_session_feature_matrix(session, analysis_zones=analysis_zones)
df_norm, df_meta = normalize_relative_to_mean(df_raw)
df_standardized, _, _ = standardize_features(df_norm)
print(f'Datos estandarizados listos: {df_standardized.shape}')
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 2. Análisis de Componentes Principales (PCA)"""))
    cells.append(nbf.v4.new_code_cell("""# Ajustar PCA con 2 componentes
df_pca, pca_model, pca_summary = perform_pca(df_standardized, n_components=2)
print(f"Varianza explicada por PC1: {pca_summary['explained_variance_ratio'][0]*100:.2f}%")
print(f"Varianza explicada por PC2: {pca_summary['explained_variance_ratio'][1]*100:.2f}%")
print(f"Varianza explicada acumulada: {pca_summary['cumulative_variance']*100:.2f}%")

display(df_pca.head(10))
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 3. Análisis de Cargas Factoriales (*Loadings*) y Biplot de PCA"""))
    cells.append(nbf.v4.new_code_cell("""# Calcular matriz de loadings
df_loadings = compute_pca_loadings(pca_model, df_standardized.columns.tolist())
print('--- Top 5 Features con mayor peso en PC1 ---')
display(df_loadings['PC1'].abs().sort_values(ascending=False).head(5))

# Biplot interactivo
fig_biplot = plot_pca_biplot(df_pca, df_loadings, top_n_features=6)
plt.show()
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 4. Proyección No Lineal con t-SNE"""))
    cells.append(nbf.v4.new_code_cell("""# Ajustar t-SNE
df_tsne, tsne_model = perform_tsne(df_standardized, n_components=2, perplexity=5.0)

plt.figure(figsize=(9, 7))
sns.scatterplot(data=df_tsne, x='TSNE1', y='TSNE2', s=160, color='#00d2be', edgecolor='black')
for drv in df_tsne.index:
    plt.annotate(drv, (df_tsne.loc[drv, 'TSNE1'] + 0.3, df_tsne.loc[drv, 'TSNE2'] + 0.3), fontsize=10, fontweight='bold')

plt.title('Proyección 2D t-SNE de Estilos de Conducción', fontsize=13, fontweight='bold')
plt.xlabel('t-SNE Dimensión 1')
plt.ylabel('t-SNE Dimensión 2')
plt.grid(True, linestyle=':', alpha=0.5)
plt.tight_layout()
plt.show()
"""))

    nb.cells = cells
    with open('notebooks/03_dimensionality_reduction_pca_tsne.ipynb', 'w', encoding='utf-8') as f:
        nbf.write(nb, f)


def create_notebook_04():
    nb = nbf.v4.new_notebook()
    nb.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
    cells = []

    cells.append(nbf.v4.new_markdown_cell("""# 04 - Clustering No Supervisado y Caracterización de Arquetipos
**Tesis de Maestría en Ciencia de Datos - Universidad Austral**  
*Autor: Nicolás Palavecino | Tutor: Ezequiel Nuske*

---

## 1. Fundamentos de Clustering No Supervisado
Para agrupar a los pilotos sin imponer etiquetas humanas preconcebidas, aplicamos y comparamos múltiples algoritmos:
- **K-Means**: Particionamiento por minimización de inercia intra-clúster.
- **Clustering Jerárquico Aglomerativo**: Agrupamiento jerárquico ascendente con criterio de enlace *Ward*.
- **Modelos de Mezclas Gaussianas (GMM)**: Asignación probabilística (*soft clustering*).
- **Métricas de Selección de $k$**: Método del Codo, Coeficiente de Silueta (*Silhouette Score*), Índice Davies-Bouldin y Calinski-Harabasz.
"""))

    cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from f1_style_clustering.data.loader import load_session, enable_cache
from f1_style_clustering.features.zoi import extract_circuit_zones
from f1_style_clustering.features.aggregators import build_session_feature_matrix
from f1_style_clustering.features.preprocessor import normalize_relative_to_mean, standardize_features
from f1_style_clustering.models.dimensionality import perform_pca
from f1_style_clustering.models.clustering import fit_kmeans, fit_agglomerative, fit_gmm
from f1_style_clustering.models.evaluation import find_optimal_k, evaluate_clustering
from f1_style_clustering.analysis.archetypes import characterize_clusters, assign_archetype_names, get_driver_archetype_summary
from f1_style_clustering.visualization.cluster_plots import plot_pca_clusters, plot_optimal_k_evaluation
from f1_style_clustering.visualization.radar_charts import plot_cluster_radar_chart

enable_cache('cache')
session = load_session(year=2025, grand_prix='Italian Grand Prix', session_type='R')
analysis_zones = extract_circuit_zones(session)
df_raw = build_session_feature_matrix(session, analysis_zones=analysis_zones)
df_norm, df_meta = normalize_relative_to_mean(df_raw)
df_standardized, _, _ = standardize_features(df_norm)
df_pca, _, pca_summary = perform_pca(df_standardized, n_components=2)
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 2. Determinación Objetiva del Número Óptimo de Clústeres ($k$)"""))
    cells.append(nbf.v4.new_code_cell("""# Evaluación en rango k in [2, 6]
df_eval = find_optimal_k(df_standardized, k_min=2, k_max=6)
display(df_eval)

fig_k = plot_optimal_k_evaluation(df_eval)
plt.show()
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 3. Ajuste de Modelos de Clustering y Visualización en Espacio PCA"""))
    cells.append(nbf.v4.new_code_cell("""# Ajustar K-Means con k=3
K_OPTIMAL = 3
cluster_labels, km_model = fit_kmeans(df_standardized, n_clusters=K_OPTIMAL)
metrics = evaluate_clustering(df_standardized, cluster_labels, km_model)

print(f"Silhouette Score: {metrics.silhouette:.3f} | Davies-Bouldin: {metrics.davies_bouldin:.3f}")

# Caracterización de arquetipos
profiles = characterize_clusters(df_standardized, cluster_labels)
archetype_names = assign_archetype_names(profiles)
df_summary = get_driver_archetype_summary(df_standardized, cluster_labels, df_meta)

display(df_summary)

# Visualización PCA con clústeres
fig_pca_clusters = plot_pca_clusters(df_pca, cluster_labels, pca_summary, archetype_names=archetype_names)
plt.show()
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 4. Perfilado de Arquetipos mediante Gráficos de Radar"""))
    cells.append(nbf.v4.new_code_cell("""# Gráfico de radar multidimensional
radar_features = [c for c in df_standardized.columns if 'ApexSpeed' in c or 'MaxDecel' in c or 'ThrottleRate' in c][:6]
fig_radar = plot_cluster_radar_chart(profiles, features=radar_features, archetype_names=archetype_names)
plt.show()
"""))

    nb.cells = cells
    with open('notebooks/04_driver_clustering_and_archetypes.ipynb', 'w', encoding='utf-8') as f:
        nbf.write(nb, f)


def create_notebook_05():
    nb = nbf.v4.new_notebook()
    nb.metadata['kernelspec'] = {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}
    cells = []

    cells.append(nbf.v4.new_markdown_cell("""# 05 - Aplicaciones Prácticas: Comparación Teammates, Puesta a Punto y Estrategia
**Tesis de Maestría en Ciencia de Datos - Universidad Austral**  
*Autor: Nicolás Palavecino | Tutor: Ezequiel Nuske*

---

## 1. Aplicaciones Prácticas según el Plan de Trabajo Final
En este notebook se abordan los tres objetivos específicos de la tesis:
1. **Comparación Intra-Equipo (*Teammates*)**: Comparar pilotos del mismo equipo para aislar el factor humano y diseñar puestas a punto (*setups*) personalizadas.
2. **Optimización de Inversiones y Desarrollo Técnico**: Identificar la sinergia entre la filosofía técnica del monoplaza y el estilo del piloto.
3. **Scouting y Compatibilidad de Contratación**: Marco objetivo para emparejar perfiles de conducción de pilotos potenciales con la ventana operativa del coche.
4. **Sinergia con Degradación de Neumáticos**: Relación entre agresividad de frenado/tracción y pendiente de degradación en carrera.
"""))

    cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from f1_style_clustering.data.loader import load_session, enable_cache
from f1_style_clustering.features.zoi import extract_circuit_zones
from f1_style_clustering.features.aggregators import build_session_feature_matrix
from f1_style_clustering.features.preprocessor import normalize_relative_to_mean, standardize_features
from f1_style_clustering.models.clustering import fit_kmeans
from f1_style_clustering.analysis.archetypes import characterize_clusters, assign_archetype_names
from f1_style_clustering.analysis.teammates import compare_teammates, compute_intra_team_deltas
from f1_style_clustering.visualization.radar_charts import plot_driver_radar_comparison

enable_cache('cache')
session = load_session(year=2025, grand_prix='Italian Grand Prix', session_type='R')
analysis_zones = extract_circuit_zones(session)
df_raw = build_session_feature_matrix(session, analysis_zones=analysis_zones)
df_norm, df_meta = normalize_relative_to_mean(df_raw)
df_standardized, _, _ = standardize_features(df_norm)
cluster_labels, _ = fit_kmeans(df_standardized, n_clusters=3)
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 2. Comparación Intra-Equipo (*Teammates* en Monoplazas Idénticos)"""))
    cells.append(nbf.v4.new_code_cell("""# Calcular distancias euclidianas y deltas de estilo entre compañeros de equipo
teammates_df = compare_teammates(df_standardized, df_meta)
print('--- Distancias de Estilo Intra-Equipo ---')
display(teammates_df[['Team', 'Driver_1', 'Driver_2', 'Style_Euclidean_Distance']].sort_values(by='Style_Euclidean_Distance', ascending=False))
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 3. Análisis de Detalle de Pareja de Compañeros (ej. McLaren / Ferrari / Mercedes)"""))
    cells.append(nbf.v4.new_code_cell("""# Seleccionar una pareja de compañeros para análisis detallado
if not teammates_df.empty:
    sample_pair = teammates_df.iloc[0]
    d1, d2 = sample_pair['Driver_1'], sample_pair['Driver_2']
    print(f"Analizando deltas detallados: {d1} vs {d2} ({sample_pair['Team']})")
    
    df_deltas = compute_intra_team_deltas(df_standardized, d1, d2)
    display(df_deltas.head(8))
    
    # Gráfico de radar comparativo
    radar_feats = [c for c in df_standardized.columns if 'ApexSpeed' in c or 'MaxDecel' in c or 'ThrottleRate' in c][:6]
    fig_comp = plot_driver_radar_comparison(df_standardized, drivers=[d1, d2], features=radar_feats, title=f"Comparación de Estilo: {d1} vs {d2}")
    plt.show()
"""))

    cells.append(nbf.v4.new_markdown_cell("""## 4. Matriz de Compatibilidad para Scouting y Scouting de Talento"""))
    cells.append(nbf.v4.new_code_cell("""# Matriz de distancia euclidiana entre todos los pilotos (para encontrar perfiles análogos)
from scipy.spatial.distance import cdist

dist_matrix = pd.DataFrame(
    cdist(df_standardized.values, df_standardized.values, metric='euclidean'),
    index=df_standardized.index,
    columns=df_standardized.index,
)

plt.figure(figsize=(11, 9))
sns.heatmap(dist_matrix, cmap='viridis_r', annot=True, fmt='.1f')
plt.title('Matriz de Disimilitud Euclidiana de Estilo de Conducción entre Pilotos', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.show()
"""))

    nb.cells = cells
    with open('notebooks/05_teammate_and_strategy_applications.ipynb', 'w', encoding='utf-8') as f:
        nbf.write(nb, f)


def main():
    Path("notebooks").mkdir(parents=True, exist_ok=True)
    create_notebook_02()
    create_notebook_03()
    create_notebook_04()
    create_notebook_05()
    print("All notebooks (02 to 05) created successfully!")


if __name__ == "__main__":
    main()

