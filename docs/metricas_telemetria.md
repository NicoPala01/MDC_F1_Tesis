# Métricas de telemetría: qué separa pilotos, qué separa autos (Monza 2025)

Pregunta: ¿qué métricas de telemetría, y qué normalización, describen mejor el estilo de un piloto en la matriz de vueltas de Monza 2025 (842 vueltas, 19 pilotos, 10 equipos)?

Se probaron cinco familias en paralelo: frenada, trazada y dinámica lateral (X/Y), acelerador y marcha, normalización y control de confusores, y granularidad por curva y consistencia. Cada una tiene código, tablas y un `REPORT.md` en `experiments/telemetry_candidates/<familia>/`. `experiments/telemetry_candidates/integrated/run.py` reconstruye la matriz con la implementación de `src/` de las métricas que sobrevivieron y compara conjuntos de features por vuelta, por bloque de 5 vueltas y por piloto.

Insumos reproducibles:

- `scripts/export_lap_telemetry.py`: exporta a `cache/derived/` la telemetría de las vueltas canónicas (car data a ~4 Hz, telemetría fusionada con X/Y/Z y distancia al auto de adelante, campos de vuelta, zonas, esquinas, clima), para prototipar sin recargar FastF1.
- `scripts/evaluate_candidate_features.py <csv>`: puntúa columnas candidatas con los criterios de abajo y mide la ganancia de clustering.
- `analysis/feature_evaluation.py`: la librería de esos criterios.

## Resumen

1. **Las clases actuales separan fase de carrera, no estilo.** En el k=2 del pipeline la vuelta mediana es 15 en una clase y 33.5 en la otra; en el k=3 del estudio anterior (`docs/separacion_algoritmos_metricas.md`) es 15 / 22 / 38. La causa: `apex_speed_rel` y `brake_point_rel` siguen la carga de combustible y la evolución de la pista. Dentro de cada piloto, ρ con el número de vuelta es +0.78 para la velocidad de ápice y −0.5 para el punto de frenado. Restar la mediana de la sesión es un corrimiento constante y no lo puede sacar.
2. **Normalizar contra la mediana del campo en la misma vuelta lo corrige.** En k=3 por vuelta, la diferencia de vuelta mediana entre clases baja de 23 a 1.5, la AMI con el piloto sube de 0.197 a 0.258, prediction strength de 0.69 a 0.82 y bootstrap ARI de 0.87 a 0.94. Si además se restan los efectos de compuesto y vida del neumático estimados dentro de cada piloto, la AMI con el piloto llega a 0.279 y la AMI con el compuesto queda en 0.037. La silueta baja de 0.204 a 0.190–0.198: el eje de combustible la estaba inflando.
3. **Hay métricas nuevas con más señal entre compañeros de equipo que cualquiera de las 17 actuales.** Liberación de freno → acelerador a fondo en curvas medias: ω² piloto-dentro-de-equipo 0.355 (la mejor actual es el coast, 0.12–0.15). Modulación del acelerador en Ascari: 0.257. Lift-and-coast antes de Ascari: 0.214. Ápice → acelerador a fondo en Ascari: 0.159, con sólo 2 % de varianza de equipo. Ubicación del ápice respecto de la marca geométrica (con X/Y): 0.155.
4. **Esas métricas no mejoran el K-means por vuelta.** Son muy confiables promediadas por piloto (Spearman-Brown ≥ 0.95) y ruidosas vuelta a vuelta. Agregadas a la matriz bajan la prediction strength en k=3 de 0.82 a 0.57. Sirven para el perfil del piloto y la comparación con el compañero, no como entrada del clustering.
5. **Lo que no sirve.** Deceleración pico (a 4 Hz se mide el cuarto de segundo más empinado, no el pedal), desplazamiento lateral de la línea (Monza se corre por la misma línea a decímetros), aceleración lateral (es velocidad de ápice con otra unidad), velocidad de salida y RPM (son el auto), consistencia por ventana móvil (no sobrevive a bloques no solapados), dispersión de tiempos de sector (ritmo y tráfico), excluir vueltas con tráfico, z-score dentro de piloto (borra al piloto), y normalizar por vuelta *y* compuesto (sesgo de composición).

## Criterios de una métrica de estilo

`analysis.feature_evaluation.score_features` mide, por columna:

| criterio | columna | lectura |
| --- | --- | --- |
| auto | `share_team` | fracción de la suma de cuadrados entre equipos. Alta = el auto. |
| piloto con el mismo auto | `omega2_driver_in_team`, `p_driver_in_team` | ω² de la varianza entre compañeros de equipo, descontando el azar, con su test F. Es el criterio central. |
| confiabilidad | `spearman_brown` | correlación de las medias por piloto en vueltas pares contra impares, corregida a carrera completa. |
| orden entre compañeros | `teammate_sign_agreement` | en cuántos equipos el mismo compañero queda adelante en las dos mitades. |
| neumático | `omega2_compound_within`, `rho_tyre_life_within` | asociación con el compuesto (ω²) y con la vida del neumático (ρ), dentro de cada piloto. |
| combustible / pista | `rho_lap_within` | ρ con el número de vuelta dentro de cada piloto. |
| redundancia | `max_abs_rho_existing` | |ρ| máxima con las 17 columnas actuales. |

`recommended` exige: ceros ≤ 90 %, cobertura ≥ 90 %, ω² piloto-dentro-de-equipo ≥ 0.03 con p < 0.01, `share_team` < 0.5, Spearman-Brown ≥ 0.7, ω² de compuesto < 0.05 y |ρ| con las actuales < 0.8.

`clustering_gain` compara particiones con silueta, nulo de permutación, prediction strength, bootstrap ARI, AMI con piloto y con compuesto, fracción de equipos cuyos pilotos caen en clases modales distintas (`teammate_split_rate`), y la fuga de fase (`lap_span`, `tyre_life_span`: diferencia entre la mayor y la menor mediana por clase).

## Las 17 columnas actuales bajo esos criterios

Normalización actual (mediana de sesión por tipología). Orden por ω² piloto-dentro-de-equipo.

| columna | share_team | ω² piloto/equipo | Spearman-Brown | orden compañeros | ω² compuesto | ρ vuelta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| slow__coast_frac | 0.342 | 0.153 | 0.969 | 0.889 | 0.066 | −0.193 |
| medium__coast_frac | 0.452 | 0.136 | 0.984 | 0.889 | 0.070 | −0.175 |
| fast__coast_frac | 0.229 | 0.124 | 0.985 | 0.778 | 0.077 | −0.343 |
| medium__trail_brake_frac | 0.234 | 0.119 | 0.975 | 1.000 | 0.014 | +0.033 |
| medium__throttle_attack | 0.098 | 0.108 | 0.995 | 1.000 | 0.006 | −0.084 |
| fast__apex_speed_rel | 0.211 | 0.096 | 0.983 | 1.000 | 0.413 | +0.778 |
| medium__apex_speed_rel | 0.213 | 0.085 | 0.990 | 0.889 | 0.558 | +0.785 |
| medium__brake_point_rel | 0.073 | 0.069 | 0.946 | 0.889 | 0.146 | −0.489 |
| fast__brake_point_rel | 0.104 | 0.053 | 0.941 | 1.000 | 0.170 | −0.509 |
| slow__apex_speed_rel | 0.060 | 0.048 | 0.892 | 0.667 | 0.075 | −0.060 |
| slow__brake_point_rel | 0.115 | 0.040 | 0.926 | 1.000 | 0.211 | −0.509 |
| slow__trail_brake_frac | 0.223 | 0.040 | 0.957 | 0.889 | 0.007 | +0.073 |
| slow__full_throttle_frac | 0.115 | 0.027 | 0.876 | 0.778 | 0.018 | +0.079 |
| slow__throttle_attack | 0.207 | 0.020 | 0.953 | 0.778 | 0.005 | −0.037 |
| fast__full_throttle_frac | 0.012 | 0.018 | −0.118 | — | 0.007 | — |
| fast__trail_brake_frac | 0.061 | 0.007 | 0.783 | 0.444 | 0.014 | +0.039 |
| medium__full_throttle_frac | 0.012 | 0.002 | −0.168 | — | −0.010 | — |

`medium__throttle_attack` tiene 95 % de ceros. Como referencia de auto puro, la velocidad en la trampa de velocidad da `share_team` 0.21 y ω² piloto/equipo 0.006.

## Normalización

Estrategias sobre las 7 columnas base (ICC ≥ 0.25: `fast/medium__apex_speed_rel`, `slow/medium/fast__coast_frac`, `slow/medium__trail_brake_frac`). Medias sobre las 7 columnas y K-means k=3 por vuelta, z-score. Fuente: `experiments/telemetry_candidates/normalization/strategy_summary.csv` (842 vueltas). La prediction strength depende de las mitades aleatorias: en la corrida integrada de más abajo (838 vueltas, otra semilla) la misma estrategia da 0.82 en vez de 0.74.

| estrategia | ω² piloto/equipo | ω² compuesto | \|ρ vuelta\| | silueta k=3 | PS k=3 | AMI piloto | AMI compuesto | lap_span |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mediana de sesión (actual) | 0.108 | 0.172 | 0.340 | 0.204 | 0.69 | 0.198 | 0.009 | 23 |
| misma vuelta (`lap_synchronous`) | 0.135 | 0.048 | 0.079 | 0.190 | 0.74 | 0.258 | 0.048 | 1 |
| misma vuelta + neumático dentro de piloto | 0.132 | 0.036 | 0.025 | 0.196 | 0.73 | 0.277 | 0.034 | 6 |
| regresión vuelta + compuesto + vida, efectos fijos de piloto | 0.129 | 0.033 | 0.054 | 0.201 | 0.76 | 0.279 | 0.031 | 3.5 |
| tendencia lineal por piloto | 0.142 | 0.009 | 0.042 | 0.199 | 0.76 | 0.282 | 0.037 | 1 |
| excluir vueltas con auto a < 50 m | 0.127 | 0.164 | 0.305 | 0.207 | 0.74 | 0.218 | 0.022 | 20 |
| z-score dentro de piloto | −0.011 | 0.160 | 0.340 | 0.142 | 0.48 | −0.005 | 0.036 | 24.5 |
| relativo al compañero | 0.374 | 0.048 | 0.000 | 0.147 | 0.54 | 0.189 | 0.004 | 1 |

- **Misma vuelta** es la base recomendada: no estima pendientes por piloto, así que no se come la gestión de cada uno. Si una vuelta tiene menos de 8 autos (la 40 tiene 2), la referencia se ensancha a ±1, ±2, ±3 vueltas.
- **Misma vuelta + neumático dentro de piloto** (`remove_within_driver_effects`) estima una pendiente común de compuesto y vida del neumático con efectos fijos de piloto y resta sólo esa parte. Mantiene el nivel de cada piloto y de cada equipo.
- **La tendencia lineal por piloto** da números parecidos, pero usa la pendiente de cada piloto, que en otra carrera puede ser su estrategia de stint. No conviene como opción por defecto.
- **Excluir tráfico** no cambia el eje: las clases siguen en vuelta 19 contra 35. El tráfico existe (explica 16 % de la velocidad de entrada a la T1), pero no es lo que siguen estas columnas.
- **Relativo al compañero** cambia la pregunta: anula el equipo por construcción y el `teammate_split_rate` = 1 es automático. Bootstrap ARI 0.41.
- **Misma vuelta y mismo compuesto** (`normalize_lap_synchronous(by="Compound")`) baja la AMI con el compuesto a ~0, pero en una misma vuelta quienes van con MEDIUM y quienes van con HARD son autos distintos. La ω² de compuesto dentro de piloto de `medium__apex_speed_rel` sube de 0.12 a 0.22. Es un sesgo de composición; queda en el código sólo como chequeo de sensibilidad.

Clustering de las 7 columnas base, mismas 838 vueltas (`integrated/comparison.csv`):

| unidad | normalización | k | tamaños | silueta | gap | PS | boot ARI | AMI piloto | AMI compuesto | split compañeros | lap_span |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vuelta | sesión | 2 | 501, 337 | 0.257 | 0.150 | 0.92 | 0.97 | 0.125 | −0.001 | 0.33 | 18 |
| vuelta | sesión | 3 | 311, 277, 250 | 0.204 | 0.091 | 0.69 | 0.87 | 0.197 | 0.009 | 0.56 | 23 |
| vuelta | misma vuelta | 2 | 514, 324 | 0.218 | 0.111 | 0.81 | 0.92 | 0.164 | 0.024 | 0.22 | 1 |
| vuelta | misma vuelta | 3 | 314, 274, 250 | 0.190 | 0.086 | 0.82 | 0.94 | 0.258 | 0.049 | 0.22 | 1.5 |
| vuelta | misma vuelta + neumático | 3 | 327, 262, 249 | 0.198 | 0.094 | 0.83 | 0.89 | 0.279 | 0.037 | 0.33 | 6 |
| bloque 5 | sesión | 3 | 64, 49, 48 | 0.261 | 0.143 | 0.53 | 0.82 | 0.210 | −0.010 | 0.56 | 22.5 |
| bloque 5 | misma vuelta | 3 | 62, 60, 39 | 0.240 | 0.123 | 0.67 | 0.76 | 0.338 | 0.075 | 0.44 | 2 |
| bloque 5 | misma vuelta + neumático | 3 | 59, 52, 50 | 0.252 | 0.131 | 0.71 | 0.89 | 0.372 | 0.034 | 0.22 | 8.5 |

El nulo de permutación casi no cambia (0.10–0.12), así que la caída de silueta es la del eje de fase que se fue, no un aumento del ruido.

## Familias de métricas nuevas

ω² es piloto-dentro-de-equipo. "lapsync" = restada la mediana del campo en la misma vuelta y zona.

### Frenada (`experiments/telemetry_candidates/braking/`)

| métrica | ω² | share_team | Spearman-Brown | orden compañeros | ω² compuesto | ρ vuelta | \|ρ\| actuales |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| lift-and-coast antes de Ascari, lapsync (s) | 0.214 | 0.187 | 0.982 | 1.00 | 0.017 | +0.066 | 0.70 (`fast__coast_frac`) |
| liberación del freno → ápice en curvas medias, lapsync (m) | 0.284 (0.119 sin OCO) | 0.384 | 0.993 | 0.89 | −0.002 | +0.057 | 0.55 |
| liberación del freno → ápice en Rettifilo (m) | 0.167 | 0.307 | 0.986 | 1.00 | 0.027 | +0.055 | 0.57 |
| cantidad de aplicaciones de freno en Rettifilo | 0.132 | 0.244 | 0.982 | 1.00 | 0.001 | +0.025 | 0.50 |

Lift-and-coast: Lawson, Antonelli, Alonso y Colapinto levantan antes de frenar en Ascari; sus compañeros no. Sin normalizar por vuelta deriva con la carrera (ρ −0.38) y repite el coast (|ρ| 0.81).

No sirvió: deceleración pico (mediana 4.25 g en la T1, físicamente razonable, pero ω² ≤ 0.03: a 4 Hz es el cuarto de segundo más empinado), tiempo hasta el pico (una muestra de ancho), velocidad de entrada (ω² 0.06, `share_team` 0.21; el rebufo explica 16 %), cociente de caída de velocidad (es velocidad de ápice), duración y deceleración media (se caen al sacar el compuesto, el combustible o a Ocon), lift en Parabólica (ρ −0.30 con la vuelta: ahorro de combustible que crece en la carrera).

### Acelerador y marcha (`experiments/telemetry_candidates/throttle/`)

| métrica | ω² | share_team | Spearman-Brown | orden compañeros | ω² compuesto | ρ vuelta | \|ρ\| actuales |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| última muestra de freno → acelerador ≥ 95 %, curvas medias, lapsync (s) | 0.393 | 0.128 | 0.993 | 1.00 | 0.027 | −0.003 | 0.33 |
| variación del acelerador más allá de un camino monótono, Ascari, lapsync (%/m) | 0.260 | 0.137 | 0.979 | 0.89 | 0.041 | +0.059 | 0.21 |
| ápice → acelerador ≥ 95 %, Ascari, lapsync (s) | 0.148 | 0.023 | 0.963 | 0.89 | 0.010 | −0.044 | 0.14 |
| distancia dentro de +3 % de la velocidad mínima, medias, lapsync (m) | 0.130 | 0.213 | 0.970 | 1.00 | 0.043 | −0.006 | 0.33 |
| marcha mínima en Rettifilo | 0.379 | 0.313 | 0.996 | 1.00 | −0.006 | — | 0.34 |

La marcha mínima es real y angosta: 71 de 842 vueltas de Rettifilo son en 3.ª, 32 de Hamilton y 39 de Ocon; el resto, incluidos sus compañeros, en 2.ª. Es binaria y no va al K-means.

No sirvió: cociente deceleración/aceleración alrededor del ápice (forma V contra U; a 4 Hz y velocidad entera los bordes saltan una muestra), velocidad a +100/+200 m del ápice (`share_team` 0.42: potencia), solapamiento freno-acelerador (`share_team` 0.60), RPM en el ápice (`share_team` 0.46), RPM del cambio ascendente en Rettifilo (ω² 0.30 pero mitad auto), levantadas ≥ 10 puntos (cero en Rettifilo), acelerador parcial y duración de la rampa (`share_team` 0.40–0.56), Curva Grande (se hace a fondo en las 842 vueltas).

### Trazada y dinámica lateral (`experiments/telemetry_candidates/line/`)

Línea de referencia de la sesión desde X/Y, suavizado Savitzky–Golay, estación a lo largo de esa línea y desplazamiento lateral con signo.

| métrica | ω² | share_team | Spearman-Brown | orden compañeros | ω² compuesto | ρ vuelta | \|ρ\| actuales |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ápice tardío: estación de la velocidad mínima − marca geométrica, medias (m) | 0.155 | 0.112 | 0.956 | 0.89 | 0.027 | +0.17 | 0.13 |
| ápice tardío en Parabólica (m) | 0.092 | 0.117 | 0.963 | 1.00 | 0.021 | +0.04 | 0.09 |
| ápice tardío en Ascari (m) | 0.074 | 0.084 | 0.933 | 0.67 | 0.012 | +0.03 | 0.18 |

Es casi ortogonal al coast y al trail braking. Diferencias entre compañeros de 3–6 m (GAS más tarde que COL, STR que ALO, HAD que LAW, HAM que LEC, PIA que NOR). Con la `Distance` integrada del pipeline, en vez de la estación sobre la línea de referencia, la misma métrica cae a ω² 0.044: la deriva de 4 m (mediana) a 12 m (p90) entre vueltas la tapa. Por eso no se integró a `src/`.

No sirvió: desplazamiento lateral, ancho de pista usado, radio mínimo (la línea es la misma a decímetros: el residual de T1 tiene 8 cm de desvío), aceleración lateral (3.8 g en Parabólica, físicamente correcta, pero |ρ| 0.92 con la velocidad de ápice y ρ +0.76 con la vuelta), punto de giro (fijado por la geometría de las chicanas), ápice de Roggia (ω² 0.006).

Agregar el ápice tardío al K-means baja la silueta de 0.256 a 0.209 y la prediction strength de 0.90 a 0.88 en k=2: ordena a los pilotos en un eje continuo de ~10 m, no en grupos.

### Granularidad por curva y consistencia (`experiments/telemetry_candidates/granularity/`)

Por curva, la parte de auto es menor que en el agregado por tipología: `medium__coast_frac` tiene `share_team` 0.452, y cada curva media por separado 0.17–0.36. El agregado conserva lo que el auto hace en todas las curvas y cancela hábitos de una curva. Lesmo 1 y Lesmo 2 son el mismo hábito entre pilotos (Spearman 0.91); Roggia y Lesmo 1 no (0.08). La mejor columna limpia por curva es el trail braking de Lesmo 1 (ω² 0.122, ω² compuesto 0.006, ρ vuelta +0.03). Curva Grande es constante en todas las métricas: `fast__*` es Ascari.

Reemplazar las 7 columnas base por la mejor curva de cada una no mejora la partición (k=2: gap 0.133 contra 0.145, PS 0.77 contra 0.90). Usar las 16 columnas por curva baja la silueta observada a 0.207.

La consistencia por ventana móvil de 5 vueltas parece la mejor métrica de compañeros (IQR del coast en Lesmo 2: ω² 0.157), pero las ventanas de vueltas pares e impares se solapan. En bloques no solapados el Spearman-Brown cae a 0.54 y el orden entre compañeros a 0.56. La dispersión de tiempos del sector 2 correlaciona 0.52 con la posición final: es ritmo o tráfico.

## Métricas integradas en `src/`

`features/metrics.py`, activadas con `features.extended_metrics: true` (`EXTENDED_STYLE_FEATURES`). Cada ventana se ordena por metros desde su inicio y el tiempo se integra desde la velocidad (`order_along_track`), así sobreviven a una zona que cruce la línea de llegada. En una zona a fondo (sin freno y con acelerador > 10 %) todas dan NaN y la tipología toma la mediana de las zonas activas.

| columna | definición | ventana |
| --- | --- | --- |
| `release_to_full_s` | tiempo desde la última muestra con freno hasta el cruce interpolado de 95 % de acelerador después del ápice cinemático | frenado ∪ ápice ∪ salida |
| `apex_to_full_s` | tiempo desde el ápice cinemático (mínimo de velocidad) hasta ese cruce de 95 % | frenado ∪ ápice ∪ salida |
| `throttle_excess_tv` | `(Σ|ΔThrottle| − |Throttle_fin − Throttle_inicio|) / longitud`, %/m; 0 si el pedal sólo se mueve en un sentido | ápice ∪ salida |
| `lift_coast_s` | tiempo entre el primer acelerador ≤ 5 % después del último ≥ 95 % y el inicio de la frenada; 0 si pasa del acelerador al freno sin coast | 100 m antes de la ventana de frenado ∪ frenado |

`get_min_gear` queda como descriptor. Puntajes con la implementación de `src/`, normalizadas por vuelta (838 vueltas):

| columna | ω² | share_team | Spearman-Brown | orden compañeros | ω² compuesto | ρ vuelta | \|ρ\| actuales |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| medium__release_to_full_s | 0.355 | 0.165 | 0.987 | 1.00 | 0.043 | −0.046 | 0.27 |
| fast__throttle_excess_tv | 0.257 | 0.140 | 0.979 | 0.89 | 0.041 | +0.059 | 0.21 |
| fast__lift_coast_s | 0.214 | 0.190 | 0.979 | 1.00 | 0.019 | +0.066 | 0.70 |
| medium__lift_coast_s | 0.199 | 0.178 | 0.965 | 0.86 | 0.033 | −0.345 | 0.52 |
| slow__throttle_excess_tv | 0.178 | 0.074 | 0.942 | 1.00 | 0.012 | +0.047 | 0.28 |
| slow__release_to_full_s | 0.171 | 0.274 | 0.983 | 1.00 | 0.025 | +0.141 | 0.53 |
| fast__apex_to_full_s | 0.159 | 0.024 | 0.965 | 0.89 | 0.014 | −0.025 | 0.12 |
| medium__apex_to_full_s | 0.153 | 0.331 | 0.974 | 0.89 | 0.019 | +0.014 | 0.26 |

`medium__lift_coast_s` pasa los umbrales pero tiene ρ −0.35 con la vuelta: el lift en Parabólica crece en la carrera (ahorro de combustible). Es gestión, no hábito.

Perfil por piloto, mediana de vueltas normalizadas por vuelta (s; positivo = más que el campo en esa vuelta):

| equipo | piloto | liberación → pleno, medias | ápice → pleno, Ascari | lift-and-coast, Ascari |
| --- | --- | ---: | ---: | ---: |
| Ferrari | HAM / LEC | +0.30 / +0.11 | −0.03 / −0.02 | 0 / 0 |
| McLaren | NOR / PIA | −0.21 / +0.16 | −0.14 / +0.27 | 0 / 0 |
| Red Bull | VER / TSU | −0.30 / +0.12 | −0.08 / +0.10 | 0 / 0.09 |
| Haas | OCO / BEA | −0.51 / +0.10 | +0.30 / −0.05 | 0 / 0 |
| Mercedes | RUS / ANT | −0.02 / −0.12 | −0.01 / −0.00 | 0 / 0.33 |
| Racing Bulls | HAD / LAW | +0.05 / −0.11 | +0.05 / −0.02 | 0 / 0.39 |
| Aston Martin | STR / ALO | +0.07 / −0.06 | −0.14 / +0.17 | 0 / 0.21 |
| Alpine | GAS / COL | −0.08 / +0.21 | −0.15 / +0.00 | 0 / 0.12 |
| Williams | SAI / ALB | −0.21 / +0.03 | −0.02 / +0.20 | 0 / 0 |

En las curvas medias, Verstappen, Norris y Ocon pasan del freno al acelerador a fondo 0.4–0.6 s antes que sus compañeros; Hamilton es el que más tarda de toda la grilla (+0.30 s). En Ascari, Piastri, Ocon y Alonso tardan 0.3–0.4 s más que sus compañeros desde el ápice hasta el acelerador a fondo.

### Con las métricas nuevas en el K-means

| unidad | conjunto | k | silueta | gap | PS | boot ARI | AMI piloto | lap_span |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vuelta | 7 base, misma vuelta | 3 | 0.190 | 0.086 | 0.82 | 0.94 | 0.258 | 1.5 |
| vuelta | 7 base + 3 nuevas | 3 | 0.147 | 0.069 | 0.57 | 0.64 | 0.256 | 4 |
| vuelta | selección greedy de 8 (nuevas + actuales) | 3 | 0.147 | 0.023 | 0.64 | 0.81 | 0.185 | 12 |
| bloque 5 | 7 base, misma vuelta | 3 | 0.240 | 0.123 | 0.67 | 0.76 | 0.338 | 2 |
| bloque 5 | 7 base + 3 nuevas | 4 | 0.216 | 0.129 | 0.44 | 0.57 | 0.467 | 6.5 |

Las 3 nuevas son liberación → pleno en curvas medias, modulación en Ascari y lift-and-coast en Ascari. La selección greedy crea una clase de "vueltas con lift-and-coast" (vuelta mediana 17 contra 27–29) porque esa columna es 58–78 % ceros: vuelve a filtrar la fase de carrera por la gestión. A nivel piloto (distancia de energía entre nubes de vueltas), cualquier conjunto deja a Ocon solo o da bootstrap ARI 0.02–0.6: con 19 pilotos no hay una partición estable.

## Clases con la configuración recomendada

Misma vuelta + neumático dentro de piloto, 7 columnas base, z-score, K-means k=3, por vuelta (`integrated/`). Medianas por clase (ya relativas al campo en la misma vuelta):

| columna | 0 (262) | 1 (327) | 2 (249) |
| --- | ---: | ---: | ---: |
| fast__apex_speed_rel | −2.0 | −0.2 | +2.9 |
| medium__apex_speed_rel | −3.2 | −0.8 | +5.1 |
| fast__coast_frac | +0.011 | −0.005 | −0.001 |
| medium__coast_frac | +0.025 | −0.019 | +0.003 |
| slow__coast_frac | +0.035 | −0.019 | +0.005 |
| medium__trail_brake_frac | −0.045 | +0.054 | −0.018 |
| slow__trail_brake_frac | −0.019 | +0.029 | −0.016 |

Clase 0: ápice lento, más coast, menos trail braking (LAW 0.96, TSU 0.96, STR 0.89, ALO 0.79, ANT 0.76, HAD 0.60). Clase 1: más trail braking y menos coast (OCO 0.98, HAM 0.96, LEC 0.85, SAI 0.84, BOR 0.70, BEA 0.68, ALB 0.55). Clase 2: ápice rápido (PIA 0.98, NOR 0.96, VER 0.96, COL 0.50, RUS 0.40). GAS queda repartido 21 / 21 entre 1 y 2. Vuelta mediana 22 / 27 / 28.

Compuesto por clase: MEDIUM 0.34 / 0.41 / 0.63. McLaren corrió casi toda la carrera con MEDIUM y SOFT, así que en la clase 2 el compuesto no se puede separar del piloto: el efecto fijo de neumático sólo se estima con pilotos que usaron más de un compuesto.

La variante completa de `run_pipeline` (`lap_synchronous`, `within_driver_tyre_effects`, `feature_screening: {drop_near_constant: true, min_icc: 0.25}`, `standardization: zscore`) se queda con 9 columnas (el ICC sobre la matriz normalizada agrega `fast__brake_point_rel` y `slow__full_throttle_frac`), elige k=3 por Davies-Bouldin (1.56; silueta 0.195 bajo el umbral 0.25), estabilidad entre semillas 0.985, tamaños 295 / 293 / 250 y vuelta mediana por clase 27 / 22 / 26.

## Recomendación

1. `features.lap_synchronous` y `features.within_driver_tyre_effects` ya están en true por defecto. Sin eso, en Monza las clases son primera mitad contra segunda mitad de carrera. La corrida principal con esa configuración (17 columnas, escalado robusto, el mismo algoritmo) está en `docs/monza_2025_throttle_onset_off.md`: k=3 por Davies-Bouldin, silueta 0.133, Davies-Bouldin 1.986, tamaños 349 / 266 / 227, vuelta mediana por clase 26 / 27 / 24.
2. `features.feature_screening` (`drop_near_constant: true`, `min_icc: 0.25`) con `standardization: zscore` es una variante evaluada, no la configuración principal (resultado en la sección anterior). El ajuste de neumático deja intactas las columnas con IQR 0, así que sin el screening el escalado robusto ya no aísla vueltas.
3. `features.extended_metrics` queda en false por defecto. Encenderlo da `driver_extended_profile` (mediana por piloto) para describir a cada piloto y compararlo con su compañero. Esas métricas no van a la matriz del K-means.
4. Reportar siempre `lap_span` y la AMI con el compuesto junto a la silueta: una partición que mejora la silueta separando fases de carrera no es una partición de estilo.
5. Siguiente paso con más señal pendiente: el ápice tardío por proyección X/Y (`experiments/telemetry_candidates/line/extract.py`). Es la métrica con menos redundancia (|ρ| 0.13) y necesita la línea de referencia, no la `Distance` integrada.

Límites: una sola carrera; car data a ~4 Hz (Δt mediano 0.245 s) y freno booleano, así que no hay presión de freno ni deceleración pico confiable; no hay combustible ni setup en FastF1; en pilotos que usaron un solo compuesto, compuesto y estilo no se separan.
