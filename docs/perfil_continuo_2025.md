# Perfil continuo 2025

Camino experimental sobre la matriz de vueltas ya normalizada y escalada. El K-means no se toca.

## Declarado

Esto quedó escrito antes de leer cualquier resultado de este camino.

El perfil continuo es experimental. El K-means sigue siendo el default. No cambia el RobustScaler, el PCA automático del clustering, la regla de k ni las columnas del vector. La matriz es la de la temporada: las mismas features, ya normalizadas, y después el mismo escalador. `fast__brake_point_rel` queda afuera, que es la regla de temporada. Una carrera suelta no usa esa exclusión. No se sacan columnas de IQR 0.

El número de componentes es un análisis paralelo secuencial contra el nulo de permutación por columna. Cada columna de la matriz escalada se permuta por separado, se vuelve a ajustar el PCA y se guarda el autovalor. Son 50 réplicas, semilla 42. Un componente se conserva solo si su autovalor es estrictamente mayor que el percentil 95 de ese nulo y todos los componentes anteriores también lo son. El primero que no pasa corta la secuencia. Si ninguno pasa, el GP no tiene perfil. No se fuerza un componente.

El signo de la solución de referencia se fija sin mirar pilotos: la carga de mayor valor absoluto de cada eje queda positiva. El bootstrap de las cargas reajusta el PCA con ese número de componentes ya elegido. Empareja los ejes por el valor absoluto del coeficiente de congruencia de Tucker y alinea el signo para que el producto punto con la referencia no sea negativo. Son 200 réplicas, semilla 42. El intervalo es el percentil 2.5 y el 97.5.

El perfil de un piloto en un GP es la mediana de los scores de sus vueltas. El intervalo remuestrea esas vueltas con reposición, dentro de cada compuesto, y conserva el conteo de cada compuesto. Son 2000 réplicas, semilla 42, los mismos percentiles de las predicciones ya commiteadas. Una vuelta sin compuesto entra en el estrato `missing`. No se imputa.

La concordancia entre GP es el coeficiente de Tucker de los ejes del mismo índice, en la intersección de las features, con el signo alineado. Con menos de 2 features en común no se define.

La concordancia de compañeros usa `TeamName` de esa carrera. La distancia es la euclídea entre las medianas de los scores. El nulo permuta esas medianas entre los pilotos del GP, 50 veces, semilla 42. Los compañeros quedan más cerca que los pares al azar solo si esa distancia media es estrictamente menor que el percentil 5 del nulo.

Un eje se describe por la feature de mayor carga absoluta y por el signo de esa carga. No se usa la reputación de los pilotos para ponerle nombre.

Las predicciones (a) y (b) de `docs/temporada_2025.md` se evalúan con las mismas reglas de intervalos, sobre la matriz de la carrera suelta de Monza, que conserva `fast__brake_point_rel`. No se trasladan a un eje del PCA. (a) es Hamilton por debajo de Leclerc en `slow__brake_point_rel`, dentro de cada compuesto, en aire limpio. (b) es Leclerc por debajo de Hamilton en la mediana de la suelta de Lesmo 1, Lesmo 2 y la Parabólica. Se confirma si los dos intervalos no se tocan y la dirección es esa. Se contradice si no se tocan y la dirección es la opuesta. Si se tocan, no hay evidencia. Norris contra Piastri sigue siendo exploratorio.

## Medido

Los números de esta sección salen de `python scripts/continuous_profiles_2025.py`. Un eje se nombra por la feature de la tabla de cargas. La mediana de cada piloto está en `docs/perfil_continuo_2025/perfiles.csv`. Las cargas con intervalo están en `docs/perfil_continuo_2025/cargas_bootstrap.csv`.

| carrera | vueltas | features | componentes | varianza acumulada |
| --- | ---: | ---: | ---: | ---: |
| Australia | 547 | 16 | 3 | 0.547 |
| China | 410 | 16 | 2 | 0.583 |
| Japón | 989 | 16 | 6 | 0.935 |
| Baréin | 924 | 16 | 5 | 0.718 |
| Arabia Saudita | 798 | 16 | 5 | 0.720 |
| Miami | 104 | 16 | 4 | 0.656 |
| Emilia-Romaña | 939 | 16 | 1 | 0.619 |
| Mónaco | 1165 | 10 | 3 | 0.560 |
| España | 980 | 16 | 5 | 0.641 |
| Canadá | 1095 | 16 | 4 | 0.851 |
| Austria | 984 | 16 | 4 | 0.614 |
| Gran Bretaña | 430 | 16 | 6 | 0.732 |
| Bélgica | 734 | 16 | 4 | 0.525 |
| Hungría | 1275 | 16 | 1 | 0.290 |
| Países Bajos | 988 | 16 | 4 | 0.576 |
| Italia | 867 | 16 | 5 | 0.652 |
| Azerbaiyán | 796 | 10 | 1 | 0.602 |
| Singapur | 1106 | 16 | 4 | 0.768 |
| Estados Unidos | 897 | 16 | 5 | 0.645 |
| Ciudad de México | 940 | 12 | 5 | 0.739 |
| São Paulo | 1030 | 16 | 5 | 0.754 |
| Las Vegas | 332 | 16 | 3 | 0.579 |
| Catar | 902 | 16 | 5 | 0.938 |
| Abu Dabi | 1033 | 16 | 3 | 0.617 |

### Australia

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 2.5492 | 1.6554 | sí | 0.278 |
| PC2 | 1.4233 | 0.9781 | sí | 0.155 |
| PC3 | 1.0343 | 0.9080 | sí | 0.113 |
| PC4 | 0.8090 | 0.8473 | no | 0.088 |
| PC5 | 0.7273 | 0.7840 | no | 0.079 |
| PC6 | 0.6261 | 0.7317 | no | 0.068 |
| PC7 | 0.5297 | 0.6813 | no | 0.058 |
| PC8 | 0.4510 | 0.6536 | no | 0.049 |
| PC9 | 0.3791 | 0.6027 | no | 0.041 |
| PC10 | 0.3138 | 0.5765 | no | 0.034 |
| PC11 | 0.2259 | 0.5369 | no | 0.025 |
| PC12 | 0.0803 | 0.4990 | no | 0.009 |
| PC13 | 0.0034 | 0.0037 | no | 0.000 |
| PC14 | 0.0020 | 0.0029 | no | 0.000 |
| PC15 | 0.0009 | 0.0009 | no | 0.000 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 | PC2 | PC3 |
| --- | ---: | ---: | ---: |
| `fast__apex_speed_rel` | -0.2644 | 0.0920 | 0.2074 |
| `medium__apex_speed_rel` | -0.3007 | 0.0827 | 0.5048 |
| `slow__apex_speed_rel` | -0.2290 | 0.1432 | 0.3043 |
| `medium__brake_point_rel` | 0.1599 | 0.1700 | 0.1707 |
| `slow__brake_point_rel` | 0.0700 | 0.1706 | -0.0490 |
| `fast__coast_frac` | 0.0000 | 0.0000 | 0.0000 |
| `medium__coast_frac` | -0.2212 | 0.3537 | -0.0860 |
| `slow__coast_frac` | -0.2605 | 0.4154 | -0.1092 |
| `fast__full_throttle_frac` | -0.0002 | -0.0003 | 0.0029 |
| `medium__full_throttle_frac` | -0.0147 | -0.0119 | -0.0003 |
| `slow__full_throttle_frac` | -0.2817 | -0.2699 | 0.4338 |
| `medium__throttle_attack` | 0.5835 | 0.5981 | 0.3016 |
| `slow__throttle_attack` | -0.1898 | 0.2190 | 0.1622 |
| `fast__trail_brake_frac` | 0.0049 | -0.0050 | 0.0072 |
| `medium__trail_brake_frac` | 0.3759 | -0.3237 | 0.2418 |
| `slow__trail_brake_frac` | 0.2063 | -0.1583 | 0.4412 |

PC1: la carga de mayor valor absoluto es `medium__throttle_attack` (0.5835, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `medium__throttle_attack` (0.5981, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5048, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 7 pares, distancia media 1.288, percentil 5 del nulo 1.470, percentil de la distancia 0.0, más cerca que el nulo: sí.

### China

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 8.9537 | 8.8890 | sí | 0.480 |
| PC2 | 1.9153 | 1.8430 | sí | 0.103 |
| PC3 | 1.5551 | 1.5676 | no | 0.083 |
| PC4 | 1.2313 | 0.9243 | no | 0.066 |
| PC5 | 0.9965 | 0.8260 | no | 0.053 |
| PC6 | 0.8131 | 0.7589 | no | 0.044 |
| PC7 | 0.6672 | 0.7066 | no | 0.036 |
| PC8 | 0.6124 | 0.6752 | no | 0.033 |
| PC9 | 0.5026 | 0.6358 | no | 0.027 |
| PC10 | 0.4731 | 0.6016 | no | 0.025 |
| PC11 | 0.4226 | 0.5737 | no | 0.023 |
| PC12 | 0.2690 | 0.5299 | no | 0.014 |
| PC13 | 0.2247 | 0.4737 | no | 0.012 |
| PC14 | 0.0010 | 0.0012 | no | 0.000 |
| PC15 | 0.0007 | 0.0007 | no | 0.000 |
| PC16 | 0.0003 | 0.0003 | no | 0.000 |

| feature | PC1 | PC2 |
| --- | ---: | ---: |
| `fast__apex_speed_rel` | 0.0072 | 0.0288 |
| `medium__apex_speed_rel` | -0.0082 | 0.0257 |
| `slow__apex_speed_rel` | -0.0064 | 0.1207 |
| `medium__brake_point_rel` | -0.0117 | 0.0801 |
| `slow__brake_point_rel` | 0.0132 | 0.1279 |
| `fast__coast_frac` | 0.0004 | -0.0008 |
| `medium__coast_frac` | -0.0470 | -0.0439 |
| `slow__coast_frac` | -0.0414 | -0.0973 |
| `fast__full_throttle_frac` | 0.0296 | -0.0207 |
| `medium__full_throttle_frac` | -0.0010 | -0.0084 |
| `slow__full_throttle_frac` | 0.9926 | -0.0003 |
| `medium__throttle_attack` | 0.0278 | 0.8065 |
| `slow__throttle_attack` | -0.0824 | 0.4674 |
| `fast__trail_brake_frac` | -0.0001 | 0.0001 |
| `medium__trail_brake_frac` | 0.0377 | 0.1510 |
| `slow__trail_brake_frac` | 0.0220 | 0.2399 |

PC1: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.9926, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `medium__throttle_attack` (0.8065, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 9 pares, distancia media 0.578, percentil 5 del nulo 0.570, percentil de la distancia 6.0, más cerca que el nulo: no.

### Japón

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 36.9962 | 36.9717 | sí | 0.811 |
| PC2 | 1.7724 | 0.8081 | sí | 0.039 |
| PC3 | 1.2347 | 0.7577 | sí | 0.027 |
| PC4 | 1.2089 | 0.7312 | sí | 0.026 |
| PC5 | 0.7702 | 0.7092 | sí | 0.017 |
| PC6 | 0.7051 | 0.6868 | sí | 0.015 |
| PC7 | 0.5959 | 0.6629 | no | 0.013 |
| PC8 | 0.5321 | 0.6500 | no | 0.012 |
| PC9 | 0.4119 | 0.6307 | no | 0.009 |
| PC10 | 0.3696 | 0.6119 | no | 0.008 |
| PC11 | 0.3316 | 0.5906 | no | 0.007 |
| PC12 | 0.2700 | 0.5757 | no | 0.006 |
| PC13 | 0.2061 | 0.5524 | no | 0.005 |
| PC14 | 0.1785 | 0.4825 | no | 0.004 |
| PC15 | 0.0536 | 0.4530 | no | 0.001 |
| PC16 | 0.0032 | 0.0039 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 | PC5 | PC6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | -0.0015 | 0.1372 | 0.3904 | 0.2532 | -0.1178 | -0.1690 |
| `medium__apex_speed_rel` | 0.0018 | -0.0506 | 0.3260 | 0.2267 | 0.5385 | 0.1932 |
| `slow__apex_speed_rel` | 0.0044 | 0.1197 | 0.3359 | 0.3368 | 0.1782 | -0.1447 |
| `medium__brake_point_rel` | -0.0097 | 0.1446 | -0.0287 | 0.3602 | -0.1862 | 0.5745 |
| `slow__brake_point_rel` | 0.0000 | 0.0223 | -0.3573 | 0.0264 | -0.1625 | 0.4435 |
| `fast__coast_frac` | -0.0076 | 0.5762 | -0.0207 | -0.0460 | -0.0747 | 0.0088 |
| `medium__coast_frac` | -0.0058 | 0.5804 | -0.0437 | 0.0012 | -0.1131 | 0.0792 |
| `slow__coast_frac` | -0.0027 | 0.3505 | 0.0513 | -0.0691 | 0.0931 | -0.2278 |
| `fast__full_throttle_frac` | 0.0143 | -0.1777 | 0.4616 | 0.1141 | -0.2638 | 0.2270 |
| `medium__full_throttle_frac` | 0.0140 | -0.0349 | 0.4044 | -0.3495 | -0.3303 | 0.2521 |
| `slow__full_throttle_frac` | 0.9995 | 0.0105 | -0.0209 | 0.0179 | 0.0045 | -0.0017 |
| `medium__throttle_attack` | -0.0129 | 0.0390 | -0.2516 | 0.4614 | -0.1265 | -0.2623 |
| `slow__throttle_attack` | 0.0075 | 0.0584 | 0.1583 | 0.1021 | -0.5283 | -0.2920 |
| `fast__trail_brake_frac` | -0.0001 | -0.0067 | -0.0118 | -0.0088 | -0.0059 | 0.0108 |
| `medium__trail_brake_frac` | -0.0023 | -0.3169 | -0.1152 | 0.0749 | -0.3156 | -0.2278 |
| `slow__trail_brake_frac` | -0.0151 | -0.1130 | -0.1271 | 0.5188 | -0.0527 | 0.0845 |

PC1: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.9995, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `medium__coast_frac` (0.5804, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `fast__full_throttle_frac` (0.4616, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `slow__trail_brake_frac` (0.5188, positiva). El intervalo de esa carga no incluye el 0.
PC5: la carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5385, positiva). El intervalo de esa carga no incluye el 0.
PC6: la carga de mayor valor absoluto es `medium__brake_point_rel` (0.5745, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 1.872, percentil 5 del nulo 2.209, percentil de la distancia 0.0, más cerca que el nulo: sí.

### Baréin

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 2.4643 | 1.4890 | sí | 0.228 |
| PC2 | 1.7091 | 1.2914 | sí | 0.158 |
| PC3 | 1.4267 | 0.9394 | sí | 0.132 |
| PC4 | 1.2745 | 0.8721 | sí | 0.118 |
| PC5 | 0.8791 | 0.8236 | sí | 0.081 |
| PC6 | 0.6631 | 0.6992 | no | 0.061 |
| PC7 | 0.5018 | 0.6545 | no | 0.046 |
| PC8 | 0.4365 | 0.6297 | no | 0.040 |
| PC9 | 0.3227 | 0.6060 | no | 0.030 |
| PC10 | 0.3179 | 0.5867 | no | 0.029 |
| PC11 | 0.2665 | 0.5606 | no | 0.025 |
| PC12 | 0.1997 | 0.5274 | no | 0.018 |
| PC13 | 0.1646 | 0.4983 | no | 0.015 |
| PC14 | 0.1344 | 0.4730 | no | 0.012 |
| PC15 | 0.0323 | 0.4542 | no | 0.003 |
| PC16 | 0.0014 | 0.0019 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 | PC5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | -0.0700 | -0.1991 | 0.3488 | -0.0950 | -0.2095 |
| `medium__apex_speed_rel` | -0.1869 | 0.2273 | 0.1158 | -0.4304 | -0.0811 |
| `slow__apex_speed_rel` | -0.3705 | 0.7335 | 0.1408 | -0.2311 | -0.0259 |
| `medium__brake_point_rel` | -0.0554 | 0.2951 | -0.0038 | 0.5811 | -0.1399 |
| `slow__brake_point_rel` | -0.0954 | 0.3073 | 0.0131 | 0.4885 | -0.0126 |
| `fast__coast_frac` | 0.2754 | 0.2045 | -0.2839 | -0.1362 | 0.1772 |
| `medium__coast_frac` | 0.2436 | 0.2007 | -0.2659 | -0.1173 | 0.0535 |
| `slow__coast_frac` | 0.2712 | 0.2022 | -0.2948 | -0.1503 | 0.1951 |
| `fast__full_throttle_frac` | -0.1095 | -0.0197 | 0.4211 | -0.1031 | -0.1589 |
| `medium__full_throttle_frac` | 0.4153 | 0.1310 | 0.5707 | -0.0362 | 0.5372 |
| `slow__full_throttle_frac` | 0.3275 | 0.0496 | 0.1601 | 0.0820 | -0.2343 |
| `medium__throttle_attack` | -0.2169 | -0.1023 | -0.2552 | -0.0932 | -0.0589 |
| `slow__throttle_attack` | -0.2715 | -0.0797 | -0.1113 | -0.1654 | 0.1934 |
| `fast__trail_brake_frac` | -0.0041 | 0.0113 | 0.0004 | 0.0083 | 0.0041 |
| `medium__trail_brake_frac` | -0.3173 | -0.0730 | 0.0229 | 0.2568 | 0.5560 |
| `slow__trail_brake_frac` | -0.2979 | -0.1548 | -0.0016 | -0.0208 | 0.3716 |

PC1: la carga de mayor valor absoluto es `medium__full_throttle_frac` (0.4153, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__apex_speed_rel` (0.7335, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `medium__full_throttle_frac` (0.5707, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `medium__brake_point_rel` (0.5811, positiva). El intervalo de esa carga no incluye el 0.
PC5: la carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5560, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 1.701, percentil 5 del nulo 2.061, percentil de la distancia 0.0, más cerca que el nulo: sí.

### Arabia Saudita

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 3.0256 | 1.9238 | sí | 0.269 |
| PC2 | 1.9503 | 1.2798 | sí | 0.173 |
| PC3 | 1.1606 | 0.9456 | sí | 0.103 |
| PC4 | 1.0889 | 0.8626 | sí | 0.097 |
| PC5 | 0.8841 | 0.8120 | sí | 0.078 |
| PC6 | 0.6840 | 0.7689 | no | 0.061 |
| PC7 | 0.5737 | 0.6778 | no | 0.051 |
| PC8 | 0.4448 | 0.6356 | no | 0.039 |
| PC9 | 0.4029 | 0.6134 | no | 0.036 |
| PC10 | 0.3044 | 0.5867 | no | 0.027 |
| PC11 | 0.2244 | 0.5624 | no | 0.020 |
| PC12 | 0.2137 | 0.5222 | no | 0.019 |
| PC13 | 0.1431 | 0.4930 | no | 0.013 |
| PC14 | 0.1325 | 0.4632 | no | 0.012 |
| PC15 | 0.0299 | 0.4420 | no | 0.003 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 | PC5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | 0.2045 | 0.3907 | 0.5207 | 0.6408 | -0.0008 |
| `medium__apex_speed_rel` | 0.1927 | 0.0359 | -0.2298 | 0.0288 | -0.3450 |
| `slow__apex_speed_rel` | 0.1198 | 0.0637 | -0.4936 | 0.1701 | -0.3456 |
| `medium__brake_point_rel` | -0.1808 | 0.1973 | -0.1525 | -0.0957 | 0.2566 |
| `slow__brake_point_rel` | -0.2093 | 0.0044 | 0.3360 | -0.3655 | 0.3074 |
| `fast__coast_frac` | 0.0038 | -0.3825 | -0.1012 | 0.3024 | 0.2817 |
| `medium__coast_frac` | 0.0205 | -0.3641 | -0.0781 | 0.2397 | 0.2366 |
| `slow__coast_frac` | -0.0083 | -0.3068 | -0.0930 | 0.3980 | 0.3059 |
| `fast__full_throttle_frac` | 0.4224 | 0.1158 | -0.0822 | -0.0095 | 0.0482 |
| `medium__full_throttle_frac` | 0.7043 | 0.1273 | -0.0533 | -0.2671 | 0.4316 |
| `slow__full_throttle_frac` | 0.3605 | -0.2840 | 0.1644 | -0.1068 | -0.1573 |
| `medium__throttle_attack` | -0.0523 | 0.1102 | -0.2853 | 0.0339 | 0.1866 |
| `slow__throttle_attack` | -0.0484 | 0.1448 | -0.3576 | 0.0336 | 0.2880 |
| `fast__trail_brake_frac` | -0.0000 | -0.0000 | -0.0000 | -0.0000 | -0.0000 |
| `medium__trail_brake_frac` | -0.1209 | 0.3962 | -0.1047 | 0.0771 | 0.1855 |
| `slow__trail_brake_frac` | -0.0750 | 0.3602 | -0.1197 | 0.1358 | 0.0820 |

PC1: la carga de mayor valor absoluto es `medium__full_throttle_frac` (0.7043, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `medium__trail_brake_frac` (0.3962, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `fast__apex_speed_rel` (0.5207, positiva). El intervalo de esa carga incluye el 0.
PC4: la carga de mayor valor absoluto es `fast__apex_speed_rel` (0.6408, positiva). El intervalo de esa carga no incluye el 0.
PC5: la carga de mayor valor absoluto es `medium__full_throttle_frac` (0.4316, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 8 pares, distancia media 1.435, percentil 5 del nulo 2.270, percentil de la distancia 0.0, más cerca que el nulo: sí.

### Miami

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 2.9162 | 2.7409 | sí | 0.207 |
| PC2 | 2.5907 | 1.9748 | sí | 0.184 |
| PC3 | 2.1884 | 1.6859 | sí | 0.155 |
| PC4 | 1.5590 | 1.4429 | sí | 0.111 |
| PC5 | 1.1399 | 1.2438 | no | 0.081 |
| PC6 | 0.9712 | 1.1236 | no | 0.069 |
| PC7 | 0.8475 | 1.0036 | no | 0.060 |
| PC8 | 0.6598 | 0.8861 | no | 0.047 |
| PC9 | 0.4090 | 0.7724 | no | 0.029 |
| PC10 | 0.3238 | 0.6745 | no | 0.023 |
| PC11 | 0.2519 | 0.5681 | no | 0.018 |
| PC12 | 0.2374 | 0.4629 | no | 0.017 |
| PC13 | 0.0090 | 0.4074 | no | 0.001 |
| PC14 | 0.0035 | 0.3483 | no | 0.000 |
| PC15 | 0.0007 | 0.0041 | no | 0.000 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 |
| --- | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | 0.0126 | -0.1077 | 0.1979 | 0.1242 |
| `medium__apex_speed_rel` | 0.3011 | -0.2729 | 0.4082 | -0.1719 |
| `slow__apex_speed_rel` | -0.1351 | -0.1714 | 0.2362 | 0.4333 |
| `medium__brake_point_rel` | 0.1595 | -0.4207 | 0.4494 | -0.5052 |
| `slow__brake_point_rel` | 0.1981 | -0.0681 | -0.1455 | 0.1735 |
| `fast__coast_frac` | -0.2884 | -0.1269 | 0.1188 | 0.1350 |
| `medium__coast_frac` | -0.2915 | -0.1306 | 0.1205 | 0.1367 |
| `slow__coast_frac` | -0.2843 | -0.1283 | 0.1145 | 0.1429 |
| `fast__full_throttle_frac` | -0.0528 | 0.7433 | 0.6238 | 0.0166 |
| `medium__full_throttle_frac` | 0.2336 | 0.1935 | 0.0298 | -0.0368 |
| `slow__full_throttle_frac` | 0.4823 | -0.1333 | 0.1879 | 0.5644 |
| `medium__throttle_attack` | -0.2066 | -0.1772 | 0.1687 | 0.1867 |
| `slow__throttle_attack` | -0.4021 | -0.0510 | 0.0745 | -0.2242 |
| `fast__trail_brake_frac` | 0.0083 | 0.0053 | -0.0072 | -0.0075 |
| `medium__trail_brake_frac` | -0.0000 | -0.0000 | -0.0000 | -0.0000 |
| `slow__trail_brake_frac` | 0.2879 | 0.1076 | -0.1188 | -0.1388 |

PC1: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.4823, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `fast__full_throttle_frac` (0.7433, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `fast__full_throttle_frac` (0.6238, positiva). El intervalo de esa carga incluye el 0.
PC4: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.5644, positiva). El intervalo de esa carga incluye el 0.

Compañeros: 4 pares, distancia media 2.524, percentil 5 del nulo 2.035, percentil de la distancia 48.0, más cerca que el nulo: no.

### Emilia-Romaña

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 14.3122 | 13.9805 | sí | 0.619 |
| PC2 | 2.6403 | 2.6644 | no | 0.114 |
| PC3 | 1.3878 | 0.8783 | no | 0.060 |
| PC4 | 1.1801 | 0.8364 | no | 0.051 |
| PC5 | 0.8404 | 0.7882 | no | 0.036 |
| PC6 | 0.7312 | 0.7134 | no | 0.032 |
| PC7 | 0.4883 | 0.6505 | no | 0.021 |
| PC8 | 0.4348 | 0.6221 | no | 0.019 |
| PC9 | 0.3957 | 0.5960 | no | 0.017 |
| PC10 | 0.3388 | 0.5675 | no | 0.015 |
| PC11 | 0.2656 | 0.5405 | no | 0.011 |
| PC12 | 0.1131 | 0.5238 | no | 0.005 |
| PC13 | 0.0056 | 0.0076 | no | 0.000 |
| PC14 | 0.0010 | 0.0011 | no | 0.000 |
| PC15 | 0.0000 | 0.0000 | no | 0.000 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 |
| --- | ---: |
| `fast__apex_speed_rel` | 0.0123 |
| `medium__apex_speed_rel` | 0.0213 |
| `slow__apex_speed_rel` | 0.0035 |
| `medium__brake_point_rel` | 0.0017 |
| `slow__brake_point_rel` | -0.0086 |
| `fast__coast_frac` | -0.0000 |
| `medium__coast_frac` | -0.0147 |
| `slow__coast_frac` | -0.0163 |
| `fast__full_throttle_frac` | -0.0010 |
| `medium__full_throttle_frac` | -0.0111 |
| `slow__full_throttle_frac` | -0.1633 |
| `medium__throttle_attack` | 0.9849 |
| `slow__throttle_attack` | 0.0402 |
| `fast__trail_brake_frac` | 0.0000 |
| `medium__trail_brake_frac` | 0.0005 |
| `slow__trail_brake_frac` | 0.0169 |

PC1: la carga de mayor valor absoluto es `medium__throttle_attack` (0.9849, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 1.734, percentil 5 del nulo 1.478, percentil de la distancia 56.0, más cerca que el nulo: no.

### Mónaco

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 1.8032 | 1.2859 | sí | 0.237 |
| PC2 | 1.4343 | 1.1147 | sí | 0.189 |
| PC3 | 1.0128 | 0.8502 | sí | 0.133 |
| PC4 | 0.7075 | 0.7948 | no | 0.093 |
| PC5 | 0.6298 | 0.7347 | no | 0.083 |
| PC6 | 0.5600 | 0.6944 | no | 0.074 |
| PC7 | 0.4698 | 0.6472 | no | 0.062 |
| PC8 | 0.4256 | 0.6242 | no | 0.056 |
| PC9 | 0.3519 | 0.5958 | no | 0.046 |
| PC10 | 0.2001 | 0.4199 | no | 0.026 |

| feature | PC1 | PC2 | PC3 |
| --- | ---: | ---: | ---: |
| `fast__apex_speed_rel` | 0.2577 | 0.1726 | -0.3127 |
| `slow__apex_speed_rel` | 0.2727 | 0.1020 | -0.3550 |
| `slow__brake_point_rel` | -0.2077 | -0.1286 | 0.6627 |
| `fast__coast_frac` | -0.1922 | -0.4728 | -0.2799 |
| `slow__coast_frac` | -0.1154 | -0.2976 | -0.2343 |
| `fast__full_throttle_frac` | 0.3422 | 0.1099 | -0.0713 |
| `slow__full_throttle_frac` | 0.6115 | -0.0690 | 0.1057 |
| `slow__throttle_attack` | -0.4184 | 0.7288 | -0.1719 |
| `fast__trail_brake_frac` | 0.2705 | 0.1798 | 0.2839 |
| `slow__trail_brake_frac` | 0.1628 | 0.2255 | 0.2781 |

PC1: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.6115, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__throttle_attack` (0.7288, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `slow__brake_point_rel` (0.6627, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 1.237, percentil 5 del nulo 1.239, percentil de la distancia 6.0, más cerca que el nulo: sí.

### España

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 2.0616 | 1.2335 | sí | 0.202 |
| PC2 | 1.6233 | 0.9085 | sí | 0.159 |
| PC3 | 1.1255 | 0.8661 | sí | 0.111 |
| PC4 | 0.9125 | 0.8302 | sí | 0.090 |
| PC5 | 0.8034 | 0.7987 | sí | 0.079 |
| PC6 | 0.6281 | 0.7712 | no | 0.062 |
| PC7 | 0.5897 | 0.7199 | no | 0.058 |
| PC8 | 0.5257 | 0.6873 | no | 0.052 |
| PC9 | 0.4410 | 0.6647 | no | 0.043 |
| PC10 | 0.4193 | 0.6381 | no | 0.041 |
| PC11 | 0.3903 | 0.6182 | no | 0.038 |
| PC12 | 0.2877 | 0.6043 | no | 0.028 |
| PC13 | 0.2670 | 0.5699 | no | 0.026 |
| PC14 | 0.1035 | 0.5357 | no | 0.010 |
| PC15 | 0.0033 | 0.0039 | no | 0.000 |
| PC16 | 0.0028 | 0.0036 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 | PC5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | 0.0525 | 0.3255 | -0.0202 | 0.0182 | 0.0866 |
| `medium__apex_speed_rel` | 0.2304 | 0.2729 | -0.0846 | 0.4039 | -0.1080 |
| `slow__apex_speed_rel` | 0.2175 | 0.2032 | -0.1283 | 0.3513 | -0.0465 |
| `medium__brake_point_rel` | 0.0073 | -0.1965 | 0.4084 | -0.0377 | 0.0456 |
| `slow__brake_point_rel` | -0.0380 | -0.0563 | 0.2619 | -0.3997 | -0.2309 |
| `fast__coast_frac` | 0.5914 | -0.0079 | 0.4961 | -0.0416 | -0.2556 |
| `medium__coast_frac` | 0.4350 | -0.2581 | -0.2895 | -0.1213 | 0.1000 |
| `slow__coast_frac` | 0.4276 | -0.2305 | -0.2114 | -0.1050 | 0.0283 |
| `fast__full_throttle_frac` | -0.0083 | 0.0116 | -0.0037 | -0.0089 | 0.0030 |
| `medium__full_throttle_frac` | 0.1419 | 0.5143 | -0.0189 | -0.3685 | -0.0938 |
| `slow__full_throttle_frac` | -0.0319 | 0.5833 | 0.1027 | -0.1032 | 0.1512 |
| `medium__throttle_attack` | -0.0488 | -0.0620 | 0.3650 | 0.1808 | 0.7252 |
| `slow__throttle_attack` | 0.2494 | 0.0677 | 0.3275 | -0.0448 | 0.2249 |
| `fast__trail_brake_frac` | -0.0149 | 0.0021 | 0.0079 | 0.0053 | -0.0018 |
| `medium__trail_brake_frac` | -0.2921 | -0.0578 | 0.2979 | 0.0737 | -0.4292 |
| `slow__trail_brake_frac` | 0.0473 | -0.0085 | 0.1605 | 0.5813 | -0.2340 |

PC1: la carga de mayor valor absoluto es `fast__coast_frac` (0.5914, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.5833, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `fast__coast_frac` (0.4961, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `slow__trail_brake_frac` (0.5813, positiva). El intervalo de esa carga no incluye el 0.
PC5: la carga de mayor valor absoluto es `medium__throttle_attack` (0.7252, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 9 pares, distancia media 1.318, percentil 5 del nulo 2.150, percentil de la distancia 0.0, más cerca que el nulo: sí.

### Canadá

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 15.7078 | 15.5678 | sí | 0.666 |
| PC2 | 2.1371 | 0.9764 | sí | 0.091 |
| PC3 | 1.2373 | 0.8957 | sí | 0.052 |
| PC4 | 0.9947 | 0.8613 | sí | 0.042 |
| PC5 | 0.7464 | 0.8124 | no | 0.032 |
| PC6 | 0.6389 | 0.7710 | no | 0.027 |
| PC7 | 0.5608 | 0.7338 | no | 0.024 |
| PC8 | 0.5028 | 0.7029 | no | 0.021 |
| PC9 | 0.4706 | 0.6805 | no | 0.020 |
| PC10 | 0.2814 | 0.6468 | no | 0.012 |
| PC11 | 0.2382 | 0.6103 | no | 0.010 |
| PC12 | 0.0634 | 0.5606 | no | 0.003 |
| PC13 | 0.0020 | 0.0022 | no | 0.000 |
| PC14 | 0.0005 | 0.0011 | no | 0.000 |
| PC15 | 0.0001 | 0.0001 | no | 0.000 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 |
| --- | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | -0.0601 | -0.1784 | -0.0750 | 0.5766 |
| `medium__apex_speed_rel` | 0.0003 | 0.3091 | 0.3018 | 0.1026 |
| `slow__apex_speed_rel` | 0.0094 | 0.3119 | 0.5205 | 0.0487 |
| `medium__brake_point_rel` | 0.0172 | -0.2979 | -0.2051 | -0.1920 |
| `slow__brake_point_rel` | 0.0228 | -0.3945 | -0.2636 | -0.0179 |
| `fast__coast_frac` | -0.0000 | -0.0002 | 0.0001 | -0.0006 |
| `medium__coast_frac` | 0.0004 | -0.3406 | 0.4819 | -0.1541 |
| `slow__coast_frac` | -0.0011 | -0.3133 | 0.4713 | -0.1972 |
| `fast__full_throttle_frac` | 0.0002 | 0.0023 | -0.0005 | 0.0029 |
| `medium__full_throttle_frac` | -0.0287 | 0.4572 | -0.1336 | 0.1882 |
| `slow__full_throttle_frac` | -0.0058 | 0.0014 | 0.0000 | 0.0044 |
| `medium__throttle_attack` | -0.0111 | 0.0917 | -0.0077 | 0.1397 |
| `slow__throttle_attack` | 0.9946 | -0.0057 | 0.0049 | 0.0893 |
| `fast__trail_brake_frac` | 0.0002 | -0.0004 | -0.0006 | 0.0005 |
| `medium__trail_brake_frac` | 0.0151 | 0.2057 | -0.2072 | -0.4667 |
| `slow__trail_brake_frac` | 0.0707 | 0.2388 | -0.0748 | -0.5234 |

PC1: la carga de mayor valor absoluto es `slow__throttle_attack` (0.9946, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `medium__full_throttle_frac` (0.4572, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `slow__apex_speed_rel` (0.5205, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `fast__apex_speed_rel` (0.5766, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 2.095, percentil 5 del nulo 2.104, percentil de la distancia 4.0, más cerca que el nulo: sí.

### Austria

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 3.1541 | 2.6861 | sí | 0.284 |
| PC2 | 1.3714 | 0.9488 | sí | 0.123 |
| PC3 | 1.2721 | 0.8335 | sí | 0.114 |
| PC4 | 1.0252 | 0.7929 | sí | 0.092 |
| PC5 | 0.7366 | 0.7563 | no | 0.066 |
| PC6 | 0.6375 | 0.7189 | no | 0.057 |
| PC7 | 0.5556 | 0.6901 | no | 0.050 |
| PC8 | 0.4361 | 0.6619 | no | 0.039 |
| PC9 | 0.3983 | 0.6404 | no | 0.036 |
| PC10 | 0.3963 | 0.6026 | no | 0.036 |
| PC11 | 0.3542 | 0.5751 | no | 0.032 |
| PC12 | 0.3506 | 0.5531 | no | 0.032 |
| PC13 | 0.2275 | 0.4763 | no | 0.020 |
| PC14 | 0.2013 | 0.4183 | no | 0.018 |
| PC15 | 0.0001 | 0.0001 | no | 0.000 |
| PC16 | 0.0001 | 0.0001 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 |
| --- | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | 0.2248 | 0.1898 | -0.2823 | -0.1579 |
| `medium__apex_speed_rel` | 0.0621 | 0.5527 | -0.1607 | -0.1767 |
| `slow__apex_speed_rel` | -0.0228 | 0.3943 | -0.1662 | -0.4472 |
| `medium__brake_point_rel` | -0.0788 | -0.0632 | 0.0379 | -0.1256 |
| `slow__brake_point_rel` | -0.0302 | -0.4413 | 0.1046 | -0.0313 |
| `fast__coast_frac` | -0.0001 | -0.0012 | -0.0001 | -0.0003 |
| `medium__coast_frac` | 0.0566 | -0.2579 | -0.2585 | -0.2616 |
| `slow__coast_frac` | 0.0337 | -0.1904 | -0.2944 | -0.3480 |
| `fast__full_throttle_frac` | 0.0267 | 0.1112 | 0.0123 | 0.0121 |
| `medium__full_throttle_frac` | 0.8795 | 0.0289 | 0.3779 | -0.0223 |
| `slow__full_throttle_frac` | 0.0850 | 0.2541 | -0.3595 | 0.6064 |
| `medium__throttle_attack` | -0.2980 | 0.1154 | 0.1463 | -0.0179 |
| `slow__throttle_attack` | -0.1096 | 0.0761 | 0.3699 | -0.3356 |
| `fast__trail_brake_frac` | -0.0002 | -0.0001 | 0.0003 | 0.0003 |
| `medium__trail_brake_frac` | -0.1503 | 0.1765 | 0.3182 | 0.2268 |
| `slow__trail_brake_frac` | -0.1697 | 0.2712 | 0.4115 | -0.0691 |

PC1: la carga de mayor valor absoluto es `medium__full_throttle_frac` (0.8795, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5527, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `slow__trail_brake_frac` (0.4115, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.6064, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 7 pares, distancia media 1.069, percentil 5 del nulo 1.361, percentil de la distancia 2.0, más cerca que el nulo: sí.

### Gran Bretaña

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 4.3380 | 4.2963 | sí | 0.241 |
| PC2 | 2.5063 | 2.2669 | sí | 0.139 |
| PC3 | 2.2138 | 1.8040 | sí | 0.123 |
| PC4 | 1.8181 | 1.2128 | sí | 0.101 |
| PC5 | 1.2467 | 1.0245 | sí | 0.069 |
| PC6 | 1.0264 | 0.9274 | sí | 0.057 |
| PC7 | 0.8236 | 0.8664 | no | 0.046 |
| PC8 | 0.7052 | 0.8250 | no | 0.039 |
| PC9 | 0.6302 | 0.7876 | no | 0.035 |
| PC10 | 0.5566 | 0.7440 | no | 0.031 |
| PC11 | 0.5095 | 0.7225 | no | 0.028 |
| PC12 | 0.4376 | 0.6850 | no | 0.024 |
| PC13 | 0.3945 | 0.6542 | no | 0.022 |
| PC14 | 0.2988 | 0.6121 | no | 0.017 |
| PC15 | 0.2580 | 0.5841 | no | 0.014 |
| PC16 | 0.2088 | 0.4852 | no | 0.012 |

| feature | PC1 | PC2 | PC3 | PC4 | PC5 | PC6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | -0.0623 | 0.2622 | -0.3734 | 0.2328 | -0.4088 | 0.0882 |
| `medium__apex_speed_rel` | -0.0988 | 0.0762 | -0.2961 | 0.2052 | -0.1287 | 0.3860 |
| `slow__apex_speed_rel` | 0.0337 | 0.0638 | -0.2184 | 0.3027 | -0.1519 | -0.3027 |
| `medium__brake_point_rel` | 0.0896 | -0.0957 | 0.2666 | -0.0928 | 0.0633 | -0.3353 |
| `slow__brake_point_rel` | 0.9752 | 0.1370 | -0.1145 | 0.0067 | 0.0612 | 0.0918 |
| `fast__coast_frac` | 0.0038 | -0.1259 | -0.0887 | 0.3465 | 0.3634 | 0.1623 |
| `medium__coast_frac` | -0.0351 | -0.1755 | -0.0814 | 0.2987 | 0.2451 | 0.2001 |
| `slow__coast_frac` | 0.0112 | -0.1043 | -0.1716 | 0.3552 | 0.1562 | -0.3579 |
| `fast__full_throttle_frac` | 0.0448 | 0.3639 | 0.5890 | 0.3956 | -0.4433 | 0.0359 |
| `medium__full_throttle_frac` | -0.0206 | 0.0716 | 0.2969 | 0.1507 | 0.2000 | 0.4383 |
| `slow__full_throttle_frac` | -0.1491 | 0.8169 | -0.1370 | -0.1126 | 0.4716 | -0.0816 |
| `medium__throttle_attack` | -0.0063 | -0.0648 | -0.2695 | -0.0217 | -0.2045 | 0.1681 |
| `slow__throttle_attack` | 0.0096 | -0.1351 | -0.0642 | -0.0409 | -0.0133 | 0.2011 |
| `fast__trail_brake_frac` | 0.0021 | 0.0764 | -0.0948 | -0.3688 | -0.1974 | -0.0354 |
| `medium__trail_brake_frac` | -0.0027 | 0.0508 | -0.2244 | -0.2014 | -0.1700 | -0.0365 |
| `slow__trail_brake_frac` | -0.0022 | 0.0128 | 0.0849 | -0.3121 | -0.0152 | 0.4061 |

PC1: la carga de mayor valor absoluto es `slow__brake_point_rel` (0.9752, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.8169, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `fast__full_throttle_frac` (0.5890, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `fast__full_throttle_frac` (0.3956, positiva). El intervalo de esa carga incluye el 0.
PC5: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.4716, positiva). El intervalo de esa carga no incluye el 0.
PC6: la carga de mayor valor absoluto es `medium__full_throttle_frac` (0.4383, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 7 pares, distancia media 2.595, percentil 5 del nulo 2.883, percentil de la distancia 2.0, más cerca que el nulo: sí.

### Bélgica

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 1.4589 | 1.1860 | sí | 0.159 |
| PC2 | 1.2825 | 0.9878 | sí | 0.140 |
| PC3 | 1.1995 | 0.8520 | sí | 0.131 |
| PC4 | 0.8650 | 0.8015 | sí | 0.094 |
| PC5 | 0.7594 | 0.7625 | no | 0.083 |
| PC6 | 0.7010 | 0.7204 | no | 0.077 |
| PC7 | 0.6042 | 0.6897 | no | 0.066 |
| PC8 | 0.5385 | 0.6558 | no | 0.059 |
| PC9 | 0.4541 | 0.6258 | no | 0.050 |
| PC10 | 0.4072 | 0.5829 | no | 0.044 |
| PC11 | 0.3506 | 0.5568 | no | 0.038 |
| PC12 | 0.3221 | 0.5254 | no | 0.035 |
| PC13 | 0.2134 | 0.5005 | no | 0.023 |
| PC14 | 0.0004 | 0.0004 | no | 0.000 |
| PC15 | 0.0000 | 0.0000 | no | 0.000 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 |
| --- | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | 0.7449 | -0.0407 | -0.3009 | 0.2038 |
| `medium__apex_speed_rel` | 0.4306 | -0.0727 | 0.0521 | -0.0545 |
| `slow__apex_speed_rel` | 0.2538 | -0.3165 | 0.0104 | -0.1972 |
| `medium__brake_point_rel` | 0.0190 | -0.1803 | 0.6475 | 0.0622 |
| `slow__brake_point_rel` | -0.1357 | 0.0162 | 0.0882 | 0.6637 |
| `fast__coast_frac` | -0.0000 | 0.0000 | -0.0000 | -0.0000 |
| `medium__coast_frac` | 0.1028 | -0.2497 | 0.3689 | -0.0681 |
| `slow__coast_frac` | 0.1200 | -0.3579 | 0.3007 | -0.1655 |
| `fast__full_throttle_frac` | 0.0004 | 0.0001 | -0.0002 | -0.0006 |
| `medium__full_throttle_frac` | 0.1352 | 0.3601 | 0.0104 | -0.4862 |
| `slow__full_throttle_frac` | 0.2284 | 0.4558 | 0.0994 | 0.1675 |
| `medium__throttle_attack` | 0.0359 | -0.3071 | -0.1586 | 0.3698 |
| `slow__throttle_attack` | 0.0198 | -0.3547 | -0.2157 | -0.0499 |
| `fast__trail_brake_frac` | -0.0028 | 0.0014 | 0.0004 | 0.0013 |
| `medium__trail_brake_frac` | -0.2474 | -0.1731 | -0.2819 | -0.1451 |
| `slow__trail_brake_frac` | -0.1348 | -0.2865 | -0.3031 | -0.1242 |

PC1: la carga de mayor valor absoluto es `fast__apex_speed_rel` (0.7449, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.4558, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `medium__brake_point_rel` (0.6475, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `slow__brake_point_rel` (0.6637, positiva). El intervalo de esa carga incluye el 0.

Compañeros: 10 pares, distancia media 1.582, percentil 5 del nulo 1.651, percentil de la distancia 2.0, más cerca que el nulo: sí.

### Hungría

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 4.3758 | 3.1178 | sí | 0.290 |
| PC2 | 2.0454 | 2.5968 | no | 0.136 |
| PC3 | 2.0360 | 1.2947 | no | 0.135 |
| PC4 | 1.4216 | 0.8865 | no | 0.094 |
| PC5 | 0.9859 | 0.8472 | no | 0.065 |
| PC6 | 0.7919 | 0.7775 | no | 0.053 |
| PC7 | 0.6381 | 0.7422 | no | 0.042 |
| PC8 | 0.5867 | 0.7189 | no | 0.039 |
| PC9 | 0.5072 | 0.6942 | no | 0.034 |
| PC10 | 0.4257 | 0.6708 | no | 0.028 |
| PC11 | 0.3895 | 0.6522 | no | 0.026 |
| PC12 | 0.3478 | 0.6319 | no | 0.023 |
| PC13 | 0.2998 | 0.6144 | no | 0.020 |
| PC14 | 0.1927 | 0.5765 | no | 0.013 |
| PC15 | 0.0166 | 0.5230 | no | 0.001 |
| PC16 | 0.0081 | 0.0105 | no | 0.001 |

| feature | PC1 |
| --- | ---: |
| `fast__apex_speed_rel` | 0.1480 |
| `medium__apex_speed_rel` | 0.0954 |
| `slow__apex_speed_rel` | 0.0107 |
| `medium__brake_point_rel` | -0.0517 |
| `slow__brake_point_rel` | -0.0564 |
| `fast__coast_frac` | -0.0105 |
| `medium__coast_frac` | -0.0216 |
| `slow__coast_frac` | -0.0300 |
| `fast__full_throttle_frac` | 0.7244 |
| `medium__full_throttle_frac` | 0.5619 |
| `slow__full_throttle_frac` | 0.3440 |
| `medium__throttle_attack` | -0.0446 |
| `slow__throttle_attack` | 0.0075 |
| `fast__trail_brake_frac` | -0.0044 |
| `medium__trail_brake_frac` | -0.0237 |
| `slow__trail_brake_frac` | 0.0091 |

PC1: la carga de mayor valor absoluto es `fast__full_throttle_frac` (0.7244, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 0.982, percentil 5 del nulo 0.646, percentil de la distancia 78.0, más cerca que el nulo: no.

### Países Bajos

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 2.0606 | 1.5969 | sí | 0.203 |
| PC2 | 1.5890 | 0.8431 | sí | 0.157 |
| PC3 | 1.2292 | 0.8100 | sí | 0.121 |
| PC4 | 0.9699 | 0.7632 | sí | 0.096 |
| PC5 | 0.6814 | 0.7315 | no | 0.067 |
| PC6 | 0.6091 | 0.6973 | no | 0.060 |
| PC7 | 0.5557 | 0.6609 | no | 0.055 |
| PC8 | 0.4911 | 0.6342 | no | 0.048 |
| PC9 | 0.4198 | 0.6010 | no | 0.041 |
| PC10 | 0.3967 | 0.5779 | no | 0.039 |
| PC11 | 0.3281 | 0.5420 | no | 0.032 |
| PC12 | 0.2967 | 0.5216 | no | 0.029 |
| PC13 | 0.2153 | 0.4986 | no | 0.021 |
| PC14 | 0.1682 | 0.4768 | no | 0.017 |
| PC15 | 0.1360 | 0.4489 | no | 0.013 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 |
| --- | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | -0.3786 | 0.0205 | 0.3328 | 0.0250 |
| `medium__apex_speed_rel` | 0.2673 | -0.2497 | -0.1894 | -0.3437 |
| `slow__apex_speed_rel` | 0.2750 | -0.2374 | -0.2366 | -0.1374 |
| `medium__brake_point_rel` | 0.2491 | 0.0615 | -0.0639 | 0.3922 |
| `slow__brake_point_rel` | -0.0517 | 0.0580 | 0.1598 | 0.5827 |
| `fast__coast_frac` | 0.2046 | -0.3716 | -0.0381 | 0.1126 |
| `medium__coast_frac` | 0.2170 | -0.3806 | 0.0241 | 0.1842 |
| `slow__coast_frac` | 0.1036 | -0.3612 | 0.0873 | 0.1749 |
| `fast__full_throttle_frac` | -0.0633 | -0.0651 | 0.1504 | -0.2697 |
| `medium__full_throttle_frac` | -0.1271 | -0.0604 | -0.0984 | -0.1493 |
| `slow__full_throttle_frac` | -0.1127 | -0.2135 | 0.1466 | -0.3311 |
| `medium__throttle_attack` | 0.6418 | 0.3185 | 0.6448 | -0.1835 |
| `slow__throttle_attack` | 0.2747 | 0.1344 | -0.2962 | 0.1895 |
| `fast__trail_brake_frac` | -0.0000 | -0.0000 | 0.0000 | -0.0000 |
| `medium__trail_brake_frac` | 0.0077 | 0.4625 | -0.2616 | -0.0811 |
| `slow__trail_brake_frac` | 0.1580 | 0.2709 | -0.3638 | -0.1051 |

PC1: la carga de mayor valor absoluto es `medium__throttle_attack` (0.6418, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `medium__trail_brake_frac` (0.4625, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `medium__throttle_attack` (0.6448, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `slow__brake_point_rel` (0.5827, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 1.711, percentil 5 del nulo 1.625, percentil de la distancia 8.0, más cerca que el nulo: no.

### Italia

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 1.8838 | 1.2892 | sí | 0.184 |
| PC2 | 1.7213 | 1.1899 | sí | 0.168 |
| PC3 | 1.1379 | 1.0245 | sí | 0.111 |
| PC4 | 1.0013 | 0.9435 | sí | 0.098 |
| PC5 | 0.9370 | 0.7859 | sí | 0.091 |
| PC6 | 0.6441 | 0.7277 | no | 0.063 |
| PC7 | 0.5808 | 0.7014 | no | 0.057 |
| PC8 | 0.5317 | 0.6619 | no | 0.052 |
| PC9 | 0.4228 | 0.6231 | no | 0.041 |
| PC10 | 0.4069 | 0.5950 | no | 0.040 |
| PC11 | 0.3241 | 0.5624 | no | 0.032 |
| PC12 | 0.2694 | 0.5239 | no | 0.026 |
| PC13 | 0.2153 | 0.4873 | no | 0.021 |
| PC14 | 0.1659 | 0.4531 | no | 0.016 |
| PC15 | 0.0004 | 0.0005 | no | 0.000 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 | PC5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | 0.1711 | 0.3885 | -0.1473 | -0.1384 | 0.0187 |
| `medium__apex_speed_rel` | 0.1580 | 0.3666 | -0.1812 | -0.0545 | -0.0410 |
| `slow__apex_speed_rel` | -0.0057 | 0.3379 | -0.3562 | 0.1962 | 0.7034 |
| `medium__brake_point_rel` | -0.1320 | -0.2833 | 0.1613 | -0.2299 | 0.2168 |
| `slow__brake_point_rel` | -0.2658 | -0.3696 | 0.1216 | -0.2952 | 0.5261 |
| `fast__coast_frac` | 0.2013 | -0.2164 | 0.0715 | 0.3135 | -0.0651 |
| `medium__coast_frac` | 0.2326 | -0.2498 | 0.1053 | 0.1624 | 0.1081 |
| `slow__coast_frac` | 0.2374 | -0.1519 | 0.1571 | 0.5375 | 0.0180 |
| `fast__full_throttle_frac` | 0.0001 | 0.0003 | -0.0009 | -0.0006 | -0.0005 |
| `medium__full_throttle_frac` | 0.0001 | -0.0000 | -0.0001 | 0.0001 | 0.0001 |
| `slow__full_throttle_frac` | 0.5390 | 0.1911 | 0.4544 | -0.4300 | 0.1501 |
| `medium__throttle_attack` | -0.0712 | 0.0440 | -0.0161 | -0.0561 | -0.0221 |
| `slow__throttle_attack` | -0.3325 | -0.0063 | -0.1954 | 0.1467 | -0.0384 |
| `fast__trail_brake_frac` | -0.3024 | 0.4050 | 0.6811 | 0.3463 | 0.1374 |
| `medium__trail_brake_frac` | -0.3670 | 0.1950 | 0.1474 | -0.0366 | -0.0319 |
| `slow__trail_brake_frac` | -0.2727 | 0.1037 | 0.0799 | -0.2346 | -0.3447 |

PC1: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.5390, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `fast__trail_brake_frac` (0.4050, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `fast__trail_brake_frac` (0.6811, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `slow__coast_frac` (0.5375, positiva). El intervalo de esa carga no incluye el 0.
PC5: la carga de mayor valor absoluto es `slow__apex_speed_rel` (0.7034, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 9 pares, distancia media 1.528, percentil 5 del nulo 1.690, percentil de la distancia 2.0, más cerca que el nulo: sí.

### Azerbaiyán

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 26.6270 | 26.3457 | sí | 0.602 |
| PC2 | 14.1792 | 14.3333 | no | 0.321 |
| PC3 | 1.0809 | 0.9271 | no | 0.024 |
| PC4 | 0.8672 | 0.7674 | no | 0.020 |
| PC5 | 0.6601 | 0.7193 | no | 0.015 |
| PC6 | 0.4692 | 0.6833 | no | 0.011 |
| PC7 | 0.3440 | 0.6416 | no | 0.008 |
| PC8 | 0.0009 | 0.0027 | no | 0.000 |
| PC9 | 0.0000 | 0.0000 | no | 0.000 |
| PC10 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 |
| --- | ---: |
| `fast__apex_speed_rel` | -0.0221 |
| `slow__apex_speed_rel` | -0.0038 |
| `slow__brake_point_rel` | 0.0299 |
| `fast__coast_frac` | -0.0000 |
| `slow__coast_frac` | -0.0380 |
| `fast__full_throttle_frac` | -0.1118 |
| `slow__full_throttle_frac` | -0.0082 |
| `slow__throttle_attack` | 0.9895 |
| `fast__trail_brake_frac` | 0.0000 |
| `slow__trail_brake_frac` | 0.0736 |

PC1: la carga de mayor valor absoluto es `slow__throttle_attack` (0.9895, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 9 pares, distancia media 2.004, percentil 5 del nulo 1.231, percentil de la distancia 30.0, más cerca que el nulo: no.

### Singapur

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 8.0188 | 8.0154 | sí | 0.520 |
| PC2 | 1.6004 | 0.8955 | sí | 0.104 |
| PC3 | 1.2306 | 0.8460 | sí | 0.080 |
| PC4 | 0.9770 | 0.7966 | sí | 0.063 |
| PC5 | 0.7319 | 0.7475 | no | 0.047 |
| PC6 | 0.5845 | 0.7083 | no | 0.038 |
| PC7 | 0.5431 | 0.6823 | no | 0.035 |
| PC8 | 0.4760 | 0.6578 | no | 0.031 |
| PC9 | 0.4079 | 0.6344 | no | 0.026 |
| PC10 | 0.3855 | 0.6020 | no | 0.025 |
| PC11 | 0.2706 | 0.5631 | no | 0.018 |
| PC12 | 0.1744 | 0.4550 | no | 0.011 |
| PC13 | 0.0051 | 0.0064 | no | 0.000 |
| PC14 | 0.0024 | 0.0028 | no | 0.000 |
| PC15 | 0.0001 | 0.0001 | no | 0.000 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 |
| --- | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | -0.0134 | 0.1560 | 0.6057 | -0.0909 |
| `medium__apex_speed_rel` | -0.0235 | -0.1016 | -0.4055 | -0.2006 |
| `slow__apex_speed_rel` | 0.0195 | 0.0583 | -0.4971 | -0.0316 |
| `medium__brake_point_rel` | 0.0155 | -0.1640 | 0.1570 | 0.6870 |
| `slow__brake_point_rel` | -0.0066 | -0.2538 | 0.1569 | 0.3683 |
| `fast__coast_frac` | 0.0000 | 0.0010 | -0.0010 | 0.0010 |
| `medium__coast_frac` | 0.0164 | 0.3958 | -0.1971 | 0.3612 |
| `slow__coast_frac` | 0.0167 | 0.5086 | -0.1950 | 0.3512 |
| `fast__full_throttle_frac` | -0.0006 | 0.0002 | 0.0026 | -0.0062 |
| `medium__full_throttle_frac` | -0.0113 | 0.0002 | -0.0013 | -0.0075 |
| `slow__full_throttle_frac` | -0.0174 | 0.0313 | -0.0654 | -0.1492 |
| `medium__throttle_attack` | 0.9988 | -0.0115 | 0.0143 | -0.0298 |
| `slow__throttle_attack` | 0.0087 | -0.2191 | -0.2078 | 0.1789 |
| `fast__trail_brake_frac` | 0.0000 | -0.0000 | 0.0000 | -0.0000 |
| `medium__trail_brake_frac` | 0.0023 | -0.4752 | 0.0001 | -0.0038 |
| `slow__trail_brake_frac` | 0.0012 | -0.4248 | -0.2184 | 0.1840 |

PC1: la carga de mayor valor absoluto es `medium__throttle_attack` (0.9988, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__coast_frac` (0.5086, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `fast__apex_speed_rel` (0.6057, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `medium__brake_point_rel` (0.6870, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 1.218, percentil 5 del nulo 1.335, percentil de la distancia 0.0, más cerca que el nulo: sí.

### Estados Unidos

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 2.6054 | 2.3939 | sí | 0.232 |
| PC2 | 1.7751 | 0.8427 | sí | 0.158 |
| PC3 | 1.0687 | 0.7876 | sí | 0.095 |
| PC4 | 1.0456 | 0.7558 | sí | 0.093 |
| PC5 | 0.7401 | 0.7302 | sí | 0.066 |
| PC6 | 0.6515 | 0.6974 | no | 0.058 |
| PC7 | 0.6151 | 0.6690 | no | 0.055 |
| PC8 | 0.5179 | 0.6503 | no | 0.046 |
| PC9 | 0.4868 | 0.6292 | no | 0.043 |
| PC10 | 0.4476 | 0.6060 | no | 0.040 |
| PC11 | 0.3775 | 0.5864 | no | 0.034 |
| PC12 | 0.3586 | 0.5698 | no | 0.032 |
| PC13 | 0.2696 | 0.5504 | no | 0.024 |
| PC14 | 0.2006 | 0.5274 | no | 0.018 |
| PC15 | 0.0625 | 0.4817 | no | 0.006 |
| PC16 | 0.0009 | 0.0009 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 | PC5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | 0.0529 | -0.1777 | -0.1895 | 0.4986 | 0.2239 |
| `medium__apex_speed_rel` | 0.0871 | -0.0844 | 0.3333 | 0.4182 | -0.0851 |
| `slow__apex_speed_rel` | 0.0761 | -0.0467 | 0.4461 | 0.3842 | -0.0684 |
| `medium__brake_point_rel` | -0.0360 | 0.2394 | 0.2017 | -0.2653 | -0.4274 |
| `slow__brake_point_rel` | -0.0424 | 0.0360 | -0.0020 | -0.2047 | 0.4786 |
| `fast__coast_frac` | -0.0909 | 0.3667 | 0.0769 | 0.0622 | 0.1404 |
| `medium__coast_frac` | -0.1646 | 0.5702 | 0.1114 | 0.1034 | 0.0178 |
| `slow__coast_frac` | -0.1594 | 0.4982 | 0.1468 | 0.1211 | -0.0298 |
| `fast__full_throttle_frac` | 0.9079 | 0.3014 | -0.0531 | -0.1405 | 0.1323 |
| `medium__full_throttle_frac` | 0.2830 | -0.0713 | 0.0296 | 0.1872 | -0.3513 |
| `slow__full_throttle_frac` | 0.0850 | 0.0428 | -0.1173 | 0.2393 | -0.3452 |
| `medium__throttle_attack` | 0.0314 | 0.1072 | 0.0286 | 0.2998 | 0.4265 |
| `slow__throttle_attack` | 0.0431 | -0.0703 | 0.3925 | -0.0795 | 0.2298 |
| `fast__trail_brake_frac` | 0.0002 | -0.0023 | -0.0011 | -0.0042 | 0.0001 |
| `medium__trail_brake_frac` | 0.0718 | -0.2575 | 0.3590 | -0.2456 | 0.0029 |
| `slow__trail_brake_frac` | 0.0175 | -0.1104 | 0.5218 | -0.1369 | 0.1026 |

PC1: la carga de mayor valor absoluto es `fast__full_throttle_frac` (0.9079, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `medium__coast_frac` (0.5702, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `slow__trail_brake_frac` (0.5218, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `fast__apex_speed_rel` (0.4986, positiva). El intervalo de esa carga no incluye el 0.
PC5: la carga de mayor valor absoluto es `slow__brake_point_rel` (0.4786, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 1.707, percentil 5 del nulo 1.916, percentil de la distancia 0.0, más cerca que el nulo: sí.

### Ciudad de México

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 3.3035 | 3.1445 | sí | 0.266 |
| PC2 | 2.6117 | 1.8780 | sí | 0.211 |
| PC3 | 1.2839 | 0.9907 | sí | 0.104 |
| PC4 | 1.0416 | 0.9092 | sí | 0.084 |
| PC5 | 0.9223 | 0.8272 | sí | 0.074 |
| PC6 | 0.6899 | 0.7915 | no | 0.056 |
| PC7 | 0.6151 | 0.7577 | no | 0.050 |
| PC8 | 0.5221 | 0.7253 | no | 0.042 |
| PC9 | 0.4719 | 0.7010 | no | 0.038 |
| PC10 | 0.4290 | 0.6677 | no | 0.035 |
| PC11 | 0.3282 | 0.6422 | no | 0.026 |
| PC12 | 0.1839 | 0.6166 | no | 0.015 |

| feature | PC1 | PC2 | PC3 | PC4 | PC5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `medium__apex_speed_rel` | 0.1080 | 0.0858 | 0.2715 | 0.3326 | 0.2612 |
| `slow__apex_speed_rel` | -0.0253 | 0.0041 | 0.2040 | 0.5366 | 0.2573 |
| `medium__brake_point_rel` | -0.0330 | 0.0174 | 0.0078 | -0.4331 | 0.3857 |
| `slow__brake_point_rel` | -0.0537 | -0.1785 | -0.1915 | -0.2528 | 0.6556 |
| `medium__coast_frac` | 0.0740 | 0.2489 | 0.4243 | -0.4197 | 0.1348 |
| `slow__coast_frac` | 0.0075 | 0.2395 | 0.4625 | -0.1930 | 0.0343 |
| `medium__full_throttle_frac` | 0.8895 | -0.4246 | 0.1007 | -0.0708 | -0.0443 |
| `slow__full_throttle_frac` | 0.3826 | 0.6134 | -0.4165 | 0.1044 | 0.1734 |
| `medium__throttle_attack` | 0.0336 | 0.0289 | 0.3131 | 0.3345 | 0.3709 |
| `slow__throttle_attack` | -0.1679 | -0.3897 | 0.2620 | -0.0185 | -0.0544 |
| `medium__trail_brake_frac` | -0.0909 | -0.2816 | -0.2681 | 0.0913 | 0.2449 |
| `slow__trail_brake_frac` | -0.0550 | -0.2295 | -0.1784 | 0.0124 | 0.1874 |

PC1: la carga de mayor valor absoluto es `medium__full_throttle_frac` (0.8895, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.6134, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `slow__coast_frac` (0.4625, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `slow__apex_speed_rel` (0.5366, positiva). El intervalo de esa carga no incluye el 0.
PC5: la carga de mayor valor absoluto es `slow__brake_point_rel` (0.6556, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 9 pares, distancia media 1.746, percentil 5 del nulo 1.676, percentil de la distancia 14.0, más cerca que el nulo: no.

### São Paulo

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 2.0054 | 1.0367 | sí | 0.223 |
| PC2 | 1.8019 | 0.9657 | sí | 0.201 |
| PC3 | 1.2060 | 0.9001 | sí | 0.134 |
| PC4 | 0.9526 | 0.8553 | sí | 0.106 |
| PC5 | 0.8000 | 0.7980 | sí | 0.089 |
| PC6 | 0.6277 | 0.7535 | no | 0.070 |
| PC7 | 0.5892 | 0.7267 | no | 0.066 |
| PC8 | 0.4740 | 0.6956 | no | 0.053 |
| PC9 | 0.3937 | 0.6652 | no | 0.044 |
| PC10 | 0.0912 | 0.6435 | no | 0.010 |
| PC11 | 0.0269 | 0.6124 | no | 0.003 |
| PC12 | 0.0047 | 0.5864 | no | 0.001 |
| PC13 | 0.0028 | 0.0030 | no | 0.000 |
| PC14 | 0.0007 | 0.0010 | no | 0.000 |
| PC15 | 0.0000 | 0.0000 | no | 0.000 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 | PC5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | 0.1623 | 0.0835 | -0.0254 | 0.4430 | 0.8537 |
| `medium__apex_speed_rel` | 0.2842 | 0.1762 | 0.1321 | 0.0616 | -0.0899 |
| `slow__apex_speed_rel` | 0.3657 | 0.0719 | 0.2851 | 0.5583 | -0.3578 |
| `medium__brake_point_rel` | 0.0774 | -0.1073 | -0.1317 | -0.5054 | 0.2799 |
| `slow__brake_point_rel` | -0.0915 | -0.2053 | 0.0620 | 0.2079 | 0.1449 |
| `fast__coast_frac` | 0.0000 | 0.0000 | -0.0000 | -0.0000 | -0.0000 |
| `medium__coast_frac` | 0.5186 | -0.0046 | -0.1573 | -0.1568 | -0.0039 |
| `slow__coast_frac` | 0.5197 | 0.0091 | -0.1738 | -0.1715 | -0.0325 |
| `fast__full_throttle_frac` | -0.0013 | 0.0105 | -0.0014 | -0.0018 | 0.0003 |
| `medium__full_throttle_frac` | -0.0945 | 0.6611 | -0.0359 | -0.0642 | 0.0244 |
| `slow__full_throttle_frac` | -0.0982 | 0.6797 | -0.0420 | -0.0648 | 0.0132 |
| `medium__throttle_attack` | 0.0704 | 0.0091 | 0.6271 | -0.2516 | 0.1358 |
| `slow__throttle_attack` | 0.0502 | 0.0140 | 0.6494 | -0.2255 | 0.1180 |
| `fast__trail_brake_frac` | 0.0000 | 0.0000 | -0.0000 | 0.0000 | 0.0000 |
| `medium__trail_brake_frac` | -0.0071 | -0.0048 | 0.0004 | -0.0030 | 0.0049 |
| `slow__trail_brake_frac` | -0.4239 | -0.0593 | 0.0805 | 0.1143 | -0.0391 |

PC1: la carga de mayor valor absoluto es `slow__coast_frac` (0.5197, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.6797, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `slow__throttle_attack` (0.6494, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `slow__apex_speed_rel` (0.5583, positiva). El intervalo de esa carga no incluye el 0.
PC5: la carga de mayor valor absoluto es `fast__apex_speed_rel` (0.8537, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 8 pares, distancia media 1.689, percentil 5 del nulo 1.752, percentil de la distancia 2.0, más cerca que el nulo: sí.

### Las Vegas

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 2.2101 | 1.7371 | sí | 0.249 |
| PC2 | 1.7588 | 1.2659 | sí | 0.198 |
| PC3 | 1.1841 | 1.0790 | sí | 0.133 |
| PC4 | 0.8428 | 0.9563 | no | 0.095 |
| PC5 | 0.6979 | 0.8490 | no | 0.078 |
| PC6 | 0.6016 | 0.8020 | no | 0.068 |
| PC7 | 0.5482 | 0.7227 | no | 0.062 |
| PC8 | 0.4154 | 0.6806 | no | 0.047 |
| PC9 | 0.3583 | 0.6298 | no | 0.040 |
| PC10 | 0.2723 | 0.5693 | no | 0.031 |
| PC11 | 0.0037 | 0.0037 | no | 0.000 |
| PC12 | 0.0001 | 0.0002 | no | 0.000 |
| PC13 | 0.0000 | 0.0000 | no | 0.000 |
| PC14 | 0.0000 | 0.0000 | no | 0.000 |
| PC15 | 0.0000 | 0.0000 | no | 0.000 |
| PC16 | 0.0000 | 0.0000 | no | 0.000 |

| feature | PC1 | PC2 | PC3 |
| --- | ---: | ---: | ---: |
| `fast__apex_speed_rel` | -0.2002 | -0.3450 | 0.5905 |
| `medium__apex_speed_rel` | -0.1505 | -0.3863 | -0.4751 |
| `slow__apex_speed_rel` | -0.0119 | -0.1098 | -0.2029 |
| `medium__brake_point_rel` | 0.1058 | 0.3048 | 0.3426 |
| `slow__brake_point_rel` | -0.1244 | 0.2180 | 0.3616 |
| `fast__coast_frac` | -0.0000 | -0.0000 | -0.0000 |
| `medium__coast_frac` | 0.0023 | 0.0031 | 0.0003 |
| `slow__coast_frac` | 0.3668 | 0.5659 | -0.1699 |
| `fast__full_throttle_frac` | -0.0009 | -0.0024 | -0.0031 |
| `medium__full_throttle_frac` | -0.0000 | -0.0000 | 0.0000 |
| `slow__full_throttle_frac` | 0.7077 | -0.4512 | 0.1323 |
| `medium__throttle_attack` | -0.0000 | -0.0000 | 0.0000 |
| `slow__throttle_attack` | -0.3709 | 0.1931 | -0.1021 |
| `fast__trail_brake_frac` | -0.0000 | -0.0000 | 0.0000 |
| `medium__trail_brake_frac` | -0.1303 | -0.0602 | 0.2760 |
| `slow__trail_brake_frac` | -0.3472 | -0.1205 | -0.0572 |

PC1: la carga de mayor valor absoluto es `slow__full_throttle_frac` (0.7077, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__coast_frac` (0.5659, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `fast__apex_speed_rel` (0.5905, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 5 pares, distancia media 1.607, percentil 5 del nulo 1.178, percentil de la distancia 26.0, más cerca que el nulo: no.

### Catar

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 36.8596 | 36.7574 | sí | 0.833 |
| PC2 | 1.7853 | 0.8945 | sí | 0.040 |
| PC3 | 1.0583 | 0.8398 | sí | 0.024 |
| PC4 | 0.9853 | 0.7934 | sí | 0.022 |
| PC5 | 0.8239 | 0.7506 | sí | 0.019 |
| PC6 | 0.6518 | 0.7252 | no | 0.015 |
| PC7 | 0.4625 | 0.6986 | no | 0.010 |
| PC8 | 0.4266 | 0.6604 | no | 0.010 |
| PC9 | 0.3779 | 0.6349 | no | 0.009 |
| PC10 | 0.3643 | 0.6012 | no | 0.008 |
| PC11 | 0.2247 | 0.5631 | no | 0.005 |
| PC12 | 0.2016 | 0.5305 | no | 0.005 |
| PC13 | 0.0091 | 0.0109 | no | 0.000 |
| PC14 | 0.0051 | 0.0072 | no | 0.000 |
| PC15 | 0.0046 | 0.0048 | no | 0.000 |
| PC16 | 0.0002 | 0.0003 | no | 0.000 |

| feature | PC1 | PC2 | PC3 | PC4 | PC5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `fast__apex_speed_rel` | -0.0047 | 0.2204 | 0.1180 | -0.0302 | -0.3862 |
| `medium__apex_speed_rel` | 0.0033 | 0.3156 | 0.2760 | 0.0449 | -0.3592 |
| `slow__apex_speed_rel` | 0.0111 | 0.4090 | 0.3407 | -0.1711 | -0.2087 |
| `medium__brake_point_rel` | 0.0117 | -0.0974 | 0.1787 | 0.4927 | 0.2631 |
| `slow__brake_point_rel` | 0.0113 | -0.1071 | 0.1860 | 0.5785 | 0.1868 |
| `fast__coast_frac` | -0.0001 | 0.0032 | 0.0028 | 0.0052 | 0.0007 |
| `medium__coast_frac` | -0.0037 | 0.3438 | 0.2093 | 0.2833 | 0.0093 |
| `slow__coast_frac` | 0.0041 | 0.4244 | 0.1352 | -0.2260 | 0.5679 |
| `fast__full_throttle_frac` | -0.0010 | 0.0078 | -0.0030 | 0.0018 | 0.0001 |
| `medium__full_throttle_frac` | -0.0168 | 0.2347 | -0.5270 | 0.1645 | -0.1077 |
| `slow__full_throttle_frac` | -0.0069 | 0.0021 | 0.0019 | -0.0049 | -0.0088 |
| `medium__throttle_attack` | 0.0312 | -0.2550 | 0.5854 | -0.2155 | 0.1613 |
| `slow__throttle_attack` | 0.9984 | 0.0279 | -0.0417 | 0.0038 | 0.0012 |
| `fast__trail_brake_frac` | 0.0012 | -0.0154 | -0.0129 | -0.0185 | 0.0154 |
| `medium__trail_brake_frac` | 0.0216 | -0.3480 | -0.0058 | -0.3944 | 0.0284 |
| `slow__trail_brake_frac` | 0.0315 | -0.3507 | 0.2069 | 0.1720 | -0.4613 |

PC1: la carga de mayor valor absoluto es `slow__throttle_attack` (0.9984, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__coast_frac` (0.4244, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `medium__throttle_attack` (0.5854, positiva). El intervalo de esa carga no incluye el 0.
PC4: la carga de mayor valor absoluto es `slow__brake_point_rel` (0.5785, positiva). El intervalo de esa carga no incluye el 0.
PC5: la carga de mayor valor absoluto es `slow__coast_frac` (0.5679, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 1.941, percentil 5 del nulo 2.181, percentil de la distancia 2.0, más cerca que el nulo: sí.

### Abu Dabi

| componente | autovalor | percentil 95 del nulo | se conserva | varianza |
| --- | ---: | ---: | --- | ---: |
| PC1 | 5.0432 | 2.8609 | sí | 0.329 |
| PC2 | 2.5825 | 2.5315 | sí | 0.168 |
| PC3 | 1.8451 | 1.7246 | sí | 0.120 |
| PC4 | 1.0816 | 1.1547 | no | 0.071 |
| PC5 | 0.9424 | 0.9922 | no | 0.061 |
| PC6 | 0.6754 | 0.9024 | no | 0.044 |
| PC7 | 0.6273 | 0.7650 | no | 0.041 |
| PC8 | 0.5159 | 0.7194 | no | 0.034 |
| PC9 | 0.4805 | 0.6815 | no | 0.031 |
| PC10 | 0.4146 | 0.6392 | no | 0.027 |
| PC11 | 0.4023 | 0.6083 | no | 0.026 |
| PC12 | 0.3012 | 0.5796 | no | 0.020 |
| PC13 | 0.2201 | 0.5433 | no | 0.014 |
| PC14 | 0.1526 | 0.5162 | no | 0.010 |
| PC15 | 0.0537 | 0.4372 | no | 0.003 |
| PC16 | 0.0001 | 0.0002 | no | 0.000 |

| feature | PC1 | PC2 | PC3 |
| --- | ---: | ---: | ---: |
| `fast__apex_speed_rel` | -0.1592 | 0.1220 | -0.0845 |
| `medium__apex_speed_rel` | 0.1609 | 0.4536 | 0.1894 |
| `slow__apex_speed_rel` | 0.1348 | 0.6441 | 0.2437 |
| `medium__brake_point_rel` | 0.5108 | -0.5264 | 0.1243 |
| `slow__brake_point_rel` | 0.6654 | 0.1012 | 0.1779 |
| `fast__coast_frac` | -0.0358 | -0.0955 | 0.4453 |
| `medium__coast_frac` | -0.0677 | -0.0803 | 0.3985 |
| `slow__coast_frac` | -0.0399 | -0.0669 | 0.3926 |
| `fast__full_throttle_frac` | -0.0971 | 0.1605 | -0.1687 |
| `medium__full_throttle_frac` | -0.0441 | 0.0448 | 0.2928 |
| `slow__full_throttle_frac` | -0.1594 | -0.0424 | 0.1514 |
| `medium__throttle_attack` | 0.0279 | 0.0035 | -0.1437 |
| `slow__throttle_attack` | 0.1348 | 0.0801 | -0.2349 |
| `fast__trail_brake_frac` | 0.0004 | -0.0003 | -0.0005 |
| `medium__trail_brake_frac` | 0.2871 | 0.0316 | -0.2407 |
| `slow__trail_brake_frac` | 0.2852 | 0.1418 | -0.2616 |

PC1: la carga de mayor valor absoluto es `slow__brake_point_rel` (0.6654, positiva). El intervalo de esa carga no incluye el 0.
PC2: la carga de mayor valor absoluto es `slow__apex_speed_rel` (0.6441, positiva). El intervalo de esa carga no incluye el 0.
PC3: la carga de mayor valor absoluto es `fast__coast_frac` (0.4453, positiva). El intervalo de esa carga no incluye el 0.

Compañeros: 10 pares, distancia media 1.569, percentil 5 del nulo 1.920, percentil de la distancia 0.0, más cerca que el nulo: sí.

Componentes retenidos: mínimo 1, máximo 6, en 24 carreras.
Compañeros más cerca que el nulo en 16 carreras: Australia, Japón, Baréin, Arabia Saudita, Mónaco, España, Canadá, Austria, Gran Bretaña, Bélgica, Italia, Singapur, Estados Unidos, São Paulo, Catar, Abu Dabi.
No lo están en: China, Miami, Emilia-Romaña, Hungría, Países Bajos, Azerbaiyán, Ciudad de México, Las Vegas.

### Congruencia de Tucker entre GP

Pares de ejes con coeficiente definido: 842. Mediana: 0.248.
PC1: n=276, mediana 0.239, cuartiles 0.095 y 0.398, mínimo 0.000, máximo 0.997.
PC2: n=210, mediana 0.289, cuartiles 0.131 y 0.475, mínimo 0.001, máximo 0.859.
PC3: n=190, mediana 0.248, cuartiles 0.128 y 0.383, mínimo 0.001, máximo 0.820.
PC4: n=120, mediana 0.282, cuartiles 0.132 y 0.436, mínimo 0.005, máximo 0.756.
PC5: n=45, mediana 0.184, cuartiles 0.035 y 0.257, mínimo 0.002, máximo 0.759.
PC6: n=1, mediana 0.109, cuartiles 0.109 y 0.109, mínimo 0.109, máximo 0.109.

### Predicciones a priori

Aire limpio en la matriz de la carrera suelta: 173 vueltas. No lo son: 16. Sin onset en la zona slow: 0.
(a) MEDIUM: no hay evidencia. Hamilton n=30 mediana=-0.777 [-6.278, 3.816]. Leclerc n=27 mediana=-10.418 [-19.911, -5.661].
Norris contra Piastri en MEDIUM, exploratorio: Norris n=43 mediana=-12.028 [-16.058, -2.952]. Piastri n=36 mediana=1.054 [-1.499, 4.093].
(a) HARD: no hay evidencia. Hamilton n=11 mediana=1.251 [-9.150, 7.691]. Leclerc n=17 mediana=-10.600 [-20.047, -4.827].
Norris contra Piastri en SOFT, exploratorio: Norris n=4 mediana=-17.312 [-19.988, -3.441]. Piastri n=5 mediana=9.649 [3.016, 23.483].
(b) no hay evidencia. Leclerc n=44 mediana=79.178 [74.829, 81.550]. Hamilton n=45 mediana=79.928 [77.158, 82.380].
Norris contra Piastri en la suelta, exploratorio: Norris n=48 mediana=81.996 [78.064, 85.513]. Piastri n=48 mediana=85.190 [83.513, 88.754].
