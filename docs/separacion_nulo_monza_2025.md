# Separación contra un nulo de columnas permutadas (Monza 2025)

Corrida: `python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R`.

La matriz es la del pipeline con la configuración por defecto: mediana de sesión por tipología, mediana del campo en la misma vuelta, ajuste de compuesto y vida dentro de piloto, y las columnas de estilo que entran al K-means (onset apagado, sin `fast__throttle_attack`). El espacio de la silueta es el de ajuste: RobustScaler y PCA automático al 85 % de varianza, K-means++ con la semilla y el `n_init` de `config/pipeline_config.yaml`. Cada réplica del nulo permuta cada columna por su cuenta y vuelve a ajustar el escalador y el PCA. Se conservan las marginales (empates, ceros, colas) y se rompe la relación entre columnas.

Vueltas: 842. Pilotos: 19. Columnas: 17. Componentes en el ajuste: 10. Varianza acumulada: 0.8775. k elegido: 3 (regla `davies_bouldin`).

La silueta observada de esta tabla y la de `eval_df` del pipeline difieren a lo sumo en 0.000000 (mismo espacio y el mismo K-means).

## Percentil de la silueta real

Nulo: 200 permutaciones pedidas. El percentil es el porcentaje de siluetas nulas menores o iguales que la real. Criterio de lectura declarado, no medido: la real se separa del nulo en un k si ese percentil es mayor que 95.

| k | silueta | nulo media | nulo p50 | nulo p95 | percentil | separa del nulo | permutaciones | PCs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 0.1355 | 0.0713 | 0.0693 | 0.0856 | 100.0 | sí | 200 | 10 |
| 3 | 0.1330 | 0.0655 | 0.0649 | 0.0756 | 100.0 | sí | 200 | 10 |
| 4 | 0.1157 | 0.0645 | 0.0644 | 0.0712 | 100.0 | sí | 200 | 10 |
| 5 | 0.1125 | 0.0651 | 0.0656 | 0.0700 | 100.0 | sí | 200 | 10 |
| 6 | 0.1150 | 0.0659 | 0.0659 | 0.0705 | 100.0 | sí | 200 | 10 |
| 7 | 0.1099 | 0.0656 | 0.0656 | 0.0713 | 100.0 | sí | 200 | 10 |

El k de la regla se separa del nulo según el criterio declarado. En los seis k el percentil es 100: las 200 permutaciones quedan por debajo de la silueta real. En el k=3 la real es 0.1330 y el percentil 95 del nulo es 0.0756.

Eso no convierte la partición en clases compactas. La silueta sigue por debajo de 0.25, que es el umbral con el que la regla deja de usar la silueta máxima y pasa a Davies-Bouldin. El k elegido sigue siendo 3 por esa regla. Separarse de este nulo quiere decir que la relación entre columnas aporta silueta; no que los grupos estén bien separados en el espacio.

Este nulo no es el de `docs/separacion_algoritmos_metricas.md`. Allí se permutaban las componentes ya calculadas. Aquí se permutan las 17 columnas normalizadas y se vuelven a ajustar RobustScaler y el PCA. Bajo el nulo el PCA retiene más componentes (mediana 12, contra 10 en los datos reales).

Como la real sí se separa, no corresponde pasar el resultado a una partición solo descriptiva, a un perfil continuo por los scores de las PC, ni a una asignación blanda. La asignación blanda no está implementada. Esas tres quedan como alternativas si en otra matriz —por ejemplo el vector por zona— la real cayera dentro del nulo.

## Sensibilidad sin columnas de IQR 0 o casi constantes

RobustScaler sustituye una escala 0 por 1. Una columna con IQR 0 entra a la distancia con esa escala. «Casi constantes» son las de `near_constant_columns`: más del 90 % de ceros, o menos de 3 valores distintos. Sacarlas es solo esta comparación. El vector por defecto no cambia.

Columnas apartadas: `fast__full_throttle_frac` (IQR 0, casi constante); `medium__full_throttle_frac` (IQR 0, casi constante); `medium__throttle_attack` (IQR 0, casi constante).

Columnas que quedan: 14. Misma regla de lectura.

| k | silueta | nulo media | nulo p50 | nulo p95 | percentil | separa del nulo | permutaciones | PCs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 0.1380 | 0.0747 | 0.0725 | 0.0879 | 100.0 | sí | 200 | 9 |
| 3 | 0.1395 | 0.0691 | 0.0689 | 0.0763 | 100.0 | sí | 200 | 9 |
| 4 | 0.1198 | 0.0692 | 0.0693 | 0.0754 | 100.0 | sí | 200 | 9 |
| 5 | 0.1178 | 0.0702 | 0.0705 | 0.0745 | 100.0 | sí | 200 | 9 |
| 6 | 0.1151 | 0.0706 | 0.0704 | 0.0758 | 100.0 | sí | 200 | 9 |
| 7 | 0.1212 | 0.0706 | 0.0708 | 0.0760 | 100.0 | sí | 200 | 9 |

En el k=3 de la regla, sin esas columnas, el percentil es 100.0 y el criterio declarado dice que sí se separa. La silueta pasa de 0.1330 a 0.1395 y el PCA queda en 9 componentes (mediana 11 bajo el nulo). La separación no la fabrican las tres columnas de IQR 0.

`medium__throttle_attack` es la única de esas tres con peso en las PC: escala 1 y picos grandes en la unidad cruda, peso 0.0435. `fast__full_throttle_frac` y `medium__full_throttle_frac` también quedan con escala 1, pero sus picos son chicos y el peso en las PC es 0.

## Diagnóstico por columna

Sobre la matriz ya normalizada, antes del escalador. `var_within` es la varianza agrupada dentro de piloto (MSW). `var_between` es la varianza, sin ponderar por vueltas, de las medias de cada piloto. `identical_frac` es la fracción de valores finitos iguales al valor más repetido. `peso_pc_share` es la suma de cargas al cuadrado por la varianza explicada de cada PC usada, renormalizada para que las columnas sumen 1. `scaler_scale` es la escala que ajustó RobustScaler; en una columna de IQR 0 esa escala queda en 1.

| columna | var_within | var_between | entre/dentro | idénticos | valores | iqr | escala | IQR 0 | peso PC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fast__trail_brake_frac | 0.000620 | 0.000056 | 0.090 | 0.001 | 842 | 0.023125 | 0.0231 | no | 0.1263 |
| slow__full_throttle_frac | 0.004160 | 0.000812 | 0.195 | 0.012 | 642 | 0.067735 | 0.0677 | no | 0.1045 |
| slow__apex_speed_rel | 6.843610 | 1.464919 | 0.214 | 0.007 | 563 | 2.881325 | 2.8813 | no | 0.0994 |
| slow__brake_point_rel | 378.989458 | 121.499896 | 0.321 | 0.002 | 841 | 22.987486 | 22.9875 | no | 0.0919 |
| fast__brake_point_rel | 251.066562 | 84.702410 | 0.337 | 0.001 | 842 | 19.621805 | 19.6218 | no | 0.0833 |
| medium__brake_point_rel | 89.364099 | 22.076839 | 0.247 | 0.002 | 840 | 12.402399 | 12.4024 | no | 0.0722 |
| slow__trail_brake_frac | 0.002303 | 0.000875 | 0.380 | 0.001 | 842 | 0.067804 | 0.0678 | no | 0.0647 |
| medium__trail_brake_frac | 0.005327 | 0.003024 | 0.568 | 0.001 | 842 | 0.109240 | 0.1092 | no | 0.0581 |
| slow__coast_frac | 0.000854 | 0.000896 | 1.050 | 0.002 | 840 | 0.050791 | 0.0508 | no | 0.0497 |
| fast__coast_frac | 0.000098 | 0.000063 | 0.646 | 0.007 | 743 | 0.015861 | 0.0159 | no | 0.0487 |
| fast__apex_speed_rel | 4.600963 | 5.232581 | 1.137 | 0.005 | 704 | 3.972326 | 3.9723 | no | 0.0445 |
| medium__throttle_attack | 0.374113 | 0.098526 | 0.263 | 0.951 | 39 | 0.000000 | 1.0000 | sí | 0.0435 |
| medium__apex_speed_rel | 11.240265 | 16.961933 | 1.509 | 0.004 | 758 | 7.150087 | 7.1501 | no | 0.0432 |
| slow__throttle_attack | 65.441853 | 19.794317 | 0.302 | 0.010 | 734 | 12.183711 | 12.1837 | no | 0.0358 |
| medium__coast_frac | 0.000304 | 0.000452 | 1.484 | 0.005 | 796 | 0.039417 | 0.0394 | no | 0.0344 |
| fast__full_throttle_frac | 0.000459 | 0.000040 | 0.088 | 0.998 | 3 | 0.000000 | 1.0000 | sí | 0.0000 |
| medium__full_throttle_frac | 0.000012 | 0.000000 | 0.024 | 0.995 | 5 | 0.000000 | 1.0000 | sí | 0.0000 |

