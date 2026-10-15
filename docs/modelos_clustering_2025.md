# Modelos de clustering 2025

Comparación experimental sobre la matriz de vueltas ya normalizada y escalada. El K-means del pipeline no se toca.

## Declarado

Esto quedó escrito antes de leer cualquier resultado de esta comparación.

El camino es experimental. El K-means del pipeline sigue siendo el default: su rango sigue en 2 a 7 y su `n_init` sigue en 20. Este módulo no lo llama. La matriz es la de la temporada, ya normalizada y después el mismo RobustScaler, sin el PCA del clustering. `fast__brake_point_rel` queda afuera en cada GP. Monza suelta conserva la columna. No se sacan columnas de IQR 0.

El K de los modelos que eligen K va de 2 a 10. No se repite el tope en 7. La semilla es 42. Un candidato entra si tiene al menos dos clases y la clase más chica, sin contar el ruido, tiene al menos `max(3, ceil(0.05 * vueltas))` vueltas. Si ninguno entra, se reintenta con piso 3. Si tampoco, el modelo no elige. Entre los que entran, gana la silueta más alta y, si empatan, el K menor. El GMM no usa esa silueta para elegir: entre los candidatos que pasan el piso gana el BIC más bajo, después el K menor y después `full` antes que `diag`. Su `n_init` es 2, no el 20 de `docs/gmm_2025.md`, y aquí K empieza en 2. Covarianza `full` y `diag`, `reg_covar` 1e-6. K-means usa `n_init` 10. K-medians usa `n_init` 5 y 40 iteraciones. K-medoids usa `n_init` 3 y 30 iteraciones, con distancia euclídea. Ward y average son aglomerativos euclídeos y no tienen semilla. El espectral usa 10 vecinos, afinidad de vecinos más cercanos y `cluster_qr`. Fuzzy c-means usa m=2, `n_init` 3 y 100 iteraciones. HDBSCAN no elige K. Su `min_cluster_size` y su `min_samples` son `max(15, ceil(0.05 * vueltas))`. Si ese tamaño no cabe en la matriz, no se ajusta.

La batería, en cada GP y cada modelo, es la silueta euclídea de las vueltas que no son ruido, el DBCV solo en HDBSCAN, la fracción de ruido o de baja pertenencia, el tamaño de la clase mínima, el ARI medio entre réplicas bootstrap y el ARI contra el K-means de esta misma grilla. La baja pertenencia es una posterior o una membresía máxima estrictamente menor que 0.8. El 0.8 no cuenta. En HDBSCAN la fracción es la de etiquetas `-1`. En un modelo duro esa fracción es 0. El bootstrap son 20 remuestras, semilla 42, reajustando el K ya elegido y sin repetir la selección. El ARI de cada par se calcula en la intersección de las filas originales, sin el ruido. No entra en los nulos. El ARI contra K-means usa todas las etiquetas, ruido incluido. Si el K-means de la grilla no elige, ese ARI no se define. En la fila K-means el ARI es 1.

Hay estructura solo si el estadístico real supera el percentil 95 de los tres nulos. En HDBSCAN ese estadístico es el DBCV. En el resto es la silueta. No se mezclan. El umbral es el cuantil lineal de numpy y la comparación es estricta. Al lado se imprime el porcentaje de réplicas finitas con estadístico menor o igual que el real. Los nulos son los del PR 11, 50 réplicas, con la selección completa en cada réplica. La permutación reordena cada columna antes del escalador, semilla 42. El gaussiano se sortea en la matriz ya escalada y no se vuelve a escalar, semilla 43. La cópula se sortea antes del escalador y después se vuelve a ajustar el RobustScaler, semilla 44. El 50 quedó fijado porque una grilla sintética de 1275 por 16 tarda alrededor de cuatro segundos: 50 réplicas de los tres nulos entran en el costo. No se bajó a 30 después de ver un percentil.

Una clase queda marcada si una feature concentra más de la mitad de la distancia L1 entre su media y la media de la matriz, y el IQR de esa feature dentro de la clase es a lo sumo 1e-8. Es una marca, no entra en el nulo. El consenso de un GP es estructura en al menos la mitad de los modelos de la grilla. Un modelo que no elige cuenta como que no tiene estructura. No se nombra una clase por la reputación de un piloto.

## Medido

Los números de esta sección salen de `python scripts/modelos_clustering_2025.py`. La batería y los nulos están en `docs/modelos_clustering_2025/resumen.csv` y `docs/modelos_clustering_2025/nulos.csv`. Las clases marcadas están en `docs/modelos_clustering_2025/clases.csv`.

| carrera | modelo | K | detalle | silueta | DBCV | fracción | tipo | tamaño mínimo | bootstrap | ARI K-means | supera los tres |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| Australia | kmeans | 2 |  | 0.184 |  | 0.000 | ninguna | 184 | 0.824 | 1.000 | no |
| Australia | kmedians | 2 |  | 0.171 |  | 0.000 | ninguna | 172 | 0.575 | 0.662 | sí |
| Australia | kmedoids | 2 |  | 0.154 |  | 0.000 | ninguna | 213 | 0.182 | 0.624 | no |
| Australia | gmm | 4 | full | 0.022 |  | 0.011 | baja pertenencia | 31 | 0.600 | 0.175 | no |
| Australia | ward | 2 |  | 0.135 |  | 0.000 | ninguna | 224 | 0.348 | 0.467 | no |
| Australia | average |  |  |  |  |  |  |  |  | no definido | no |
| Australia | spectral | 2 |  | 0.160 |  | 0.000 | ninguna | 217 | 0.334 | 0.696 | no |
| Australia | hdbscan |  | min=28 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Australia | fuzzy_cmeans | 2 |  | 0.150 |  | 1.000 | baja pertenencia | 253 | 0.775 | 0.558 | no |
| China | kmeans | 2 |  | 0.536 |  | 0.000 | ninguna | 63 | 1.000 | 1.000 | no |
| China | kmedians | 2 |  | 0.536 |  | 0.000 | ninguna | 63 | 0.902 | 1.000 | no |
| China | kmedoids | 2 |  | 0.536 |  | 0.000 | ninguna | 63 | 0.654 | 1.000 | no |
| China | gmm | 2 | diag | 0.182 |  | 0.000 | baja pertenencia | 21 | 0.693 | -0.024 | no |
| China | ward | 2 |  | 0.537 |  | 0.000 | ninguna | 60 | 0.883 | 0.962 | no |
| China | average |  |  |  |  |  |  |  |  | no definido | no |
| China | spectral | 2 |  | 0.536 |  | 0.000 | ninguna | 63 | 0.965 | 1.000 | no |
| China | hdbscan | 2 | min=21 | 0.583 | 0.007 | 0.107 | ruido | 34 | 0.987 | 0.817 | no |
| China | fuzzy_cmeans | 2 |  | 0.533 |  | 0.115 | baja pertenencia | 64 | 0.988 | 0.987 | no |
| Japón | kmeans | 2 |  | 0.761 |  | 0.000 | ninguna | 144 | 1.000 | 1.000 | no |
| Japón | kmedians | 2 |  | 0.761 |  | 0.000 | ninguna | 144 | 0.587 | 1.000 | no |
| Japón | kmedoids | 2 |  | 0.761 |  | 0.000 | ninguna | 144 | 0.704 | 1.000 | no |
| Japón | gmm | 3 | full | 0.142 |  | 0.003 | baja pertenencia | 121 | 0.655 | 0.614 | no |
| Japón | ward | 2 |  | 0.761 |  | 0.000 | ninguna | 144 | 1.000 | 1.000 | no |
| Japón | average | 2 |  | 0.761 |  | 0.000 | ninguna | 144 | 1.000 | 1.000 | no |
| Japón | spectral | 2 |  | 0.761 |  | 0.000 | ninguna | 144 | 1.000 | 1.000 | no |
| Japón | hdbscan | 2 | min=50 | 0.761 | 0.484 | 0.000 | ruido | 144 | 1.000 | 1.000 | no |
| Japón | fuzzy_cmeans | 2 |  | 0.761 |  | 0.000 | baja pertenencia | 144 | 1.000 | 1.000 | no |
| Baréin | kmeans | 2 |  | 0.155 |  | 0.000 | ninguna | 424 | 0.503 | 1.000 | no |
| Baréin | kmedians | 2 |  | 0.134 |  | 0.000 | ninguna | 454 | 0.606 | 0.528 | sí |
| Baréin | kmedoids | 2 |  | 0.168 |  | 0.000 | ninguna | 310 | 0.304 | 0.509 | sí |
| Baréin | gmm | 4 | full | 0.103 |  | 0.023 | baja pertenencia | 16 | 0.679 | 0.217 | no |
| Baréin | ward | 2 |  | 0.122 |  | 0.000 | ninguna | 421 | 0.247 | 0.519 | no |
| Baréin | average |  |  |  |  |  |  |  |  | no definido | no |
| Baréin | spectral | 2 |  | 0.160 |  | 0.000 | ninguna | 360 | 0.634 | 0.683 | no |
| Baréin | hdbscan |  | min=47 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Baréin | fuzzy_cmeans | 2 |  | 0.150 |  | 1.000 | baja pertenencia | 450 | 0.849 | 0.866 | sí |
| Arabia Saudita | kmeans | 2 |  | 0.135 |  | 0.000 | ninguna | 349 | 0.548 | 1.000 | no |
| Arabia Saudita | kmedians | 3 |  | 0.120 |  | 0.000 | ninguna | 227 | 0.710 | 0.309 | no |
| Arabia Saudita | kmedoids | 2 |  | 0.141 |  | 0.000 | ninguna | 238 | 0.270 | 0.120 | no |
| Arabia Saudita | gmm | 6 | diag | 0.075 |  | 0.089 | baja pertenencia | 94 | 0.532 | 0.224 | no |
| Arabia Saudita | ward | 2 |  | 0.188 |  | 0.000 | ninguna | 123 | 0.174 | 0.019 | no |
| Arabia Saudita | average |  |  |  |  |  |  |  |  | no definido | no |
| Arabia Saudita | spectral | 4 |  | 0.121 |  | 0.000 | ninguna | 110 | 0.411 | 0.230 | no |
| Arabia Saudita | hdbscan |  | min=40 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Arabia Saudita | fuzzy_cmeans | 2 |  | 0.123 |  | 1.000 | baja pertenencia | 383 | 0.428 | 0.030 | no |
| Miami | kmeans | 2 |  | 0.196 |  | 0.000 | ninguna | 25 | 0.552 | 1.000 | no |
| Miami | kmedians | 3 |  | 0.163 |  | 0.000 | ninguna | 23 | 0.558 | 0.417 | no |
| Miami | kmedoids | 3 |  | 0.129 |  | 0.000 | ninguna | 24 | 0.355 | 0.480 | no |
| Miami | gmm | 2 | full | 0.048 |  | 0.000 | baja pertenencia | 23 | 0.208 | -0.018 | no |
| Miami | ward | 2 |  | 0.177 |  | 0.000 | ninguna | 23 | 0.636 | 0.917 | no |
| Miami | average |  |  |  |  |  |  |  |  | no definido | no |
| Miami | spectral | 2 |  | 0.196 |  | 0.000 | ninguna | 25 | 0.963 | 1.000 | no |
| Miami | hdbscan |  | min=15 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Miami | fuzzy_cmeans | 3 |  | 0.153 |  | 1.000 | baja pertenencia | 20 | 0.336 | 0.352 | no |
| Emilia-Romaña | kmeans | 2 |  | 0.613 |  | 0.000 | ninguna | 100 | 0.976 | 1.000 | no |
| Emilia-Romaña | kmedians | 2 |  | 0.602 |  | 0.000 | ninguna | 108 | 0.879 | 0.947 | no |
| Emilia-Romaña | kmedoids | 2 |  | 0.617 |  | 0.000 | ninguna | 96 | 0.857 | 0.972 | no |
| Emilia-Romaña | gmm | 2 | full | 0.441 |  | 0.011 | baja pertenencia | 206 | 0.803 | 0.502 | no |
| Emilia-Romaña | ward | 2 |  | 0.606 |  | 0.000 | ninguna | 100 | 0.778 | 0.932 | no |
| Emilia-Romaña | average |  |  |  |  |  |  |  |  | no definido | no |
| Emilia-Romaña | spectral | 2 |  | 0.584 |  | 0.000 | ninguna | 120 | 0.907 | 0.873 | no |
| Emilia-Romaña | hdbscan |  | min=47 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Emilia-Romaña | fuzzy_cmeans | 2 |  | 0.602 |  | 0.098 | baja pertenencia | 108 | 0.961 | 0.947 | no |
| Mónaco | kmeans | 3 |  | 0.156 |  | 0.000 | ninguna | 226 | 0.876 | 1.000 | no |
| Mónaco | kmedians | 3 |  | 0.135 |  | 0.000 | ninguna | 244 | 0.700 | 0.657 | no |
| Mónaco | kmedoids | 3 |  | 0.151 |  | 0.000 | ninguna | 155 | 0.421 | 0.495 | no |
| Mónaco | gmm | 8 | diag | 0.055 |  | 0.304 | baja pertenencia | 59 | 0.429 | 0.300 | no |
| Mónaco | ward | 2 |  | 0.187 |  | 0.000 | ninguna | 289 | 0.498 | 0.310 | no |
| Mónaco | average |  |  |  |  |  |  |  |  | no definido | no |
| Mónaco | spectral | 2 |  | 0.213 |  | 0.000 | ninguna | 256 | 0.633 | 0.368 | no |
| Mónaco | hdbscan |  | min=59 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Mónaco | fuzzy_cmeans | 2 |  | 0.152 |  | 1.000 | baja pertenencia | 568 | 0.789 | 0.589 | sí |
| España | kmeans | 2 |  | 0.126 |  | 0.000 | ninguna | 433 | 0.562 | 1.000 | no |
| España | kmedians | 2 |  | 0.115 |  | 0.000 | ninguna | 435 | 0.474 | 0.659 | no |
| España | kmedoids | 2 |  | 0.141 |  | 0.000 | ninguna | 255 | 0.248 | 0.266 | no |
| España | gmm | 3 | full | -0.001 |  | 0.000 | baja pertenencia | 107 | 0.972 | 0.003 | no |
| España | ward | 2 |  | 0.155 |  | 0.000 | ninguna | 140 | 0.407 | 0.149 | no |
| España | average | 2 |  | 0.274 |  | 0.000 | ninguna | 4 | 0.309 | 0.002 | no |
| España | spectral | 2 |  | 0.166 |  | 0.000 | ninguna | 150 | 0.821 | 0.169 | sí |
| España | hdbscan |  | min=49 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| España | fuzzy_cmeans | 2 |  | 0.116 |  | 1.000 | baja pertenencia | 457 | 0.655 | 0.437 | no |
| Canadá | kmeans | 2 |  | 0.683 |  | 0.000 | ninguna | 93 | 0.989 | 1.000 | no |
| Canadá | kmedians | 2 |  | 0.674 |  | 0.000 | ninguna | 99 | 0.875 | 0.959 | no |
| Canadá | kmedoids | 3 |  | 0.123 |  | 0.000 | ninguna | 95 | 0.347 | 0.239 | no |
| Canadá | gmm | 2 | full | 0.506 |  | 0.000 | baja pertenencia | 180 | 0.997 | 0.576 | no |
| Canadá | ward | 2 |  | 0.702 |  | 0.000 | ninguna | 71 | 0.777 | 0.835 | no |
| Canadá | average | 2 |  | 0.666 |  | 0.000 | ninguna | 103 | 0.780 | 0.934 | no |
| Canadá | spectral | 2 |  | 0.565 |  | 0.000 | ninguna | 155 | 0.996 | 0.669 | no |
| Canadá | hdbscan |  | min=55 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Canadá | fuzzy_cmeans | 2 |  | 0.683 |  | 0.049 | baja pertenencia | 93 | 0.989 | 1.000 | no |
| Austria | kmeans | 2 |  | 0.268 |  | 0.000 | ninguna | 130 | 0.824 | 1.000 | no |
| Austria | kmedians | 2 |  | 0.117 |  | 0.000 | ninguna | 421 | 0.625 | 0.108 | no |
| Austria | kmedoids | 2 |  | 0.220 |  | 0.000 | ninguna | 190 | 0.184 | 0.677 | no |
| Austria | gmm | 7 | diag | 0.057 |  | 0.233 | baja pertenencia | 9 | 0.447 | 0.097 | no |
| Austria | ward | 2 |  | 0.291 |  | 0.000 | ninguna | 104 | 0.976 | 0.833 | sí |
| Austria | average | 2 |  | 0.549 |  | 0.000 | ninguna | 6 | 0.898 | -0.010 | no |
| Austria | spectral | 2 |  | 0.291 |  | 0.000 | ninguna | 104 | 0.979 | 0.845 | sí |
| Austria | hdbscan |  | min=50 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Austria | fuzzy_cmeans | 2 |  | 0.123 |  | 1.000 | baja pertenencia | 444 | 0.769 | 0.126 | no |
| Gran Bretaña | kmeans | 2 |  | 0.402 |  | 0.000 | ninguna | 39 | 0.996 | 1.000 | no |
| Gran Bretaña | kmedians | 2 |  | 0.095 |  | 0.000 | ninguna | 88 | 0.217 | -0.056 | no |
| Gran Bretaña | kmedoids | 2 |  | 0.099 |  | 0.000 | ninguna | 123 | 0.177 | -0.036 | no |
| Gran Bretaña | gmm | 7 | diag | 0.049 |  | 0.147 | baja pertenencia | 23 | 0.373 | 0.077 | no |
| Gran Bretaña | ward | 2 |  | 0.402 |  | 0.000 | ninguna | 39 | 0.989 | 1.000 | no |
| Gran Bretaña | average |  |  |  |  |  |  |  |  | no definido | no |
| Gran Bretaña | spectral | 2 |  | 0.402 |  | 0.000 | ninguna | 39 | 0.988 | 1.000 | no |
| Gran Bretaña | hdbscan |  | min=22 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Gran Bretaña | fuzzy_cmeans | 2 |  | 0.155 |  | 1.000 | baja pertenencia | 145 | 0.274 | 0.200 | no |
| Bélgica | kmeans | 2 |  | 0.097 |  | 0.000 | ninguna | 316 | 0.363 | 1.000 | no |
| Bélgica | kmedians | 2 |  | 0.081 |  | 0.000 | ninguna | 309 | 0.332 | 0.399 | no |
| Bélgica | kmedoids | 2 |  | 0.086 |  | 0.000 | ninguna | 286 | 0.133 | 0.388 | no |
| Bélgica | gmm | 6 | diag | 0.030 |  | 0.243 | baja pertenencia | 25 | 0.484 | 0.088 | no |
| Bélgica | ward | 2 |  | 0.077 |  | 0.000 | ninguna | 283 | 0.105 | -0.001 | no |
| Bélgica | average | 2 |  | 0.344 |  | 0.000 | ninguna | 3 | 0.365 | 0.003 | no |
| Bélgica | spectral | 2 |  | 0.084 |  | 0.000 | ninguna | 319 | 0.118 | 0.035 | no |
| Bélgica | hdbscan |  | min=37 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Bélgica | fuzzy_cmeans | 2 |  | 0.088 |  | 1.000 | baja pertenencia | 357 | 0.246 | 0.157 | no |
| Hungría | kmeans | 2 |  | 0.126 |  | 0.000 | ninguna | 535 | 0.354 | 1.000 | no |
| Hungría | kmedians | 2 |  | 0.116 |  | 0.000 | ninguna | 573 | 0.749 | 0.716 | no |
| Hungría | kmedoids | 2 |  | 0.083 |  | 0.000 | ninguna | 569 | 0.266 | 0.166 | no |
| Hungría | gmm | 2 | full | 0.356 |  | 0.011 | baja pertenencia | 83 | 0.303 | 0.041 | no |
| Hungría | ward |  |  |  |  |  |  |  |  | no definido | no |
| Hungría | average |  |  |  |  |  |  |  |  | no definido | no |
| Hungría | spectral | 2 |  | 0.494 |  | 0.000 | ninguna | 36 | 0.662 | -0.013 | no |
| Hungría | hdbscan |  | min=64 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Hungría | fuzzy_cmeans | 2 |  | 0.119 |  | 1.000 | baja pertenencia | 617 | 0.578 | 0.604 | no |
| Países Bajos | kmeans | 2 |  | 0.140 |  | 0.000 | ninguna | 408 | 0.836 | 1.000 | no |
| Países Bajos | kmedians | 2 |  | 0.127 |  | 0.000 | ninguna | 369 | 0.868 | 0.575 | no |
| Países Bajos | kmedoids | 3 |  | 0.113 |  | 0.000 | ninguna | 85 | 0.291 | 0.422 | no |
| Países Bajos | gmm | 9 | diag | 0.025 |  | 0.203 | baja pertenencia | 54 | 0.322 | 0.140 | no |
| Países Bajos | ward | 2 |  | 0.111 |  | 0.000 | ninguna | 401 | 0.468 | 0.521 | no |
| Países Bajos | average |  |  |  |  |  |  |  |  | no definido | no |
| Países Bajos | spectral | 3 |  | 0.139 |  | 0.000 | ninguna | 96 | 0.662 | 0.693 | no |
| Países Bajos | hdbscan |  | min=50 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Países Bajos | fuzzy_cmeans | 2 |  | 0.132 |  | 1.000 | baja pertenencia | 451 | 0.683 | 0.819 | no |
| Italia | kmeans | 2 |  | 0.123 |  | 0.000 | ninguna | 388 | 0.471 | 1.000 | sí |
| Italia | kmedians | 3 |  | 0.112 |  | 0.000 | ninguna | 247 | 0.740 | 0.348 | sí |
| Italia | kmedoids | 3 |  | 0.087 |  | 0.000 | ninguna | 256 | 0.290 | 0.364 | no |
| Italia | gmm | 2 | full | 0.232 |  | 0.000 | baja pertenencia | 52 | 0.675 | 0.013 | no |
| Italia | ward | 2 |  | 0.088 |  | 0.000 | ninguna | 411 | 0.134 | 0.349 | no |
| Italia | average |  |  |  |  |  |  |  |  | no definido | no |
| Italia | spectral | 2 |  | 0.110 |  | 0.000 | ninguna | 384 | 0.230 | 0.165 | no |
| Italia | hdbscan |  | min=44 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Italia | fuzzy_cmeans | 2 |  | 0.118 |  | 1.000 | baja pertenencia | 425 | 0.340 | 0.470 | sí |
| Monza suelta | kmeans | 2 |  | 0.118 |  | 0.000 | ninguna | 368 | 0.378 | 1.000 | no |
| Monza suelta | kmedians | 3 |  | 0.108 |  | 0.000 | ninguna | 231 | 0.723 | 0.330 | no |
| Monza suelta | kmedoids | 2 |  | 0.087 |  | 0.000 | ninguna | 416 | 0.234 | 0.196 | no |
| Monza suelta | gmm | 2 | full | 0.236 |  | 0.000 | baja pertenencia | 53 | 0.902 | 0.020 | no |
| Monza suelta | ward | 2 |  | 0.092 |  | 0.000 | ninguna | 308 | 0.130 | 0.187 | no |
| Monza suelta | average |  |  |  |  |  |  |  |  | no definido | no |
| Monza suelta | spectral | 2 |  | 0.111 |  | 0.000 | ninguna | 375 | 0.208 | 0.002 | no |
| Monza suelta | hdbscan |  | min=43 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Monza suelta | fuzzy_cmeans | 2 |  | 0.113 |  | 1.000 | baja pertenencia | 386 | 0.326 | 0.138 | no |
| Azerbaiyán | kmeans | 2 |  | 0.651 |  | 0.000 | ninguna | 84 | 0.960 | 1.000 | no |
| Azerbaiyán | kmedians | 3 |  | 0.625 |  | 0.000 | ninguna | 92 | 0.820 | 0.416 | no |
| Azerbaiyán | kmedoids | 3 |  | 0.626 |  | 0.000 | ninguna | 85 | 0.688 | 0.438 | no |
| Azerbaiyán | gmm | 4 | diag | 0.420 |  | 0.016 | baja pertenencia | 76 | 0.861 | 0.267 | no |
| Azerbaiyán | ward | 3 |  | 0.622 |  | 0.000 | ninguna | 102 | 0.906 | 0.391 | no |
| Azerbaiyán | average |  |  |  |  |  |  |  |  | no definido | no |
| Azerbaiyán | spectral | 3 |  | 0.604 |  | 0.000 | ninguna | 120 | 0.931 | 0.338 | no |
| Azerbaiyán | hdbscan | 2 | min=40 | 0.688 | 0.004 | 0.172 | ruido | 116 | 0.999 | 0.340 | no |
| Azerbaiyán | fuzzy_cmeans | 2 |  | 0.637 |  | 0.188 | baja pertenencia | 95 | 0.614 | 0.915 | no |
| Singapur | kmeans | 2 |  | 0.623 |  | 0.000 | ninguna | 74 | 0.984 | 1.000 | no |
| Singapur | kmedians | 2 |  | 0.591 |  | 0.000 | ninguna | 90 | 0.451 | 0.880 | no |
| Singapur | kmedoids | 3 |  | 0.102 |  | 0.000 | ninguna | 86 | 0.180 | 0.200 | no |
| Singapur | gmm | 2 | full | 0.325 |  | 0.000 | baja pertenencia | 231 | 0.796 | 0.346 | no |
| Singapur | ward | 2 |  | 0.631 |  | 0.000 | ninguna | 69 | 0.808 | 0.958 | no |
| Singapur | average | 2 |  | 0.776 |  | 0.000 | ninguna | 5 | 0.780 | 0.111 | no |
| Singapur | spectral | 2 |  | 0.566 |  | 0.000 | ninguna | 101 | 0.931 | 0.809 | no |
| Singapur | hdbscan |  | min=56 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Singapur | fuzzy_cmeans | 2 |  | 0.431 |  | 1.000 | baja pertenencia | 170 | 0.767 | 0.505 | no |
| Estados Unidos | kmeans | 2 |  | 0.383 |  | 0.000 | ninguna | 63 | 0.911 | 1.000 | no |
| Estados Unidos | kmedians | 4 |  | 0.108 |  | 0.000 | ninguna | 63 | 0.507 | 0.124 | no |
| Estados Unidos | kmedoids | 2 |  | 0.383 |  | 0.000 | ninguna | 63 | 0.219 | 1.000 | no |
| Estados Unidos | gmm | 2 | full | 0.332 |  | 0.000 | baja pertenencia | 77 | 0.596 | 0.875 | no |
| Estados Unidos | ward | 2 |  | 0.383 |  | 0.000 | ninguna | 63 | 1.000 | 1.000 | no |
| Estados Unidos | average |  |  |  |  |  |  |  |  | no definido | no |
| Estados Unidos | spectral | 2 |  | 0.383 |  | 0.000 | ninguna | 63 | 1.000 | 1.000 | no |
| Estados Unidos | hdbscan |  | min=45 |  |  | 1.000 | ruido | 0 | 1.000 | 0.000 | no |
| Estados Unidos | fuzzy_cmeans | 2 |  | 0.121 |  | 1.000 | baja pertenencia | 380 | 0.733 | 0.070 | no |
| Ciudad de México | kmeans | 2 |  | 0.843 |  | 0.000 | ninguna | 3 | 0.462 | 1.000 | no |
| Ciudad de México | kmedians | 2 |  | 0.313 |  | 0.000 | ninguna | 112 | 0.601 | -0.005 | sí |
| Ciudad de México | kmedoids | 2 |  | 0.345 |  | 0.000 | ninguna | 116 | 0.407 | 0.024 | sí |
| Ciudad de México | gmm | 2 | full | 0.070 |  | 0.253 | baja pertenencia | 383 | 0.286 | 0.003 | no |
| Ciudad de México | ward | 2 |  | 0.843 |  | 0.000 | ninguna | 3 | 0.490 | 1.000 | no |
| Ciudad de México | average | 2 |  | 0.843 |  | 0.000 | ninguna | 3 | 0.937 | 1.000 | no |
| Ciudad de México | spectral | 2 |  | 0.302 |  | 0.000 | ninguna | 125 | 0.754 | -0.005 | sí |
| Ciudad de México | hdbscan |  | min=47 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Ciudad de México | fuzzy_cmeans | 2 |  | 0.150 |  | 1.000 | baja pertenencia | 376 | 0.808 | -0.002 | no |
| São Paulo | kmeans | 2 |  | 0.131 |  | 0.000 | ninguna | 464 | 0.614 | 1.000 | no |
| São Paulo | kmedians | 2 |  | 0.132 |  | 0.000 | ninguna | 371 | 0.752 | 0.603 | no |
| São Paulo | kmedoids | 2 |  | 0.088 |  | 0.000 | ninguna | 460 | 0.165 | 0.029 | no |
| São Paulo | gmm | 2 | full | 0.240 |  | 0.001 | baja pertenencia | 34 | 0.750 | 0.010 | no |
| São Paulo | ward | 2 |  | 0.090 |  | 0.000 | ninguna | 437 | 0.166 | 0.278 | no |
| São Paulo | average |  |  |  |  |  |  |  |  | no definido | no |
| São Paulo | spectral | 2 |  | 0.122 |  | 0.000 | ninguna | 509 | 0.334 | 0.684 | no |
| São Paulo | hdbscan |  | min=52 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| São Paulo | fuzzy_cmeans | 2 |  | 0.128 |  | 1.000 | baja pertenencia | 497 | 0.728 | 0.854 | no |
| Las Vegas | kmeans | 2 |  | 0.181 |  | 0.000 | ninguna | 91 | 0.429 | 1.000 | no |
| Las Vegas | kmedians | 2 |  | 0.191 |  | 0.000 | ninguna | 84 | 0.332 | 0.865 | no |
| Las Vegas | kmedoids | 2 |  | 0.176 |  | 0.000 | ninguna | 86 | 0.168 | 0.751 | no |
| Las Vegas | gmm | 4 | diag | 0.060 |  | 0.048 | baja pertenencia | 22 | 0.514 | 0.058 | no |
| Las Vegas | ward | 2 |  | 0.188 |  | 0.000 | ninguna | 73 | 0.303 | 0.780 | no |
| Las Vegas | average | 2 |  | 0.405 |  | 0.000 | ninguna | 5 | 0.562 | -0.005 | no |
| Las Vegas | spectral | 2 |  | 0.183 |  | 0.000 | ninguna | 80 | 0.431 | 0.794 | no |
| Las Vegas | hdbscan |  | min=17 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Las Vegas | fuzzy_cmeans | 2 |  | 0.138 |  | 1.000 | baja pertenencia | 147 | 0.515 | 0.436 | no |
| Catar | kmeans | 2 |  | 0.727 |  | 0.000 | ninguna | 102 | 0.965 | 1.000 | no |
| Catar | kmedians | 2 |  | 0.717 |  | 0.000 | ninguna | 113 | 0.894 | 0.927 | no |
| Catar | kmedoids | 2 |  | 0.716 |  | 0.000 | ninguna | 114 | 0.499 | 0.921 | no |
| Catar | gmm | 3 | diag | 0.389 |  | 0.029 | baja pertenencia | 98 | 0.896 | 0.374 | no |
| Catar | ward | 2 |  | 0.713 |  | 0.000 | ninguna | 116 | 0.893 | 0.909 | no |
| Catar | average | 2 |  | 0.704 |  | 0.000 | ninguna | 123 | 0.418 | 0.867 | no |
| Catar | spectral | 2 |  | 0.568 |  | 0.000 | ninguna | 195 | 0.854 | 0.542 | no |
| Catar | hdbscan |  | min=46 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Catar | fuzzy_cmeans | 2 |  | 0.726 |  | 0.045 | baja pertenencia | 103 | 0.969 | 0.993 | no |
| Abu Dabi | kmeans | 2 |  | 0.711 |  | 0.000 | ninguna | 24 | 0.877 | 1.000 | sí |
| Abu Dabi | kmedians | 2 |  | 0.118 |  | 0.000 | ninguna | 510 | 0.728 | 0.001 | no |
| Abu Dabi | kmedoids | 2 |  | 0.557 |  | 0.000 | ninguna | 52 | 0.156 | 0.519 | sí |
| Abu Dabi | gmm | 2 | diag | 0.588 |  | 0.003 | baja pertenencia | 53 | 0.713 | 0.592 | sí |
| Abu Dabi | ward | 2 |  | 0.720 |  | 0.000 | ninguna | 22 | 0.703 | 0.954 | no |
| Abu Dabi | average |  |  |  |  |  |  |  |  | no definido | no |
| Abu Dabi | spectral | 2 |  | 0.549 |  | 0.000 | ninguna | 66 | 0.926 | 0.494 | no |
| Abu Dabi | hdbscan |  | min=52 |  |  | 1.000 | ruido | 0 |  | 0.000 | no |
| Abu Dabi | fuzzy_cmeans | 2 |  | 0.125 |  | 1.000 | baja pertenencia | 501 | 0.693 | 0.005 | no |

| carrera | nulo | modelo | n | p95 | percentil | supera p95 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Australia | permutación | kmeans | 50 | 0.157 | 100.0 | sí |
| Australia | gaussiano | kmeans | 50 | 0.167 | 100.0 | sí |
| Australia | cópula | kmeans | 50 | 0.225 | 92.0 | no |
| Australia | permutación | kmedians | 50 | 0.146 | 100.0 | sí |
| Australia | gaussiano | kmedians | 50 | 0.157 | 100.0 | sí |
| Australia | cópula | kmedians | 50 | 0.148 | 98.0 | sí |
| Australia | permutación | kmedoids | 50 | 0.135 | 96.0 | sí |
| Australia | gaussiano | kmedoids | 50 | 0.157 | 92.0 | no |
| Australia | cópula | kmedoids | 50 | 0.214 | 78.0 | no |
| Australia | permutación | gmm | 50 | 0.029 | 90.0 | no |
| Australia | gaussiano | gmm | 50 | 0.123 | 6.0 | no |
| Australia | cópula | gmm | 50 | 0.279 | 56.0 | no |
| Australia | permutación | ward | 50 | 0.175 | 16.0 | no |
| Australia | gaussiano | ward | 50 | 0.144 | 80.0 | no |
| Australia | cópula | ward | 50 | 0.241 | 50.0 | no |
| Australia | permutación | average | 12 |  |  | no |
| Australia | gaussiano | average | 18 |  |  | no |
| Australia | cópula | average | 19 |  |  | no |
| Australia | permutación | spectral | 50 | 0.155 | 98.0 | sí |
| Australia | gaussiano | spectral | 50 | 0.164 | 84.0 | no |
| Australia | cópula | spectral | 50 | 0.193 | 68.0 | no |
| Australia | permutación | hdbscan | 0 |  |  | no |
| Australia | gaussiano | hdbscan | 0 |  |  | no |
| Australia | cópula | hdbscan | 1 |  |  | no |
| Australia | permutación | fuzzy_cmeans | 50 | 0.102 | 100.0 | sí |
| Australia | gaussiano | fuzzy_cmeans | 50 | 0.167 | 22.0 | no |
| Australia | cópula | fuzzy_cmeans | 50 | 0.154 | 86.0 | no |
| China | permutación | kmeans | 50 | 0.537 | 88.0 | no |
| China | gaussiano | kmeans | 50 | 0.262 | 100.0 | sí |
| China | cópula | kmeans | 50 | 0.579 | 60.0 | no |
| China | permutación | kmedians | 50 | 0.537 | 90.0 | no |
| China | gaussiano | kmedians | 50 | 0.259 | 100.0 | sí |
| China | cópula | kmedians | 50 | 0.579 | 64.0 | no |
| China | permutación | kmedoids | 50 | 0.536 | 92.0 | no |
| China | gaussiano | kmedoids | 50 | 0.259 | 100.0 | sí |
| China | cópula | kmedoids | 50 | 0.573 | 68.0 | no |
| China | permutación | gmm | 50 | 0.529 | 46.0 | no |
| China | gaussiano | gmm | 50 | 0.105 | 100.0 | sí |
| China | cópula | gmm | 50 | 0.414 | 68.0 | no |
| China | permutación | ward | 50 | 0.542 | 82.0 | no |
| China | gaussiano | ward | 50 | 0.244 | 100.0 | sí |
| China | cópula | ward | 50 | 0.582 | 62.0 | no |
| China | permutación | average | 0 |  |  | no |
| China | gaussiano | average | 33 |  |  | no |
| China | cópula | average | 13 |  |  | no |
| China | permutación | spectral | 50 | 0.535 | 96.0 | sí |
| China | gaussiano | spectral | 50 | 0.260 | 100.0 | sí |
| China | cópula | spectral | 50 | 0.579 | 62.0 | no |
| China | permutación | hdbscan | 49 | 0.017 | 77.6 | no |
| China | gaussiano | hdbscan | 0 |  |  | no |
| China | cópula | hdbscan | 46 | 0.023 | 71.7 | no |
| China | permutación | fuzzy_cmeans | 50 | 0.534 | 88.0 | no |
| China | gaussiano | fuzzy_cmeans | 50 | 0.262 | 100.0 | sí |
| China | cópula | fuzzy_cmeans | 50 | 0.577 | 62.0 | no |
| Japón | permutación | kmeans | 50 | 0.758 | 100.0 | sí |
| Japón | gaussiano | kmeans | 50 | 0.410 | 100.0 | sí |
| Japón | cópula | kmeans | 50 | 0.781 | 38.0 | no |
| Japón | permutación | kmedians | 50 | 0.758 | 100.0 | sí |
| Japón | gaussiano | kmedians | 50 | 0.409 | 100.0 | sí |
| Japón | cópula | kmedians | 50 | 0.781 | 44.0 | no |
| Japón | permutación | kmedoids | 50 | 0.758 | 100.0 | sí |
| Japón | gaussiano | kmedoids | 50 | 0.407 | 100.0 | sí |
| Japón | cópula | kmedoids | 50 | 0.780 | 56.0 | no |
| Japón | permutación | gmm | 50 | 0.126 | 98.0 | sí |
| Japón | gaussiano | gmm | 50 | 0.281 | 42.0 | no |
| Japón | cópula | gmm | 50 | 0.145 | 88.0 | no |
| Japón | permutación | ward | 50 | 0.758 | 100.0 | sí |
| Japón | gaussiano | ward | 50 | 0.397 | 100.0 | sí |
| Japón | cópula | ward | 50 | 0.781 | 38.0 | no |
| Japón | permutación | average | 50 | 0.758 | 100.0 | sí |
| Japón | gaussiano | average | 39 | 0.561 | 100.0 | sí |
| Japón | cópula | average | 50 | 0.781 | 38.0 | no |
| Japón | permutación | spectral | 50 | 0.758 | 100.0 | sí |
| Japón | gaussiano | spectral | 50 | 0.409 | 100.0 | sí |
| Japón | cópula | spectral | 50 | 0.781 | 38.0 | no |
| Japón | permutación | hdbscan | 50 | 0.503 | 62.0 | no |
| Japón | gaussiano | hdbscan | 0 |  |  | no |
| Japón | cópula | hdbscan | 50 | 0.562 | 42.0 | no |
| Japón | permutación | fuzzy_cmeans | 50 | 0.758 | 100.0 | sí |
| Japón | gaussiano | fuzzy_cmeans | 50 | 0.410 | 100.0 | sí |
| Japón | cópula | fuzzy_cmeans | 50 | 0.781 | 38.0 | no |
| Baréin | permutación | kmeans | 50 | 0.166 | 68.0 | no |
| Baréin | gaussiano | kmeans | 50 | 0.138 | 100.0 | sí |
| Baréin | cópula | kmeans | 49 | 0.847 | 87.8 | no |
| Baréin | permutación | kmedians | 50 | 0.130 | 96.0 | sí |
| Baréin | gaussiano | kmedians | 50 | 0.129 | 98.0 | sí |
| Baréin | cópula | kmedians | 50 | 0.132 | 96.0 | sí |
| Baréin | permutación | kmedoids | 50 | 0.135 | 100.0 | sí |
| Baréin | gaussiano | kmedoids | 50 | 0.127 | 100.0 | sí |
| Baréin | cópula | kmedoids | 50 | 0.164 | 96.0 | sí |
| Baréin | permutación | gmm | 50 | 0.087 | 98.0 | sí |
| Baréin | gaussiano | gmm | 50 | 0.103 | 94.0 | sí |
| Baréin | cópula | gmm | 50 | 0.171 | 64.0 | no |
| Baréin | permutación | ward | 46 | 0.185 | 10.9 | no |
| Baréin | gaussiano | ward | 50 | 0.114 | 100.0 | sí |
| Baréin | cópula | ward | 46 | 0.847 | 60.9 | no |
| Baréin | permutación | average | 0 |  |  | no |
| Baréin | gaussiano | average | 18 |  |  | no |
| Baréin | cópula | average | 9 |  |  | no |
| Baréin | permutación | spectral | 50 | 0.158 | 94.0 | sí |
| Baréin | gaussiano | spectral | 50 | 0.135 | 100.0 | sí |
| Baréin | cópula | spectral | 50 | 0.177 | 72.0 | no |
| Baréin | permutación | hdbscan | 0 |  |  | no |
| Baréin | gaussiano | hdbscan | 0 |  |  | no |
| Baréin | cópula | hdbscan | 0 |  |  | no |
| Baréin | permutación | fuzzy_cmeans | 50 | 0.114 | 100.0 | sí |
| Baréin | gaussiano | fuzzy_cmeans | 50 | 0.138 | 100.0 | sí |
| Baréin | cópula | fuzzy_cmeans | 50 | 0.141 | 100.0 | sí |
| Arabia Saudita | permutación | kmeans | 50 | 0.104 | 100.0 | sí |
| Arabia Saudita | gaussiano | kmeans | 50 | 0.158 | 0.0 | no |
| Arabia Saudita | cópula | kmeans | 50 | 0.142 | 90.0 | no |
| Arabia Saudita | permutación | kmedians | 50 | 0.045 | 100.0 | sí |
| Arabia Saudita | gaussiano | kmedians | 50 | 0.151 | 10.0 | no |
| Arabia Saudita | cópula | kmedians | 50 | 0.123 | 84.0 | no |
| Arabia Saudita | permutación | kmedoids | 50 | 0.056 | 100.0 | sí |
| Arabia Saudita | gaussiano | kmedoids | 50 | 0.150 | 72.0 | no |
| Arabia Saudita | cópula | kmedoids | 50 | 0.124 | 100.0 | sí |
| Arabia Saudita | permutación | gmm | 50 | 0.381 | 10.0 | no |
| Arabia Saudita | gaussiano | gmm | 50 | 0.119 | 62.0 | no |
| Arabia Saudita | cópula | gmm | 50 | 0.427 | 12.0 | no |
| Arabia Saudita | permutación | ward | 50 | 0.385 | 0.0 | no |
| Arabia Saudita | gaussiano | ward | 50 | 0.136 | 100.0 | sí |
| Arabia Saudita | cópula | ward | 50 | 0.778 | 74.0 | no |
| Arabia Saudita | permutación | average | 0 |  |  | no |
| Arabia Saudita | gaussiano | average | 27 |  |  | no |
| Arabia Saudita | cópula | average | 19 |  |  | no |
| Arabia Saudita | permutación | spectral | 50 | 0.317 | 0.0 | no |
| Arabia Saudita | gaussiano | spectral | 50 | 0.155 | 0.0 | no |
| Arabia Saudita | cópula | spectral | 50 | 0.407 | 20.0 | no |
| Arabia Saudita | permutación | hdbscan | 0 |  |  | no |
| Arabia Saudita | gaussiano | hdbscan | 0 |  |  | no |
| Arabia Saudita | cópula | hdbscan | 0 |  |  | no |
| Arabia Saudita | permutación | fuzzy_cmeans | 50 | 0.061 | 100.0 | sí |
| Arabia Saudita | gaussiano | fuzzy_cmeans | 50 | 0.157 | 0.0 | no |
| Arabia Saudita | cópula | fuzzy_cmeans | 50 | 0.132 | 58.0 | no |
| Miami | permutación | kmeans | 50 | 0.230 | 22.0 | no |
| Miami | gaussiano | kmeans | 50 | 0.156 | 100.0 | sí |
| Miami | cópula | kmeans | 49 | 0.444 | 38.8 | no |
| Miami | permutación | kmedians | 50 | 0.229 | 18.0 | no |
| Miami | gaussiano | kmedians | 50 | 0.141 | 100.0 | sí |
| Miami | cópula | kmedians | 50 | 0.404 | 64.0 | no |
| Miami | permutación | kmedoids | 50 | 0.221 | 26.0 | no |
| Miami | gaussiano | kmedoids | 50 | 0.139 | 86.0 | no |
| Miami | cópula | kmedoids | 50 | 0.428 | 26.0 | no |
| Miami | permutación | gmm | 50 | 0.144 | 36.0 | no |
| Miami | gaussiano | gmm | 50 | 0.126 | 0.0 | no |
| Miami | cópula | gmm | 50 | 0.364 | 16.0 | no |
| Miami | permutación | ward | 50 | 0.229 | 2.0 | no |
| Miami | gaussiano | ward | 50 | 0.140 | 100.0 | sí |
| Miami | cópula | ward | 47 | 0.474 | 34.0 | no |
| Miami | permutación | average | 0 |  |  | no |
| Miami | gaussiano | average | 14 |  |  | no |
| Miami | cópula | average | 14 |  |  | no |
| Miami | permutación | spectral | 50 | 0.229 | 26.0 | no |
| Miami | gaussiano | spectral | 50 | 0.148 | 100.0 | sí |
| Miami | cópula | spectral | 50 | 0.428 | 46.0 | no |
| Miami | permutación | hdbscan | 0 |  |  | no |
| Miami | gaussiano | hdbscan | 0 |  |  | no |
| Miami | cópula | hdbscan | 3 |  |  | no |
| Miami | permutación | fuzzy_cmeans | 50 | 0.213 | 2.0 | no |
| Miami | gaussiano | fuzzy_cmeans | 50 | 0.150 | 96.0 | sí |
| Miami | cópula | fuzzy_cmeans | 50 | 0.428 | 44.0 | no |
| Emilia-Romaña | permutación | kmeans | 50 | 0.602 | 100.0 | sí |
| Emilia-Romaña | gaussiano | kmeans | 50 | 0.317 | 100.0 | sí |
| Emilia-Romaña | cópula | kmeans | 50 | 0.700 | 48.0 | no |
| Emilia-Romaña | permutación | kmedians | 50 | 0.594 | 100.0 | sí |
| Emilia-Romaña | gaussiano | kmedians | 50 | 0.313 | 100.0 | sí |
| Emilia-Romaña | cópula | kmedians | 50 | 0.691 | 56.0 | no |
| Emilia-Romaña | permutación | kmedoids | 50 | 0.599 | 100.0 | sí |
| Emilia-Romaña | gaussiano | kmedoids | 50 | 0.315 | 100.0 | sí |
| Emilia-Romaña | cópula | kmedoids | 50 | 0.689 | 64.0 | no |
| Emilia-Romaña | permutación | gmm | 50 | 0.440 | 94.0 | sí |
| Emilia-Romaña | gaussiano | gmm | 50 | 0.246 | 100.0 | sí |
| Emilia-Romaña | cópula | gmm | 50 | 0.540 | 64.0 | no |
| Emilia-Romaña | permutación | ward | 50 | 0.629 | 26.0 | no |
| Emilia-Romaña | gaussiano | ward | 50 | 0.301 | 100.0 | sí |
| Emilia-Romaña | cópula | ward | 50 | 0.701 | 36.0 | no |
| Emilia-Romaña | permutación | average | 8 |  |  | no |
| Emilia-Romaña | gaussiano | average | 32 |  |  | no |
| Emilia-Romaña | cópula | average | 28 |  |  | no |
| Emilia-Romaña | permutación | spectral | 50 | 0.580 | 96.0 | sí |
| Emilia-Romaña | gaussiano | spectral | 50 | 0.316 | 100.0 | sí |
| Emilia-Romaña | cópula | spectral | 50 | 0.666 | 54.0 | no |
| Emilia-Romaña | permutación | hdbscan | 0 |  |  | no |
| Emilia-Romaña | gaussiano | hdbscan | 0 |  |  | no |
| Emilia-Romaña | cópula | hdbscan | 0 |  |  | no |
| Emilia-Romaña | permutación | fuzzy_cmeans | 50 | 0.595 | 100.0 | sí |
| Emilia-Romaña | gaussiano | fuzzy_cmeans | 50 | 0.317 | 100.0 | sí |
| Emilia-Romaña | cópula | fuzzy_cmeans | 50 | 0.697 | 50.0 | no |
| Mónaco | permutación | kmeans | 50 | 0.189 | 0.0 | no |
| Mónaco | gaussiano | kmeans | 50 | 0.146 | 100.0 | sí |
| Mónaco | cópula | kmeans | 50 | 0.240 | 34.0 | no |
| Mónaco | permutación | kmedians | 50 | 0.167 | 8.0 | no |
| Mónaco | gaussiano | kmedians | 50 | 0.130 | 98.0 | sí |
| Mónaco | cópula | kmedians | 50 | 0.143 | 70.0 | no |
| Mónaco | permutación | kmedoids | 50 | 0.189 | 80.0 | no |
| Mónaco | gaussiano | kmedoids | 50 | 0.137 | 100.0 | sí |
| Mónaco | cópula | kmedoids | 50 | 0.207 | 64.0 | no |
| Mónaco | permutación | gmm | 50 | 0.099 | 12.0 | no |
| Mónaco | gaussiano | gmm | 50 | 0.138 | 0.0 | no |
| Mónaco | cópula | gmm | 50 | 0.134 | 26.0 | no |
| Mónaco | permutación | ward | 50 | 0.169 | 100.0 | sí |
| Mónaco | gaussiano | ward | 50 | 0.124 | 100.0 | sí |
| Mónaco | cópula | ward | 50 | 0.210 | 76.0 | no |
| Mónaco | permutación | average | 17 |  |  | no |
| Mónaco | gaussiano | average | 19 |  |  | no |
| Mónaco | cópula | average | 30 |  |  | no |
| Mónaco | permutación | spectral | 50 | 0.181 | 100.0 | sí |
| Mónaco | gaussiano | spectral | 50 | 0.142 | 100.0 | sí |
| Mónaco | cópula | spectral | 50 | 0.224 | 76.0 | no |
| Mónaco | permutación | hdbscan | 0 |  |  | no |
| Mónaco | gaussiano | hdbscan | 0 |  |  | no |
| Mónaco | cópula | hdbscan | 0 |  |  | no |
| Mónaco | permutación | fuzzy_cmeans | 50 | 0.143 | 100.0 | sí |
| Mónaco | gaussiano | fuzzy_cmeans | 50 | 0.146 | 100.0 | sí |
| Mónaco | cópula | fuzzy_cmeans | 50 | 0.146 | 100.0 | sí |
| España | permutación | kmeans | 50 | 0.140 | 10.0 | no |
| España | gaussiano | kmeans | 50 | 0.125 | 98.0 | sí |
| España | cópula | kmeans | 50 | 0.142 | 66.0 | no |
| España | permutación | kmedians | 50 | 0.127 | 40.0 | no |
| España | gaussiano | kmedians | 50 | 0.117 | 90.0 | no |
| España | cópula | kmedians | 50 | 0.118 | 92.0 | no |
| España | permutación | kmedoids | 50 | 0.118 | 100.0 | sí |
| España | gaussiano | kmedoids | 50 | 0.114 | 100.0 | sí |
| España | cópula | kmedoids | 50 | 0.154 | 88.0 | no |
| España | permutación | gmm | 50 | 0.004 | 84.0 | no |
| España | gaussiano | gmm | 50 | 0.093 | 0.0 | no |
| España | cópula | gmm | 50 | 0.013 | 76.0 | no |
| España | permutación | ward | 50 | 0.145 | 100.0 | sí |
| España | gaussiano | ward | 50 | 0.104 | 100.0 | sí |
| España | cópula | ward | 50 | 0.176 | 72.0 | no |
| España | permutación | average | 6 | 0.307 | 50.0 | no |
| España | gaussiano | average | 22 | 0.299 | 72.7 | no |
| España | cópula | average | 16 | 0.355 | 18.8 | no |
| España | permutación | spectral | 50 | 0.136 | 100.0 | sí |
| España | gaussiano | spectral | 50 | 0.122 | 100.0 | sí |
| España | cópula | spectral | 50 | 0.164 | 96.0 | sí |
| España | permutación | hdbscan | 0 |  |  | no |
| España | gaussiano | hdbscan | 0 |  |  | no |
| España | cópula | hdbscan | 0 |  |  | no |
| España | permutación | fuzzy_cmeans | 50 | 0.086 | 100.0 | sí |
| España | gaussiano | fuzzy_cmeans | 50 | 0.124 | 48.0 | no |
| España | cópula | fuzzy_cmeans | 50 | 0.117 | 92.0 | no |
| Canadá | permutación | kmeans | 50 | 0.677 | 100.0 | sí |
| Canadá | gaussiano | kmeans | 50 | 0.336 | 100.0 | sí |
| Canadá | cópula | kmeans | 50 | 0.700 | 58.0 | no |
| Canadá | permutación | kmedians | 50 | 0.675 | 90.0 | no |
| Canadá | gaussiano | kmedians | 50 | 0.333 | 100.0 | sí |
| Canadá | cópula | kmedians | 50 | 0.695 | 62.0 | no |
| Canadá | permutación | kmedoids | 50 | 0.677 | 40.0 | no |
| Canadá | gaussiano | kmedoids | 50 | 0.334 | 0.0 | no |
| Canadá | cópula | kmedoids | 50 | 0.700 | 14.0 | no |
| Canadá | permutación | gmm | 50 | 0.545 | 80.0 | no |
| Canadá | gaussiano | gmm | 50 | 0.261 | 100.0 | sí |
| Canadá | cópula | gmm | 50 | 0.487 | 100.0 | sí |
| Canadá | permutación | ward | 50 | 0.707 | 64.0 | no |
| Canadá | gaussiano | ward | 50 | 0.322 | 100.0 | sí |
| Canadá | cópula | ward | 50 | 0.721 | 76.0 | no |
| Canadá | permutación | average | 50 | 0.733 | 12.0 | no |
| Canadá | gaussiano | average | 35 | 0.500 | 100.0 | sí |
| Canadá | cópula | average | 47 | 0.738 | 12.8 | no |
| Canadá | permutación | spectral | 50 | 0.629 | 0.0 | no |
| Canadá | gaussiano | spectral | 50 | 0.334 | 100.0 | sí |
| Canadá | cópula | spectral | 50 | 0.667 | 8.0 | no |
| Canadá | permutación | hdbscan | 0 |  |  | no |
| Canadá | gaussiano | hdbscan | 0 |  |  | no |
| Canadá | cópula | hdbscan | 0 |  |  | no |
| Canadá | permutación | fuzzy_cmeans | 50 | 0.677 | 100.0 | sí |
| Canadá | gaussiano | fuzzy_cmeans | 50 | 0.336 | 100.0 | sí |
| Canadá | cópula | fuzzy_cmeans | 50 | 0.699 | 62.0 | no |
| Austria | permutación | kmeans | 50 | 0.253 | 100.0 | sí |
| Austria | gaussiano | kmeans | 50 | 0.163 | 100.0 | sí |
| Austria | cópula | kmeans | 50 | 0.278 | 88.0 | no |
| Austria | permutación | kmedians | 50 | 0.252 | 66.0 | no |
| Austria | gaussiano | kmedians | 50 | 0.149 | 0.0 | no |
| Austria | cópula | kmedians | 50 | 0.117 | 94.0 | no |
| Austria | permutación | kmedoids | 50 | 0.249 | 74.0 | no |
| Austria | gaussiano | kmedoids | 50 | 0.154 | 100.0 | sí |
| Austria | cópula | kmedoids | 50 | 0.282 | 74.0 | no |
| Austria | permutación | gmm | 50 | 0.255 | 4.0 | no |
| Austria | gaussiano | gmm | 50 | 0.124 | 22.0 | no |
| Austria | cópula | gmm | 50 | 0.263 | 42.0 | no |
| Austria | permutación | ward | 50 | 0.257 | 100.0 | sí |
| Austria | gaussiano | ward | 50 | 0.146 | 100.0 | sí |
| Austria | cópula | ward | 50 | 0.288 | 96.0 | sí |
| Austria | permutación | average | 50 | 0.547 | 96.0 | sí |
| Austria | gaussiano | average | 25 | 0.328 | 100.0 | sí |
| Austria | cópula | average | 43 | 0.602 | 65.1 | no |
| Austria | permutación | spectral | 50 | 0.256 | 100.0 | sí |
| Austria | gaussiano | spectral | 50 | 0.160 | 100.0 | sí |
| Austria | cópula | spectral | 50 | 0.287 | 96.0 | sí |
| Austria | permutación | hdbscan | 0 |  |  | no |
| Austria | gaussiano | hdbscan | 0 |  |  | no |
| Austria | cópula | hdbscan | 0 |  |  | no |
| Austria | permutación | fuzzy_cmeans | 50 | 0.079 | 100.0 | sí |
| Austria | gaussiano | fuzzy_cmeans | 50 | 0.163 | 0.0 | no |
| Austria | cópula | fuzzy_cmeans | 50 | 0.128 | 78.0 | no |
| Gran Bretaña | permutación | kmeans | 50 | 0.393 | 100.0 | sí |
| Gran Bretaña | gaussiano | kmeans | 50 | 0.148 | 100.0 | sí |
| Gran Bretaña | cópula | kmeans | 50 | 0.447 | 48.0 | no |
| Gran Bretaña | permutación | kmedians | 50 | 0.393 | 24.0 | no |
| Gran Bretaña | gaussiano | kmedians | 50 | 0.138 | 38.0 | no |
| Gran Bretaña | cópula | kmedians | 50 | 0.442 | 22.0 | no |
| Gran Bretaña | permutación | kmedoids | 50 | 0.396 | 42.0 | no |
| Gran Bretaña | gaussiano | kmedoids | 50 | 0.136 | 24.0 | no |
| Gran Bretaña | cópula | kmedoids | 50 | 0.440 | 16.0 | no |
| Gran Bretaña | permutación | gmm | 50 | 0.150 | 8.0 | no |
| Gran Bretaña | gaussiano | gmm | 50 | 0.071 | 0.0 | no |
| Gran Bretaña | cópula | gmm | 50 | 0.113 | 0.0 | no |
| Gran Bretaña | permutación | ward | 50 | 0.395 | 100.0 | sí |
| Gran Bretaña | gaussiano | ward | 50 | 0.130 | 100.0 | sí |
| Gran Bretaña | cópula | ward | 50 | 0.447 | 46.0 | no |
| Gran Bretaña | permutación | average | 38 |  |  | no |
| Gran Bretaña | gaussiano | average | 13 |  |  | no |
| Gran Bretaña | cópula | average | 41 |  |  | no |
| Gran Bretaña | permutación | spectral | 50 | 0.394 | 100.0 | sí |
| Gran Bretaña | gaussiano | spectral | 50 | 0.144 | 100.0 | sí |
| Gran Bretaña | cópula | spectral | 50 | 0.447 | 50.0 | no |
| Gran Bretaña | permutación | hdbscan | 0 |  |  | no |
| Gran Bretaña | gaussiano | hdbscan | 0 |  |  | no |
| Gran Bretaña | cópula | hdbscan | 1 |  |  | no |
| Gran Bretaña | permutación | fuzzy_cmeans | 50 | 0.169 | 56.0 | no |
| Gran Bretaña | gaussiano | fuzzy_cmeans | 50 | 0.148 | 100.0 | sí |
| Gran Bretaña | cópula | fuzzy_cmeans | 50 | 0.218 | 70.0 | no |
| Bélgica | permutación | kmeans | 50 | 0.071 | 100.0 | sí |
| Bélgica | gaussiano | kmeans | 50 | 0.103 | 44.0 | no |
| Bélgica | cópula | kmeans | 50 | 0.100 | 80.0 | no |
| Bélgica | permutación | kmedians | 50 | 0.048 | 100.0 | sí |
| Bélgica | gaussiano | kmedians | 50 | 0.091 | 30.0 | no |
| Bélgica | cópula | kmedians | 50 | 0.085 | 64.0 | no |
| Bélgica | permutación | kmedoids | 50 | 0.072 | 98.0 | sí |
| Bélgica | gaussiano | kmedoids | 50 | 0.088 | 88.0 | no |
| Bélgica | cópula | kmedoids | 50 | 0.087 | 94.0 | no |
| Bélgica | permutación | gmm | 50 | 0.119 | 62.0 | no |
| Bélgica | gaussiano | gmm | 50 | 0.092 | 0.0 | no |
| Bélgica | cópula | gmm | 50 | 0.072 | 16.0 | no |
| Bélgica | permutación | ward | 50 | 0.220 | 30.0 | no |
| Bélgica | gaussiano | ward | 50 | 0.082 | 88.0 | no |
| Bélgica | cópula | ward | 50 | 0.105 | 74.0 | no |
| Bélgica | permutación | average | 32 | 0.409 | 31.2 | no |
| Bélgica | gaussiano | average | 8 | 0.270 | 100.0 | sí |
| Bélgica | cópula | average | 32 | 0.430 | 18.8 | no |
| Bélgica | permutación | spectral | 50 | 0.137 | 22.0 | no |
| Bélgica | gaussiano | spectral | 50 | 0.099 | 4.0 | no |
| Bélgica | cópula | spectral | 50 | 0.165 | 16.0 | no |
| Bélgica | permutación | hdbscan | 0 |  |  | no |
| Bélgica | gaussiano | hdbscan | 0 |  |  | no |
| Bélgica | cópula | hdbscan | 0 |  |  | no |
| Bélgica | permutación | fuzzy_cmeans | 50 | 0.064 | 100.0 | sí |
| Bélgica | gaussiano | fuzzy_cmeans | 50 | 0.102 | 28.0 | no |
| Bélgica | cópula | fuzzy_cmeans | 50 | 0.097 | 38.0 | no |
| Hungría | permutación | kmeans | 15 | 0.563 | 0.0 | no |
| Hungría | gaussiano | kmeans | 50 | 0.166 | 0.0 | no |
| Hungría | cópula | kmeans | 43 | 0.875 | 37.2 | no |
| Hungría | permutación | kmedians | 50 | 0.100 | 98.0 | sí |
| Hungría | gaussiano | kmedians | 50 | 0.158 | 0.0 | no |
| Hungría | cópula | kmedians | 50 | 0.122 | 82.0 | no |
| Hungría | permutación | kmedoids | 50 | 0.069 | 96.0 | sí |
| Hungría | gaussiano | kmedoids | 50 | 0.160 | 0.0 | no |
| Hungría | cópula | kmedoids | 50 | 0.139 | 10.0 | no |
| Hungría | permutación | gmm | 50 | 0.393 | 86.0 | no |
| Hungría | gaussiano | gmm | 50 | 0.137 | 100.0 | sí |
| Hungría | cópula | gmm | 50 | 0.366 | 94.0 | no |
| Hungría | permutación | ward | 0 |  |  | no |
| Hungría | gaussiano | ward | 50 |  |  | no |
| Hungría | cópula | ward | 35 |  |  | no |
| Hungría | permutación | average | 0 |  |  | no |
| Hungría | gaussiano | average | 30 |  |  | no |
| Hungría | cópula | average | 17 |  |  | no |
| Hungría | permutación | spectral | 50 | 0.475 | 100.0 | sí |
| Hungría | gaussiano | spectral | 50 | 0.164 | 100.0 | sí |
| Hungría | cópula | spectral | 50 | 0.628 | 70.0 | no |
| Hungría | permutación | hdbscan | 0 |  |  | no |
| Hungría | gaussiano | hdbscan | 0 |  |  | no |
| Hungría | cópula | hdbscan | 0 |  |  | no |
| Hungría | permutación | fuzzy_cmeans | 50 | 0.085 | 100.0 | sí |
| Hungría | gaussiano | fuzzy_cmeans | 50 | 0.166 | 0.0 | no |
| Hungría | cópula | fuzzy_cmeans | 50 | 0.119 | 96.0 | sí |
| Países Bajos | permutación | kmeans | 50 | 0.175 | 0.0 | no |
| Países Bajos | gaussiano | kmeans | 50 | 0.124 | 100.0 | sí |
| Países Bajos | cópula | kmeans | 50 | 0.201 | 94.0 | no |
| Países Bajos | permutación | kmedians | 50 | 0.125 | 96.0 | sí |
| Países Bajos | gaussiano | kmedians | 50 | 0.111 | 100.0 | sí |
| Países Bajos | cópula | kmedians | 50 | 0.196 | 92.0 | no |
| Países Bajos | permutación | kmedoids | 50 | 0.118 | 94.0 | no |
| Países Bajos | gaussiano | kmedoids | 50 | 0.113 | 98.0 | sí |
| Países Bajos | cópula | kmedoids | 50 | 0.202 | 64.0 | no |
| Países Bajos | permutación | gmm | 50 | 0.024 | 94.0 | sí |
| Países Bajos | gaussiano | gmm | 50 | 0.098 | 4.0 | no |
| Países Bajos | cópula | gmm | 50 | 0.160 | 12.0 | no |
| Países Bajos | permutación | ward | 50 | 0.221 | 0.0 | no |
| Países Bajos | gaussiano | ward | 50 | 0.099 | 100.0 | sí |
| Países Bajos | cópula | ward | 50 | 0.258 | 34.0 | no |
| Países Bajos | permutación | average | 5 |  |  | no |
| Países Bajos | gaussiano | average | 22 |  |  | no |
| Países Bajos | cópula | average | 18 |  |  | no |
| Países Bajos | permutación | spectral | 50 | 0.187 | 0.0 | no |
| Países Bajos | gaussiano | spectral | 50 | 0.121 | 100.0 | sí |
| Países Bajos | cópula | spectral | 50 | 0.239 | 24.0 | no |
| Países Bajos | permutación | hdbscan | 0 |  |  | no |
| Países Bajos | gaussiano | hdbscan | 0 |  |  | no |
| Países Bajos | cópula | hdbscan | 0 |  |  | no |
| Países Bajos | permutación | fuzzy_cmeans | 50 | 0.086 | 100.0 | sí |
| Países Bajos | gaussiano | fuzzy_cmeans | 50 | 0.124 | 100.0 | sí |
| Países Bajos | cópula | fuzzy_cmeans | 50 | 0.183 | 94.0 | no |
| Italia | permutación | kmeans | 50 | 0.083 | 100.0 | sí |
| Italia | gaussiano | kmeans | 50 | 0.116 | 100.0 | sí |
| Italia | cópula | kmeans | 50 | 0.123 | 94.0 | sí |
| Italia | permutación | kmedians | 50 | 0.045 | 100.0 | sí |
| Italia | gaussiano | kmedians | 50 | 0.105 | 100.0 | sí |
| Italia | cópula | kmedians | 50 | 0.110 | 98.0 | sí |
| Italia | permutación | kmedoids | 50 | 0.072 | 100.0 | sí |
| Italia | gaussiano | kmedoids | 50 | 0.106 | 48.0 | no |
| Italia | cópula | kmedoids | 50 | 0.127 | 26.0 | no |
| Italia | permutación | gmm | 50 | 0.259 | 66.0 | no |
| Italia | gaussiano | gmm | 50 | 0.084 | 100.0 | sí |
| Italia | cópula | gmm | 50 | 0.314 | 42.0 | no |
| Italia | permutación | ward | 1 | 0.739 | 0.0 | no |
| Italia | gaussiano | ward | 50 | 0.093 | 86.0 | no |
| Italia | cópula | ward | 50 | 0.770 | 28.0 | no |
| Italia | permutación | average | 0 |  |  | no |
| Italia | gaussiano | average | 8 |  |  | no |
| Italia | cópula | average | 11 |  |  | no |
| Italia | permutación | spectral | 50 | 0.207 | 18.0 | no |
| Italia | gaussiano | spectral | 50 | 0.112 | 88.0 | no |
| Italia | cópula | spectral | 50 | 0.193 | 56.0 | no |
| Italia | permutación | hdbscan | 0 |  |  | no |
| Italia | gaussiano | hdbscan | 0 |  |  | no |
| Italia | cópula | hdbscan | 0 |  |  | no |
| Italia | permutación | fuzzy_cmeans | 50 | 0.062 | 100.0 | sí |
| Italia | gaussiano | fuzzy_cmeans | 50 | 0.115 | 100.0 | sí |
| Italia | cópula | fuzzy_cmeans | 50 | 0.117 | 96.0 | sí |
| Monza suelta | permutación | kmeans | 50 | 0.077 | 100.0 | sí |
| Monza suelta | gaussiano | kmeans | 50 | 0.113 | 100.0 | sí |
| Monza suelta | cópula | kmeans | 50 | 0.122 | 86.0 | no |
| Monza suelta | permutación | kmedians | 50 | 0.044 | 100.0 | sí |
| Monza suelta | gaussiano | kmedians | 50 | 0.103 | 100.0 | sí |
| Monza suelta | cópula | kmedians | 50 | 0.111 | 88.0 | no |
| Monza suelta | permutación | kmedoids | 50 | 0.057 | 100.0 | sí |
| Monza suelta | gaussiano | kmedoids | 50 | 0.102 | 56.0 | no |
| Monza suelta | cópula | kmedoids | 50 | 0.105 | 26.0 | no |
| Monza suelta | permutación | gmm | 50 | 0.249 | 84.0 | no |
| Monza suelta | gaussiano | gmm | 50 | 0.084 | 100.0 | sí |
| Monza suelta | cópula | gmm | 50 | 0.319 | 62.0 | no |
| Monza suelta | permutación | ward | 5 | 0.722 | 0.0 | no |
| Monza suelta | gaussiano | ward | 50 | 0.090 | 96.0 | sí |
| Monza suelta | cópula | ward | 48 | 0.761 | 50.0 | no |
| Monza suelta | permutación | average | 0 |  |  | no |
| Monza suelta | gaussiano | average | 15 |  |  | no |
| Monza suelta | cópula | average | 10 |  |  | no |
| Monza suelta | permutación | spectral | 50 | 0.198 | 54.0 | no |
| Monza suelta | gaussiano | spectral | 50 | 0.108 | 100.0 | sí |
| Monza suelta | cópula | spectral | 50 | 0.153 | 72.0 | no |
| Monza suelta | permutación | hdbscan | 0 |  |  | no |
| Monza suelta | gaussiano | hdbscan | 0 |  |  | no |
| Monza suelta | cópula | hdbscan | 0 |  |  | no |
| Monza suelta | permutación | fuzzy_cmeans | 50 | 0.058 | 100.0 | sí |
| Monza suelta | gaussiano | fuzzy_cmeans | 50 | 0.111 | 98.0 | sí |
| Monza suelta | cópula | fuzzy_cmeans | 50 | 0.115 | 88.0 | no |
| Azerbaiyán | permutación | kmeans | 50 | 0.650 | 96.0 | sí |
| Azerbaiyán | gaussiano | kmeans | 50 | 0.340 | 100.0 | sí |
| Azerbaiyán | cópula | kmeans | 50 | 0.677 | 44.0 | no |
| Azerbaiyán | permutación | kmedians | 50 | 0.627 | 84.0 | no |
| Azerbaiyán | gaussiano | kmedians | 50 | 0.336 | 100.0 | sí |
| Azerbaiyán | cópula | kmedians | 50 | 0.654 | 58.0 | no |
| Azerbaiyán | permutación | kmedoids | 50 | 0.629 | 86.0 | no |
| Azerbaiyán | gaussiano | kmedoids | 50 | 0.337 | 100.0 | sí |
| Azerbaiyán | cópula | kmedoids | 50 | 0.660 | 44.0 | no |
| Azerbaiyán | permutación | gmm | 50 | 0.505 | 76.0 | no |
| Azerbaiyán | gaussiano | gmm | 50 | 0.312 | 100.0 | sí |
| Azerbaiyán | cópula | gmm | 50 | 0.476 | 36.0 | no |
| Azerbaiyán | permutación | ward | 50 | 0.670 | 38.0 | no |
| Azerbaiyán | gaussiano | ward | 50 | 0.321 | 100.0 | sí |
| Azerbaiyán | cópula | ward | 50 | 0.696 | 30.0 | no |
| Azerbaiyán | permutación | average | 0 |  |  | no |
| Azerbaiyán | gaussiano | average | 28 |  |  | no |
| Azerbaiyán | cópula | average | 17 |  |  | no |
| Azerbaiyán | permutación | spectral | 50 | 0.612 | 72.0 | no |
| Azerbaiyán | gaussiano | spectral | 50 | 0.337 | 100.0 | sí |
| Azerbaiyán | cópula | spectral | 50 | 0.636 | 56.0 | no |
| Azerbaiyán | permutación | hdbscan | 50 | 0.015 | 58.0 | no |
| Azerbaiyán | gaussiano | hdbscan | 0 |  |  | no |
| Azerbaiyán | cópula | hdbscan | 50 | 0.019 | 62.0 | no |
| Azerbaiyán | permutación | fuzzy_cmeans | 50 | 0.636 | 96.0 | sí |
| Azerbaiyán | gaussiano | fuzzy_cmeans | 50 | 0.339 | 100.0 | sí |
| Azerbaiyán | cópula | fuzzy_cmeans | 50 | 0.675 | 30.0 | no |
| Singapur | permutación | kmeans | 50 | 0.620 | 100.0 | sí |
| Singapur | gaussiano | kmeans | 50 | 0.271 | 100.0 | sí |
| Singapur | cópula | kmeans | 50 | 0.639 | 68.0 | no |
| Singapur | permutación | kmedians | 50 | 0.604 | 60.0 | no |
| Singapur | gaussiano | kmedians | 50 | 0.270 | 100.0 | sí |
| Singapur | cópula | kmedians | 50 | 0.626 | 80.0 | no |
| Singapur | permutación | kmedoids | 50 | 0.612 | 30.0 | no |
| Singapur | gaussiano | kmedoids | 50 | 0.266 | 0.0 | no |
| Singapur | cópula | kmedoids | 50 | 0.627 | 16.0 | no |
| Singapur | permutación | gmm | 50 | 0.385 | 80.0 | no |
| Singapur | gaussiano | gmm | 50 | 0.210 | 100.0 | sí |
| Singapur | cópula | gmm | 50 | 0.300 | 96.0 | sí |
| Singapur | permutación | ward | 50 | 0.660 | 88.0 | no |
| Singapur | gaussiano | ward | 50 | 0.255 | 100.0 | sí |
| Singapur | cópula | ward | 50 | 0.667 | 70.0 | no |
| Singapur | permutación | average | 48 | 0.781 | 79.2 | no |
| Singapur | gaussiano | average | 39 | 0.463 | 100.0 | sí |
| Singapur | cópula | average | 43 | 0.799 | 76.7 | no |
| Singapur | permutación | spectral | 50 | 0.580 | 56.0 | no |
| Singapur | gaussiano | spectral | 50 | 0.268 | 100.0 | sí |
| Singapur | cópula | spectral | 50 | 0.606 | 60.0 | no |
| Singapur | permutación | hdbscan | 0 |  |  | no |
| Singapur | gaussiano | hdbscan | 0 |  |  | no |
| Singapur | cópula | hdbscan | 0 |  |  | no |
| Singapur | permutación | fuzzy_cmeans | 50 | 0.421 | 100.0 | sí |
| Singapur | gaussiano | fuzzy_cmeans | 50 | 0.270 | 100.0 | sí |
| Singapur | cópula | fuzzy_cmeans | 50 | 0.459 | 80.0 | no |
| Estados Unidos | permutación | kmeans | 50 | 0.386 | 92.0 | no |
| Estados Unidos | gaussiano | kmeans | 50 | 0.139 | 100.0 | sí |
| Estados Unidos | cópula | kmeans | 50 | 0.425 | 14.0 | no |
| Estados Unidos | permutación | kmedians | 50 | 0.384 | 60.0 | no |
| Estados Unidos | gaussiano | kmedians | 50 | 0.109 | 86.0 | no |
| Estados Unidos | cópula | kmedians | 50 | 0.151 | 26.0 | no |
| Estados Unidos | permutación | kmedoids | 50 | 0.380 | 100.0 | sí |
| Estados Unidos | gaussiano | kmedoids | 50 | 0.127 | 100.0 | sí |
| Estados Unidos | cópula | kmedoids | 50 | 0.421 | 68.0 | no |
| Estados Unidos | permutación | gmm | 50 | 0.386 | 6.0 | no |
| Estados Unidos | gaussiano | gmm | 50 | 0.104 | 100.0 | sí |
| Estados Unidos | cópula | gmm | 50 | 0.424 | 14.0 | no |
| Estados Unidos | permutación | ward | 50 | 0.386 | 92.0 | no |
| Estados Unidos | gaussiano | ward | 50 | 0.120 | 100.0 | sí |
| Estados Unidos | cópula | ward | 50 | 0.425 | 12.0 | no |
| Estados Unidos | permutación | average | 28 |  |  | no |
| Estados Unidos | gaussiano | average | 20 |  |  | no |
| Estados Unidos | cópula | average | 32 |  |  | no |
| Estados Unidos | permutación | spectral | 50 | 0.386 | 92.0 | no |
| Estados Unidos | gaussiano | spectral | 50 | 0.135 | 100.0 | sí |
| Estados Unidos | cópula | spectral | 50 | 0.425 | 12.0 | no |
| Estados Unidos | permutación | hdbscan | 0 |  |  | no |
| Estados Unidos | gaussiano | hdbscan | 0 |  |  | no |
| Estados Unidos | cópula | hdbscan | 0 |  |  | no |
| Estados Unidos | permutación | fuzzy_cmeans | 50 | 0.105 | 100.0 | sí |
| Estados Unidos | gaussiano | fuzzy_cmeans | 50 | 0.138 | 4.0 | no |
| Estados Unidos | cópula | fuzzy_cmeans | 50 | 0.121 | 94.0 | no |
| Ciudad de México | permutación | kmeans | 50 | 0.842 | 100.0 | sí |
| Ciudad de México | gaussiano | kmeans | 50 | 0.159 | 100.0 | sí |
| Ciudad de México | cópula | kmeans | 50 | 0.852 | 80.0 | no |
| Ciudad de México | permutación | kmedians | 50 | 0.213 | 100.0 | sí |
| Ciudad de México | gaussiano | kmedians | 50 | 0.132 | 100.0 | sí |
| Ciudad de México | cópula | kmedians | 50 | 0.243 | 100.0 | sí |
| Ciudad de México | permutación | kmedoids | 50 | 0.253 | 100.0 | sí |
| Ciudad de México | gaussiano | kmedoids | 50 | 0.151 | 100.0 | sí |
| Ciudad de México | cópula | kmedoids | 50 | 0.249 | 100.0 | sí |
| Ciudad de México | permutación | gmm | 50 | 0.261 | 36.0 | no |
| Ciudad de México | gaussiano | gmm | 50 | 0.141 | 8.0 | no |
| Ciudad de México | cópula | gmm | 50 | 0.167 | 12.0 | no |
| Ciudad de México | permutación | ward | 50 | 0.842 | 100.0 | sí |
| Ciudad de México | gaussiano | ward | 50 | 0.141 | 100.0 | sí |
| Ciudad de México | cópula | ward | 47 | 0.852 | 76.6 | no |
| Ciudad de México | permutación | average | 50 | 0.842 | 100.0 | sí |
| Ciudad de México | gaussiano | average | 20 | 0.348 | 100.0 | sí |
| Ciudad de México | cópula | average | 31 | 0.852 | 64.5 | no |
| Ciudad de México | permutación | spectral | 50 | 0.259 | 100.0 | sí |
| Ciudad de México | gaussiano | spectral | 50 | 0.156 | 100.0 | sí |
| Ciudad de México | cópula | spectral | 50 | 0.292 | 96.0 | sí |
| Ciudad de México | permutación | hdbscan | 0 |  |  | no |
| Ciudad de México | gaussiano | hdbscan | 0 |  |  | no |
| Ciudad de México | cópula | hdbscan | 0 |  |  | no |
| Ciudad de México | permutación | fuzzy_cmeans | 50 | 0.167 | 24.0 | no |
| Ciudad de México | gaussiano | fuzzy_cmeans | 50 | 0.159 | 48.0 | no |
| Ciudad de México | cópula | fuzzy_cmeans | 50 | 0.159 | 84.0 | no |
| São Paulo | permutación | kmeans | 50 | 0.078 | 100.0 | sí |
| São Paulo | gaussiano | kmeans | 50 | 0.140 | 46.0 | no |
| São Paulo | cópula | kmeans | 50 | 0.138 | 74.0 | no |
| São Paulo | permutación | kmedians | 50 | 0.050 | 100.0 | sí |
| São Paulo | gaussiano | kmedians | 50 | 0.133 | 88.0 | no |
| São Paulo | cópula | kmedians | 50 | 0.133 | 92.0 | no |
| São Paulo | permutación | kmedoids | 50 | 0.060 | 100.0 | sí |
| São Paulo | gaussiano | kmedoids | 50 | 0.131 | 0.0 | no |
| São Paulo | cópula | kmedoids | 50 | 0.144 | 4.0 | no |
| São Paulo | permutación | gmm | 50 | 0.159 | 100.0 | sí |
| São Paulo | gaussiano | gmm | 50 | 0.110 | 100.0 | sí |
| São Paulo | cópula | gmm | 50 | 0.252 | 92.0 | no |
| São Paulo | permutación | ward | 50 | 0.197 | 16.0 | no |
| São Paulo | gaussiano | ward | 50 | 0.110 | 18.0 | no |
| São Paulo | cópula | ward | 50 | 0.800 | 18.0 | no |
| São Paulo | permutación | average | 0 |  |  | no |
| São Paulo | gaussiano | average | 13 |  |  | no |
| São Paulo | cópula | average | 11 |  |  | no |
| São Paulo | permutación | spectral | 50 | 0.125 | 92.0 | no |
| São Paulo | gaussiano | spectral | 50 | 0.136 | 14.0 | no |
| São Paulo | cópula | spectral | 50 | 0.132 | 32.0 | no |
| São Paulo | permutación | hdbscan | 0 |  |  | no |
| São Paulo | gaussiano | hdbscan | 0 |  |  | no |
| São Paulo | cópula | hdbscan | 0 |  |  | no |
| São Paulo | permutación | fuzzy_cmeans | 50 | 0.066 | 100.0 | sí |
| São Paulo | gaussiano | fuzzy_cmeans | 50 | 0.139 | 46.0 | no |
| São Paulo | cópula | fuzzy_cmeans | 50 | 0.135 | 48.0 | no |
| Las Vegas | permutación | kmeans | 50 | 0.168 | 100.0 | sí |
| Las Vegas | gaussiano | kmeans | 50 | 0.159 | 100.0 | sí |
| Las Vegas | cópula | kmeans | 50 | 0.250 | 54.0 | no |
| Las Vegas | permutación | kmedians | 50 | 0.167 | 100.0 | sí |
| Las Vegas | gaussiano | kmedians | 50 | 0.150 | 100.0 | sí |
| Las Vegas | cópula | kmedians | 50 | 0.245 | 64.0 | no |
| Las Vegas | permutación | kmedoids | 50 | 0.155 | 100.0 | sí |
| Las Vegas | gaussiano | kmedoids | 50 | 0.149 | 100.0 | sí |
| Las Vegas | cópula | kmedoids | 50 | 0.238 | 70.0 | no |
| Las Vegas | permutación | gmm | 50 | 0.147 | 86.0 | no |
| Las Vegas | gaussiano | gmm | 50 | 0.147 | 0.0 | no |
| Las Vegas | cópula | gmm | 50 | 0.081 | 78.0 | no |
| Las Vegas | permutación | ward | 50 | 0.151 | 100.0 | sí |
| Las Vegas | gaussiano | ward | 50 | 0.141 | 100.0 | sí |
| Las Vegas | cópula | ward | 50 | 0.254 | 56.0 | no |
| Las Vegas | permutación | average | 15 | 0.414 | 86.7 | no |
| Las Vegas | gaussiano | average | 12 | 0.324 | 100.0 | sí |
| Las Vegas | cópula | average | 14 | 0.488 | 57.1 | no |
| Las Vegas | permutación | spectral | 50 | 0.159 | 100.0 | sí |
| Las Vegas | gaussiano | spectral | 50 | 0.155 | 100.0 | sí |
| Las Vegas | cópula | spectral | 50 | 0.248 | 62.0 | no |
| Las Vegas | permutación | hdbscan | 0 |  |  | no |
| Las Vegas | gaussiano | hdbscan | 0 |  |  | no |
| Las Vegas | cópula | hdbscan | 0 |  |  | no |
| Las Vegas | permutación | fuzzy_cmeans | 50 | 0.135 | 98.0 | sí |
| Las Vegas | gaussiano | fuzzy_cmeans | 50 | 0.159 | 28.0 | no |
| Las Vegas | cópula | fuzzy_cmeans | 50 | 0.171 | 52.0 | no |
| Catar | permutación | kmeans | 50 | 0.724 | 100.0 | sí |
| Catar | gaussiano | kmeans | 50 | 0.423 | 100.0 | sí |
| Catar | cópula | kmeans | 50 | 0.742 | 46.0 | no |
| Catar | permutación | kmedians | 50 | 0.714 | 100.0 | sí |
| Catar | gaussiano | kmedians | 50 | 0.421 | 100.0 | sí |
| Catar | cópula | kmedians | 50 | 0.737 | 40.0 | no |
| Catar | permutación | kmedoids | 50 | 0.718 | 88.0 | no |
| Catar | gaussiano | kmedoids | 50 | 0.422 | 100.0 | sí |
| Catar | cópula | kmedoids | 50 | 0.737 | 52.0 | no |
| Catar | permutación | gmm | 50 | 0.369 | 98.0 | sí |
| Catar | gaussiano | gmm | 50 | 0.268 | 100.0 | sí |
| Catar | cópula | gmm | 50 | 0.456 | 80.0 | no |
| Catar | permutación | ward | 50 | 0.729 | 38.0 | no |
| Catar | gaussiano | ward | 50 | 0.413 | 100.0 | sí |
| Catar | cópula | ward | 50 | 0.744 | 26.0 | no |
| Catar | permutación | average | 31 | 0.758 | 45.2 | no |
| Catar | gaussiano | average | 38 | 0.522 | 100.0 | sí |
| Catar | cópula | average | 38 | 0.776 | 10.5 | no |
| Catar | permutación | spectral | 50 | 0.700 | 0.0 | no |
| Catar | gaussiano | spectral | 50 | 0.421 | 100.0 | sí |
| Catar | cópula | spectral | 50 | 0.713 | 10.0 | no |
| Catar | permutación | hdbscan | 0 |  |  | no |
| Catar | gaussiano | hdbscan | 0 |  |  | no |
| Catar | cópula | hdbscan | 0 |  |  | no |
| Catar | permutación | fuzzy_cmeans | 50 | 0.723 | 100.0 | sí |
| Catar | gaussiano | fuzzy_cmeans | 50 | 0.422 | 100.0 | sí |
| Catar | cópula | fuzzy_cmeans | 50 | 0.742 | 46.0 | no |
| Abu Dabi | permutación | kmeans | 50 | 0.628 | 100.0 | sí |
| Abu Dabi | gaussiano | kmeans | 50 | 0.188 | 100.0 | sí |
| Abu Dabi | cópula | kmeans | 50 | 0.672 | 96.0 | sí |
| Abu Dabi | permutación | kmedians | 50 | 0.069 | 100.0 | sí |
| Abu Dabi | gaussiano | kmedians | 50 | 0.178 | 0.0 | no |
| Abu Dabi | cópula | kmedians | 50 | 0.124 | 80.0 | no |
| Abu Dabi | permutación | kmedoids | 50 | 0.316 | 100.0 | sí |
| Abu Dabi | gaussiano | kmedoids | 50 | 0.179 | 100.0 | sí |
| Abu Dabi | cópula | kmedoids | 50 | 0.316 | 98.0 | sí |
| Abu Dabi | permutación | gmm | 50 | 0.426 | 100.0 | sí |
| Abu Dabi | gaussiano | gmm | 50 | 0.133 | 100.0 | sí |
| Abu Dabi | cópula | gmm | 50 | 0.473 | 100.0 | sí |
| Abu Dabi | permutación | ward | 50 | 0.606 | 100.0 | sí |
| Abu Dabi | gaussiano | ward | 50 | 0.165 | 100.0 | sí |
| Abu Dabi | cópula | ward | 50 | 0.796 | 92.0 | no |
| Abu Dabi | permutación | average | 0 |  |  | no |
| Abu Dabi | gaussiano | average | 29 |  |  | no |
| Abu Dabi | cópula | average | 24 |  |  | no |
| Abu Dabi | permutación | spectral | 50 | 0.586 | 10.0 | no |
| Abu Dabi | gaussiano | spectral | 50 | 0.185 | 100.0 | sí |
| Abu Dabi | cópula | spectral | 50 | 0.628 | 52.0 | no |
| Abu Dabi | permutación | hdbscan | 0 |  |  | no |
| Abu Dabi | gaussiano | hdbscan | 0 |  |  | no |
| Abu Dabi | cópula | hdbscan | 0 |  |  | no |
| Abu Dabi | permutación | fuzzy_cmeans | 50 | 0.119 | 98.0 | sí |
| Abu Dabi | gaussiano | fuzzy_cmeans | 50 | 0.187 | 0.0 | no |
| Abu Dabi | cópula | fuzzy_cmeans | 50 | 0.138 | 52.0 | no |

| carrera | modelos que superan los tres | modelos en la grilla | consenso |
| --- | ---: | ---: | --- |
| Australia | 1 | 9 | no |
| China | 0 | 9 | no |
| Japón | 0 | 9 | no |
| Baréin | 3 | 9 | no |
| Arabia Saudita | 0 | 9 | no |
| Miami | 0 | 9 | no |
| Emilia-Romaña | 0 | 9 | no |
| Mónaco | 1 | 9 | no |
| España | 1 | 9 | no |
| Canadá | 0 | 9 | no |
| Austria | 2 | 9 | no |
| Gran Bretaña | 0 | 9 | no |
| Bélgica | 0 | 9 | no |
| Hungría | 0 | 9 | no |
| Países Bajos | 0 | 9 | no |
| Italia | 3 | 9 | no |
| Monza suelta | 0 | 9 | no |
| Azerbaiyán | 0 | 9 | no |
| Singapur | 0 | 9 | no |
| Estados Unidos | 0 | 9 | no |
| Ciudad de México | 3 | 9 | no |
| São Paulo | 0 | 9 | no |
| Las Vegas | 0 | 9 | no |
| Catar | 0 | 9 | no |
| Abu Dabi | 3 | 9 | no |

Ninguna carrera tiene consenso.

### Australia

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `fast__full_throttle_frac`, `medium__full_throttle_frac`, `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### China

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `medium__full_throttle_frac`, `medium__throttle_attack`, `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Japón

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Baréin

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Arabia Saudita

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Miami

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__trail_brake_frac`, `medium__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Emilia-Romaña

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `fast__full_throttle_frac`, `medium__full_throttle_frac`, `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Mónaco

Ninguna columna tiene IQR a lo sumo 1e-8 antes del escalador.

Ninguna clase queda marcada por una feature apilada.

### España

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__full_throttle_frac`, `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Canadá

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `fast__full_throttle_frac`, `slow__full_throttle_frac`, `slow__throttle_attack`, `fast__trail_brake_frac`.

| modelo | clase | feature | parte de la distancia L1 | IQR dentro de la clase |
| --- | ---: | --- | ---: | ---: |
| kmeans | 0 | slow__throttle_attack | 0.805 | 0.000000 |
| kmedians | 1 | slow__throttle_attack | 0.804 | 0.000000 |
| gmm | 0 | slow__throttle_attack | 0.750 | 0.000000 |
| ward | 1 | slow__throttle_attack | 0.804 | 0.000000 |
| average | 0 | slow__throttle_attack | 0.800 | 0.000000 |
| spectral | 1 | slow__throttle_attack | 0.769 | 0.000000 |
| fuzzy_cmeans | 1 | slow__throttle_attack | 0.805 | 0.000000 |

### Austria

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Gran Bretaña

Ninguna columna tiene IQR a lo sumo 1e-8 antes del escalador.

Ninguna clase queda marcada por una feature apilada.

### Bélgica

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `fast__full_throttle_frac`, `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Hungría

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Países Bajos

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Italia

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__full_throttle_frac`, `medium__full_throttle_frac`, `medium__throttle_attack`.

Ninguna clase queda marcada por una feature apilada.

### Monza suelta

Esta matriz incluye `fast__brake_point_rel`.

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__full_throttle_frac`, `medium__full_throttle_frac`, `medium__throttle_attack`.

Ninguna clase queda marcada por una feature apilada.

### Azerbaiyán

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `slow__full_throttle_frac`, `slow__throttle_attack`, `fast__trail_brake_frac`.

| modelo | clase | feature | parte de la distancia L1 | IQR dentro de la clase |
| --- | ---: | --- | ---: | ---: |
| kmeans | 0 | slow__throttle_attack | 0.820 | 0.000000 |
| fuzzy_cmeans | 1 | slow__throttle_attack | 0.799 | 0.000000 |

### Singapur

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `fast__full_throttle_frac`, `medium__full_throttle_frac`, `medium__throttle_attack`, `fast__trail_brake_frac`.

| modelo | clase | feature | parte de la distancia L1 | IQR dentro de la clase |
| --- | ---: | --- | ---: | ---: |
| kmeans | 0 | medium__throttle_attack | 0.878 | 0.000000 |
| kmedians | 0 | medium__throttle_attack | 0.867 | 0.000000 |
| gmm | 1 | medium__throttle_attack | 0.708 | 0.000000 |
| ward | 0 | medium__throttle_attack | 0.879 | 0.000000 |
| average | 1 | medium__throttle_attack | 0.901 | 0.000000 |
| spectral | 1 | medium__throttle_attack | 0.877 | 0.000000 |
| fuzzy_cmeans | 1 | medium__throttle_attack | 0.747 | 0.000000 |

### Estados Unidos

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Ciudad de México

Ninguna columna tiene IQR a lo sumo 1e-8 antes del escalador.

Ninguna clase queda marcada por una feature apilada.

### São Paulo

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `fast__full_throttle_frac`, `fast__trail_brake_frac`, `medium__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Las Vegas

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `medium__coast_frac`, `fast__full_throttle_frac`, `medium__full_throttle_frac`, `medium__throttle_attack`, `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.

### Catar

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__coast_frac`, `fast__full_throttle_frac`, `slow__full_throttle_frac`, `slow__throttle_attack`, `fast__trail_brake_frac`.

| modelo | clase | feature | parte de la distancia L1 | IQR dentro de la clase |
| --- | ---: | --- | ---: | ---: |
| kmeans | 0 | slow__throttle_attack | 0.870 | 0.000000 |
| kmedians | 0 | slow__throttle_attack | 0.857 | 0.000000 |
| kmedoids | 1 | slow__throttle_attack | 0.864 | 0.000000 |
| gmm | 0 | slow__throttle_attack | 0.782 | 0.000000 |
| ward | 0 | slow__throttle_attack | 0.862 | 0.000000 |
| average | 0 | slow__throttle_attack | 0.862 | 0.000000 |
| spectral | 1 | slow__throttle_attack | 0.859 | 0.000000 |
| fuzzy_cmeans | 0 | slow__throttle_attack | 0.868 | 0.000000 |

### Abu Dabi

Columnas con IQR a lo sumo 1e-8 antes del escalador: `fast__trail_brake_frac`.

Ninguna clase queda marcada por una feature apilada.
