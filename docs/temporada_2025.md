# Temporada 2025 con la configuración por defecto

Comando: `python scripts/run_pipeline.py --season 2025`.

Arrancó el 2026-10-14 a las 18:31:20 UTC y terminó a las 19:01:27 UTC (30 min 7 s), con código de salida 0. El cache de FastF1 tenía solo el Italian Grand Prix; las otras 23 carreras se bajaron en esa corrida. FastF1 3.8.3. No se cambió K-means, RobustScaler, PCA automático, la regla de k ni las columnas del vector.

El calendario de 2025 tiene 24 carreras. 18 dejaron una clasificación. 6 no. La tendencia de temporada se escribió igual: es el nombre de clase más frecuente entre las carreras en las que el piloto aparece, con piso `min_races_season: 8`. No hay un segundo clustering.

Silueta y Davies-Bouldin de la tabla son los tres decimales que imprimió el pipeline. `n` es el de ese renglón.

## Carrera por carrera

| carrera | resultado | vueltas | pilotos | k | regla | silueta | Davies-Bouldin | zonas |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| Australia | no entra | 3 |  |  |  |  |  | fallback |
| China | no entra | 18 |  |  |  |  |  | fallback |
| Japón | entra | 837 | 20 | 2 | silhouette | 0.818 | 0.276 | fallback |
| Baréin | entra | 45 | 2 | 2 | silhouette | 0.570 | 0.913 | fallback |
| Arabia Saudita | no entra | 10 |  |  |  |  |  | fallback |
| Miami | entra | 46 | 7 | 6 | davies_bouldin | 0.190 | 1.298 | fallback |
| Emilia-Romaña | no entra |  |  |  |  |  |  | fallback |
| Mónaco | entra | 1013 | 20 | 2 | silhouette | 0.736 | 0.375 | key_corners |
| España | entra | 635 | 19 | 7 | davies_bouldin | 0.112 | 2.022 | fallback |
| Canadá | entra | 18 | 5 | 2 | davies_bouldin | 0.218 | 1.534 | fallback |
| Austria | entra | 980 | 17 | 2 | silhouette | 0.289 | 1.446 | fallback |
| Gran Bretaña | entra | 402 | 16 | 2 | silhouette | 0.434 | 1.013 | key_corners |
| Bélgica | entra | 367 | 20 | 5 | davies_bouldin | 0.101 | 2.122 | fallback |
| Hungría | no entra | 1253 |  |  |  |  |  | fallback |
| Países Bajos | entra | 964 | 20 | 3 | davies_bouldin | 0.161 | 1.888 | fallback |
| Italia | entra | 842 | 19 | 3 | davies_bouldin | 0.133 | 1.986 | key_corners |
| Azerbaiyán | entra | 21 | 4 | 2 | silhouette | 0.279 | 1.492 | fallback |
| Singapur | no entra | 3 |  |  |  |  |  | fallback |
| Estados Unidos | entra | 126 | 11 | 3 | davies_bouldin | 0.147 | 1.875 | fallback |
| Ciudad de México | entra | 940 | 19 | 2 | silhouette | 0.856 | 0.265 | fallback |
| São Paulo | entra | 451 | 18 | 4 | davies_bouldin | 0.123 | 1.888 | fallback |
| Las Vegas | entra | 48 | 5 | 4 | davies_bouldin | 0.201 | 1.466 | fallback |
| Catar | entra | 378 | 20 | 2 | silhouette | 0.843 | 0.351 | fallback |
| Abu Dabi | entra | 76 | 6 | 2 | silhouette | 0.254 | 1.491 | fallback |

Italia coincide con la corrida de Monza ya documentada: 842 vueltas, k=3 por Davies-Bouldin, silueta 0.133. Solo Italia, Gran Bretaña y Mónaco usan `key_corners`. El resto usa `_zones_from_speed_threshold_fallback`, con los 350 m / ±60 m / 250 m de `default_zoi_offsets`. La fracción de inicios de frenada en el borde de la ventana de 350 m se midió solo en Monza (issue #10, `docs/vector_por_zona_monza_2025.md`): 5.10 % de los inicios, concentrado en Lesmo 2. No se repitió esa cuenta en las otras carreras.

Varias siluetas del fallback son altas (Japón 0.818, México 0.856, Catar 0.843). No se les corrió el nulo de columnas. En Monza, el vector por zona también dio siluetas altas y quedó por debajo de ese nulo (`docs/vector_por_zona_monza_2025.md`). Una silueta alta en esta tabla no dice que la carrera se separe del nulo.

## Por qué seis carreras no entran

El mensaje del pipeline está en `docs/season_2025/per_race.csv`. Después de la corrida, con el cache ya escrito, se volvió a armar la matriz de cuatro de esas seis para ver qué columna vacía el `dropna`. China y Arabia Saudita no se reabrieron.

En Australia, Imola, Hungría y Singapur el fallback crea una zona por curva de FastF1 (11, 14, 13 y 14 zonas). La columna que falta es `brake_point_rel` de la tipología fast:

| carrera | vueltas en la tabla por tipología | fracción sin `fast` / `brake_point_rel` | vueltas con todas las columnas, antes del filtro de piloto |
| --- | ---: | ---: | ---: |
| Australia | 547 | 0.987 | 7 |
| Emilia-Romaña | 939 | 0.997 | 3 |
| Hungría | 1275 | 0.017 | 1253 |
| Singapur | 1106 | 0.997 | 3 |

Australia se quedó con n=3 después del mínimo de 3 vueltas por piloto, y ningún k de 2 a 7 armó clases de al menos 3. Singapur igual, con n=3. En Imola las 3 vueltas completas no alcanzaron para que un piloto tuviera 3, y la matriz salió vacía: el mensaje fue «No complete laps could be classified». China (n=18) y Arabia Saudita (n=10) fallaron por el mismo piso de tamaño; no medí qué columna les borró vueltas.

Hungría es el otro caso. Llegaron 1253 vueltas y 20 pilotos, con las 17 columnas. El PCA automático dejó 9 componentes y varianza 0.865. Con la semilla 42 y `n_init` 20, cada k de 2 a 7 deja una clase de 2 vueltas:

| k | tamaño mínimo | tamaños |
| --- | ---: | --- |
| 2 | 2 | 2, 1251 |
| 3 | 2 | 2, 606, 645 |
| 4 | 2 | 2, 33, 501, 717 |
| 5 | 2 | 2, 33, 216, 444, 558 |
| 6 | 2 | 2, 33, 123, 223, 368, 504 |
| 7 | 2 | 2, 33, 101, 152, 316, 320, 329 |

El piso de la sesión sería `ceil(0.05 × 1253) = 63`. El reintento del pipeline baja el piso a 3. Los dos rechazan todos los k, porque esa clase de 2 vueltas no se va. No se bajó el piso ni se sacó la clase para forzar un resultado.

## Tendencia modal

20 pilotos llegan al piso de 8 carreras. Los 20 salen con el nombre «No dominant trait». En la tabla piloto × GP hay 21 pilotos y 18 carreras (DOO solo aparece en Japón y no llega al piso). De 378 celdas, 248 tienen clase. 141 de esas 248 son «No dominant trait».

Carreras en las que todos los pilotos perfilados llevan ese único nombre: Japón (20), Mónaco (20), Azerbaiyán (4), México (19), Las Vegas (5) y Catar (20). Austria tiene 16 de 17 y Gran Bretaña 15 de 16. Italia tiene 19 pilotos y 3 nombres, ninguno es «No dominant trait». España, Canadá, Estados Unidos, São Paulo y Abu Dabi tampoco lo usan.

El acuerdo de cada piloto con su nombre modal está en `docs/season_2025/stability.csv`. Va de 0.47 (RUS, 15 carreras) a 0.75 (LEC, 12 carreras). El nombre modal es el mismo para todos, así que ese acuerdo mide cuántas carreras del piloto cayeron en «No dominant trait», no una coincidencia entre estilos distintos.

«No dominant trait» es el texto de `name_classes_from_medians` cuando ningún rasgo de la clase llega a 0.25 IQR. En Mónaco la silueta es 0.736 y k=2, y aun así los 20 perfiles modales reciben ese texto: la clase que concentra las vueltas de cada piloto no llegó al umbral de nombre.

Tablas: `docs/season_2025/archetype_by_race.csv`, `driver_summary.csv`, `driver_profiles.csv`, `stability.csv`. Las salidas crudas de cada GP quedaron en `results/2025/` y no se versionan, salvo `driver_laps_by_class.csv`, que el repo ya trata aparte. El cache tampoco se versiona.

## Predicciones a priori del baseline (2026-10-14)

Esta sección se escribió el 2026-10-14, antes de evaluar estas dos predicciones. No tiene los números de esa evaluación. No cambia el K-means, el RobustScaler, el PCA automático, la regla de k ni las columnas del vector.

Las dos predicciones son de Monza 2025 R. Lesmo 1, Lesmo 2 y la Parabólica están en esa carrera, y el baseline de Hamilton contra Leclerc que ya está en el repo también.

`slow__brake_point_rel` es la columna del vector de la carrera suelta, la que entra al escalador: mediana de sesión de la tipología, mediana del campo en la misma vuelta, y ajuste de compuesto y vida dentro del piloto. Un valor más chico es un inicio de frenada más cerca del ápice.

**(a)** En vueltas de aire limpio, y dentro de un mismo compuesto, la mediana de `slow__brake_point_rel` de Hamilton es menor que la de Leclerc.

Aire limpio, definido antes de medir: en la zona slow, el mínimo de `DistanceToDriverAhead` en los 150 m anteriores al onset. Si no hay un auto adelante, la vuelta es aire limpio. Si ese mínimo es menor que 50 m, no lo es. El corte de 50 m es el que el repo ya usa para tráfico. Una vuelta sin onset en la zona slow no entra. No se imputa la frenada y no se usa una columna `braked`.

El contraste se hace por compuesto, solo en los compuestos que los dos pilotos tienen. No se mezclan compuestos.

**(b)** Leclerc suelta el freno más cerca del ápice que Hamilton en Lesmo 1, Lesmo 2 y la Parabólica, como un solo diagnóstico. La distancia es la de la muestra en la que el freno pasa de puesto a suelto, medida hasta el ápice, en la ventana de frenada que el pipeline ya usa en cada una de esas tres curvas. Por vuelta se toma la mediana de las curvas que tienen suelta. Una curva sin suelta no se imputa y no entra en esa mediana. Si ninguna de las tres tiene suelta, la vuelta no entra. El veredicto es uno solo, sobre esa mediana, no tres tests.

El bootstrap es el mismo en (a) y en (b): 2000 remuestreos de las vueltas de cada piloto por separado, con reposición, semilla 42. El intervalo de cada piloto es el percentil 2.5 y el 97.5 de su mediana. Son dos intervalos. No es el intervalo de la diferencia.

Regla de lectura, fijada antes de ver los intervalos: se confirma si los dos intervalos no se tocan y la dirección es la de la predicción. Se contradice si no se tocan y la dirección es la opuesta. En cualquier otro caso no hay evidencia. Para (a) la dirección predicha es Hamilton entero por debajo de Leclerc. Para (b) es Leclerc entero por debajo de Hamilton.

Norris contra Piastri usa el mismo cálculo en (a) y en (b). Queda como exploratorio: no confirma ni contradice el baseline.

## Evaluación de esas predicciones

Esta sección se escribió después del texto de arriba, con la corrida `python scripts/monza_baseline_predictions.py` sobre Monza 2025 R. No cambia esas reglas. El vector es el de la carrera suelta, así que `slow__brake_point_rel` entra al escalador. La zona slow de Monza es la Variante del Rettifilo. De las vueltas de Hamilton, Leclerc, Norris y Piastri que están en esa matriz, 173 quedan en aire limpio y 16 no. Ninguna se fue por falta de onset en la zona slow.

**(a)** Cada intervalo es el percentil 2.5 y el 97.5 de la mediana del piloto, 2000 remuestreos con reposición, semilla 42, un generador por piloto. Un valor más chico sigue siendo un inicio más cerca del ápice.

| compuesto | piloto | n | mediana | intervalo |
| --- | --- | ---: | ---: | --- |
| MEDIUM | Hamilton | 30 | −0,78 | −6,28 a 3,82 |
| MEDIUM | Leclerc | 27 | −10,42 | −19,91 a −5,66 |
| HARD | Hamilton | 11 | 1,25 | −9,15 a 7,69 |
| HARD | Leclerc | 17 | −10,60 | −20,05 a −4,83 |

En MEDIUM el intervalo de Hamilton llega hasta 3,82 y el de Leclerc hasta −5,66: se pisan. En HARD el de Hamilton llega hasta −9,15 y el de Leclerc hasta −4,83: también se pisan. En los dos compuestos no hay evidencia. No comparten SOFT, así que ese compuesto no entra.

Norris contra Piastri, el mismo cálculo, sin lectura de baseline. En MEDIUM, Norris (n=43, mediana −12,03, intervalo −16,06 a −2,95) queda entero por debajo de Piastri (n=36, mediana 1,05, intervalo −1,50 a 4,09). En SOFT, Norris (n=4, mediana −17,31, intervalo −19,99 a −3,44) queda entero por debajo de Piastri (n=5, mediana 9,65, intervalo 3,02 a 23,48). No comparten HARD. Eso no confirma ni contradice el baseline.

**(b)** Distancia de la última suelta al ápice, en metros, mediana de Lesmo 1, Lesmo 2 y la Parabólica. Las tres curvas están en las ventanas del pipeline. Un valor más chico es una suelta más cerca del ápice.

| piloto | n con suelta | mediana | intervalo |
| --- | ---: | ---: | --- |
| Leclerc | 44 | 79,18 | 74,83 a 81,55 |
| Hamilton | 45 | 79,93 | 77,16 a 82,38 |

Los intervalos se pisan. No hay evidencia. De las vueltas canónicas, Hamilton tiene 49 y Leclerc 48; las que no entran no tienen suelta en ninguna de las tres curvas.

Norris (n=48, mediana 82,00, intervalo 78,06 a 85,51) y Piastri (n=48, mediana 85,19, intervalo 83,51 a 88,75) también se pisan. Sigue siendo exploratorio.

## Tres nulos y columnas degeneradas

Esta sección se escribió después de `python scripts/season_2025_triple_null.py`, con las 24 carreras de 2025. No cambia el K-means, el RobustScaler, el PCA automático, la regla de k ni las columnas del vector por defecto. `fast__brake_point_rel` está afuera en esta matriz de temporada. Cada nulo tiene 50 réplicas. Las semillas son 42, 43 y 44. Una elección de k con `select_k_rule_based` tarda cerca de un segundo, y 200 réplicas por tres nulos no terminan la temporada. El 50 quedó fijo antes de ver estos percentiles.

El estadístico de cada réplica es la silueta del k que elige esa regla. Al lado se guarda el máximo de los puntajes de nombre entre tipologías. El nombrador no cambió. Hay estructura solo si la silueta real es estrictamente mayor que el percentil 95 de la permutación por columna, del nulo gaussiano y de la cópula gaussiana. El percentil de la tabla es el porcentaje de réplicas finitas menores o iguales que la real. La columna de estructura usa esa comparación estricta, no el redondeo del percentil.

En la matriz de temporada hay estructura en 2 de 24 carreras: Bélgica e Italia. Hungría no elige k. Una silueta alta no alcanza: Japón tiene 0.859 y percentil 0 contra la permutación.

| carrera | vueltas | dropna | k | silueta | permutación | gaussiano | cópula | estructura |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Abu Dabi | 1033 | 11 | 2 | 0.739 | 100.0 | 100.0 | 92.0 | no |
| Arabia Saudita | 798 | 0 | 3 | 0.150 | 100.0 | 70.0 | 88.0 | no |
| Australia | 547 | 0 | 5 | 0.135 | 24.0 | 44.0 | 66.0 | no |
| Austria | 984 | 0 | 2 | 0.303 | 100.0 | 100.0 | 88.0 | no |
| Azerbaiyán | 796 | 0 | 3 | 0.774 | 8.0 | 100.0 | 38.0 | no |
| Baréin | 924 | 0 | 2 | 0.186 | 88.0 | 100.0 | 87.8 | no |
| Bélgica | 734 | 0 | 7 | 0.108 | 100.0 | 98.0 | 100.0 | sí |
| Canadá | 1095 | 59 | 2 | 0.751 | 100.0 | 100.0 | 72.0 | no |
| Catar | 902 | 2 | 2 | 0.824 | 28.0 | 100.0 | 40.0 | no |
| China | 410 | 532 | 2 | 0.602 | 64.0 | 100.0 | 62.0 | no |
| Ciudad de México | 940 | 162 | 2 | 0.856 | 78.0 | 100.0 | 75.5 | no |
| Emilia-Romaña | 939 | 0 | 2 | 0.668 | 56.0 | 100.0 | 52.0 | no |
| España | 980 | 0 | 4 | 0.138 | 6.0 | 100.0 | 100.0 | no |
| Estados Unidos | 897 | 1 | 2 | 0.411 | 18.0 | 100.0 | 8.0 | no |
| Gran Bretaña | 430 | 5 | 2 | 0.446 | 100.0 | 100.0 | 50.0 | no |
| Hungría | 1275 | 0 |  |  |  |  |  | no |
| Italia | 867 | 2 | 3 | 0.140 | 100.0 | 100.0 | 96.0 | sí |
| Japón | 989 | 0 | 2 | 0.859 | 0.0 | 100.0 | 28.0 | no |
| Las Vegas | 332 | 425 | 7 | 0.144 | 96.0 | 78.0 | 26.0 | no |
| Miami | 104 | 743 | 4 | 0.202 | 0.0 | 100.0 | 36.7 | no |
| Mónaco | 1165 | 0 | 5 | 0.180 | 98.0 | 100.0 | 68.0 | no |
| Países Bajos | 988 | 10 | 3 | 0.158 | 0.0 | 100.0 | 94.0 | no |
| Singapur | 1106 | 0 | 2 | 0.676 | 100.0 | 100.0 | 72.0 | no |
| São Paulo | 1030 | 2 | 5 | 0.118 | 100.0 | 54.0 | 28.0 | no |

Bélgica queda en k=7 por Davies-Bouldin, silueta 0.108, percentiles 100, 98 y 100. Italia, sin `fast__brake_point_rel`, queda en k=3 por Davies-Bouldin, silueta 0.140, percentiles 100, 100 y 96. En las dos la concordancia de compañeros, con `TeamName` de esa carrera, no supera el percentil 95 de la permutación: Bélgica 0.30 (percentil 70, 10 pares) e Italia 0.556 (percentil 36, 9 pares). En Bélgica, Colapinto y Gasly (Alpine) caen en la misma clase; Lawson y Hadjar (Racing Bulls) no; Tsunoda y Verstappen (Red Bull) no. En Italia, Colapinto y Gasly sí, Lawson y Hadjar sí, Tsunoda y Verstappen no. Esa concordancia no se lee en el resto de las carreras, porque no hay estructura.

La tasa de nombres falsos, con el máximo entre tipologías y el umbral 0.25, es alta bajo la permutación en casi toda la temporada. En varias carreras de k=2 queda en 0.50. En Bélgica, Emilia-Romaña y São Paulo llega a 1. El nombrador no se tocó.

### Sensibilidad sin columnas de IQR 0

Mismos tres nulos, mismas 50 réplicas, después de sacar las columnas con IQR 0. Gran Bretaña, Mónaco y Ciudad de México no tienen ninguna y no se rehicieron.

| carrera | columnas sacadas | k | silueta | permutación | gaussiano | cópula | estructura |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Abu Dabi | fast__trail_brake_frac | 2 | 0.739 | 100.0 | 100.0 | 96.0 | sí |
| Arabia Saudita | fast__trail_brake_frac | 3 | 0.150 | 100.0 | 70.0 | 88.0 | no |
| Australia | fast__coast_frac, fast__full_throttle_frac, medium__full_throttle_frac, fast__trail_brake_frac | 5 | 0.135 | 20.0 | 44.0 | 80.0 | no |
| Austria | fast__coast_frac, fast__trail_brake_frac | 2 | 0.303 | 100.0 | 100.0 | 86.0 | no |
| Azerbaiyán | fast__coast_frac, slow__full_throttle_frac, slow__throttle_attack, fast__trail_brake_frac | 2 | 0.697 | 100.0 | 100.0 | 54.0 | no |
| Baréin | fast__trail_brake_frac | 2 | 0.186 | 82.0 | 100.0 | 80.0 | no |
| Bélgica | fast__coast_frac, fast__full_throttle_frac, fast__trail_brake_frac | 7 | 0.108 | 100.0 | 98.0 | 100.0 | sí |
| Canadá | fast__coast_frac, fast__full_throttle_frac, slow__full_throttle_frac, slow__throttle_attack, fast__trail_brake_frac | 6 | 0.136 | 100.0 | 100.0 | 100.0 | sí |
| Catar | fast__coast_frac, fast__full_throttle_frac, slow__full_throttle_frac, slow__throttle_attack, fast__trail_brake_frac | 7 | 0.121 | 100.0 | 96.0 | 98.0 | sí |
| China | fast__coast_frac, medium__full_throttle_frac, medium__throttle_attack, fast__trail_brake_frac | 2 | 0.615 | 100.0 | 100.0 | 78.0 | no |
| Emilia-Romaña | fast__coast_frac, fast__full_throttle_frac, medium__full_throttle_frac, fast__trail_brake_frac | 2 | 0.668 | 78.0 | 100.0 | 54.0 | no |
| España | fast__full_throttle_frac, fast__trail_brake_frac | 4 | 0.138 | 4.0 | 100.0 | 100.0 | no |
| Estados Unidos | fast__trail_brake_frac | 2 | 0.411 | 14.0 | 100.0 | 12.0 | no |
| Hungría | fast__trail_brake_frac |  |  |  |  |  | no |
| Italia | fast__full_throttle_frac, medium__full_throttle_frac, medium__throttle_attack | 3 | 0.147 | 100.0 | 100.0 | 94.0 | no |
| Japón | fast__trail_brake_frac | 2 | 0.859 | 0.0 | 100.0 | 22.0 | no |
| Las Vegas | fast__coast_frac, medium__coast_frac, fast__full_throttle_frac, medium__full_throttle_frac, medium__throttle_attack, fast__trail_brake_frac | 7 | 0.144 | 98.0 | 78.0 | 30.0 | no |
| Miami | fast__trail_brake_frac, medium__trail_brake_frac | 4 | 0.202 | 0.0 | 100.0 | 22.0 | no |
| Países Bajos | fast__trail_brake_frac | 3 | 0.158 | 0.0 | 100.0 | 94.0 | no |
| Singapur | fast__coast_frac, fast__full_throttle_frac, medium__full_throttle_frac, medium__throttle_attack, fast__trail_brake_frac | 7 | 0.111 | 100.0 | 88.0 | 80.0 | no |
| São Paulo | fast__coast_frac, fast__full_throttle_frac, fast__trail_brake_frac, medium__trail_brake_frac | 5 | 0.118 | 100.0 | 52.0 | 24.0 | no |

Bélgica sigue con estructura. Italia deja de tenerla: la cópula baja a percentil 94 y su percentil 95 sube a 0.479, por encima de la silueta 0.147. Abu Dabi, Canadá y Catar pasan solo en esta sensibilidad. En Abu Dabi el k sigue en 2 y la silueta sigue en 0.739; sacar `fast__trail_brake_frac` mueve la cópula de 92 a 96. En Canadá el k pasa de 2 a 6 y la silueta de 0.751 a 0.136. En Catar el k pasa de 2 a 7 y la silueta de 0.824 a 0.121. Hungría sigue sin un k válido.

### Monza, con la columna y la referencia de ceros

La carrera suelta conserva `fast__brake_point_rel`. Son 842 vueltas, 17 columnas, k=3 por Davies-Bouldin, silueta 0.133. Percentiles: permutación 100, gaussiano 100, cópula 86. No hay estructura. Sin las tres columnas de IQR 0 (`fast__full_throttle_frac`, `medium__full_throttle_frac`, `medium__throttle_attack`) la silueta es 0.139 y los percentiles son 100, 100 y 92. Tampoco. La matriz de temporada, que saca la columna de frenada fast, es la fila Italia de arriba y sí pasa.

La referencia se parte en dos, porque restar la mediana de sesión convierte un 1 casi constante en un 0. Antes de esa mediana, en la mediana por tipología: `fast__coast_frac` tiene el 35.6 % en 0; `medium__throttle_attack` tiene el 95.1 % en un único valor, que es 0; `fast__full_throttle_frac` tiene el 99.8 % en 1; `medium__full_throttle_frac` tiene el 99.5 % en 1. En la matriz que entra al escalador, con la columna de frenada adentro, esos dos full throttle quedan en 0 en el 99.8 % y el 99.5 %, `medium__throttle_attack` sigue con el 95.1 % en un único valor, y `fast__coast_frac` ya no tiene el 35.6 % en 0.

### Fracción en 0 y en 1

Cada fila es una columna de la matriz que entra al escalador. `iqr0` marca IQR 0. En Ciudad de México no hay columnas `fast__`: el IQR de `fast__full_throttle_frac` no existe en esa matriz.

| carrera | columna | frac 0 | frac 1 | IQR | iqr0 |
| --- | --- | ---: | ---: | ---: | --- |
| Abu Dabi | `fast__apex_speed_rel` | 0.000 | 0.000 | 6.2196 | no |
| Abu Dabi | `medium__apex_speed_rel` | 0.000 | 0.000 | 5.9885 | no |
| Abu Dabi | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.6593 | no |
| Abu Dabi | `medium__brake_point_rel` | 0.000 | 0.000 | 17.3157 | no |
| Abu Dabi | `slow__brake_point_rel` | 0.000 | 0.000 | 12.6207 | no |
| Abu Dabi | `fast__coast_frac` | 0.000 | 0.000 | 0.0225 | no |
| Abu Dabi | `medium__coast_frac` | 0.000 | 0.000 | 0.0433 | no |
| Abu Dabi | `slow__coast_frac` | 0.000 | 0.000 | 0.0371 | no |
| Abu Dabi | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.0324 | no |
| Abu Dabi | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.3555 | no |
| Abu Dabi | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.1575 | no |
| Abu Dabi | `medium__throttle_attack` | 0.000 | 0.000 | 12.5071 | no |
| Abu Dabi | `slow__throttle_attack` | 0.000 | 0.000 | 12.3738 | no |
| Abu Dabi | `fast__trail_brake_frac` | 0.996 | 0.000 | 0.0000 | sí |
| Abu Dabi | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.1183 | no |
| Abu Dabi | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0830 | no |
| Arabia Saudita | `fast__apex_speed_rel` | 0.000 | 0.000 | 3.0538 | no |
| Arabia Saudita | `medium__apex_speed_rel` | 0.000 | 0.000 | 8.2865 | no |
| Arabia Saudita | `slow__apex_speed_rel` | 0.000 | 0.000 | 2.8779 | no |
| Arabia Saudita | `medium__brake_point_rel` | 0.000 | 0.000 | 20.9745 | no |
| Arabia Saudita | `slow__brake_point_rel` | 0.000 | 0.000 | 19.7207 | no |
| Arabia Saudita | `fast__coast_frac` | 0.000 | 0.000 | 0.0200 | no |
| Arabia Saudita | `medium__coast_frac` | 0.000 | 0.000 | 0.0278 | no |
| Arabia Saudita | `slow__coast_frac` | 0.000 | 0.000 | 0.0423 | no |
| Arabia Saudita | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.0391 | no |
| Arabia Saudita | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.0393 | no |
| Arabia Saudita | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0596 | no |
| Arabia Saudita | `medium__throttle_attack` | 0.000 | 0.000 | 9.5330 | no |
| Arabia Saudita | `slow__throttle_attack` | 0.000 | 0.000 | 7.3809 | no |
| Arabia Saudita | `fast__trail_brake_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Arabia Saudita | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.0817 | no |
| Arabia Saudita | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.1424 | no |
| Australia | `fast__apex_speed_rel` | 0.000 | 0.000 | 4.1569 | no |
| Australia | `medium__apex_speed_rel` | 0.000 | 0.000 | 7.1421 | no |
| Australia | `slow__apex_speed_rel` | 0.000 | 0.000 | 4.0855 | no |
| Australia | `medium__brake_point_rel` | 0.000 | 0.000 | 18.6073 | no |
| Australia | `slow__brake_point_rel` | 0.000 | 0.000 | 21.8057 | no |
| Australia | `fast__coast_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Australia | `medium__coast_frac` | 0.000 | 0.000 | 0.0227 | no |
| Australia | `slow__coast_frac` | 0.000 | 0.000 | 0.0173 | no |
| Australia | `fast__full_throttle_frac` | 0.987 | 0.000 | 0.0000 | sí |
| Australia | `medium__full_throttle_frac` | 0.731 | 0.000 | 0.0000 | sí |
| Australia | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0240 | no |
| Australia | `medium__throttle_attack` | 0.000 | 0.000 | 5.3837 | no |
| Australia | `slow__throttle_attack` | 0.000 | 0.000 | 6.0246 | no |
| Australia | `fast__trail_brake_frac` | 0.995 | 0.004 | 0.0000 | sí |
| Australia | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.0888 | no |
| Australia | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0906 | no |
| Austria | `fast__apex_speed_rel` | 0.000 | 0.000 | 5.1337 | no |
| Austria | `medium__apex_speed_rel` | 0.000 | 0.000 | 5.3037 | no |
| Austria | `slow__apex_speed_rel` | 0.000 | 0.000 | 4.3980 | no |
| Austria | `medium__brake_point_rel` | 0.000 | 0.000 | 16.3543 | no |
| Austria | `slow__brake_point_rel` | 0.000 | 0.000 | 14.3780 | no |
| Austria | `fast__coast_frac` | 0.993 | 0.000 | 0.0000 | sí |
| Austria | `medium__coast_frac` | 0.000 | 0.000 | 0.0352 | no |
| Austria | `slow__coast_frac` | 0.000 | 0.000 | 0.0350 | no |
| Austria | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.1438 | no |
| Austria | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.0431 | no |
| Austria | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0739 | no |
| Austria | `medium__throttle_attack` | 0.000 | 0.000 | 9.9761 | no |
| Austria | `slow__throttle_attack` | 0.000 | 0.000 | 9.1179 | no |
| Austria | `fast__trail_brake_frac` | 0.999 | 0.000 | 0.0000 | sí |
| Austria | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.1548 | no |
| Austria | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0776 | no |
| Azerbaiyán | `fast__apex_speed_rel` | 0.000 | 0.000 | 2.8048 | no |
| Azerbaiyán | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.0484 | no |
| Azerbaiyán | `slow__brake_point_rel` | 0.000 | 0.000 | 12.0348 | no |
| Azerbaiyán | `fast__coast_frac` | 0.987 | 0.000 | 0.0000 | sí |
| Azerbaiyán | `slow__coast_frac` | 0.000 | 0.000 | 0.0197 | no |
| Azerbaiyán | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.0165 | no |
| Azerbaiyán | `slow__full_throttle_frac` | 0.873 | 0.000 | 0.0000 | sí |
| Azerbaiyán | `slow__throttle_attack` | 0.784 | 0.000 | 0.0000 | sí |
| Azerbaiyán | `fast__trail_brake_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Azerbaiyán | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0902 | no |
| Baréin | `fast__apex_speed_rel` | 0.000 | 0.000 | 8.4320 | no |
| Baréin | `medium__apex_speed_rel` | 0.000 | 0.000 | 6.8777 | no |
| Baréin | `slow__apex_speed_rel` | 0.000 | 0.000 | 4.3064 | no |
| Baréin | `medium__brake_point_rel` | 0.000 | 0.000 | 17.9690 | no |
| Baréin | `slow__brake_point_rel` | 0.000 | 0.000 | 11.6119 | no |
| Baréin | `fast__coast_frac` | 0.000 | 0.000 | 0.0213 | no |
| Baréin | `medium__coast_frac` | 0.000 | 0.000 | 0.0351 | no |
| Baréin | `slow__coast_frac` | 0.000 | 0.000 | 0.0298 | no |
| Baréin | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.0386 | no |
| Baréin | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.1494 | no |
| Baréin | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0914 | no |
| Baréin | `medium__throttle_attack` | 0.000 | 0.000 | 11.2553 | no |
| Baréin | `slow__throttle_attack` | 0.000 | 0.000 | 10.8967 | no |
| Baréin | `fast__trail_brake_frac` | 0.984 | 0.001 | 0.0000 | sí |
| Baréin | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.0651 | no |
| Baréin | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.1201 | no |
| Bélgica | `fast__apex_speed_rel` | 0.000 | 0.000 | 3.4440 | no |
| Bélgica | `medium__apex_speed_rel` | 0.000 | 0.000 | 4.9456 | no |
| Bélgica | `slow__apex_speed_rel` | 0.000 | 0.000 | 2.7250 | no |
| Bélgica | `medium__brake_point_rel` | 0.000 | 0.000 | 18.9714 | no |
| Bélgica | `slow__brake_point_rel` | 0.000 | 0.000 | 15.8501 | no |
| Bélgica | `fast__coast_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Bélgica | `medium__coast_frac` | 0.000 | 0.000 | 0.0281 | no |
| Bélgica | `slow__coast_frac` | 0.000 | 0.000 | 0.0359 | no |
| Bélgica | `fast__full_throttle_frac` | 0.997 | 0.000 | 0.0000 | sí |
| Bélgica | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.1129 | no |
| Bélgica | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0741 | no |
| Bélgica | `medium__throttle_attack` | 0.000 | 0.000 | 11.7915 | no |
| Bélgica | `slow__throttle_attack` | 0.000 | 0.000 | 8.1478 | no |
| Bélgica | `fast__trail_brake_frac` | 0.971 | 0.000 | 0.0000 | sí |
| Bélgica | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.1353 | no |
| Bélgica | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.1208 | no |
| Canadá | `fast__apex_speed_rel` | 0.000 | 0.000 | 3.3349 | no |
| Canadá | `medium__apex_speed_rel` | 0.000 | 0.000 | 5.7717 | no |
| Canadá | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.4409 | no |
| Canadá | `medium__brake_point_rel` | 0.000 | 0.000 | 14.2170 | no |
| Canadá | `slow__brake_point_rel` | 0.000 | 0.000 | 14.3198 | no |
| Canadá | `fast__coast_frac` | 0.997 | 0.000 | 0.0000 | sí |
| Canadá | `medium__coast_frac` | 0.000 | 0.000 | 0.0236 | no |
| Canadá | `slow__coast_frac` | 0.000 | 0.000 | 0.0352 | no |
| Canadá | `fast__full_throttle_frac` | 0.995 | 0.000 | 0.0000 | sí |
| Canadá | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.0434 | no |
| Canadá | `slow__full_throttle_frac` | 0.900 | 0.000 | 0.0000 | sí |
| Canadá | `medium__throttle_attack` | 0.000 | 0.000 | 6.7395 | no |
| Canadá | `slow__throttle_attack` | 0.856 | 0.000 | 0.0000 | sí |
| Canadá | `fast__trail_brake_frac` | 0.999 | 0.000 | 0.0000 | sí |
| Canadá | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.0634 | no |
| Canadá | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0592 | no |
| Catar | `fast__apex_speed_rel` | 0.000 | 0.000 | 7.0575 | no |
| Catar | `medium__apex_speed_rel` | 0.000 | 0.000 | 5.2512 | no |
| Catar | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.0347 | no |
| Catar | `medium__brake_point_rel` | 0.000 | 0.000 | 8.6515 | no |
| Catar | `slow__brake_point_rel` | 0.000 | 0.000 | 12.4713 | no |
| Catar | `fast__coast_frac` | 0.847 | 0.000 | 0.0000 | sí |
| Catar | `medium__coast_frac` | 0.000 | 0.000 | 0.0267 | no |
| Catar | `slow__coast_frac` | 0.000 | 0.000 | 0.0294 | no |
| Catar | `fast__full_throttle_frac` | 0.829 | 0.000 | 0.0000 | sí |
| Catar | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.2048 | no |
| Catar | `slow__full_throttle_frac` | 0.884 | 0.000 | 0.0000 | sí |
| Catar | `medium__throttle_attack` | 0.000 | 0.000 | 11.5265 | no |
| Catar | `slow__throttle_attack` | 0.775 | 0.000 | 0.0000 | sí |
| Catar | `fast__trail_brake_frac` | 0.927 | 0.000 | 0.0000 | sí |
| Catar | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.1071 | no |
| Catar | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0959 | no |
| China | `fast__apex_speed_rel` | 0.000 | 0.000 | 5.2515 | no |
| China | `medium__apex_speed_rel` | 0.000 | 0.000 | 6.1635 | no |
| China | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.1447 | no |
| China | `medium__brake_point_rel` | 0.000 | 0.000 | 17.0511 | no |
| China | `slow__brake_point_rel` | 0.000 | 0.000 | 11.7380 | no |
| China | `fast__coast_frac` | 0.880 | 0.000 | 0.0000 | sí |
| China | `medium__coast_frac` | 0.000 | 0.000 | 0.0259 | no |
| China | `slow__coast_frac` | 0.000 | 0.000 | 0.0304 | no |
| China | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.6030 | no |
| China | `medium__full_throttle_frac` | 0.971 | 0.000 | 0.0000 | sí |
| China | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0231 | no |
| China | `medium__throttle_attack` | 0.988 | 0.000 | 0.0000 | sí |
| China | `slow__throttle_attack` | 0.000 | 0.000 | 2.7646 | no |
| China | `fast__trail_brake_frac` | 0.985 | 0.000 | 0.0000 | sí |
| China | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.1728 | no |
| China | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0714 | no |
| Ciudad de México | `medium__apex_speed_rel` | 0.000 | 0.000 | 4.1051 | no |
| Ciudad de México | `slow__apex_speed_rel` | 0.000 | 0.000 | 2.7079 | no |
| Ciudad de México | `medium__brake_point_rel` | 0.000 | 0.000 | 10.3596 | no |
| Ciudad de México | `slow__brake_point_rel` | 0.000 | 0.000 | 25.3919 | no |
| Ciudad de México | `medium__coast_frac` | 0.000 | 0.000 | 0.0219 | no |
| Ciudad de México | `slow__coast_frac` | 0.000 | 0.000 | 0.0224 | no |
| Ciudad de México | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.0183 | no |
| Ciudad de México | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.1000 | no |
| Ciudad de México | `medium__throttle_attack` | 0.000 | 0.000 | 2.8538 | no |
| Ciudad de México | `slow__throttle_attack` | 0.000 | 0.000 | 9.4838 | no |
| Ciudad de México | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.0570 | no |
| Ciudad de México | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0688 | no |
| Emilia-Romaña | `fast__apex_speed_rel` | 0.000 | 0.000 | 2.7164 | no |
| Emilia-Romaña | `medium__apex_speed_rel` | 0.000 | 0.000 | 8.7154 | no |
| Emilia-Romaña | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.0953 | no |
| Emilia-Romaña | `medium__brake_point_rel` | 0.000 | 0.000 | 19.1652 | no |
| Emilia-Romaña | `slow__brake_point_rel` | 0.000 | 0.000 | 14.1394 | no |
| Emilia-Romaña | `fast__coast_frac` | 0.999 | 0.000 | 0.0000 | sí |
| Emilia-Romaña | `medium__coast_frac` | 0.000 | 0.000 | 0.0308 | no |
| Emilia-Romaña | `slow__coast_frac` | 0.000 | 0.000 | 0.0340 | no |
| Emilia-Romaña | `fast__full_throttle_frac` | 0.972 | 0.000 | 0.0000 | sí |
| Emilia-Romaña | `medium__full_throttle_frac` | 0.774 | 0.000 | 0.0000 | sí |
| Emilia-Romaña | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0282 | no |
| Emilia-Romaña | `medium__throttle_attack` | 0.000 | 0.000 | 1.6934 | no |
| Emilia-Romaña | `slow__throttle_attack` | 0.000 | 0.000 | 5.4831 | no |
| Emilia-Romaña | `fast__trail_brake_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Emilia-Romaña | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.1464 | no |
| Emilia-Romaña | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0826 | no |
| España | `fast__apex_speed_rel` | 0.000 | 0.000 | 3.6632 | no |
| España | `medium__apex_speed_rel` | 0.000 | 0.000 | 4.6637 | no |
| España | `slow__apex_speed_rel` | 0.000 | 0.000 | 4.6889 | no |
| España | `medium__brake_point_rel` | 0.000 | 0.000 | 15.3316 | no |
| España | `slow__brake_point_rel` | 0.000 | 0.000 | 9.9603 | no |
| España | `fast__coast_frac` | 0.000 | 0.000 | 0.0241 | no |
| España | `medium__coast_frac` | 0.000 | 0.000 | 0.0268 | no |
| España | `slow__coast_frac` | 0.000 | 0.000 | 0.0223 | no |
| España | `fast__full_throttle_frac` | 0.841 | 0.000 | 0.0000 | sí |
| España | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.1416 | no |
| España | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0421 | no |
| España | `medium__throttle_attack` | 0.000 | 0.000 | 6.6233 | no |
| España | `slow__throttle_attack` | 0.000 | 0.000 | 6.1732 | no |
| España | `fast__trail_brake_frac` | 0.893 | 0.000 | 0.0000 | sí |
| España | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.0657 | no |
| España | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.1386 | no |
| Estados Unidos | `fast__apex_speed_rel` | 0.000 | 0.000 | 4.0377 | no |
| Estados Unidos | `medium__apex_speed_rel` | 0.000 | 0.000 | 5.6532 | no |
| Estados Unidos | `slow__apex_speed_rel` | 0.000 | 0.000 | 2.7256 | no |
| Estados Unidos | `medium__brake_point_rel` | 0.000 | 0.000 | 12.9601 | no |
| Estados Unidos | `slow__brake_point_rel` | 0.000 | 0.000 | 9.0483 | no |
| Estados Unidos | `fast__coast_frac` | 0.000 | 0.000 | 0.0362 | no |
| Estados Unidos | `medium__coast_frac` | 0.000 | 0.000 | 0.0228 | no |
| Estados Unidos | `slow__coast_frac` | 0.000 | 0.000 | 0.0282 | no |
| Estados Unidos | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.0364 | no |
| Estados Unidos | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.0313 | no |
| Estados Unidos | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.1093 | no |
| Estados Unidos | `medium__throttle_attack` | 0.000 | 0.000 | 5.2752 | no |
| Estados Unidos | `slow__throttle_attack` | 0.000 | 0.000 | 7.8683 | no |
| Estados Unidos | `fast__trail_brake_frac` | 0.986 | 0.000 | 0.0000 | sí |
| Estados Unidos | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.1240 | no |
| Estados Unidos | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.1095 | no |
| Gran Bretaña | `fast__apex_speed_rel` | 0.000 | 0.000 | 6.7932 | no |
| Gran Bretaña | `medium__apex_speed_rel` | 0.000 | 0.000 | 8.7674 | no |
| Gran Bretaña | `slow__apex_speed_rel` | 0.000 | 0.000 | 4.0785 | no |
| Gran Bretaña | `medium__brake_point_rel` | 0.000 | 0.000 | 22.6981 | no |
| Gran Bretaña | `slow__brake_point_rel` | 0.000 | 0.000 | 21.4867 | no |
| Gran Bretaña | `fast__coast_frac` | 0.000 | 0.000 | 0.0294 | no |
| Gran Bretaña | `medium__coast_frac` | 0.000 | 0.000 | 0.0370 | no |
| Gran Bretaña | `slow__coast_frac` | 0.000 | 0.000 | 0.0262 | no |
| Gran Bretaña | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.0471 | no |
| Gran Bretaña | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.1164 | no |
| Gran Bretaña | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.1007 | no |
| Gran Bretaña | `medium__throttle_attack` | 0.000 | 0.000 | 12.2416 | no |
| Gran Bretaña | `slow__throttle_attack` | 0.000 | 0.000 | 10.0207 | no |
| Gran Bretaña | `fast__trail_brake_frac` | 0.000 | 0.000 | 0.1486 | no |
| Gran Bretaña | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.2958 | no |
| Gran Bretaña | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0540 | no |
| Hungría | `fast__apex_speed_rel` | 0.000 | 0.000 | 7.2800 | no |
| Hungría | `medium__apex_speed_rel` | 0.000 | 0.000 | 6.1377 | no |
| Hungría | `slow__apex_speed_rel` | 0.000 | 0.000 | 4.2930 | no |
| Hungría | `medium__brake_point_rel` | 0.000 | 0.000 | 16.4019 | no |
| Hungría | `slow__brake_point_rel` | 0.000 | 0.000 | 10.8467 | no |
| Hungría | `fast__coast_frac` | 0.000 | 0.000 | 0.0442 | no |
| Hungría | `medium__coast_frac` | 0.000 | 0.000 | 0.0285 | no |
| Hungría | `slow__coast_frac` | 0.000 | 0.000 | 0.0277 | no |
| Hungría | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.0151 | no |
| Hungría | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.0355 | no |
| Hungría | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0305 | no |
| Hungría | `medium__throttle_attack` | 0.000 | 0.000 | 9.7805 | no |
| Hungría | `slow__throttle_attack` | 0.000 | 0.000 | 7.3703 | no |
| Hungría | `fast__trail_brake_frac` | 0.756 | 0.001 | 0.0000 | sí |
| Hungría | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.1189 | no |
| Hungría | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0965 | no |
| Italia | `fast__apex_speed_rel` | 0.000 | 0.000 | 3.9226 | no |
| Italia | `medium__apex_speed_rel` | 0.000 | 0.000 | 7.1696 | no |
| Italia | `slow__apex_speed_rel` | 0.000 | 0.000 | 2.8936 | no |
| Italia | `medium__brake_point_rel` | 0.000 | 0.000 | 12.5680 | no |
| Italia | `slow__brake_point_rel` | 0.000 | 0.000 | 22.7150 | no |
| Italia | `fast__coast_frac` | 0.000 | 0.000 | 0.0165 | no |
| Italia | `medium__coast_frac` | 0.000 | 0.000 | 0.0388 | no |
| Italia | `slow__coast_frac` | 0.000 | 0.000 | 0.0510 | no |
| Italia | `fast__full_throttle_frac` | 0.998 | 0.000 | 0.0000 | sí |
| Italia | `medium__full_throttle_frac` | 0.995 | 0.000 | 0.0000 | sí |
| Italia | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0643 | no |
| Italia | `medium__throttle_attack` | 0.950 | 0.000 | 0.0000 | sí |
| Italia | `slow__throttle_attack` | 0.000 | 0.000 | 12.2397 | no |
| Italia | `fast__trail_brake_frac` | 0.000 | 0.000 | 0.0234 | no |
| Italia | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.1072 | no |
| Italia | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0677 | no |
| Japón | `fast__apex_speed_rel` | 0.000 | 0.000 | 6.0711 | no |
| Japón | `medium__apex_speed_rel` | 0.000 | 0.000 | 5.9743 | no |
| Japón | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.2145 | no |
| Japón | `medium__brake_point_rel` | 0.000 | 0.000 | 15.3643 | no |
| Japón | `slow__brake_point_rel` | 0.000 | 0.000 | 12.9141 | no |
| Japón | `fast__coast_frac` | 0.000 | 0.000 | 0.0237 | no |
| Japón | `medium__coast_frac` | 0.000 | 0.000 | 0.0355 | no |
| Japón | `slow__coast_frac` | 0.000 | 0.000 | 0.0687 | no |
| Japón | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.0296 | no |
| Japón | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.1288 | no |
| Japón | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0195 | no |
| Japón | `medium__throttle_attack` | 0.000 | 0.000 | 11.1978 | no |
| Japón | `slow__throttle_attack` | 0.000 | 0.000 | 5.7896 | no |
| Japón | `fast__trail_brake_frac` | 0.858 | 0.000 | 0.0000 | sí |
| Japón | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.2455 | no |
| Japón | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0670 | no |
| Las Vegas | `fast__apex_speed_rel` | 0.000 | 0.000 | 4.9945 | no |
| Las Vegas | `medium__apex_speed_rel` | 0.000 | 0.000 | 7.0568 | no |
| Las Vegas | `slow__apex_speed_rel` | 0.000 | 0.000 | 2.6784 | no |
| Las Vegas | `medium__brake_point_rel` | 0.000 | 0.000 | 19.1424 | no |
| Las Vegas | `slow__brake_point_rel` | 0.000 | 0.000 | 13.3171 | no |
| Las Vegas | `fast__coast_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Las Vegas | `medium__coast_frac` | 0.901 | 0.000 | 0.0000 | sí |
| Las Vegas | `slow__coast_frac` | 0.000 | 0.000 | 0.0144 | no |
| Las Vegas | `fast__full_throttle_frac` | 0.964 | 0.000 | 0.0000 | sí |
| Las Vegas | `medium__full_throttle_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Las Vegas | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0527 | no |
| Las Vegas | `medium__throttle_attack` | 1.000 | 0.000 | 0.0000 | sí |
| Las Vegas | `slow__throttle_attack` | 0.000 | 0.000 | 8.1850 | no |
| Las Vegas | `fast__trail_brake_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Las Vegas | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.0651 | no |
| Las Vegas | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0640 | no |
| Miami | `fast__apex_speed_rel` | 0.000 | 0.000 | 3.7268 | no |
| Miami | `medium__apex_speed_rel` | 0.000 | 0.000 | 9.1931 | no |
| Miami | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.3804 | no |
| Miami | `medium__brake_point_rel` | 0.000 | 0.000 | 5.2818 | no |
| Miami | `slow__brake_point_rel` | 0.000 | 0.000 | 9.2341 | no |
| Miami | `fast__coast_frac` | 0.000 | 0.000 | 0.0120 | no |
| Miami | `medium__coast_frac` | 0.000 | 0.000 | 0.0246 | no |
| Miami | `slow__coast_frac` | 0.000 | 0.000 | 0.0267 | no |
| Miami | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.0457 | no |
| Miami | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.0168 | no |
| Miami | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0196 | no |
| Miami | `medium__throttle_attack` | 0.000 | 0.000 | 4.6791 | no |
| Miami | `slow__throttle_attack` | 0.000 | 0.000 | 6.2329 | no |
| Miami | `fast__trail_brake_frac` | 0.846 | 0.000 | 0.0000 | sí |
| Miami | `medium__trail_brake_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Miami | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0813 | no |
| Mónaco | `fast__apex_speed_rel` | 0.000 | 0.000 | 6.4369 | no |
| Mónaco | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.1345 | no |
| Mónaco | `slow__brake_point_rel` | 0.000 | 0.000 | 23.3260 | no |
| Mónaco | `fast__coast_frac` | 0.000 | 0.000 | 0.0458 | no |
| Mónaco | `slow__coast_frac` | 0.000 | 0.000 | 0.0591 | no |
| Mónaco | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.1261 | no |
| Mónaco | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.1289 | no |
| Mónaco | `slow__throttle_attack` | 0.000 | 0.000 | 8.9625 | no |
| Mónaco | `fast__trail_brake_frac` | 0.000 | 0.000 | 0.1253 | no |
| Mónaco | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0527 | no |
| Países Bajos | `fast__apex_speed_rel` | 0.000 | 0.000 | 4.5432 | no |
| Países Bajos | `medium__apex_speed_rel` | 0.000 | 0.000 | 7.2671 | no |
| Países Bajos | `slow__apex_speed_rel` | 0.000 | 0.000 | 5.4932 | no |
| Países Bajos | `medium__brake_point_rel` | 0.000 | 0.000 | 9.9891 | no |
| Países Bajos | `slow__brake_point_rel` | 0.000 | 0.000 | 11.3281 | no |
| Países Bajos | `fast__coast_frac` | 0.000 | 0.000 | 0.0456 | no |
| Países Bajos | `medium__coast_frac` | 0.000 | 0.000 | 0.0573 | no |
| Países Bajos | `slow__coast_frac` | 0.000 | 0.000 | 0.0409 | no |
| Países Bajos | `fast__full_throttle_frac` | 0.000 | 0.000 | 0.2398 | no |
| Países Bajos | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.1623 | no |
| Países Bajos | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.2923 | no |
| Países Bajos | `medium__throttle_attack` | 0.000 | 0.000 | 4.9865 | no |
| Países Bajos | `slow__throttle_attack` | 0.000 | 0.000 | 8.0113 | no |
| Países Bajos | `fast__trail_brake_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Países Bajos | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.1188 | no |
| Países Bajos | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0871 | no |
| Singapur | `fast__apex_speed_rel` | 0.000 | 0.000 | 5.2362 | no |
| Singapur | `medium__apex_speed_rel` | 0.000 | 0.000 | 5.4651 | no |
| Singapur | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.5634 | no |
| Singapur | `medium__brake_point_rel` | 0.000 | 0.000 | 10.9473 | no |
| Singapur | `slow__brake_point_rel` | 0.000 | 0.000 | 11.3275 | no |
| Singapur | `fast__coast_frac` | 0.997 | 0.000 | 0.0000 | sí |
| Singapur | `medium__coast_frac` | 0.000 | 0.000 | 0.0251 | no |
| Singapur | `slow__coast_frac` | 0.000 | 0.000 | 0.0247 | no |
| Singapur | `fast__full_throttle_frac` | 0.990 | 0.000 | 0.0000 | sí |
| Singapur | `medium__full_throttle_frac` | 0.874 | 0.000 | 0.0000 | sí |
| Singapur | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.1311 | no |
| Singapur | `medium__throttle_attack` | 0.839 | 0.000 | 0.0000 | sí |
| Singapur | `slow__throttle_attack` | 0.000 | 0.000 | 12.4949 | no |
| Singapur | `fast__trail_brake_frac` | 1.000 | 0.000 | 0.0000 | sí |
| Singapur | `medium__trail_brake_frac` | 0.000 | 0.000 | 0.0780 | no |
| Singapur | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0824 | no |
| São Paulo | `fast__apex_speed_rel` | 0.000 | 0.000 | 4.3776 | no |
| São Paulo | `medium__apex_speed_rel` | 0.000 | 0.000 | 6.3870 | no |
| São Paulo | `slow__apex_speed_rel` | 0.000 | 0.000 | 3.6335 | no |
| São Paulo | `medium__brake_point_rel` | 0.000 | 0.000 | 27.5642 | no |
| São Paulo | `slow__brake_point_rel` | 0.000 | 0.000 | 8.8612 | no |
| São Paulo | `fast__coast_frac` | 1.000 | 0.000 | 0.0000 | sí |
| São Paulo | `medium__coast_frac` | 0.000 | 0.000 | 0.0183 | no |
| São Paulo | `slow__coast_frac` | 0.000 | 0.000 | 0.0180 | no |
| São Paulo | `fast__full_throttle_frac` | 0.999 | 0.000 | 0.0000 | sí |
| São Paulo | `medium__full_throttle_frac` | 0.000 | 0.000 | 0.0285 | no |
| São Paulo | `slow__full_throttle_frac` | 0.000 | 0.000 | 0.0274 | no |
| São Paulo | `medium__throttle_attack` | 0.000 | 0.000 | 5.3427 | no |
| São Paulo | `slow__throttle_attack` | 0.000 | 0.000 | 5.7317 | no |
| São Paulo | `fast__trail_brake_frac` | 1.000 | 0.000 | 0.0000 | sí |
| São Paulo | `medium__trail_brake_frac` | 0.970 | 0.000 | 0.0000 | sí |
| São Paulo | `slow__trail_brake_frac` | 0.000 | 0.000 | 0.0855 | no |

### Vueltas que saca el dropna

El contraste es el de antes del filtro de piloto. Compuesto, vida de neumático y posición no se separan de forma grosera en las carreras que más vueltas pierden. Miami pierde 743 de 857, China 532 de 942, Las Vegas 425 de 760, Ciudad de México 162 de 1102 y Canadá 59 de 1154. En China la vida mediana es 13 en las que quedan y 15 en las que salen, y la posición mediana es 10 y 9.5. En Las Vegas, 13 y 16, y la posición 10 y 8. El resto de las carreras pierde 11 vueltas o menos. Australia, con la columna afuera, no pierde ninguna y se queda con 547.

### Hungría

Con `fast__brake_point_rel` adentro, 1253 vueltas y 17 columnas, la clase mínima de k=2 a k=7 es exactamente Colapinto vuelta 38 y Gasly vuelta 59. El IQR de `fast__full_throttle_frac` en esa matriz es 0.0149. El z robusto de esas dos vueltas en esa columna es 36.8 y 36.2. El percentil 99 del máximo |z| de la vuelta es 10.6 y no se usó como umbral.

Colapinto 38 no es bandera, ni boxes, ni hueco de telemetría, ni tráfico: el auto más cercano al final de la vuelta está a 73.3 m. Gasly 59 tampoco es bandera, boxes ni hueco, y sí es tráfico: el más cercano está a 25.9 m. Como una de las dos vueltas es un fallo de filtro, el recorte de z mayor que 10 no se evalúa. El conteo de ese umbral, sin aplicarlo, marcaría 13 vueltas.

Sacar esas dos vueltas a mano, que no es el recorte, deja en k=2 clases de 601 y 650, y de k=3 a k=7 una clase de 33. El barrido de piso se corrió después del nulo, sobre la matriz con la columna, sin sacar vueltas. Los pisos 3, 33 y 63 no dejan ningún k válido, porque la clase de 2 sigue ahí.

Sin `fast__brake_point_rel` la temporada tampoco elige k en Hungría: 1275 vueltas, 0 perdidas en el dropna, y todo k de 2 a 7 tiene una clase de menos de 3.

### Bordes de 350 m, solo en el fallback

Italia, Gran Bretaña y Mónaco no entran. La ventana de 350 m es la geométrica. La ventana del pipeline es esa longitud después del recorte entre zonas, así que no es el mismo borde. La ventana escalada es una sola clusterización, sin los tres nulos. En Japón y Abu Dabi esa matriz no produce un k válido.

| carrera | borde pipeline | borde 350 m | borde escalado |
| --- | ---: | ---: | ---: |
| Abu Dabi | 884/6288 (14.1 %) | 1946/8983 (21.7 %) | 1379/10374 (13.3 %) |
| Arabia Saudita | 173/4370 (4.0 %) | 1686/8079 (20.9 %) | 1619/10750 (15.1 %) |
| Australia | 15/3799 (0.4 %) | 1403/5821 (24.1 %) | 1013/5790 (17.5 %) |
| Austria | 19/6638 (0.3 %) | 647/8824 (7.3 %) | 1085/8813 (12.3 %) |
| Azerbaiyán | 236/6436 (3.7 %) | 1432/8003 (17.9 %) | 3052/9477 (32.2 %) |
| Baréin | 399/5757 (6.9 %) | 969/6677 (14.5 %) | 972/5745 (16.9 %) |
| Bélgica | 180/5399 (3.3 %) | 1966/8105 (24.3 %) | 988/6643 (14.9 %) |
| Canadá | 15/6605 (0.2 %) | 1161/7768 (14.9 %) | 418/7746 (5.4 %) |
| Catar | 36/6913 (0.5 %) | 1180/9888 (11.9 %) | 3469/11049 (31.4 %) |
| China | 855/7626 (11.2 %) | 2858/10310 (27.7 %) | 2424/10311 (23.5 %) |
| Ciudad de México | 7/5556 (0.1 %) | 1925/7533 (25.6 %) | 322/7061 (4.6 %) |
| Emilia-Romaña | 300/5136 (5.8 %) | 1399/7967 (17.6 %) | 1186/7564 (15.7 %) |
| España | 473/6852 (6.9 %) | 3836/10659 (36.0 %) | 1372/8834 (15.5 %) |
| Estados Unidos | 102/7894 (1.3 %) | 4850/11926 (40.7 %) | 2825/12375 (22.8 %) |
| Hungría | 1170/12360 (9.5 %) | 3956/15997 (24.7 %) | 5757/15929 (36.1 %) |
| Japón | 1259/6363 (19.8 %) | 4296/12088 (35.5 %) | 52/9271 (0.6 %) |
| Las Vegas | 480/4899 (9.8 %) | 1704/6185 (27.6 %) | 1075/5413 (19.9 %) |
| Miami | 1289/4532 (28.4 %) | 2254/8562 (26.3 %) | 3/8939 (0.0 %) |
| Países Bajos | 122/7460 (1.6 %) | 3591/10868 (33.0 %) | 3983/9801 (40.6 %) |
| Singapur | 175/10841 (1.6 %) | 3421/13869 (24.7 %) | 2395/12381 (19.3 %) |
| São Paulo | 980/6449 (15.2 %) | 2168/10740 (20.2 %) | 3195/10716 (29.8 %) |

