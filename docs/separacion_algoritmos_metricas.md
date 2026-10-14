# Separación de clases: algoritmos y métricas alternativas (Monza 2025)

Pregunta: ¿se pueden separar mejor las vueltas de Monza 2025 que con el K-means++ del pipeline (silueta 0.2326 en k=2, DB 1.82, regla `davies_bouldin`)? Se probaron otros conjuntos de features, otras unidades de muestra, otros algoritmos y otras métricas sobre la misma matriz: 842 vueltas, 19 pilotos, 17 columnas de estilo, onset apagado, sin residualizar equipo ni neumático (`docs/monza_2025_throttle_onset_off.md`).

> **Corrección (ver `docs/metricas_telemetria.md`).** Las particiones de este documento usan la normalización por mediana de sesión, y separan fase de carrera: en el k=3 recomendado abajo la vuelta mediana por clase es 15 / 22 / 38, y en el k=2 del pipeline 33.5 / 12. La velocidad de ápice y el punto de frenado siguen la carga de combustible dentro de cada piloto. Con la normalización por vuelta sincronizada, en estas 7 columnas las clases quedan en la misma fase (vuelta mediana 22 / 27 / 28), la AMI con el piloto sube de 0.197 a 0.258–0.279 y HAM y LEC siguen juntos, con NOR, PIA y VER en otra clase. En la corrida principal del pipeline (17 columnas, `docs/monza_2025_throttle_onset_off.md`) no: HAM y LEC quedan en clases distintas y NOR, PIA y VER en la misma. Las conclusiones sobre algoritmos (ninguno supera a K-means sobre las mismas columnas; HDBSCAN, cuantiles y UMAP no ayudan) y sobre la selección por ICC siguen valiendo.

Script: `python scripts/monza_separation_benchmark.py`. Escribe `separation_benchmark.csv`, `feature_icc.csv`, `k_selectors.json` y `driver_energy_clusters.json` en `results/2025/italian_grand_prix/separation/`. Código: `features/screening.py`, `models/separation.py`, `models/alternatives.py`. El camino K-means de `pipeline.py` no se tocó.

## Resumen

1. **La silueta del pipeline es casi la de un nulo sin estructura conjunta.** Permutando cada columna por separado (se conservan las marginales, se destruye la correlación entre columnas) el mismo K-means llega a 0.205 en k=2 contra 0.233 observado. Para k=3 y k=4 la silueta observada queda *debajo* del nulo. Las 9 componentes PCA del espacio de ajuste no contienen clases; contienen marginales.
2. **El ruido vuelta a vuelta tapa la señal.** El ICC(1) por piloto —la fracción de varianza de cada columna que está *entre* pilotos— va de 0.60 (`medium__coast_frac`) a 0.00 (`medium__full_throttle_frac`). Siete columnas superan 0.25; las tres casi constantes (ceros en más del 95 % de las vueltas) y el trail braking de curva rápida son ruido de vuelta.
3. **Lo que mejora la separación es filtrar features por ICC y promediar vueltas en bloques, no cambiar de algoritmo.** Con las 7 columnas de ICC ≥ 0.25 en z-score, K-means k=2 da silueta 0.256 contra nulo 0.112 (brecha +0.145, bootstrap ARI 0.95). Con medianas de bloques de 5 vueltas (161 filas), 0.308 contra 0.119 (brecha +0.189, bootstrap ARI 0.91). La AMI con el piloto sube de 0.05 a 0.13–0.28.
4. **Los selectores de k coinciden en k=3 para las 7 columnas por vuelta:** estadístico gap (k*=3), BIC y ICL de GMM con covarianza completa (3) e ICL diagonal (3). Prediction strength 0.88 en k=2 y 0.72 en k=3. En esa solución HAM y LEC quedan en una clase y NOR, PIA y VER en otra; el k=2 del pipeline los juntaba a los cinco.
5. **Lo que no sirve.** HDBSCAN no encuentra modos de densidad en ningún espacio (todo ruido). `QuantileTransformer` sube la silueta a 0.39 pero porque convierte los empates (`fast__coast_frac` = 0 en el 36 % de las vueltas) en grumos: los 4 clústeres son exactamente `fast__coast_frac == 0` × la moda de `slow__throttle_attack`. UMAP infla la silueta sólo en el embedding (0.45–0.51); en el espacio original queda en 0.10–0.24. Agregar a la mediana por piloto (19 puntos) da bootstrap ARI 0.26–0.60: inestable, como ya había mostrado el Pipeline B.
6. **Fuga de confusores.** En todas las particiones válidas la AMI con el compuesto es ≤ 0.02 y el reparto HARD/MEDIUM/SOFT por clase es el mismo. La AMI con el equipo acompaña a la del piloto (un piloto tiene un solo equipo). TyreLife mediana: 18.5 contra 13 vueltas en el k=2 de las 7 columnas, parecido al 19 contra 11 del pipeline.

## Métricas agregadas

Además de silueta, Davies-Bouldin y Calinski-Harabasz (`models/evaluation.py`), `models/separation.py` calcula:

| métrica | qué responde | lectura |
| --- | --- | --- |
| `hopkins_statistic` | ¿hay tendencia a agrupar? | 0.5 uniforme; cerca de 1 agrupado. Colas pesadas lo inflan: 0.87 en el espacio del pipeline, 0.75 con las 7 columnas de ICC. |
| `permutation_null_silhouette` / `silhouette_gap` | ¿cuánta silueta gana el algoritmo con las marginales solas? | Observada menos nulo, con z. Brecha ≈ 0 es partición de marginales. |
| `gap_statistic` / `select_k_gap` | k por dispersión intra contra referencia uniforme | Regla de un error estándar (Tibshirani). |
| `prediction_strength` | ¿una mitad predice la partición de la otra? | > 0.8 reproducible (Tibshirani y Walther). |
| `gmm_information_criteria` | k por BIC e ICL de mezclas gaussianas | ICL = BIC + 2 × entropía: penaliza componentes solapados. |
| `dunn_index` | peor separación entre clases / peor diámetro | Sensible a outliers; aquí 0.02–0.17. |
| `confounder_leakage` | AMI con Driver, Team, Compound; η² de TyreLife; fracción modal media por piloto | Una partición de estilo debe tener AMI piloto > 0 y AMI compuesto ≈ 0. |
| `bootstrap_label_stability` | ARI entre el ajuste de referencia y reajustes bootstrap | Sirve para cualquier algoritmo, con o sin `predict`. |
| `group_energy_distance_matrix` | distancia entre las nubes de vueltas de dos pilotos | `2E|A−B| − E|A−A'| − E|B−B'|`; el piloto como unidad sin colapsar a una mediana. |

`features/screening.py` agrega `icc_by_group` (ICC(1) y F por columna), `near_constant_columns`, `select_features_by_icc`, `icc_weights` (pesos `ICC^0.5` para una alternativa blanda al descarte) y `block_median_matrix` (medianas de bloques consecutivos, no solapados, por piloto).

`models/alternatives.py` pone detrás de una interfaz k-means, k-medianas, k-medoides (PAM), GMM completa y diagonal, Ward, enlace promedio y completo, enlace promedio coseno, espectral (afinidad kNN) y HDBSCAN; `cluster_groups_by_distribution` agrupa pilotos por distancia de energía; `benchmark_partitions` corre la grilla y devuelve una fila de métricas por ajuste.

## ICC(1) por piloto

| columna | ICC | F | ceros | valores únicos |
| --- | ---: | ---: | ---: | ---: |
| medium__coast_frac | 0.597 | 66.4 | 0.000 | 671 |
| slow__coast_frac | 0.503 | 45.7 | 0.001 | 829 |
| medium__trail_brake_frac | 0.359 | 25.8 | 0.000 | 842 |
| fast__coast_frac | 0.359 | 25.8 | 0.356 | 543 |
| fast__apex_speed_rel | 0.311 | 20.9 | 0.000 | 44 |
| medium__apex_speed_rel | 0.302 | 20.1 | 0.031 | 74 |
| slow__trail_brake_frac | 0.266 | 17.0 | 0.001 | 842 |
| slow__throttle_attack | 0.229 | 14.1 | 0.008 | 373 |
| medium__throttle_attack | 0.206 | 12.5 | 0.951 | 39 |
| fast__brake_point_rel | 0.155 | 9.1 | 0.001 | 838 |
| slow__brake_point_rel | 0.153 | 9.0 | 0.000 | 842 |
| slow__full_throttle_frac | 0.139 | 8.2 | 0.001 | 448 |
| medium__brake_point_rel | 0.139 | 8.1 | 0.000 | 842 |
| slow__apex_speed_rel | 0.103 | 6.1 | 0.152 | 25 |
| fast__trail_brake_frac | 0.061 | 3.9 | 0.002 | 841 |
| fast__full_throttle_frac | 0.021 | 1.9 | 0.998 | 3 |
| medium__full_throttle_frac | 0.003 | 1.1 | 0.995 | 5 |

El coast y la velocidad de ápice son lo que persiste de un piloto entre vueltas. El punto de frenado, que es lo que más pesa en los contrastes HAM/LEC y NOR/PIA del documento anterior, tiene un ICC de 0.14–0.16: el piloto explica una séptima parte; el resto es vuelta.

Casi constantes (`near_constant_columns`, ceros > 90 %): `fast__full_throttle_frac`, `medium__full_throttle_frac`, `medium__throttle_attack`. Seleccionadas con ICC ≥ 0.25 (`select_features_by_icc`): `fast__apex_speed_rel`, `medium__apex_speed_rel`, `fast__coast_frac`, `medium__coast_frac`, `slow__coast_frac`, `medium__trail_brake_frac`, `slow__trail_brake_frac`.

## Pipeline actual contra el nulo de permutación

Espacio del pipeline: 17 columnas, escalado robusto, 9 componentes PCA. K-means++, `n_init=20`, `random_state=42`. Nulo: 5 permutaciones independientes de columnas, mismo algoritmo.

| k | tamaños | silueta | nulo | brecha | DB | AMI piloto | fracción modal media |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 556, 286 | 0.233 | 0.205 | +0.028 | 1.82 | 0.053 | 0.716 |
| 3 | 341, 274, 227 | 0.129 | 0.155 | −0.026 | 1.93 | 0.114 | 0.603 |
| 4 | 305, 249, 186, 102 | 0.127 | 0.150 | −0.022 | 2.05 | 0.166 | 0.581 |
| 5 | 291, 239, 179, 87, 46 | 0.137 | 0.122 | +0.016 | 1.83 | 0.167 | 0.569 |

En ese mismo espacio ningún algoritmo supera una brecha de +0.06 con clústeres de al menos 43 vueltas (GMM completa k=3: 0.212 contra 0.155; el resto, menos). El estadístico gap elige k*=1. Prediction strength: 0.85 (k=2), 0.65 (k=3), 0.47 (k=4).

## Siete columnas por ICC, z-score, por vuelta

842 vueltas, 7 columnas, sin PCA (PCA a 4 componentes baja la brecha a +0.05: el nulo sube a 0.18 porque PCA ortogonaliza las marginales).

| algoritmo | k | tamaños | silueta | nulo | brecha | DB | Dunn | AMI piloto | AMI compuesto | fracción modal |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| k-means | 2 | 502, 340 | 0.256 | 0.112 | +0.145 | 1.54 | 0.062 | 0.126 | −0.001 | 0.782 |
| k-means | 3 | 311, 281, 250 | 0.204 | 0.109 | +0.094 | 1.50 | 0.053 | 0.198 | 0.009 | 0.698 |
| k-means | 4 | 250, 206, 195, 191 | 0.175 | 0.115 | +0.060 | 1.56 | 0.053 | 0.202 | 0.010 | 0.572 |
| k-medianas | 2 | 483, 359 | 0.241 | 0.089 | +0.152 | 1.59 | 0.073 | 0.131 | 0.000 | 0.783 |
| k-medianas | 3 | 309, 280, 253 | 0.186 | 0.078 | +0.107 | 1.55 | 0.062 | 0.217 | 0.004 | 0.698 |
| GMM completa | 2 | 461, 381 | 0.159 | 0.094 | +0.065 | 1.96 | 0.049 | 0.134 | −0.001 | 0.783 |
| Ward | 2 | 677, 165 | 0.260 | 0.084 | +0.176 | 1.46 | 0.095 | 0.123 | 0.007 | 0.866 |
| Ward | 3 | 429, 248, 165 | 0.154 | 0.071 | +0.083 | 1.75 | 0.081 | 0.180 | 0.015 | 0.706 |
| promedio coseno | 2 | 529, 313 | 0.235 | 0.082 | +0.153 | 1.62 | 0.075 | 0.151 | −0.001 | 0.820 |
| promedio coseno | 3 | 313, 285, 244 | 0.182 | 0.074 | +0.107 | 1.53 | 0.058 | 0.209 | 0.006 | 0.708 |
| espectral | 2 | 465, 377 | 0.244 | 0.095 | +0.149 | 1.58 | 0.073 | 0.137 | 0.000 | 0.780 |
| espectral | 3 | 303, 298, 241 | 0.199 | 0.090 | +0.109 | 1.47 | 0.047 | 0.208 | 0.011 | 0.698 |
| HDBSCAN | — | todo ruido | | | | | | | | |

Las particiones de k-means, k-medianas, espectral y coseno son casi la misma en k=2 y k=3; los algoritmos no cambian la respuesta, el conjunto de columnas sí. GMM pierde silueta porque ajusta densidad, no separación. El ARI entre el k=2 del pipeline y este k=2 es 0.36: no es la misma partición con mejor número.

Selectores de k: gap k*=3; BIC completa 3, BIC diagonal 6; ICL completa 3, ICL diagonal 3; prediction strength 0.88 / 0.72 / 0.43 / 0.56 para k=2..5. Bootstrap ARI del k-means: 0.95 (k=2), 0.81 (k=3).

### k=3: qué separa y quién cae dónde

Medianas crudas (ya restadas de la mediana de sesión por tipología) por clase:

| columna | 0 (281) | 1 (250) | 2 (311) |
| --- | ---: | ---: | ---: |
| fast__apex_speed_rel | −25.5 | −23.5 | −18.0 |
| medium__apex_speed_rel | −4.5 | −1.5 | 7.0 |
| fast__coast_frac | 0.024 | 0.000 | 0.007 |
| medium__coast_frac | 0.028 | −0.023 | −0.001 |
| slow__coast_frac | 0.047 | −0.022 | −0.008 |
| medium__trail_brake_frac | −0.034 | 0.069 | −0.011 |
| slow__trail_brake_frac | −0.028 | 0.028 | −0.004 |

Clase 0: menos velocidad de ápice, más coast, menos trail braking. Clase 1: velocidad de ápice neutra, casi sin coast, el trail braking más alto. Clase 2: la velocidad de ápice más alta, coast y trail braking neutros.

| piloto | 0 | 1 | 2 | total | modal | fracción |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ALB | 11 | 9 | 18 | 38 | 2 | 0.474 |
| ALO | 16 | 2 | 1 | 19 | 0 | 0.842 |
| ANT | 25 | 3 | 14 | 42 | 0 | 0.595 |
| BEA | 4 | 19 | 24 | 47 | 2 | 0.511 |
| BOR | 9 | 28 | 9 | 46 | 1 | 0.609 |
| COL | 22 | 4 | 17 | 43 | 0 | 0.512 |
| GAS | 9 | 18 | 18 | 45 | 1 | 0.400 |
| HAD | 21 | 8 | 18 | 47 | 0 | 0.447 |
| HAM | 3 | 33 | 12 | 48 | 1 | 0.688 |
| LAW | 46 | 1 | 0 | 47 | 0 | 0.979 |
| LEC | 0 | 32 | 14 | 46 | 1 | 0.696 |
| NOR | 4 | 2 | 42 | 48 | 2 | 0.875 |
| OCO | 0 | 45 | 2 | 47 | 1 | 0.957 |
| PIA | 11 | 0 | 36 | 47 | 2 | 0.766 |
| RUS | 12 | 8 | 25 | 45 | 2 | 0.556 |
| SAI | 5 | 30 | 11 | 46 | 1 | 0.652 |
| STR | 39 | 4 | 3 | 46 | 0 | 0.848 |
| TSU | 44 | 1 | 3 | 48 | 0 | 0.917 |
| VER | 0 | 3 | 44 | 47 | 2 | 0.936 |

HAM y LEC van a la clase 1 (trail braking); NOR, PIA y VER a la 2 (velocidad de ápice). El k=2 del pipeline los tenía a los cinco en la clase 0. GAS (0.400) y HAD (0.447) no tienen una clase clara. Compuesto por clase: HARD 0.54 / 0.52 / 0.51, MEDIUM 0.44 / 0.48 / 0.44, SOFT 0.03 / 0.00 / 0.05. TyreLife mediana 13 / 17 / 17.

### k=2

Clase 0 (502): ápice rápido, poco coast, más trail braking. Clase 1 (340): ápice lento, más coast, menos trail braking. Modal 1: ALO, ANT, COL, HAD, LAW, STR, TSU. Modal 0: el resto. LEC y VER 46/46 y 47/47 en la clase 0; LAW 46/47 en la 1. Compuesto por clase HARD 0.53 / 0.51, MEDIUM 0.44 / 0.47. TyreLife mediana 18.5 / 13.

## Bloques de 5 vueltas

`block_median_matrix`: mediana de 5 vueltas consecutivas por piloto, bloques no solapados, sólo bloques completos. 161 bloques (3 de ALO, 7 de ALB, 8 de ANT y COL, 9 del resto). Piso de tamaño `ceil(0.05 × 161) = 9`. Las mismas 7 columnas, z-score.

| algoritmo | k | tamaños | silueta | nulo | brecha | DB | AMI piloto | fracción modal |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| k-means | 2 | 101, 60 | 0.308 | 0.119 | +0.189 | 1.28 | 0.124 | 0.804 |
| k-means | 3 | 63, 49, 49 | 0.259 | 0.116 | +0.143 | 1.33 | 0.205 | 0.713 |
| k-means | 4 | 49, 41, 37, 34 | 0.238 | 0.121 | +0.118 | 1.32 | 0.253 | 0.653 |
| k-medianas | 2 | 103, 58 | 0.306 | 0.099 | +0.208 | 1.28 | 0.125 | 0.804 |
| k-medianas | 3 | 64, 50, 47 | 0.234 | 0.090 | +0.144 | 1.40 | 0.253 | 0.767 |
| Ward | 2 | 125, 36 | 0.298 | 0.094 | +0.204 | 1.21 | 0.171 | 0.916 |
| espectral | 2 | 100, 61 | 0.298 | 0.109 | +0.188 | 1.30 | 0.151 | 0.822 |
| espectral | 5 | 38, 37, 31, 28, 27 | 0.192 | 0.109 | +0.084 | 1.55 | 0.321 | 0.682 |
| HDBSCAN | — | todo ruido | | | | | | |

Selectores: gap k*=3; BIC 4 (completa y diagonal); ICL 3 (diagonal) y 4 (completa); prediction strength 0.78 / 0.56 / 0.47 / 0.45. Bootstrap ARI del k-means: 0.91 (k=2), 0.79 (k=3). Las clases de k=3 son las mismas que por vuelta (ápice lento + coast / trail braking / ápice rápido) y la clase modal de cada piloto coincide en 18 de 19 (BEA pasa de la 2 a la 1; ANT y GAS quedan empatados 4 a 4 entre dos clases en bloques).

El bloque de 5 reduce la varianza de vuelta sin bajar a 19 puntos. El costo: 161 filas en vez de 842 y la hipótesis de que el estilo no cambia dentro de 5 vueltas seguidas.

## Pilotos por distancia de energía

Distancia de energía entre las nubes de vueltas de cada par de pilotos (7 columnas de ICC, z-score), enlace promedio. Silueta sobre la matriz de distancias.

| k | silueta | grupos |
| --- | ---: | --- |
| 2 | 0.419 | {ALO, ANT, COL, HAD, LAW, STR, TSU} / {ALB, BEA, BOR, GAS, HAM, LEC, NOR, OCO, PIA, RUS, SAI, VER} |
| 3 | 0.307 | lo mismo, con OCO solo |
| 4 | 0.330 | {ALO, ANT, COL, HAD, LAW, STR, TSU} / {NOR, PIA, VER} / {ALB, BEA, BOR, GAS, HAM, LEC, RUS, SAI} / {OCO} |

Coincide con el k=2 por vuelta. El k=4 separa a NOR, PIA y VER de HAM y LEC, como el k=3 por vuelta, pero deja a OCO solo. ARI con bootstrap de vueltas dentro de piloto, k=3: 0.58. La unidad vuelve a ser el piloto (n = 19), con la ventaja de que la distancia ve la dispersión de las vueltas y no sólo su mediana.

## Lo que no mejoró la separación

**HDBSCAN.** Con `min_cluster_size` = 5 % de las filas y `min_samples` por defecto, todo es ruido en los 24 espacios. Con `min_samples=10` en robusto o z-score, también. La densidad de la nube es unimodal: no hay valles que un método de densidad pueda cortar. Sólo encuentra clústeres en el espacio de cuantiles, donde los empates fabrican la densidad.

**QuantileTransformer.** Silueta 0.394 (k=4, 6 componentes PCA) contra 0.277 en su propio nulo. Los cuatro clústeres son `fast__coast_frac == 0` (300 vueltas) contra `≠ 0`, cruzado con la moda de `slow__throttle_attack` (−8.75) y `slow__full_throttle_frac` (0.037). La transformación a normal manda cada empate a un mismo valor y separa esos grumos. No es estilo.

**UMAP (5 dimensiones, `n_neighbors` 15 y 50, `min_dist` 0).** Silueta en el embedding 0.42–0.51 con k-means; la misma partición medida en el espacio original da 0.10–0.24, debajo o igual al z-score directo. HDBSCAN sobre UMAP encuentra 2–5 clústeres con 34–189 vueltas de ruido y AMI piloto ≤ 0.22. UMAP cambia la geometría, no la información.

**LDA con el piloto como clase y después k-means sobre las vueltas.** AMI piloto 0.30 en k=5 (la más alta), pero la brecha sobre el nulo es +0.01 a +0.05: LDA blanquea el espacio y el nulo sube con la observada. Además usa la etiqueta de piloto para construir el espacio, así que la AMI con el piloto deja de ser una validación.

**Medianas por piloto (19 puntos).** Silueta 0.21–0.24 pero bootstrap ARI 0.26–0.60. Con n = 19 cualquier k parte de a uno o dos pilotos.

**PCA en el espacio de 7 columnas.** Baja la brecha de +0.145 a +0.05 (k=2). Con 7 columnas no hace falta, y rota las marginales de modo que el nulo sube.

**Z-score contra robusto.** Con las 7 columnas de ICC dan casi lo mismo (k-means k=2: 0.256 contra 0.243; brecha +0.145 contra +0.130). El escalado robusto fue necesario en la matriz de 17 por las columnas con IQR 0; sacadas esas columnas, deja de importar.

## Nota sobre el nulo de permutación

El nulo mide la silueta que el algoritmo saca de las marginales. Para métodos que aíslan outliers puede ser alto y errático: Ward k=2 en `no_const|zscore|lap` da nulo 0.406 porque en una matriz permutada corta dos vueltas contra 840. Leer la brecha junto con los tamaños y el piso de clase, no sola.

## Recomendación

1. Antes del clustering, calcular `icc_by_group` sobre la matriz de la sesión y quedarse con las columnas de ICC ≥ 0.25 que no sean casi constantes. En Monza son 7. El umbral está en `select_features_by_icc(min_icc=...)`; es un parámetro de la tesis, no una constante.
2. Z-score sobre esas columnas, sin PCA.
3. Reportar la silueta junto con `silhouette_gap` y `prediction_strength`, y el k con tres selectores (regla actual, gap, ICL). En Monza coinciden en k=3 (y en k=2 como alternativa con mayor brecha).
4. Para el perfil del piloto, usar la clase modal de los bloques de 5 vueltas o de las vueltas: dan la misma clase en 18 de 19. Los bloques estabilizan la silueta; las vueltas conservan el conteo por clase.
5. `confounder_leakage` como tabla fija de cada corrida: AMI con compuesto ≈ 0 es la evidencia de que la partición no es neumático.

La selección por ICC ya está en el pipeline (`features.feature_screening`), junto con la normalización por vuelta sincronizada que corrige la fuga de fase de carrera (`features.lap_synchronous`, `features.within_driver_tyre_effects`). La normalización y el ajuste de neumático están encendidos por defecto; la selección por ICC sigue apagada. El resultado de Monza con la configuración por defecto está en `docs/monza_2025_throttle_onset_off.md`.
