# Clasificación de pilotos 2025 con las ZOI por circuito

Misma rama `feat/zoi-por-circuito`. No se cambió el vector, el RobustScaler, el PCA automático, la regla de k, el K-means ni los defaults. La matriz de temporada saca `fast__brake_point_rel` antes del `dropna`, que es `season.exclude_columns`. La carrera suelta de Monza la conserva.

La telemetría oficial de FastF1 no carga en este entorno: `livetiming.formula1.com` responde 401 y el mirror `livetiming-mirror.fastf1.dev` responde 404. Cada vuelta entra por el canal `car_data` de OpenF1, metido en una `Session` de FastF1, y la distancia sale de `Lap.get_car_data().add_distance()`. Las banderas de vuelta y las distancias de curva salen del archivo de Tracing Insights 2025 (`laptimes.json`, `corners.json`, `drivers.json`). No se leyó `tel.json` ni se llamó a `get_telemetry()`.

El archivo de zonas anterior es `config/circuits.yaml` en `26deacd^`: solo Italia, Gran Bretaña y Mónaco tienen `key_corners`. El archivo de esta rama tiene `key_corners` en el resto de los circuitos de 2025, salvo Hungría, que sigue en el fallback de 350 m / ±60 m / 250 m. Las ventanas de Monza, Silverstone y Mónaco no se reescribieron en ese cambio.

De 24 grandes premios, 24 dan clases. 1 supera los tres nulos. 23 dan clases y no superan los tres: esas clases quedan como no concluyentes. Son 435 celdas piloto × GP.

## Borde de ventana en Monza

La cuenta usa `scan_brake_onsets` sobre `Lap.get_car_data().add_distance()`. `edge` es verdadero cuando la primera muestra de la ventana ya está frenando. El denominador es `n_onsets`, los inicios de frenada. `n_fragments` es el número de ventanas recorridas.

Las cifras ya publicadas, con otra fuente, quedan como referencia y no se recalculan aquí. `docs/vector_por_zona_monza_2025.md`: ventana de 350 m, 261/5114 (5.10 % de los inicios); Lesmo 2, 250/811. Ventanas del pipeline, 13/5074. `docs/zoi_diagnostico_2025/informe_despues.md`, con `get_telemetry()`: 506/5141 (9.84 %).

| ventana | zona | fragmentos | inicios | borde | a 5 m | borde / inicios |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| pipeline | T1_Variante_del_Rettifilo | 869 | 868 | 0 | 0 | 0.0000 |
| pipeline | T3_Curva_Grande | 869 | 0 | 0 | 0 |  |
| pipeline | T4_Variante_della_Roggia | 869 | 868 | 0 | 0 | 0.0000 |
| pipeline | T6_Curva_di_Lesmo | 869 | 867 | 12 | 1 | 0.0138 |
| pipeline | T7_Seconda_di_Lesmo | 869 | 857 | 22 | 0 | 0.0257 |
| pipeline | T8_Variante_Ascari | 868 | 867 | 1 | 0 | 0.0012 |
| pipeline | T11_Curva_Parabolica_Alboreto | 868 | 867 | 3 | 1 | 0.0035 |
| pipeline | TOTAL | 6081 | 5194 | 38 | 2 | 0.0073 |
| 350m | T1_Variante_del_Rettifilo | 869 | 868 | 0 | 0 | 0.0000 |
| 350m | T3_Curva_Grande | 869 | 2 | 1 | 0 | 0.5000 |
| 350m | T4_Variante_della_Roggia | 869 | 868 | 0 | 0 | 0.0000 |
| 350m | T6_Curva_di_Lesmo | 869 | 868 | 1 | 0 | 0.0012 |
| 350m | T7_Seconda_di_Lesmo | 869 | 858 | 52 | 28 | 0.0606 |
| 350m | T8_Variante_Ascari | 868 | 867 | 1 | 1 | 0.0012 |
| 350m | T11_Curva_Parabolica_Alboreto | 868 | 867 | 2 | 0 | 0.0023 |
| 350m | TOTAL | 6081 | 5198 | 57 | 29 | 0.0110 |

Reloj: 975 vueltas alineadas, mediana del desfase absoluto 0.043000 s, máximo 0.597 s. t0 `2025-09-07T12:05:45.099000064+00:00`.

## Vueltas y columnas

`vueltas` es `n_after_driver_filter`. `columnas` son las de estilo que quedan en esa matriz. `dropna` es el número de vueltas que se fueron por un valor faltante. Antes es el yaml de `26deacd^`. Después es el yaml de esta rama. Las dos matrices ya tienen fuera `fast__brake_point_rel`.

| carrera | vueltas antes | columnas antes | dropna antes | fuente antes | vueltas después | columnas después | dropna después | fuente después | clases |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | --- |
| Australia | 547 | 16 | 0 | speed_threshold_fallback | 547 | 16 | 0 | key_corners | sí |
| China | 942 | 16 | 0 | speed_threshold_fallback | 942 | 16 | 0 | key_corners | sí |
| Japón | 989 | 16 | 0 | speed_threshold_fallback | 989 | 16 | 0 | key_corners | sí |
| Baréin | 924 | 16 | 0 | speed_threshold_fallback | 924 | 16 | 0 | key_corners | sí |
| Arabia Saudita | 798 | 16 | 0 | speed_threshold_fallback | 798 | 16 | 0 | key_corners | sí |
| Miami | 0 | 16 | 852 | speed_threshold_fallback | 203 | 15 | 654 | key_corners | sí |
| Emilia-Romaña | 939 | 16 | 0 | speed_threshold_fallback | 939 | 16 | 0 | key_corners | sí |
| Mónaco | 1165 | 10 | 0 | key_corners | 1165 | 10 | 0 | key_corners | sí |
| España | 980 | 16 | 0 | speed_threshold_fallback | 980 | 16 | 0 | key_corners | sí |
| Canadá | 1148 | 16 | 6 | speed_threshold_fallback | 608 | 16 | 546 | key_corners | sí |
| Austria | 984 | 16 | 0 | speed_threshold_fallback | 984 | 16 | 0 | key_corners | sí |
| Gran Bretaña | 434 | 16 | 1 | key_corners | 434 | 16 | 1 | key_corners | sí |
| Bélgica | 734 | 16 | 0 | speed_threshold_fallback | 734 | 16 | 0 | key_corners | sí |
| Hungría | 1275 | 16 | 0 | speed_threshold_fallback | 1275 | 16 | 0 | speed_threshold_fallback | sí |
| Países Bajos | 998 | 16 | 0 | speed_threshold_fallback | 998 | 16 | 0 | key_corners | sí |
| Italia | 868 | 16 | 10 | key_corners | 868 | 16 | 10 | key_corners | sí |
| Azerbaiyán | 796 | 10 | 0 | speed_threshold_fallback | 796 | 10 | 0 | key_corners | sí |
| Singapur | 1106 | 16 | 0 | speed_threshold_fallback | 1106 | 16 | 0 | key_corners | sí |
| Estados Unidos | 898 | 16 | 0 | speed_threshold_fallback | 898 | 16 | 0 | key_corners | sí |
| Ciudad de México | 1079 | 12 | 23 | speed_threshold_fallback | 1079 | 12 | 23 | key_corners | sí |
| São Paulo | 1031 | 16 | 1 | speed_threshold_fallback | 1026 | 16 | 6 | key_corners | sí |
| Las Vegas | 342 | 16 | 415 | speed_threshold_fallback | 340 | 16 | 417 | key_corners | sí |
| Catar | 902 | 16 | 2 | speed_threshold_fallback | 902 | 16 | 2 | key_corners | sí |
| Abu Dabi | 1044 | 16 | 0 | speed_threshold_fallback | 1044 | 16 | 0 | key_corners | sí |

Cambia el tamaño de la matriz en Miami (vueltas 0 a 203, columnas 16 a 15); Canadá (vueltas 1148 a 608); São Paulo (vueltas 1031 a 1026); Las Vegas (vueltas 342 a 340).

## K-means y tres nulos

K-means++ con semilla 42 y `n_init` 20, k elegido por la regla del pipeline. Cada nulo tiene 50 réplicas. Las semillas son 42, 43 y 44. Hay estructura si la silueta real es estrictamente mayor que el percentil 95 de la permutación por columna, del nulo gaussiano y de la cópula gaussiana. El percentil es el porcentaje de réplicas finitas menores o iguales que la real. La columna de estructura usa `beats_p95`, no el redondeo del percentil. Una carrera que da clases y no supera los tres queda como no concluyente.

| carrera | vueltas | dropna | k | regla | silueta | permutación | gaussiano | cópula | supera los tres | lectura |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- |
| Australia | 547 | 0 | 2 | silhouette | 0.701 | 98.0 | 100.0 | 54.0 | no | no concluyente |
| China | 942 | 0 | 3 | silhouette | 0.329 | 100.0 | 100.0 | 22.0 | no | no concluyente |
| Japón | 989 | 0 | 7 | davies_bouldin | 0.113 | 100.0 | 98.0 | 98.0 | sí | concluyente |
| Baréin | 924 | 0 | 2 | silhouette | 0.529 | 100.0 | 100.0 | 74.0 | no | no concluyente |
| Arabia Saudita | 798 | 0 | 2 | silhouette | 0.801 | 100.0 | 100.0 | 40.0 | no | no concluyente |
| Miami | 203 | 654 | 5 | davies_bouldin | 0.139 | 100.0 | 18.0 | 6.0 | no | no concluyente |
| Emilia-Romaña | 939 | 0 | 2 | silhouette | 0.514 | 100.0 | 100.0 | 44.0 | no | no concluyente |
| Mónaco | 1165 | 0 | 4 | davies_bouldin | 0.177 | 0.0 | 100.0 | 20.0 | no | no concluyente |
| España | 980 | 0 | 6 | davies_bouldin | 0.103 | 100.0 | 98.0 | 94.0 | no | no concluyente |
| Canadá | 608 | 546 | 2 | davies_bouldin | 0.170 | n=0 | 100.0 | 13.0 (n=23) | no | no concluyente |
| Austria | 984 | 0 | 2 | silhouette | 0.406 | 100.0 | 100.0 | 60.0 | no | no concluyente |
| Gran Bretaña | 434 | 1 | 2 | silhouette | 0.433 | 100.0 | 100.0 | 66.0 | no | no concluyente |
| Bélgica | 734 | 0 | 3 | davies_bouldin | 0.106 | 76.0 | 100.0 | 56.0 | no | no concluyente |
| Hungría | 1275 | 0 | 2 | davies_bouldin | 0.235 | 88.0 | 100.0 | 52.0 | no | no concluyente |
| Países Bajos | 998 | 0 | 5 | davies_bouldin | 0.147 | 70.0 | 100.0 | 100.0 | no | no concluyente |
| Italia | 868 | 10 | 2 | silhouette | 0.762 | 98.0 | 100.0 | 46.0 | no | no concluyente |
| Azerbaiyán | 796 | 0 | 6 | davies_bouldin | 0.191 | 100.0 | 100.0 | 68.8 (n=48) | no | no concluyente |
| Singapur | 1106 | 0 | 7 | davies_bouldin | 0.127 | 100.0 | 100.0 | 30.0 | no | no concluyente |
| Estados Unidos | 898 | 0 | 2 | silhouette | 0.703 | 100.0 | 100.0 | 82.0 | no | no concluyente |
| Ciudad de México | 1079 | 23 | 3 | silhouette | 0.490 | 0.0 | 100.0 | 42.0 | no | no concluyente |
| São Paulo | 1026 | 6 | 7 | davies_bouldin | 0.110 | 100.0 | 8.0 | 32.0 | no | no concluyente |
| Las Vegas | 340 | 417 | 7 | davies_bouldin | 0.144 | 96.0 | 78.0 | 66.0 | no | no concluyente |
| Catar | 902 | 2 | 2 | silhouette | 0.898 | 100.0 | 100.0 | 65.9 (n=44) | no | no concluyente |
| Abu Dabi | 1044 | 0 | 2 | silhouette | 0.709 | 100.0 | 100.0 | 88.0 | no | no concluyente |

La silueta de la tabla es la del pipeline, a tres decimales. El CSV `docs/clasificacion_pilotos_zoi_2025/por_gp.csv` guarda el valor completo, el Davies-Bouldin y los tres `beats_p95`. El percentil de la tabla va a un decimal. Si al lado figura `n`, es el número de réplicas finitas: las que no eligen k quedan fuera del percentil. `n=0` quiere decir que ninguna réplica de ese nulo eligió k, y esa carrera no lo supera.

La frecuencia de cada arquetipo cuenta celdas piloto × GP solo en las carreras que superan los tres nulos. Las 435 celdas de carreras no concluyentes no entran en este conteo.

| arquetipo | celdas | pilotos |
| --- | ---: | ---: |
| No dominant trait | 5 | 5 |
| Early braking + less full throttle on exit | 3 | 3 |
| Early braking + more coasting | 3 | 3 |
| Low apex speed + more trail braking | 3 | 3 |
| Softer throttle pickup + more full throttle on exit | 3 | 3 |
| More trail braking + less coasting | 2 | 2 |
| Sharper throttle pickup + less full throttle on exit | 1 | 1 |

## Tabla de pilotos

La clase modal usa `season_modal_summary`, con piso `min_races_season: 8`. La primera moda cuenta todas las carreras que dieron clases, igual que `docs/temporada_2025.md`. Esa moda no es una conclusión cuando las carreras que la forman no superan los tres nulos. La segunda moda cuenta solo las carreras que superan los tres. El acuerdo es la fracción de esas carreras cuyo nombre coincide con la moda. Los nombres salen de `name_classes_from_medians`. No se les pone el nombre de un piloto.

| piloto | nombre | equipo | carreras con clase | moda, todas las que dan clase | acuerdo | carreras concluyentes | moda, solo concluyentes | acuerdo concluyente |
| --- | --- | --- | ---: | --- | ---: | ---: | --- | ---: |
| ALB | Alexander Albon | Williams | 24 | No dominant trait | 0.42 | 1 | no llega a 8 |  |
| ALO | Fernando Alonso | Aston Martin | 23 | No dominant trait | 0.52 | 1 | no llega a 8 |  |
| ANT | Kimi Antonelli | Mercedes | 22 | No dominant trait | 0.45 | 1 | no llega a 8 |  |
| BEA | Oliver Bearman | Haas F1 Team | 24 | No dominant trait | 0.54 | 1 | no llega a 8 |  |
| BOR | Gabriel Bortoleto | Kick Sauber | 21 | No dominant trait | 0.48 | 1 | no llega a 8 |  |
| COL | Franco Colapinto | Alpine | 17 | No dominant trait | 0.41 | 0 |  |  |
| DOO | Jack Doohan | Alpine | 4 | no llega a 8 |  | 1 | no llega a 8 |  |
| GAS | Pierre Gasly | Alpine | 23 | No dominant trait | 0.48 | 1 | no llega a 8 |  |
| HAD | Isack Hadjar | Racing Bulls | 23 | No dominant trait | 0.43 | 1 | no llega a 8 |  |
| HAM | Lewis Hamilton | Ferrari | 24 | No dominant trait | 0.46 | 1 | no llega a 8 |  |
| HUL | Nico Hulkenberg | Kick Sauber | 23 | No dominant trait | 0.57 | 1 | no llega a 8 |  |
| LAW | Liam Lawson | Racing Bulls | 22 | No dominant trait | 0.41 | 1 | no llega a 8 |  |
| LEC | Charles Leclerc | Ferrari | 23 | No dominant trait | 0.48 | 1 | no llega a 8 |  |
| NOR | Lando Norris | McLaren | 23 | No dominant trait | 0.48 | 1 | no llega a 8 |  |
| OCO | Esteban Ocon | Haas F1 Team | 24 | No dominant trait | 0.46 | 1 | no llega a 8 |  |
| PIA | Oscar Piastri | McLaren | 23 | No dominant trait | 0.48 | 1 | no llega a 8 |  |
| RUS | George Russell | Mercedes | 23 | No dominant trait | 0.48 | 1 | no llega a 8 |  |
| SAI | Carlos Sainz | Williams | 22 | No dominant trait | 0.41 | 1 | no llega a 8 |  |
| STR | Lance Stroll | Aston Martin | 22 | No dominant trait | 0.45 | 1 | no llega a 8 |  |
| TSU | Yuki Tsunoda | Red Bull Racing | 23 | No dominant trait | 0.48 | 1 | no llega a 8 |  |
| VER | Max Verstappen | Red Bull Racing | 22 | No dominant trait | 0.45 | 1 | no llega a 8 |  |

La clase de cada piloto en cada GP está en `docs/clasificacion_pilotos_zoi_2025/clases_modales.csv`. `n_laps` es el total de vueltas del piloto en esa matriz y `modal_fraction` es la proporción que cae en la clase modal. Abajo queda la misma tabla partida por carrera. En una carrera no concluyente el nombre se imprime y la lectura de la carrera es no concluyente.

### Australia

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait | 34 | 0.971 |
| ALO | No dominant trait | 25 | 0.920 |
| ANT | No dominant trait | 33 | 0.970 |
| BEA | No dominant trait | 32 | 0.969 |
| BOR | No dominant trait | 27 | 0.963 |
| GAS | No dominant trait | 32 | 1.000 |
| HAM | No dominant trait | 34 | 0.941 |
| HUL | No dominant trait | 34 | 0.971 |
| LAW | No dominant trait | 27 | 1.000 |
| LEC | No dominant trait | 34 | 1.000 |
| NOR | No dominant trait | 35 | 1.000 |
| OCO | No dominant trait | 32 | 0.875 |
| PIA | No dominant trait | 33 | 0.970 |
| RUS | No dominant trait | 34 | 1.000 |
| STR | No dominant trait | 34 | 1.000 |
| TSU | No dominant trait | 34 | 1.000 |
| VER | No dominant trait | 33 | 1.000 |

### China

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait (class 0) | 50 | 0.720 |
| ANT | No dominant trait (class 0) | 51 | 0.784 |
| BEA | No dominant trait (class 0) | 50 | 0.800 |
| BOR | No dominant trait (class 0) | 50 | 0.680 |
| DOO | No dominant trait (class 0) | 49 | 0.816 |
| GAS | No dominant trait (class 0) | 50 | 0.620 |
| HAD | No dominant trait (class 0) | 47 | 0.787 |
| HAM | No dominant trait (class 0) | 49 | 0.816 |
| HUL | No dominant trait (class 0) | 49 | 0.592 |
| LAW | No dominant trait (class 0) | 48 | 0.667 |
| LEC | No dominant trait (class 0) | 51 | 0.804 |
| NOR | No dominant trait (class 0) | 51 | 0.686 |
| OCO | No dominant trait (class 0) | 50 | 0.700 |
| PIA | No dominant trait (class 0) | 51 | 0.686 |
| RUS | No dominant trait (class 0) | 51 | 0.667 |
| SAI | No dominant trait (class 0) | 50 | 0.820 |
| STR | No dominant trait (class 0) | 50 | 0.620 |
| TSU | No dominant trait (class 0) | 44 | 0.795 |
| VER | No dominant trait (class 0) | 51 | 0.725 |

### Japón

Lectura: concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | Sharper throttle pickup + less full throttle on exit | 50 | 0.600 |
| ALO | No dominant trait | 50 | 0.500 |
| ANT | No dominant trait | 48 | 0.562 |
| BEA | No dominant trait | 50 | 0.400 |
| BOR | Low apex speed + more trail braking | 50 | 0.380 |
| DOO | Early braking + less full throttle on exit | 50 | 0.560 |
| GAS | Softer throttle pickup + more full throttle on exit | 49 | 0.796 |
| HAD | No dominant trait | 50 | 0.560 |
| HAM | More trail braking + less coasting | 50 | 0.920 |
| HUL | No dominant trait | 50 | 0.440 |
| LAW | Early braking + less full throttle on exit | 50 | 0.580 |
| LEC | More trail braking + less coasting | 50 | 0.760 |
| NOR | Early braking + more coasting | 49 | 0.592 |
| OCO | Low apex speed + more trail braking | 50 | 0.800 |
| PIA | Early braking + more coasting | 50 | 0.400 |
| RUS | Softer throttle pickup + more full throttle on exit | 49 | 0.469 |
| SAI | Low apex speed + more trail braking | 48 | 0.688 |
| STR | Early braking + more coasting | 47 | 0.851 |
| TSU | Softer throttle pickup + more full throttle on exit | 49 | 0.592 |
| VER | Early braking + less full throttle on exit | 50 | 0.240 |

### Baréin

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait | 50 | 0.600 |
| ALO | No dominant trait | 49 | 0.551 |
| ANT | No dominant trait | 45 | 0.800 |
| BEA | No dominant trait | 48 | 0.896 |
| BOR | No dominant trait | 50 | 1.000 |
| DOO | No dominant trait | 44 | 1.000 |
| GAS | No dominant trait | 48 | 0.958 |
| HAD | No dominant trait | 45 | 0.889 |
| HAM | No dominant trait | 49 | 0.918 |
| HUL | No dominant trait | 47 | 0.830 |
| LAW | No dominant trait | 49 | 0.837 |
| LEC | No dominant trait | 49 | 0.959 |
| NOR | No dominant trait | 48 | 0.625 |
| OCO | No dominant trait | 48 | 0.854 |
| PIA | No dominant trait | 49 | 0.796 |
| RUS | No dominant trait | 30 | 0.767 |
| SAI | No dominant trait | 35 | 0.914 |
| STR | No dominant trait | 49 | 0.796 |
| TSU | No dominant trait | 47 | 0.553 |
| VER | No dominant trait | 45 | 0.978 |

### Arabia Saudita

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait | 44 | 0.977 |
| ALO | No dominant trait | 44 | 1.000 |
| ANT | No dominant trait | 44 | 1.000 |
| BEA | No dominant trait | 45 | 1.000 |
| BOR | No dominant trait | 44 | 1.000 |
| DOO | No dominant trait | 44 | 0.977 |
| HAD | No dominant trait | 43 | 1.000 |
| HAM | No dominant trait | 44 | 1.000 |
| HUL | No dominant trait | 44 | 0.977 |
| LAW | No dominant trait | 43 | 1.000 |
| LEC | No dominant trait | 45 | 1.000 |
| NOR | No dominant trait | 44 | 1.000 |
| OCO | No dominant trait | 47 | 0.979 |
| PIA | No dominant trait | 45 | 1.000 |
| RUS | No dominant trait | 45 | 1.000 |
| SAI | No dominant trait | 45 | 1.000 |
| STR | No dominant trait | 43 | 1.000 |
| VER | No dominant trait | 45 | 0.978 |

### Miami

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | Late braking + less trail braking | 6 | 0.333 |
| ALO | Early braking + low apex speed | 14 | 0.357 |
| ANT | Less trail braking + more coasting | 11 | 0.545 |
| BEA | Early braking | 5 | 0.600 |
| BOR | More trail braking + less coasting | 6 | 0.667 |
| GAS | Early braking | 12 | 0.583 |
| HAD | Less trail braking + more coasting | 7 | 0.571 |
| HAM | More trail braking + less coasting | 13 | 0.538 |
| HUL | Early braking | 14 | 0.357 |
| LAW | Less trail braking + more coasting | 6 | 0.500 |
| LEC | More trail braking + less coasting | 11 | 0.818 |
| NOR | Less trail braking + more coasting | 11 | 0.818 |
| OCO | More trail braking + less coasting | 9 | 0.778 |
| PIA | Early braking | 16 | 0.688 |
| RUS | Late braking + less trail braking | 16 | 0.750 |
| SAI | Early braking + low apex speed | 10 | 0.400 |
| STR | Less trail braking + more coasting | 13 | 0.462 |
| TSU | Late braking + less trail braking | 12 | 0.500 |
| VER | Late braking + less trail braking | 11 | 0.545 |

### Emilia-Romaña

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait | 49 | 0.776 |
| ALO | No dominant trait | 47 | 1.000 |
| ANT | No dominant trait | 40 | 0.975 |
| BEA | No dominant trait | 48 | 1.000 |
| BOR | No dominant trait | 48 | 1.000 |
| COL | No dominant trait | 48 | 0.708 |
| GAS | No dominant trait | 46 | 1.000 |
| HAD | No dominant trait | 50 | 0.960 |
| HAM | No dominant trait | 50 | 1.000 |
| HUL | No dominant trait | 49 | 1.000 |
| LAW | No dominant trait | 48 | 1.000 |
| LEC | No dominant trait | 48 | 0.979 |
| NOR | No dominant trait | 50 | 0.960 |
| OCO | No dominant trait | 25 | 1.000 |
| PIA | No dominant trait | 49 | 1.000 |
| RUS | No dominant trait | 48 | 0.958 |
| SAI | No dominant trait | 48 | 0.979 |
| STR | No dominant trait | 47 | 0.957 |
| TSU | No dominant trait | 50 | 0.980 |
| VER | No dominant trait | 51 | 1.000 |

### Mónaco

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | High apex speed + more full throttle on exit | 63 | 0.508 |
| ALO | High apex speed + more full throttle on exit | 26 | 0.654 |
| ANT | Sharper throttle pickup + less full throttle on exit | 60 | 0.567 |
| BEA | Sharper throttle pickup + less full throttle on exit | 63 | 0.651 |
| BOR | Sharper throttle pickup + less full throttle on exit | 63 | 0.667 |
| COL | Sharper throttle pickup + less full throttle on exit | 63 | 0.397 |
| GAS | Sharper throttle pickup + less full throttle on exit | 3 | 1.000 |
| HAD | High apex speed + more full throttle on exit | 64 | 0.578 |
| HAM | High apex speed + more full throttle on exit | 64 | 0.562 |
| HUL | Sharper throttle pickup + less full throttle on exit | 61 | 0.475 |
| LAW | Sharper throttle pickup + less full throttle on exit | 64 | 0.438 |
| LEC | High apex speed + more full throttle on exit | 64 | 0.703 |
| NOR | High apex speed + more full throttle on exit | 65 | 0.600 |
| OCO | Sharper throttle pickup + less full throttle on exit | 64 | 0.438 |
| PIA | High apex speed + more full throttle on exit | 65 | 0.692 |
| RUS | Sharper throttle pickup + less full throttle on exit | 59 | 0.644 |
| SAI | Sharper throttle pickup + less full throttle on exit | 63 | 0.524 |
| STR | Less trail braking + more coasting | 62 | 0.806 |
| TSU | Less trail braking + more coasting | 65 | 0.846 |
| VER | High apex speed + more full throttle on exit | 64 | 0.641 |

### España

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | Early braking + less full throttle on exit | 21 | 0.762 |
| ALO | Less trail braking + more full throttle on exit | 53 | 0.453 |
| ANT | High apex speed + more coasting | 46 | 0.478 |
| BEA | Early braking + less full throttle on exit | 52 | 0.519 |
| BOR | Low apex speed + softer throttle pickup | 54 | 0.630 |
| COL | More coasting + less full throttle on exit | 52 | 0.731 |
| GAS | More coasting + less full throttle on exit | 54 | 0.407 |
| HAD | Less trail braking + more full throttle on exit | 54 | 0.463 |
| HAM | More trail braking + less coasting | 55 | 0.836 |
| HUL | More coasting + less full throttle on exit | 54 | 0.463 |
| LAW | Less trail braking + more full throttle on exit | 53 | 0.547 |
| LEC | More trail braking + less coasting | 55 | 0.782 |
| NOR | High apex speed + more coasting | 55 | 0.673 |
| OCO | More trail braking + less coasting | 54 | 0.426 |
| PIA | High apex speed + more coasting | 55 | 0.727 |
| RUS | High apex speed + more coasting | 55 | 0.473 |
| SAI | Early braking + less full throttle on exit | 54 | 0.426 |
| TSU | Less trail braking + more full throttle on exit | 52 | 0.327 |
| VER | High apex speed + more coasting | 52 | 0.750 |

### Canadá

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | Early braking + less trail braking | 21 | 0.571 |
| ALO | Early braking + less trail braking | 33 | 0.545 |
| ANT | More trail braking | 27 | 0.815 |
| BEA | Early braking + less trail braking | 27 | 0.704 |
| BOR | Early braking + less trail braking | 29 | 0.966 |
| COL | More trail braking | 32 | 0.781 |
| GAS | More trail braking | 28 | 0.679 |
| HAD | Early braking + less trail braking | 29 | 0.862 |
| HAM | More trail braking | 31 | 0.774 |
| HUL | Early braking + less trail braking | 34 | 0.824 |
| LAW | Early braking + less trail braking | 31 | 0.839 |
| LEC | More trail braking | 35 | 0.886 |
| NOR | More trail braking | 36 | 0.639 |
| OCO | More trail braking | 31 | 0.839 |
| PIA | More trail braking | 28 | 0.643 |
| RUS | More trail braking | 30 | 0.800 |
| SAI | Early braking + less trail braking | 30 | 0.733 |
| STR | Early braking + less trail braking | 34 | 0.794 |
| TSU | Early braking + less trail braking | 32 | 0.688 |
| VER | More trail braking | 30 | 0.933 |

### Austria

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | Sharper throttle pickup | 9 | 0.556 |
| ALO | No dominant trait | 62 | 0.887 |
| BEA | No dominant trait | 59 | 0.864 |
| BOR | No dominant trait | 61 | 0.967 |
| COL | No dominant trait | 60 | 0.550 |
| GAS | No dominant trait | 61 | 0.639 |
| HAD | No dominant trait | 63 | 0.889 |
| HAM | No dominant trait | 61 | 0.721 |
| HUL | No dominant trait | 61 | 0.885 |
| LAW | No dominant trait | 64 | 1.000 |
| LEC | No dominant trait | 61 | 0.803 |
| NOR | No dominant trait | 61 | 0.951 |
| OCO | No dominant trait | 60 | 0.850 |
| PIA | No dominant trait | 60 | 0.817 |
| RUS | No dominant trait | 62 | 0.823 |
| STR | No dominant trait | 60 | 1.000 |
| TSU | No dominant trait | 59 | 0.881 |

### Gran Bretaña

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait | 31 | 0.903 |
| ALO | No dominant trait | 28 | 1.000 |
| ANT | No dominant trait | 3 | 1.000 |
| BEA | No dominant trait | 28 | 0.857 |
| GAS | No dominant trait | 27 | 1.000 |
| HAD | No dominant trait | 3 | 1.000 |
| HAM | No dominant trait | 27 | 0.963 |
| HUL | No dominant trait | 29 | 1.000 |
| LEC | No dominant trait | 29 | 1.000 |
| NOR | No dominant trait | 29 | 1.000 |
| OCO | No dominant trait | 32 | 0.781 |
| PIA | No dominant trait | 28 | 1.000 |
| RUS | No dominant trait | 29 | 1.000 |
| SAI | No dominant trait | 28 | 0.929 |
| STR | Early braking | 27 | 0.556 |
| TSU | No dominant trait | 28 | 0.821 |
| VER | No dominant trait | 28 | 0.929 |

### Bélgica

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | Low apex speed + less full throttle on exit | 37 | 0.568 |
| ALO | Low apex speed + less full throttle on exit | 35 | 0.743 |
| ANT | Low apex speed + less full throttle on exit | 35 | 0.971 |
| BEA | Less coasting + more full throttle on exit | 38 | 0.579 |
| BOR | Low apex speed + less full throttle on exit | 37 | 0.459 |
| COL | Low apex speed + less full throttle on exit | 34 | 0.559 |
| GAS | Less coasting + more full throttle on exit | 37 | 0.459 |
| HAD | More coasting | 33 | 0.909 |
| HAM | Less coasting + more full throttle on exit | 38 | 0.447 |
| HUL | Less coasting + more full throttle on exit | 36 | 0.639 |
| LAW | More coasting | 38 | 0.842 |
| LEC | Less coasting + more full throttle on exit | 38 | 1.000 |
| NOR | More coasting | 37 | 0.919 |
| OCO | Low apex speed + less full throttle on exit | 38 | 0.500 |
| PIA | More coasting | 38 | 0.947 |
| RUS | More coasting | 38 | 0.605 |
| SAI | Less coasting + more full throttle on exit | 34 | 0.765 |
| STR | More coasting | 38 | 0.684 |
| TSU | More coasting | 37 | 0.649 |
| VER | Less coasting + more full throttle on exit | 38 | 0.579 |

### Hungría

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait | 63 | 0.968 |
| ALO | No dominant trait | 67 | 0.985 |
| ANT | No dominant trait | 65 | 0.631 |
| BEA | No dominant trait | 43 | 1.000 |
| BOR | No dominant trait | 67 | 0.701 |
| COL | No dominant trait | 62 | 0.935 |
| GAS | No dominant trait | 64 | 0.922 |
| HAD | Softer throttle pickup + more full throttle on exit | 66 | 0.591 |
| HAM | No dominant trait | 65 | 1.000 |
| HUL | No dominant trait | 61 | 0.770 |
| LAW | No dominant trait | 67 | 0.507 |
| LEC | No dominant trait | 65 | 0.954 |
| NOR | No dominant trait | 66 | 0.848 |
| OCO | No dominant trait | 66 | 0.909 |
| PIA | No dominant trait | 65 | 0.923 |
| RUS | No dominant trait | 64 | 0.922 |
| SAI | No dominant trait | 63 | 0.921 |
| STR | No dominant trait | 67 | 0.910 |
| TSU | No dominant trait | 64 | 0.906 |
| VER | No dominant trait | 65 | 0.862 |

### Países Bajos

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | Sharper throttle pickup + less full throttle on exit | 55 | 0.564 |
| ALO | More trail braking + less coasting | 49 | 0.571 |
| ANT | Early braking + less trail braking | 53 | 0.283 |
| BEA | Early braking + less trail braking | 53 | 0.340 |
| BOR | More trail braking + less coasting | 49 | 0.673 |
| COL | More trail braking + less coasting | 49 | 0.347 |
| GAS | Early braking + less trail braking | 52 | 0.635 |
| HAD | High apex speed + more coasting | 55 | 0.818 |
| HAM | More trail braking + less coasting | 21 | 0.952 |
| HUL | Early braking + less trail braking | 49 | 0.612 |
| LAW | Late braking + more full throttle on exit | 52 | 0.462 |
| LEC | More trail braking + less coasting | 41 | 0.780 |
| NOR | High apex speed + more coasting | 51 | 0.843 |
| OCO | More trail braking + less coasting | 53 | 0.698 |
| PIA | High apex speed + more coasting | 55 | 0.782 |
| RUS | High apex speed + more coasting | 54 | 0.481 |
| SAI | More trail braking + less coasting | 50 | 0.480 |
| STR | High apex speed + more coasting | 51 | 0.627 |
| TSU | Early braking + less trail braking | 51 | 0.725 |
| VER | High apex speed + more coasting | 55 | 0.909 |

### Italia

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait (class 0) | 38 | 0.947 |
| ALO | No dominant trait (class 0) | 20 | 1.000 |
| ANT | No dominant trait (class 0) | 46 | 1.000 |
| BEA | No dominant trait (class 0) | 49 | 0.735 |
| BOR | No dominant trait (class 0) | 48 | 0.979 |
| COL | No dominant trait (class 0) | 45 | 0.978 |
| GAS | No dominant trait (class 0) | 45 | 0.978 |
| HAD | No dominant trait (class 0) | 48 | 0.896 |
| HAM | No dominant trait (class 0) | 49 | 0.980 |
| LAW | No dominant trait (class 0) | 48 | 0.979 |
| LEC | No dominant trait (class 0) | 48 | 0.979 |
| NOR | No dominant trait (class 0) | 49 | 0.980 |
| OCO | No dominant trait (class 0) | 48 | 0.938 |
| PIA | No dominant trait (class 0) | 49 | 1.000 |
| RUS | No dominant trait (class 0) | 48 | 1.000 |
| SAI | No dominant trait (class 0) | 47 | 0.915 |
| STR | No dominant trait (class 0) | 47 | 1.000 |
| TSU | No dominant trait (class 0) | 48 | 0.979 |
| VER | No dominant trait (class 0) | 48 | 1.000 |

### Azerbaiyán

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | Early braking + low apex speed | 42 | 0.571 |
| ALO | Early braking + low apex speed | 42 | 0.381 |
| ANT | High apex speed + less trail braking | 43 | 0.837 |
| BEA | Early braking + low apex speed | 42 | 0.476 |
| BOR | Late braking + more trail braking | 42 | 0.476 |
| COL | Late braking + more trail braking | 42 | 0.571 |
| GAS | Early braking + low apex speed | 41 | 0.634 |
| HAD | Late braking + more trail braking | 42 | 0.690 |
| HAM | More trail braking + less coasting | 42 | 0.857 |
| HUL | Early braking + low apex speed | 42 | 0.429 |
| LAW | More coasting | 41 | 0.878 |
| LEC | More trail braking + less coasting | 42 | 0.714 |
| NOR | Early braking + low apex speed | 42 | 0.429 |
| OCO | More trail braking + less coasting | 44 | 0.636 |
| RUS | High apex speed + less trail braking | 41 | 0.683 |
| SAI | Late braking + more trail braking | 41 | 0.634 |
| STR | More coasting | 42 | 0.381 |
| TSU | More coasting | 41 | 0.317 |
| VER | Late braking + more trail braking | 42 | 0.881 |

### Singapur

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | Late braking + less trail braking | 55 | 0.509 |
| ALO | More coasting | 57 | 0.404 |
| ANT | Late braking + less trail braking | 55 | 0.255 |
| BEA | Late braking | 55 | 0.309 |
| BOR | More trail braking + less coasting | 56 | 0.643 |
| COL | More trail braking + sharper throttle pickup | 54 | 0.407 |
| GAS | No dominant trait | 53 | 0.434 |
| HAD | Late braking | 56 | 0.339 |
| HAM | More trail braking + less coasting | 53 | 0.472 |
| HUL | No dominant trait | 55 | 0.291 |
| LAW | More coasting | 56 | 0.411 |
| LEC | More trail braking + less coasting | 56 | 0.518 |
| NOR | Early braking + high apex speed | 56 | 0.661 |
| OCO | More trail braking + less coasting | 54 | 0.537 |
| PIA | Early braking + high apex speed | 57 | 0.825 |
| RUS | Late braking | 57 | 0.509 |
| SAI | More trail braking + sharper throttle pickup | 55 | 0.400 |
| STR | More coasting | 55 | 0.655 |
| TSU | No dominant trait | 56 | 0.321 |
| VER | Late braking | 55 | 0.491 |

### Estados Unidos

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait | 47 | 0.787 |
| ALO | No dominant trait | 48 | 1.000 |
| ANT | No dominant trait | 46 | 0.957 |
| BEA | No dominant trait | 48 | 1.000 |
| BOR | No dominant trait | 43 | 0.953 |
| COL | No dominant trait | 47 | 0.979 |
| GAS | No dominant trait | 47 | 1.000 |
| HAD | No dominant trait | 47 | 0.936 |
| HAM | No dominant trait | 44 | 0.955 |
| HUL | No dominant trait | 50 | 0.860 |
| LAW | No dominant trait | 49 | 1.000 |
| LEC | No dominant trait | 47 | 0.957 |
| NOR | No dominant trait | 45 | 0.978 |
| OCO | No dominant trait | 48 | 0.979 |
| PIA | No dominant trait | 45 | 0.889 |
| RUS | No dominant trait | 49 | 0.980 |
| SAI | No dominant trait | 4 | 1.000 |
| STR | No dominant trait | 48 | 1.000 |
| TSU | No dominant trait | 48 | 1.000 |
| VER | No dominant trait | 48 | 1.000 |

### Ciudad de México

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait | 63 | 0.698 |
| ALO | No dominant trait | 28 | 0.643 |
| ANT | No dominant trait | 59 | 0.780 |
| BEA | No dominant trait | 61 | 0.754 |
| BOR | No dominant trait | 64 | 0.656 |
| COL | No dominant trait | 62 | 0.677 |
| GAS | No dominant trait | 62 | 0.645 |
| HAD | No dominant trait | 63 | 0.778 |
| HAM | No dominant trait | 59 | 0.644 |
| HUL | No dominant trait | 21 | 0.667 |
| LEC | No dominant trait | 62 | 0.694 |
| NOR | No dominant trait | 63 | 0.683 |
| OCO | No dominant trait | 64 | 0.750 |
| PIA | No dominant trait | 61 | 0.672 |
| RUS | No dominant trait | 61 | 0.738 |
| SAI | No dominant trait | 38 | 0.605 |
| STR | No dominant trait | 61 | 0.705 |
| TSU | No dominant trait | 64 | 0.547 |
| VER | No dominant trait | 63 | 0.619 |

### São Paulo

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | More trail braking + sharper throttle pickup | 59 | 0.356 |
| ALO | More trail braking + less coasting | 59 | 0.305 |
| ANT | High apex speed + sharper throttle pickup | 59 | 0.424 |
| BEA | High apex speed + sharper throttle pickup | 59 | 0.492 |
| COL | Late braking + more coasting | 59 | 0.746 |
| GAS | Low apex speed + more full throttle on exit | 59 | 0.356 |
| HAD | Low apex speed + more full throttle on exit | 58 | 0.276 |
| HAM | More trail braking + sharper throttle pickup | 24 | 0.458 |
| HUL | Low apex speed + more full throttle on exit | 61 | 0.311 |
| LAW | Softer throttle pickup + more full throttle on exit | 61 | 0.672 |
| NOR | Less trail braking + more coasting | 59 | 0.356 |
| OCO | More trail braking + less coasting | 60 | 0.550 |
| PIA | High apex speed + sharper throttle pickup | 59 | 0.390 |
| RUS | High apex speed + sharper throttle pickup | 57 | 0.404 |
| SAI | More trail braking + sharper throttle pickup | 58 | 0.569 |
| STR | Less trail braking + more coasting | 58 | 0.759 |
| TSU | Late braking + more coasting | 58 | 0.466 |
| VER | Softer throttle pickup + more full throttle on exit | 59 | 0.475 |

### Las Vegas

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | Less trail braking + more coasting | 25 | 0.400 |
| ALO | Low apex speed + more coasting | 28 | 0.571 |
| BEA | No dominant trait | 36 | 0.472 |
| COL | Early braking + less coasting | 4 | 0.250 |
| GAS | Less trail braking + more coasting | 6 | 1.000 |
| HAD | Less trail braking + more coasting | 11 | 0.364 |
| HAM | Early braking + less coasting | 42 | 0.595 |
| HUL | Less trail braking + more coasting | 37 | 0.405 |
| LAW | Low apex speed + more coasting | 9 | 0.556 |
| LEC | Late braking + more trail braking + less coasting | 38 | 0.737 |
| OCO | Less trail braking + more coasting | 42 | 0.357 |
| PIA | Less trail braking + more coasting | 4 | 0.500 |
| SAI | Early braking + less coasting | 43 | 0.395 |
| TSU | Low apex speed + less trail braking | 15 | 0.467 |

### Catar

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait | 47 | 1.000 |
| ALO | No dominant trait | 50 | 1.000 |
| ANT | No dominant trait | 48 | 1.000 |
| BEA | No dominant trait | 32 | 1.000 |
| BOR | No dominant trait | 50 | 1.000 |
| COL | No dominant trait | 48 | 1.000 |
| GAS | No dominant trait | 48 | 0.979 |
| HAD | No dominant trait | 46 | 1.000 |
| HAM | No dominant trait | 49 | 1.000 |
| HUL | No dominant trait | 5 | 1.000 |
| LAW | No dominant trait | 49 | 1.000 |
| LEC | No dominant trait | 49 | 0.980 |
| NOR | No dominant trait | 46 | 1.000 |
| OCO | No dominant trait | 49 | 0.980 |
| PIA | No dominant trait | 47 | 1.000 |
| RUS | No dominant trait | 46 | 1.000 |
| SAI | No dominant trait | 50 | 1.000 |
| STR | No dominant trait | 45 | 0.978 |
| TSU | No dominant trait | 48 | 1.000 |
| VER | No dominant trait | 50 | 1.000 |

### Abu Dabi

Lectura: no concluyente.

| piloto | clase | vueltas | proporción en la clase |
| --- | --- | ---: | ---: |
| ALB | No dominant trait | 50 | 1.000 |
| ALO | No dominant trait | 55 | 1.000 |
| ANT | Early braking + sharper throttle pickup | 52 | 0.519 |
| BEA | No dominant trait | 54 | 1.000 |
| BOR | No dominant trait | 53 | 1.000 |
| COL | No dominant trait | 49 | 0.980 |
| GAS | No dominant trait | 48 | 1.000 |
| HAD | No dominant trait | 51 | 1.000 |
| HAM | No dominant trait | 50 | 1.000 |
| HUL | No dominant trait | 50 | 1.000 |
| LAW | No dominant trait | 52 | 1.000 |
| LEC | No dominant trait | 51 | 1.000 |
| NOR | No dominant trait | 53 | 1.000 |
| OCO | No dominant trait | 53 | 1.000 |
| PIA | No dominant trait | 54 | 1.000 |
| RUS | No dominant trait | 55 | 1.000 |
| SAI | No dominant trait | 54 | 1.000 |
| STR | No dominant trait | 54 | 1.000 |
| TSU | No dominant trait | 53 | 1.000 |
| VER | No dominant trait | 53 | 1.000 |

## Perfil continuo

El camino es el de `docs/perfil_continuo_2025.md`: análisis paralelo de 50 permutaciones de columna, 200 bootstraps de cargas, 2000 bootstraps del perfil estratificados por compuesto, percentiles 2.5 y 97.5, semilla 42. El signo de cada eje deja positiva la carga de mayor valor absoluto. Un eje se describe por esa feature y por el signo de su carga. Los scores no se comparan entre grandes premios.

Dentro de un GP y de un componente retenido, un piloto está en el máximo si su mediana es la mayor de ese GP, y en el mínimo si es la menor. Un empate cuenta. Si la mediana máxima y la mínima son el mismo número, ese componente no tiene extremos.

Las medianas y los intervalos de cada piloto están en `docs/clasificacion_pilotos_zoi_2025/perfiles.csv`.

| carrera | vueltas | features | componentes | varianza acumulada |
| --- | ---: | ---: | ---: | ---: |
| Australia | 547 | 16 | 3 | 0.632 |
| China | 942 | 16 | 1 | 0.328 |
| Japón | 989 | 16 | 3 | 0.452 |
| Baréin | 924 | 16 | 6 | 0.831 |
| Arabia Saudita | 798 | 16 | 4 | 0.652 |
| Miami | 203 | 15 | 3 | 0.599 |
| Emilia-Romaña | 939 | 16 | 4 | 0.639 |
| Mónaco | 1165 | 10 | 3 | 0.555 |
| España | 980 | 16 | 4 | 0.525 |
| Canadá | 608 | 16 | 4 | 0.643 |
| Austria | 984 | 16 | 5 | 0.757 |
| Gran Bretaña | 434 | 16 | 6 | 0.741 |
| Bélgica | 734 | 16 | 6 | 0.703 |
| Hungría | 1275 | 16 | 5 | 0.727 |
| Países Bajos | 998 | 16 | 4 | 0.634 |
| Italia | 868 | 16 | 5 | 0.838 |
| Azerbaiyán | 796 | 10 | 3 | 0.689 |
| Singapur | 1106 | 16 | 3 | 0.527 |
| Estados Unidos | 898 | 16 | 3 | 0.788 |
| Ciudad de México | 1079 | 12 | 4 | 0.803 |
| São Paulo | 1026 | 16 | 2 | 0.400 |
| Las Vegas | 340 | 16 | 1 | 0.297 |
| Catar | 902 | 16 | 4 | 0.742 |
| Abu Dabi | 1044 | 16 | 1 | 0.386 |

| carrera | componente | feature | carga | signo | el intervalo de la carga incluye el 0 |
| --- | --- | --- | ---: | --- | --- |
| Australia | PC1 | `medium__throttle_attack` | 0.9689 | positiva | no |
| Australia | PC2 | `medium__trail_brake_frac` | 0.4910 | positiva | no |
| Australia | PC3 | `slow__full_throttle_frac` | 0.5513 | positiva | no |
| China | PC1 | `medium__full_throttle_frac` | 0.9894 | positiva | no |
| Japón | PC1 | `fast__coast_frac` | 0.5400 | positiva | no |
| Japón | PC2 | `slow__trail_brake_frac` | 0.4800 | positiva | no |
| Japón | PC3 | `medium__apex_speed_rel` | 0.5124 | positiva | no |
| Baréin | PC1 | `medium__full_throttle_frac` | 0.9606 | positiva | no |
| Baréin | PC2 | `slow__full_throttle_frac` | 0.5657 | positiva | no |
| Baréin | PC3 | `slow__apex_speed_rel` | 0.7629 | positiva | no |
| Baréin | PC4 | `medium__trail_brake_frac` | 0.5045 | positiva | no |
| Baréin | PC5 | `fast__apex_speed_rel` | 0.6194 | positiva | no |
| Baréin | PC6 | `medium__throttle_attack` | 0.7672 | positiva | no |
| Arabia Saudita | PC1 | `medium__throttle_attack` | 0.6073 | positiva | no |
| Arabia Saudita | PC2 | `medium__throttle_attack` | 0.7351 | positiva | no |
| Arabia Saudita | PC3 | `slow__apex_speed_rel` | 0.5957 | positiva | no |
| Arabia Saudita | PC4 | `slow__coast_frac` | 0.7343 | positiva | no |
| Miami | PC1 | `slow__apex_speed_rel` | 0.6696 | positiva | no |
| Miami | PC2 | `slow__apex_speed_rel` | 0.4937 | positiva | no |
| Miami | PC3 | `medium__apex_speed_rel` | 0.5658 | positiva | no |
| Emilia-Romaña | PC1 | `medium__full_throttle_frac` | 0.9267 | positiva | no |
| Emilia-Romaña | PC2 | `medium__coast_frac` | 0.5250 | positiva | no |
| Emilia-Romaña | PC3 | `medium__apex_speed_rel` | 0.5228 | positiva | no |
| Emilia-Romaña | PC4 | `fast__apex_speed_rel` | 0.6936 | positiva | no |
| Mónaco | PC1 | `fast__coast_frac` | 0.4748 | positiva | no |
| Mónaco | PC2 | `slow__brake_point_rel` | 0.8444 | positiva | no |
| Mónaco | PC3 | `fast__coast_frac` | 0.5451 | positiva | no |
| España | PC1 | `medium__trail_brake_frac` | 0.4004 | positiva | no |
| España | PC2 | `medium__apex_speed_rel` | 0.5053 | positiva | no |
| España | PC3 | `medium__coast_frac` | 0.5161 | positiva | no |
| España | PC4 | `medium__full_throttle_frac` | 0.4696 | positiva | no |
| Canadá | PC1 | `medium__throttle_attack` | 0.9160 | positiva | sí |
| Canadá | PC2 | `slow__apex_speed_rel` | 0.4304 | positiva | no |
| Canadá | PC3 | `slow__throttle_attack` | 0.9107 | positiva | no |
| Canadá | PC4 | `medium__trail_brake_frac` | 0.5699 | positiva | no |
| Austria | PC1 | `medium__throttle_attack` | 0.9401 | positiva | no |
| Austria | PC2 | `slow__full_throttle_frac` | 0.7772 | positiva | no |
| Austria | PC3 | `slow__apex_speed_rel` | 0.4960 | positiva | no |
| Austria | PC4 | `medium__trail_brake_frac` | 0.5312 | positiva | no |
| Austria | PC5 | `medium__brake_point_rel` | 0.6300 | positiva | no |
| Gran Bretaña | PC1 | `slow__brake_point_rel` | 0.9139 | positiva | no |
| Gran Bretaña | PC2 | `slow__full_throttle_frac` | 0.8631 | positiva | no |
| Gran Bretaña | PC3 | `fast__full_throttle_frac` | 0.5736 | positiva | no |
| Gran Bretaña | PC4 | `fast__trail_brake_frac` | 0.4276 | positiva | no |
| Gran Bretaña | PC5 | `fast__apex_speed_rel` | 0.4884 | positiva | no |
| Gran Bretaña | PC6 | `slow__throttle_attack` | 0.5593 | positiva | no |
| Bélgica | PC1 | `slow__full_throttle_frac` | 0.8248 | positiva | no |
| Bélgica | PC2 | `fast__apex_speed_rel` | 0.4674 | positiva | no |
| Bélgica | PC3 | `slow__trail_brake_frac` | 0.4775 | positiva | no |
| Bélgica | PC4 | `fast__apex_speed_rel` | 0.5169 | positiva | no |
| Bélgica | PC5 | `medium__brake_point_rel` | 0.5468 | positiva | no |
| Bélgica | PC6 | `slow__throttle_attack` | 0.4818 | positiva | sí |
| Hungría | PC1 | `medium__full_throttle_frac` | 0.8386 | positiva | no |
| Hungría | PC2 | `slow__coast_frac` | 0.5313 | positiva | no |
| Hungría | PC3 | `medium__apex_speed_rel` | 0.4380 | positiva | no |
| Hungría | PC4 | `slow__throttle_attack` | 0.5255 | positiva | no |
| Hungría | PC5 | `medium__brake_point_rel` | 0.5548 | positiva | no |
| Países Bajos | PC1 | `slow__full_throttle_frac` | 0.5612 | positiva | no |
| Países Bajos | PC2 | `medium__apex_speed_rel` | 0.4512 | positiva | no |
| Países Bajos | PC3 | `slow__brake_point_rel` | 0.4188 | positiva | no |
| Países Bajos | PC4 | `medium__throttle_attack` | 0.8181 | positiva | no |
| Italia | PC1 | `slow__throttle_attack` | 0.9966 | positiva | no |
| Italia | PC2 | `fast__trail_brake_frac` | 0.4099 | positiva | no |
| Italia | PC3 | `slow__brake_point_rel` | 0.4317 | positiva | no |
| Italia | PC4 | `fast__trail_brake_frac` | 0.6613 | positiva | no |
| Italia | PC5 | `slow__apex_speed_rel` | 0.7340 | positiva | no |
| Azerbaiyán | PC1 | `slow__coast_frac` | 0.7102 | positiva | no |
| Azerbaiyán | PC2 | `fast__apex_speed_rel` | 0.6773 | positiva | no |
| Azerbaiyán | PC3 | `slow__apex_speed_rel` | 0.7752 | positiva | no |
| Singapur | PC1 | `slow__trail_brake_frac` | 0.4727 | positiva | no |
| Singapur | PC2 | `fast__apex_speed_rel` | 0.6474 | positiva | no |
| Singapur | PC3 | `slow__throttle_attack` | 0.6997 | positiva | no |
| Estados Unidos | PC1 | `medium__throttle_attack` | 0.9653 | positiva | no |
| Estados Unidos | PC2 | `fast__full_throttle_frac` | 0.9688 | positiva | no |
| Estados Unidos | PC3 | `slow__full_throttle_frac` | 0.8762 | positiva | no |
| Ciudad de México | PC1 | `slow__full_throttle_frac` | 0.9981 | positiva | no |
| Ciudad de México | PC2 | `medium__trail_brake_frac` | 0.5012 | positiva | no |
| Ciudad de México | PC3 | `slow__brake_point_rel` | 0.5965 | positiva | no |
| Ciudad de México | PC4 | `medium__apex_speed_rel` | 0.6630 | positiva | no |
| São Paulo | PC1 | `medium__trail_brake_frac` | 0.5066 | positiva | no |
| São Paulo | PC2 | `slow__apex_speed_rel` | 0.6646 | positiva | no |
| Las Vegas | PC1 | `slow__coast_frac` | 0.6135 | positiva | no |
| Catar | PC1 | `slow__throttle_attack` | 0.9924 | positiva | no |
| Catar | PC2 | `slow__coast_frac` | 0.4505 | positiva | no |
| Catar | PC3 | `medium__throttle_attack` | 0.8648 | positiva | no |
| Catar | PC4 | `slow__brake_point_rel` | 0.5706 | positiva | no |
| Abu Dabi | PC1 | `slow__throttle_attack` | 0.6235 | positiva | no |

### Extremos por piloto

**ALB**

- Austria, PC1, máximo del GP (mediana 1.892, intervalo -0.720 a 4.743). La carga de mayor valor absoluto es `medium__throttle_attack` (0.9401, positiva).
- Baréin, PC1, mínimo del GP (mediana -1.483, intervalo -5.043 a 0.313). La carga de mayor valor absoluto es `medium__full_throttle_frac` (0.9606, positiva).
- Baréin, PC6, máximo del GP (mediana 1.046, intervalo 0.660 a 1.418). La carga de mayor valor absoluto es `medium__throttle_attack` (0.7672, positiva).
- Bélgica, PC6, mínimo del GP (mediana -0.620, intervalo -0.933 a -0.329). La carga de mayor valor absoluto es `slow__throttle_attack` (0.4818, positiva).
- Ciudad de México, PC4, mínimo del GP (mediana -0.804, intervalo -1.084 a -0.553). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.6630, positiva).
- España, PC1, máximo del GP (mediana 1.186, intervalo 0.489 a 1.480). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.4004, positiva).
- España, PC4, mínimo del GP (mediana -1.447, intervalo -1.698 a -1.136). La carga de mayor valor absoluto es `medium__full_throttle_frac` (0.4696, positiva).
- Países Bajos, PC1, mínimo del GP (mediana -1.587, intervalo -1.826 a -1.221). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.5612, positiva).
- Países Bajos, PC4, máximo del GP (mediana 0.654, intervalo -0.050 a 0.971). La carga de mayor valor absoluto es `medium__throttle_attack` (0.8181, positiva).
- Singapur, PC2, máximo del GP (mediana 1.130, intervalo 0.724 a 1.409). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.6474, positiva).
- Singapur, PC3, máximo del GP (mediana 0.893, intervalo 0.508 a 1.291). La carga de mayor valor absoluto es `slow__throttle_attack` (0.6997, positiva).

**ALO**

- Austria, PC2, mínimo del GP (mediana -0.683, intervalo -1.283 a -0.404). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.7772, positiva).
- España, PC2, mínimo del GP (mediana -1.253, intervalo -1.618 a -0.817). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5053, positiva).
- Las Vegas, PC1, máximo del GP (mediana 1.743, intervalo 1.488 a 2.209). La carga de mayor valor absoluto es `slow__coast_frac` (0.6135, positiva).
- Miami, PC2, mínimo del GP (mediana -1.080, intervalo -1.634 a -0.446). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.4937, positiva).
- Singapur, PC1, mínimo del GP (mediana -1.557, intervalo -1.836 a -1.229). La carga de mayor valor absoluto es `slow__trail_brake_frac` (0.4727, positiva).

**ANT**

- Abu Dabi, PC1, máximo del GP (mediana 5.845, intervalo 4.502 a 6.587). La carga de mayor valor absoluto es `slow__throttle_attack` (0.6235, positiva).
- Azerbaiyán, PC2, máximo del GP (mediana 0.978, intervalo 0.778 a 1.233). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.6773, positiva).
- Azerbaiyán, PC3, máximo del GP (mediana 1.037, intervalo 0.877 a 1.076). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.7752, positiva).
- España, PC1, mínimo del GP (mediana -1.022, intervalo -1.284 a -0.602). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.4004, positiva).
- Gran Bretaña, PC1, mínimo del GP (mediana -1.894, intervalo -1.894 a -1.276). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.9139, positiva).
- Hungría, PC5, máximo del GP (mediana 0.879, intervalo 0.707 a 1.027). La carga de mayor valor absoluto es `medium__brake_point_rel` (0.5548, positiva).
- São Paulo, PC2, máximo del GP (mediana 0.936, intervalo 0.692 a 1.171). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.6646, positiva).

**BEA**

- Estados Unidos, PC3, máximo del GP (mediana 1.108, intervalo 0.997 a 1.153). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.8762, positiva).
- Miami, PC3, mínimo del GP (mediana -1.214, intervalo -1.716 a 0.293). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5658, positiva).
- Mónaco, PC2, máximo del GP (mediana 0.827, intervalo 0.527 a 1.031). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.8444, positiva).

**BOR**

- Baréin, PC6, mínimo del GP (mediana -0.420, intervalo -0.809 a -0.211). La carga de mayor valor absoluto es `medium__throttle_attack` (0.7672, positiva).
- Canadá, PC2, mínimo del GP (mediana -1.414, intervalo -1.792 a -1.031). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.4304, positiva).
- Canadá, PC3, máximo del GP (mediana 0.390, intervalo 0.208 a 0.483). La carga de mayor valor absoluto es `slow__throttle_attack` (0.9107, positiva).
- Canadá, PC4, máximo del GP (mediana 1.514, intervalo 1.243 a 1.869). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5699, positiva).
- Catar, PC2, mínimo del GP (mediana -1.609, intervalo -1.838 a -1.314). La carga de mayor valor absoluto es `slow__coast_frac` (0.4505, positiva).
- Catar, PC3, mínimo del GP (mediana -0.993, intervalo -1.084 a -0.852). La carga de mayor valor absoluto es `medium__throttle_attack` (0.8648, positiva).

**COL**

- Azerbaiyán, PC2, mínimo del GP (mediana -0.963, intervalo -1.336 a -0.632). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.6773, positiva).
- Bélgica, PC1, mínimo del GP (mediana -1.321, intervalo -1.670 a -1.103). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.8248, positiva).
- Catar, PC4, mínimo del GP (mediana -0.965, intervalo -1.309 a -0.570). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.5706, positiva).
- Ciudad de México, PC1, máximo del GP (mediana 1.572, intervalo 0.864 a 2.196). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.9981, positiva).
- Emilia-Romaña, PC1, mínimo del GP (mediana -1.779, intervalo -2.465 a -1.298). La carga de mayor valor absoluto es `medium__full_throttle_frac` (0.9267, positiva).
- España, PC3, máximo del GP (mediana 1.465, intervalo 1.291 a 1.750). La carga de mayor valor absoluto es `medium__coast_frac` (0.5161, positiva).

**DOO**

- Arabia Saudita, PC3, mínimo del GP (mediana -1.380, intervalo -1.560 a -1.050). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.5957, positiva).

**GAS**

- Azerbaiyán, PC3, mínimo del GP (mediana -0.827, intervalo -0.995 a -0.735). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.7752, positiva).
- Baréin, PC5, máximo del GP (mediana 1.256, intervalo 1.063 a 1.366). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.6194, positiva).
- Japón, PC2, mínimo del GP (mediana -1.070, intervalo -1.385 a -0.918). La carga de mayor valor absoluto es `slow__trail_brake_frac` (0.4800, positiva).

**HAD**

- Abu Dabi, PC1, mínimo del GP (mediana -1.367, intervalo -1.571 a -1.122). La carga de mayor valor absoluto es `slow__throttle_attack` (0.6235, positiva).
- Austria, PC4, mínimo del GP (mediana -1.071, intervalo -1.300 a -0.766). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5312, positiva).
- Austria, PC5, máximo del GP (mediana 0.741, intervalo 0.384 a 1.027). La carga de mayor valor absoluto es `medium__brake_point_rel` (0.6300, positiva).
- Gran Bretaña, PC4, mínimo del GP (mediana -3.084, intervalo -3.173 a -3.084). La carga de mayor valor absoluto es `fast__trail_brake_frac` (0.4276, positiva).
- Gran Bretaña, PC5, máximo del GP (mediana 3.557, intervalo 3.557 a 3.737). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.4884, positiva).
- Hungría, PC1, máximo del GP (mediana 1.614, intervalo 0.963 a 2.093). La carga de mayor valor absoluto es `medium__full_throttle_frac` (0.8386, positiva).
- Hungría, PC3, mínimo del GP (mediana -1.044, intervalo -1.194 a -0.787). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.4380, positiva).

**HAM**

- Arabia Saudita, PC4, mínimo del GP (mediana -1.195, intervalo -1.354 a -1.068). La carga de mayor valor absoluto es `slow__coast_frac` (0.7343, positiva).
- Catar, PC1, máximo del GP (mediana -0.101, intervalo -0.136 a -0.022). La carga de mayor valor absoluto es `slow__throttle_attack` (0.9924, positiva).
- Emilia-Romaña, PC2, mínimo del GP (mediana -2.086, intervalo -2.245 a -1.855). La carga de mayor valor absoluto es `medium__coast_frac` (0.5250, positiva).
- Hungría, PC1, mínimo del GP (mediana -1.736, intervalo -2.000 a -1.440). La carga de mayor valor absoluto es `medium__full_throttle_frac` (0.8386, positiva).
- Japón, PC2, máximo del GP (mediana 1.457, intervalo 1.132 a 1.823). La carga de mayor valor absoluto es `slow__trail_brake_frac` (0.4800, positiva).
- Miami, PC2, máximo del GP (mediana 1.190, intervalo 0.850 a 1.463). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.4937, positiva).
- Mónaco, PC1, mínimo del GP (mediana -1.232, intervalo -1.474 a -0.870). La carga de mayor valor absoluto es `fast__coast_frac` (0.4748, positiva).
- Países Bajos, PC4, mínimo del GP (mediana -0.731, intervalo -0.969 a -0.523). La carga de mayor valor absoluto es `medium__throttle_attack` (0.8181, positiva).
- São Paulo, PC2, mínimo del GP (mediana -0.658, intervalo -1.003 a -0.112). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.6646, positiva).

**HUL**

- Arabia Saudita, PC1, máximo del GP (mediana 1.300, intervalo 1.031 a 1.446). La carga de mayor valor absoluto es `medium__throttle_attack` (0.6073, positiva).
- Arabia Saudita, PC2, mínimo del GP (mediana -1.046, intervalo -1.316 a -0.874). La carga de mayor valor absoluto es `medium__throttle_attack` (0.7351, positiva).
- Arabia Saudita, PC4, máximo del GP (mediana 0.901, intervalo 0.448 a 1.156). La carga de mayor valor absoluto es `slow__coast_frac` (0.7343, positiva).
- Bélgica, PC6, máximo del GP (mediana 0.797, intervalo 0.355 a 0.945). La carga de mayor valor absoluto es `slow__throttle_attack` (0.4818, positiva).
- China, PC1, mínimo del GP (mediana -0.129, intervalo -0.879 a 0.182). La carga de mayor valor absoluto es `medium__full_throttle_frac` (0.9894, positiva).

**LAW**

- Austria, PC1, mínimo del GP (mediana -1.522, intervalo -1.727 a -1.375). La carga de mayor valor absoluto es `medium__throttle_attack` (0.9401, positiva).
- Azerbaiyán, PC1, máximo del GP (mediana 1.498, intervalo 1.324 a 1.907). La carga de mayor valor absoluto es `slow__coast_frac` (0.7102, positiva).
- Bélgica, PC5, mínimo del GP (mediana -1.365, intervalo -1.596 a -1.089). La carga de mayor valor absoluto es `medium__brake_point_rel` (0.5468, positiva).
- Emilia-Romaña, PC3, mínimo del GP (mediana -1.357, intervalo -1.542 a -1.170). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5228, positiva).
- Italia, PC4, máximo del GP (mediana 1.159, intervalo 1.026 a 1.394). La carga de mayor valor absoluto es `fast__trail_brake_frac` (0.6613, positiva).

**LEC**

- Austria, PC2, máximo del GP (mediana 0.818, intervalo 0.629 a 1.007). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.7772, positiva).
- Azerbaiyán, PC1, mínimo del GP (mediana -1.276, intervalo -1.594 a -1.147). La carga de mayor valor absoluto es `slow__coast_frac` (0.7102, positiva).
- Bélgica, PC1, máximo del GP (mediana 1.444, intervalo 1.343 a 1.653). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.8248, positiva).
- Canadá, PC2, máximo del GP (mediana 1.320, intervalo 0.899 a 1.657). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.4304, positiva).
- China, PC1, máximo del GP (mediana 0.478, intervalo 0.096 a 0.559). La carga de mayor valor absoluto es `medium__full_throttle_frac` (0.9894, positiva).
- Emilia-Romaña, PC1, máximo del GP (mediana 1.509, intervalo 1.429 a 1.656). La carga de mayor valor absoluto es `medium__full_throttle_frac` (0.9267, positiva).
- Emilia-Romaña, PC4, máximo del GP (mediana 1.103, intervalo 0.912 a 1.278). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.6936, positiva).
- España, PC3, mínimo del GP (mediana -1.190, intervalo -1.388 a -0.811). La carga de mayor valor absoluto es `medium__coast_frac` (0.5161, positiva).
- Hungría, PC5, mínimo del GP (mediana -0.862, intervalo -1.162 a -0.691). La carga de mayor valor absoluto es `medium__brake_point_rel` (0.5548, positiva).
- Japón, PC3, máximo del GP (mediana 1.217, intervalo 1.027 a 1.463). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5124, positiva).
- Las Vegas, PC1, mínimo del GP (mediana -2.129, intervalo -2.428 a -1.885). La carga de mayor valor absoluto es `slow__coast_frac` (0.6135, positiva).
- Mónaco, PC2, mínimo del GP (mediana -1.206, intervalo -1.476 a -0.956). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.8444, positiva).
- Países Bajos, PC3, mínimo del GP (mediana -1.352, intervalo -1.516 a -1.224). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.4188, positiva).
- Singapur, PC3, mínimo del GP (mediana -1.054, intervalo -1.233 a -0.914). La carga de mayor valor absoluto es `slow__throttle_attack` (0.6997, positiva).

**NOR**

- Arabia Saudita, PC1, mínimo del GP (mediana -1.770, intervalo -1.926 a -1.621). La carga de mayor valor absoluto es `medium__throttle_attack` (0.6073, positiva).
- Arabia Saudita, PC2, máximo del GP (mediana 1.136, intervalo 1.027 a 1.294). La carga de mayor valor absoluto es `medium__throttle_attack` (0.7351, positiva).
- Australia, PC1, mínimo del GP (mediana -0.636, intervalo -0.742 a -0.520). La carga de mayor valor absoluto es `medium__throttle_attack` (0.9689, positiva).
- Austria, PC3, máximo del GP (mediana 0.908, intervalo 0.432 a 1.353). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.4960, positiva).
- Canadá, PC1, máximo del GP (mediana 0.300, intervalo 0.203 a 0.441). La carga de mayor valor absoluto es `medium__throttle_attack` (0.9160, positiva).
- Canadá, PC3, mínimo del GP (mediana -0.460, intervalo -0.589 a -0.363). La carga de mayor valor absoluto es `slow__throttle_attack` (0.9107, positiva).
- Canadá, PC4, mínimo del GP (mediana -0.866, intervalo -1.196 a -0.616). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5699, positiva).
- Catar, PC2, máximo del GP (mediana 1.677, intervalo 0.925 a 1.908). La carga de mayor valor absoluto es `slow__coast_frac` (0.4505, positiva).
- Catar, PC3, máximo del GP (mediana 0.640, intervalo 0.174 a 0.930). La carga de mayor valor absoluto es `medium__throttle_attack` (0.8648, positiva).
- Ciudad de México, PC3, mínimo del GP (mediana -0.877, intervalo -1.117 a -0.734). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.5965, positiva).
- Ciudad de México, PC4, máximo del GP (mediana 1.144, intervalo 0.977 a 1.323). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.6630, positiva).
- España, PC2, máximo del GP (mediana 1.215, intervalo 1.017 a 1.467). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5053, positiva).
- Italia, PC1, mínimo del GP (mediana -0.859, intervalo -0.890 a -0.828). La carga de mayor valor absoluto es `slow__throttle_attack` (0.9966, positiva).
- Miami, PC1, máximo del GP (mediana 1.370, intervalo 0.609 a 2.862). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.6696, positiva).

**OCO**

- Australia, PC1, máximo del GP (mediana 0.249, intervalo 0.176 a 0.399). La carga de mayor valor absoluto es `medium__throttle_attack` (0.9689, positiva).
- Australia, PC2, máximo del GP (mediana 2.676, intervalo 2.271 a 3.007). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.4910, positiva).
- Austria, PC4, máximo del GP (mediana 1.338, intervalo 1.191 a 1.469). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5312, positiva).
- Austria, PC5, mínimo del GP (mediana -0.841, intervalo -1.014 a -0.507). La carga de mayor valor absoluto es `medium__brake_point_rel` (0.6300, positiva).
- Baréin, PC2, mínimo del GP (mediana -1.824, intervalo -2.409 a -1.390). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.5657, positiva).
- Baréin, PC3, mínimo del GP (mediana -1.650, intervalo -1.901 a -1.295). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.7629, positiva).
- Baréin, PC4, máximo del GP (mediana 1.140, intervalo 0.721 a 1.325). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5045, positiva).
- Bélgica, PC2, mínimo del GP (mediana -1.950, intervalo -2.240 a -1.703). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.4674, positiva).
- Bélgica, PC3, máximo del GP (mediana 1.019, intervalo 0.763 a 1.207). La carga de mayor valor absoluto es `slow__trail_brake_frac` (0.4775, positiva).
- Canadá, PC1, mínimo del GP (mediana -0.214, intervalo -0.434 a -0.115). La carga de mayor valor absoluto es `medium__throttle_attack` (0.9160, positiva).
- Estados Unidos, PC1, mínimo del GP (mediana -1.129, intervalo -1.258 a -0.788). La carga de mayor valor absoluto es `medium__throttle_attack` (0.9653, positiva).
- Estados Unidos, PC2, máximo del GP (mediana 2.346, intervalo 1.357 a 3.080). La carga de mayor valor absoluto es `fast__full_throttle_frac` (0.9688, positiva).
- Estados Unidos, PC3, mínimo del GP (mediana -1.550, intervalo -2.670 a -0.514). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.8762, positiva).
- Gran Bretaña, PC4, máximo del GP (mediana 1.575, intervalo 1.298 a 1.882). La carga de mayor valor absoluto es `fast__trail_brake_frac` (0.4276, positiva).
- Hungría, PC2, mínimo del GP (mediana -1.792, intervalo -2.083 a -1.634). La carga de mayor valor absoluto es `slow__coast_frac` (0.5313, positiva).
- Italia, PC1, máximo del GP (mediana -0.567, intervalo -0.583 a -0.556). La carga de mayor valor absoluto es `slow__throttle_attack` (0.9966, positiva).
- Italia, PC3, máximo del GP (mediana 1.918, intervalo 1.684 a 2.344). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.4317, positiva).
- Italia, PC4, mínimo del GP (mediana -0.742, intervalo -0.887 a -0.499). La carga de mayor valor absoluto es `fast__trail_brake_frac` (0.6613, positiva).
- Japón, PC1, mínimo del GP (mediana -1.853, intervalo -2.033 a -1.732). La carga de mayor valor absoluto es `fast__coast_frac` (0.5400, positiva).
- Países Bajos, PC2, mínimo del GP (mediana -1.284, intervalo -1.468 a -1.190). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.4512, positiva).
- Singapur, PC1, máximo del GP (mediana 1.424, intervalo 1.109 a 1.885). La carga de mayor valor absoluto es `slow__trail_brake_frac` (0.4727, positiva).

**PIA**

- Australia, PC2, mínimo del GP (mediana -1.917, intervalo -2.189 a -1.645). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.4910, positiva).
- Australia, PC3, mínimo del GP (mediana -1.285, intervalo -1.671 a -1.036). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.5513, positiva).
- Baréin, PC3, máximo del GP (mediana 1.100, intervalo 0.829 a 1.316). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.7629, positiva).
- Baréin, PC4, mínimo del GP (mediana -1.346, intervalo -1.958 a -0.938). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5045, positiva).
- Bélgica, PC2, máximo del GP (mediana 1.914, intervalo 1.708 a 2.195). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.4674, positiva).
- Catar, PC1, mínimo del GP (mediana -0.471, intervalo -0.493 a -0.441). La carga de mayor valor absoluto es `slow__throttle_attack` (0.9924, positiva).
- Estados Unidos, PC1, máximo del GP (mediana 0.293, intervalo -0.581 a 1.193). La carga de mayor valor absoluto es `medium__throttle_attack` (0.9653, positiva).
- Gran Bretaña, PC3, mínimo del GP (mediana -2.612, intervalo -3.446 a -1.320). La carga de mayor valor absoluto es `fast__full_throttle_frac` (0.5736, positiva).
- Hungría, PC3, máximo del GP (mediana 1.500, intervalo 1.334 a 1.819). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.4380, positiva).
- Italia, PC3, mínimo del GP (mediana -1.100, intervalo -1.309 a -1.024). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.4317, positiva).
- Italia, PC5, máximo del GP (mediana 0.875, intervalo 0.688 a 1.047). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.7340, positiva).
- Singapur, PC2, mínimo del GP (mediana -1.205, intervalo -1.413 a -1.086). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.6474, positiva).

**RUS**

- Estados Unidos, PC2, mínimo del GP (mediana -0.883, intervalo -1.084 a -0.734). La carga de mayor valor absoluto es `fast__full_throttle_frac` (0.9688, positiva).
- Gran Bretaña, PC3, máximo del GP (mediana 2.299, intervalo 2.035 a 2.780). La carga de mayor valor absoluto es `fast__full_throttle_frac` (0.5736, positiva).
- Gran Bretaña, PC5, mínimo del GP (mediana -0.899, intervalo -1.495 a -0.413). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.4884, positiva).
- Italia, PC5, mínimo del GP (mediana -0.765, intervalo -1.018 a -0.580). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.7340, positiva).
- Mónaco, PC3, mínimo del GP (mediana -0.919, intervalo -1.232 a -0.814). La carga de mayor valor absoluto es `fast__coast_frac` (0.5451, positiva).

**SAI**

- Baréin, PC1, máximo del GP (mediana 1.721, intervalo 1.649 a 1.811). La carga de mayor valor absoluto es `medium__full_throttle_frac` (0.9606, positiva).
- Bélgica, PC4, máximo del GP (mediana 1.027, intervalo 0.720 a 1.115). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.5169, positiva).
- Bélgica, PC5, máximo del GP (mediana 0.786, intervalo 0.420 a 1.030). La carga de mayor valor absoluto es `medium__brake_point_rel` (0.5468, positiva).
- Ciudad de México, PC2, máximo del GP (mediana 2.167, intervalo 1.846 a 2.359). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5012, positiva).
- Miami, PC1, mínimo del GP (mediana -1.578, intervalo -2.884 a -0.766). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.6696, positiva).
- São Paulo, PC1, máximo del GP (mediana 2.263, intervalo 1.802 a 2.453). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5066, positiva).

**STR**

- Austria, PC3, mínimo del GP (mediana -0.863, intervalo -1.273 a -0.651). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.4960, positiva).
- Baréin, PC2, máximo del GP (mediana 1.747, intervalo 1.616 a 1.798). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.5657, positiva).
- Baréin, PC5, mínimo del GP (mediana -1.399, intervalo -1.649 a -1.144). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.6194, positiva).
- Bélgica, PC3, mínimo del GP (mediana -1.275, intervalo -1.601 a -0.928). La carga de mayor valor absoluto es `slow__trail_brake_frac` (0.4775, positiva).
- Bélgica, PC4, mínimo del GP (mediana -1.334, intervalo -1.567 a -0.936). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.5169, positiva).
- Ciudad de México, PC2, mínimo del GP (mediana -2.028, intervalo -2.251 a -1.781). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5012, positiva).
- Ciudad de México, PC3, máximo del GP (mediana 2.128, intervalo 1.873 a 2.302). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.5965, positiva).
- Emilia-Romaña, PC2, máximo del GP (mediana 2.254, intervalo 2.003 a 2.596). La carga de mayor valor absoluto es `medium__coast_frac` (0.5250, positiva).
- Emilia-Romaña, PC4, mínimo del GP (mediana -1.052, intervalo -1.412 a -0.903). La carga de mayor valor absoluto es `fast__apex_speed_rel` (0.6936, positiva).
- Gran Bretaña, PC1, máximo del GP (mediana 4.307, intervalo 0.719 a 5.368). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.9139, positiva).
- Gran Bretaña, PC2, máximo del GP (mediana 3.138, intervalo 1.500 a 3.648). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.8631, positiva).
- Gran Bretaña, PC6, mínimo del GP (mediana -0.966, intervalo -1.587 a -0.627). La carga de mayor valor absoluto es `slow__throttle_attack` (0.5593, positiva).
- Hungría, PC2, máximo del GP (mediana 2.552, intervalo 2.165 a 2.731). La carga de mayor valor absoluto es `slow__coast_frac` (0.5313, positiva).
- Hungría, PC4, mínimo del GP (mediana -1.036, intervalo -1.271 a -0.745). La carga de mayor valor absoluto es `slow__throttle_attack` (0.5255, positiva).
- Italia, PC2, mínimo del GP (mediana -2.004, intervalo -2.310 a -1.779). La carga de mayor valor absoluto es `fast__trail_brake_frac` (0.4099, positiva).
- Japón, PC1, máximo del GP (mediana 2.479, intervalo 2.104 a 2.987). La carga de mayor valor absoluto es `fast__coast_frac` (0.5400, positiva).
- Japón, PC3, mínimo del GP (mediana -1.435, intervalo -1.763 a -1.136). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5124, positiva).
- Mónaco, PC1, máximo del GP (mediana 1.967, intervalo 1.595 a 2.148). La carga de mayor valor absoluto es `fast__coast_frac` (0.4748, positiva).
- Países Bajos, PC3, máximo del GP (mediana 1.374, intervalo 1.169 a 1.686). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.4188, positiva).
- São Paulo, PC1, mínimo del GP (mediana -2.881, intervalo -3.214 a -2.674). La carga de mayor valor absoluto es `medium__trail_brake_frac` (0.5066, positiva).

**TSU**

- Australia, PC3, máximo del GP (mediana 0.739, intervalo 0.337 a 1.098). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.5513, positiva).
- Ciudad de México, PC1, mínimo del GP (mediana 0.149, intervalo -4.737 a 0.364). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.9981, positiva).
- Gran Bretaña, PC2, mínimo del GP (mediana -3.528, intervalo -4.088 a -2.272). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.8631, positiva).
- Hungría, PC4, máximo del GP (mediana 0.773, intervalo 0.511 a 0.949). La carga de mayor valor absoluto es `slow__throttle_attack` (0.5255, positiva).
- Mónaco, PC3, máximo del GP (mediana 1.130, intervalo 0.841 a 1.310). La carga de mayor valor absoluto es `fast__coast_frac` (0.5451, positiva).
- Países Bajos, PC1, máximo del GP (mediana 0.950, intervalo 0.542 a 1.164). La carga de mayor valor absoluto es `slow__full_throttle_frac` (0.5612, positiva).

**VER**

- Arabia Saudita, PC3, máximo del GP (mediana 1.364, intervalo 1.169 a 1.494). La carga de mayor valor absoluto es `slow__apex_speed_rel` (0.5957, positiva).
- Catar, PC4, máximo del GP (mediana 1.106, intervalo 0.906 a 1.263). La carga de mayor valor absoluto es `slow__brake_point_rel` (0.5706, positiva).
- Emilia-Romaña, PC3, máximo del GP (mediana 1.779, intervalo 1.439 a 2.092). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5228, positiva).
- España, PC4, máximo del GP (mediana 1.154, intervalo 0.952 a 1.362). La carga de mayor valor absoluto es `medium__full_throttle_frac` (0.4696, positiva).
- Gran Bretaña, PC6, máximo del GP (mediana 0.509, intervalo 0.032 a 0.936). La carga de mayor valor absoluto es `slow__throttle_attack` (0.5593, positiva).
- Italia, PC2, máximo del GP (mediana 1.641, intervalo 1.239 a 1.796). La carga de mayor valor absoluto es `fast__trail_brake_frac` (0.4099, positiva).
- Miami, PC3, máximo del GP (mediana 0.748, intervalo 0.369 a 1.233). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.5658, positiva).
- Países Bajos, PC2, máximo del GP (mediana 1.681, intervalo 1.561 a 1.904). La carga de mayor valor absoluto es `medium__apex_speed_rel` (0.4512, positiva).

## Comparación con la corrida anterior

La corrida anterior está en `docs/temporada_2025.md`, `docs/season_2025/driver_summary.csv` y `docs/season_2025/archetype_by_race.csv`, y el perfil continuo en `docs/perfil_continuo_2025.md`. Esos archivos no se reescribieron. En esa corrida los 20 pilotos que llegan al piso de 8 carreras tienen la moda «No dominant trait».

| piloto | moda anterior | moda de esta corrida, todas las que dan clase | moda solo en carreras concluyentes |
| --- | --- | --- | --- |
| ALB | No dominant trait | No dominant trait | no llega a 8 |
| ALO | No dominant trait | No dominant trait | no llega a 8 |
| ANT | No dominant trait | No dominant trait | no llega a 8 |
| BEA | No dominant trait | No dominant trait | no llega a 8 |
| BOR | No dominant trait | No dominant trait | no llega a 8 |
| COL | No dominant trait | No dominant trait |  |
| DOO |  | no llega a 8 | no llega a 8 |
| GAS | No dominant trait | No dominant trait | no llega a 8 |
| HAD | No dominant trait | No dominant trait | no llega a 8 |
| HAM | No dominant trait | No dominant trait | no llega a 8 |
| HUL | No dominant trait | No dominant trait | no llega a 8 |
| LAW | No dominant trait | No dominant trait | no llega a 8 |
| LEC | No dominant trait | No dominant trait | no llega a 8 |
| NOR | No dominant trait | No dominant trait | no llega a 8 |
| OCO | No dominant trait | No dominant trait | no llega a 8 |
| PIA | No dominant trait | No dominant trait | no llega a 8 |
| RUS | No dominant trait | No dominant trait | no llega a 8 |
| SAI | No dominant trait | No dominant trait | no llega a 8 |
| STR | No dominant trait | No dominant trait | no llega a 8 |
| TSU | No dominant trait | No dominant trait | no llega a 8 |
| VER | No dominant trait | No dominant trait | no llega a 8 |

Pilotos que llegan al piso de 8 carreras con clase y cuya moda difiere de la anterior: 0.

El ARI compara las dos particiones de pilotos, en la intersección de quienes tienen clase en las dos corridas. El texto del arquetipo solo dice quién comparte clase dentro de una corrida. Las etiquetas de cada vuelta de la corrida anterior no están versionadas: `results/2025/italian_grand_prix/driver_laps_by_class.csv` trae conteos, no la clase de cada vuelta. Por eso el ARI de esta tabla es de pilotos, no de vueltas.

| carrera | pilotos en común | ARI | estructura en esta corrida | nota |
| --- | ---: | ---: | --- | --- |
| Australia | 0 |  | no | la tabla anterior no tiene esta carrera |
| China | 0 |  | no | la tabla anterior no tiene esta carrera |
| Japón | 20 | 0.000 | sí | etiquetas modales de piloto |
| Baréin | 2 | 0.000 | no | etiquetas modales de piloto |
| Arabia Saudita | 0 |  | no | la tabla anterior no tiene esta carrera |
| Miami | 7 | -0.235 | no | etiquetas modales de piloto |
| Emilia-Romaña | 0 |  | no | la tabla anterior no tiene esta carrera |
| Mónaco | 20 | 0.000 | no | etiquetas modales de piloto |
| España | 19 | 0.208 | no | etiquetas modales de piloto |
| Canadá | 5 | 0.167 | no | etiquetas modales de piloto |
| Austria | 17 | -0.062 | no | etiquetas modales de piloto |
| Gran Bretaña | 16 | 1.000 | no | etiquetas modales de piloto |
| Bélgica | 20 | 0.126 | no | etiquetas modales de piloto |
| Hungría | 0 |  | no | la tabla anterior no tiene esta carrera |
| Países Bajos | 20 | 0.454 | no | etiquetas modales de piloto |
| Italia | 19 | 0.000 | no | etiquetas modales de piloto |
| Azerbaiyán | 4 | 0.000 | no | etiquetas modales de piloto |
| Singapur | 0 |  | no | la tabla anterior no tiene esta carrera |
| Estados Unidos | 11 | 0.000 | no | etiquetas modales de piloto |
| Ciudad de México | 19 | 1.000 | no | etiquetas modales de piloto |
| São Paulo | 18 | 0.106 | no | etiquetas modales de piloto |
| Las Vegas | 5 | 0.000 | no | etiquetas modales de piloto |
| Catar | 20 | 1.000 | no | etiquetas modales de piloto |
| Abu Dabi | 6 | 1.000 | no | etiquetas modales de piloto |

ARI definido en 18 grandes premios. Mediana 0.053. Mínimo -0.235. Máximo 1.000.

## Predicciones a priori

Las reglas son las de `docs/temporada_2025.md` y `evaluate_baseline`. La matriz es la de la carrera suelta de Monza: conserva `fast__brake_point_rel`. (a) es Hamilton por debajo de Leclerc en `slow__brake_point_rel`, dentro de cada compuesto, en aire limpio. (b) es Leclerc por debajo de Hamilton en la mediana de la suelta de Lesmo 1, Lesmo 2 y la Parabólica. Se confirma si los intervalos no se tocan y la dirección es esa. Se contradice si no se tocan y la dirección es la opuesta. Si se tocan, no hay evidencia. Norris contra Piastri es exploratorio.

Vueltas de la matriz suelta: 867. Aire limpio: 179. Sin aire limpio: 16. Sin onset en la zona slow: 0. Sin vuelta en el lookup: 0.

**(a)**

| compuesto | piloto | n | mediana | intervalo |
| --- | --- | ---: | ---: | --- |
| MEDIUM | HAM | 31 | -0.68 | -5.69 a 3.63 |
| MEDIUM | LEC | 28 | -8.36 | -19.27 a -5.56 |
| MEDIUM | NOR | 43 | -11.95 | -15.95 a -3.84 |
| MEDIUM | PIA | 37 | 1.22 | -1.20 a 7.01 |
| HARD | HAM | 11 | 0.39 | -9.39 a 7.70 |
| HARD | LEC | 18 | -11.62 | -19.16 a -5.28 |
| SOFT | NOR | 5 | -16.87 | -20.75 a -5.56 |
| SOFT | PIA | 6 | 13.27 | 2.88 a 23.28 |

MEDIUM, el baseline: no hay evidencia.
MEDIUM, Norris contra Piastri: exploratorio; los intervalos no se tocan y NOR queda por debajo de PIA. No entra en el veredicto del baseline.
HARD, el baseline: no hay evidencia.
SOFT, Norris contra Piastri: exploratorio; los intervalos no se tocan y NOR queda por debajo de PIA. No entra en el veredicto del baseline.

**(b)**

| piloto | n con suelta | mediana | intervalo |
| --- | ---: | ---: | --- |
| LEC | 48 | 94.57 | 90.81 a 97.46 |
| HAM | 49 | 94.99 | 92.73 a 98.38 |
| NOR | 49 | 97.07 | 93.13 a 101.27 |
| PIA | 49 | 101.25 | 99.71 a 104.76 |

el baseline: no hay evidencia.
Norris contra Piastri: exploratorio; los intervalos se tocan. No entra en el veredicto del baseline.
Vueltas canónicas: HAM 49, LEC 48, NOR 49, PIA 49.

Tablas: `docs/clasificacion_pilotos_zoi_2025/por_gp.csv`, `clases_modales.csv`, `perfiles.csv`, `monza_bordes.csv`, `frecuencia_arquetipos.csv`, `extremos.csv`, `comparacion_modal.csv`, `ari_por_gp.csv`. El JSON de cada GP está en `docs/clasificacion_pilotos_zoi_2025/races/`.
