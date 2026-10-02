# Monza 2025 (carrera): onset apagado, sin throttle attack en fast

Corrida: `python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R`.

`include_throttle_onset` sigue en false. `fast__throttle_attack` salió de la matriz de vueltas. Siguen `slow__throttle_attack`, `medium__throttle_attack`, `brake_point_rel` y `trail_brake_frac` en las tres tipologías.

El CLI volvió a terminar con `InvalidKPoolError`. No hay k elegido ni clase modal ni fracción por piloto.

## Matriz de esta corrida

842 vueltas, 19 pilotos (el auto 27 no entra: FastF1 marcó todas sus vueltas como inaccurate; HUL no está). **17 columnas de estilo.** No hay `throttle_onset` ni `fast__throttle_attack`. Sí están `fast__brake_point_rel` y `fast__trail_brake_frac`.

El escalado usa esas 17. PCA: 3 componentes, varianza acumulada 0.9094 (0.4644, 0.3156, 0.1294).

## Por qué el selector rechaza todos los k

Pide un clúster de al menos `ceil(0.05 * 842) = 43` vueltas y, si el pool queda vacío, reintenta con mínimo 3. Los dos intentos fallan. Davies-Bouldin no elige k: solo se usa si algún k válido tiene silueta bajo 0.25.

La tabla es el mismo K-means++ del selector (`n_init=20`, `random_state=42`) sobre el espacio de ajuste. El CLI no la escribe.

| k | tamaño mínimo | tamaños | silueta | Davies-Bouldin |
| --- | ---: | --- | ---: | ---: |
| 2 | 2 | 840, 2 | 0.9722 | 0.1526 |
| 3 | 2 | 836, 4, 2 | 0.9552 | 0.5504 |
| 4 | 2 | 817, 19, 4, 2 | 0.8604 | 0.6189 |
| 5 | 1 | 817, 19, 3, 2, 1 | 0.8614 | 0.3535 |
| 6 | 1 | 676, 141, 19, 3, 2, 1 | 0.6231 | 0.4299 |
| 7 | 1 | 676, 141, 19, 2, 2, 1, 1 | 0.6237 | 0.3046 |

En k=2, 3 y 4 el clúster chico es ALB vuelta 49 y ALO vuelta 16. En k≥5 aparece además un clúster de una sola vuelta (HAM vuelta 31).

## Columna que se dispara

`fast__full_throttle_frac`. IQR crudo 0. Es 0 en 840 vueltas. Las otras dos:

| vuelta | valor crudo | residual (Team, Compound, TyreLife) | escalado robusto |
| --- | ---: | ---: | ---: |
| ALB 49 | −0.37992026 | −0.37357873 | −128.265926 |
| ALO 16 | −0.50000000 | −0.49080328 | −168.395776 |

El IQR después de residualizar es 0.002921. Esas dos vueltas son el clúster de tamaño 2, por debajo del mínimo 3.

Las dos puntas siguientes, que no se tocaron:

- `medium__throttle_attack`: 0 en 801 de 842 vueltas, IQR crudo 0. HAM vuelta 31 vale 13.428571 en crudo y 103.438545 escalado.
- `medium__full_throttle_frac`: 0 en 838 vueltas, IQR crudo 0. PIA vuelta 34 vale −0.071666788 en crudo y −100.204659 escalado.

## Corrida anterior

Antes de sacar `fast__throttle_attack`, esa columna era 0 en 841 de 842 vueltas y 1.5625 solo en ALB vuelta 49. El escalado robusto la llevaba a 350.65 y todos los k tenían un clúster de tamaño 1. Esa hipótesis se confirma con la matriz de esa corrida. Quitarla no alcanza: el selector sigue sin pool válido.

## K-medianas, DBSCAN y t-SNE

Misma matriz: onset apagado, sin `fast__throttle_attack`, con `fast__full_throttle_frac`, 17 columnas, 842 vueltas. El ajuste usa el escalado robusto del pipeline (después de residualizar Team, Compound y TyreLife), no los 3 componentes del K-means. El camino de K-means no se modificó. Script: `scripts/monza_alt_clustering.py`.

### K-medianas

Centros = mediana por coordenada, asignación por distancia L1. 20 arranques, `random_state=42`. Silueta de Manhattan.

| k | tamaños (id: n) | mínimo | costo L1 | silueta L1 |
| --- | --- | ---: | ---: | ---: |
| 2 | 0:419, 1:423 | 419 | 9765.96 | 0.1178 |
| 3 | 0:312, 1:134, 2:396 | 134 | 9238.21 | 0.1413 |
| 4 | 0:390, 1:294, 2:20, 3:138 | 20 | 8931.28 | 0.1599 |
| 5 | 0:245, 1:206, 2:20, 3:128, 4:243 | 20 | 8657.74 | 0.0992 |
| 6 | 0:251, 1:2, 2:19, 3:261, 4:136, 5:173 | 2 | 8422.60 | 0.1141 |
| 7 | 0:188, 1:20, 2:2, 3:138, 4:159, 5:202, 6:133 | 2 | 8192.74 | 0.1095 |

Me quedo con **k=4**. Es la silueta más alta entre los k cuyo clúster más chico tiene al menos 3 vueltas (k=6 y k=7 quedan afuera). El costo L1 sigue bajando sin un codo; la silueta sube hasta k=4 (0.1599) y cae en k=5 (0.0992). La separación es débil.

Clase modal de cada piloto (vueltas en esa clase / vueltas suyas). Nadie tiene la clase 2 como moda; esas 20 vueltas están repartidas.

| piloto | clase | vueltas | fracción |
| --- | ---: | --- | ---: |
| ALB | 1 | 23/38 | 0.6053 |
| ALO | 1 | 17/19 | 0.8947 |
| ANT | 0 | 22/42 | 0.5238 |
| BEA | 1 | 26/47 | 0.5532 |
| BOR | 0 | 24/46 | 0.5217 |
| COL | 1 | 27/43 | 0.6279 |
| GAS | 0 | 39/45 | 0.8667 |
| HAD | 0 | 28/47 | 0.5957 |
| HAM | 3 | 26/48 | 0.5417 |
| LAW | 0 | 38/47 | 0.8085 |
| LEC | 3 | 46/46 | 1.0000 |
| NOR | 3 | 41/48 | 0.8542 |
| OCO | 0 | 42/47 | 0.8936 |
| PIA | 3 | 25/47 | 0.5319 |
| RUS | 1 | 29/45 | 0.6444 |
| SAI | 1 | 26/46 | 0.5652 |
| STR | 0 | 41/46 | 0.8913 |
| TSU | 0 | 48/48 | 1.0000 |
| VER | 1 | 45/47 | 0.9574 |

### DBSCAN

Métrica euclídea sobre las mismas 17 columnas escaladas. `min_samples = 2 × 17 = 34`. `eps` es la rodilla geométrica de la distancia al vecino 34 (contando el propio punto), ordenada de mayor a menor. Cae en el índice 33, `eps = 7.572039`.

Percentiles de esa distancia: p50 3.1095, p90 4.4906, p95 6.1379, p99 22.0324, máximo 167.4350. El `eps` queda entre p95 y p99.

**1 clúster** (819 vueltas) y **23 de ruido**. Con un solo clúster, la clase modal de las vueltas no-ruido es 0 para los 19 pilotos, y la fracción dentro de esas vueltas es 1. El ruido por piloto:

| piloto | ruido | vueltas |
| --- | ---: | ---: |
| ALB | 1 | 38 |
| ALO | 1 | 19 |
| ANT | 1 | 42 |
| BEA | 1 | 47 |
| BOR | 1 | 46 |
| COL | 2 | 43 |
| GAS | 0 | 45 |
| HAD | 0 | 47 |
| HAM | 12 | 48 |
| LAW | 0 | 47 |
| LEC | 0 | 46 |
| NOR | 1 | 48 |
| OCO | 0 | 47 |
| PIA | 2 | 47 |
| RUS | 0 | 45 |
| SAI | 1 | 46 |
| STR | 0 | 46 |
| TSU | 0 | 48 |
| VER | 0 | 47 |

### t-SNE

2D, perplexity **30**, `random_state=42`, init PCA, 1000 iteraciones. Color = etiqueta de k-medianas con k=4. Las cruces negras son las 23 vueltas de ruido DBSCAN. Figura: `docs/monza_2025_tsne.png`.
