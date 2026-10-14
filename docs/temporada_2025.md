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
