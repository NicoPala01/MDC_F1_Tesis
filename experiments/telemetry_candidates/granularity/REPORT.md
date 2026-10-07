# Granularidad por curva y consistencia como rasgo de estilo (Monza 2025)

Carrera: Gran Premio de Italia 2025, 842 vueltas canónicas, 19 pilotos, 10 equipos (Kick Sauber solo con BOR). Telemetría de coche ya exportada (`car.pkl`, ~4 Hz, Δt mediano 0,245 s). No se recargó FastF1. El clustering es K-means sobre columnas en z-score, sin PCA, con el mismo `clustering_gain` del evaluador (`n_perm=5`, `n_boot=10`, `random_state=42`).

## Resultado

Separar las curvas **no mejora la partición conjunta** respecto a las 7 columnas de tipología. En k=2 la brecha de silueta pasa de 0.145 (base) a 0.133 (análogo de 7 curvas); en k=3, de 0.094 a 0.094. La silueta bruta no es comparable si cambia el número de columnas: la brecha frente al nulo de permutación sí lo es, y tampoco sube.

Lo que sí cambia es la **lectura por curva**. El agregado `medium` mezcla Roggia, Lesmo 1, Lesmo 2 y Parabolica; `fast` mezcla Curva Grande (casi a fondo) con Ascari. Esa mezcla esconde rasgos de compañeros que viven en una sola curva y, a la vez, la mediana de tipología a veces es sólo la curva del medio de la distribución. Las tablas de abajo cuantifican las dos cosas.

La consistencia vuelta a vuelta, como rasgo de estilo, queda **por debajo del nivel de la curva**. La mejor dispersión móvil es `T7__coast_frac__roll_iqr5`: ω²(piloto|equipo) = 0.157, cuota de equipo = 0.118, Spearman-Brown = 0.970 (optimista: ventanas L−2…L+2 comparten vueltas entre pares e impares). El mismo rasgo en bloques no solapados de 5 vueltas (`T7__coast_frac__block_iqr5`) tiene ω²(piloto|equipo) = 0.154, Spearman-Brown = 0.544.  El ω² del bloque sigue alto, pero el Spearman-Brown cae por debajo de 0,70: el ranking del piloto no se sostiene de una mitad de la carrera a la otra cuando las ventanas ya no se solapan. La fiabilidad del rolling no se puede usar.

Los tiempos de sector no son el coche: la cuota de equipo de `sector2_time__roll_std5` es 0.076, al lado de su ω²(piloto|equipo) = 0.052 (Spearman-Brown = 0.969). Tampoco son estilo de frenada. La dispersión del sector 2 acompaña la posición en carrera (Spearman 0,52 entre medianas de piloto).

Recomendación de una línea: **usar las curvas para interpretar, no para sustituir el vector de clustering.** Una curva concreta entra en el texto cuando gana en ω²(piloto|equipo) y en fiabilidad; el vector de 7 columnas de tipología se queda. No añadir la consistencia móvil ni la dispersión de tiempos de sector.

## Definiciones

Cada vuelta de `car.pkl` entra en `extract_style_features_from_telemetry` con las ventanas de `zones.json` y `include_throttle_onset=False`. Por zona (frenada | ápice | salida, en metros de `Distance`) salen seis métricas crudas:

- `brake_point_rel`: metros desde el primer freno de la ventana de frenada hasta el ápice cinemático (argmin de velocidad en el ápice; si no hay, el ápice oficial). Mayor = frenada más temprana.
- `trail_brake_frac`: fracción espacial del ápice con `Brake` verdadero.
- `apex_speed_rel`: velocidad mínima en el ápice, en km/h. El sufijo `_rel` es el del pipeline; aquí todavía es la velocidad cruda. No es un cociente.
- `throttle_attack`: percentil 95 de `ThrottleRate` tras mediana móvil de 5 muestras, en la salida.
- `coast_frac`: fracción espacial de frenada ∪ ápice ∪ salida con acelerador ≤ 5 y sin freno.
- `full_throttle_frac`: fracción espacial de la salida con acelerador ≥ 95.

**Normalización de este experimento:** a cada métrica se le resta la mediana de sesión **de esa curva** (las 842 vueltas). No se resta la mediana de la tipología. Una columna `T4__coast_frac` es el coast de Roggia menos la mediana de Roggia. Positivo = por encima del pelotón en esa curva.

El pipeline actual hace otra cosa: resta la mediana de sesión de la **tipología** y después toma la mediana de las curvas de esa tipología. `slow` es sólo Rettifilo. `medium` es la mediana de Roggia, Lesmo 1, Lesmo 2 y Parabolica. `fast` es la mediana de Curva Grande y Ascari. `fast__throttle_attack` se descarta por casi constante; quedan 17 columnas.

**Consistencia por vuelta.** Para cada piloto y cada métrica, en la vuelta L se toma el conjunto de sus vueltas con número en [L−2, L+2] (radio 2; mínimo 3 vueltas finitas). No es una ventana de cinco filas si falta una vuelta, ni salta un hueco mayor que ese radio.

- `__roll_iqr5`: P75 − P25 de esa ventana.
- `__roll_mad5`: mediana de |x − mediana de la ventana|.
- `__absdev_rollmed5`: |x_L − mediana de la ventana|.

Esas tres se calculan sobre las 12 columnas de tipología de punto de frenada, trail braking, velocidad de ápice y coast, y sobre las mismas cuatro métricas en las siete curvas (ya normalizadas por curva: restar una constante no cambia IQR, MAD ni desviación absoluta).

**Tiempos.** `__roll_std5` es la desviación típica muestral (ddof = 1) de `Sector1Time`, `Sector2Time`, `Sector3Time` y `LapTime` (segundos) en la misma ventana de número de vuelta.

**Bloques.** `block_median_matrix` parte las vueltas observadas de cada piloto, ordenadas por `LapNumber`, en bloques no solapados de 5. `__block_iqr5` es el P75 − P25 de esas cinco vueltas. Los bloques no comparten muestras, así que su Spearman-Brown no hereda el solapamiento de la ventana móvil.

**Criterio de estilo** (el del evaluador, más la deriva). Una columna pasa el filtro estricto si: cobertura ≥ 0,90, fracción de ceros ≤ 0,90, al menos 3 valores distintos, ω²(piloto|equipo) ≥ 0,03 con p < 0,01, Spearman-Brown ≥ 0,70, ω²(compuesto|piloto) < 0,05, |ρ de Spearman con el número de vuelta, dentro del piloto| ≤ 0,35 y |ρ con la vida del neumático| ≤ 0,35. ω²(piloto|equipo) es la varianza entre compañeros de equipo por encima de la que cabría por azar (SS de piloto dentro de equipo, menos grados de libertad × MS de vuelta, sobre SS total + MS de vuelta). La cuota de equipo es la fracción de suma de cuadrados entre equipos: coche, no estilo. El filtro de redundancia del evaluador (|ρ| < 0,80 con las 17 columnas) **no** se usa para aceptar una curva: por construcción se parece a su agregado. Se informa `max_abs_rho_existing` y se juzga el resto.

El Spearman-Brown de una ventana móvil es optimista: la media del piloto en vueltas pares y la de vueltas impares comparten casi la misma ventana. Por eso la confirmación es el bloque de 5.

## Comprobación de la extracción

Reconstruyendo el paso del pipeline (mediana de tipología, luego mediana entre curvas) a partir de `car.pkl` y `zones.json`, la correlación de Pearson con `lap_matrix.csv` tiene mediana 1.0000 (mínimo 1.0000 en fast__coast_frac, n columnas comparadas = 17). La diferencia absoluta máxima por columna está en `sanity_typology_reconstruction.csv`. La extracción de este experimento es la misma función que la matriz actual.

Fracción de valores faltantes por curva (métrica cruda), antes de normalizar:

| zona | punto de frenada | trail braking | velocidad de ápice | ataque de acelerador | fracción en punto muerto | gas a fondo |
| --- | --- | --- | --- | --- | --- | --- |
| T1 Rettifilo | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| T3 Curva Grande | 1.000 | 0.001 | 0.000 | 0.000 | 0.000 | 0.000 |
| T4 Roggia | 0.005 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| T6 Lesmo 1 | 0.011 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| T7 Lesmo 2 | 0.107 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| T8 Ascari | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| T11 Parabolica | 0.001 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |

## Puntuación por curva

ω²(piloto|equipo). Es el criterio de estilo: compañeros distintos en el mismo coche. Un valor ≈ 0 es ruido de vuelta. Las celdas de columnas casi constantes siguen mostrándose; su ω² no se interpreta como estilo.

| zona | punto de frenada | trail braking | velocidad de ápice | ataque de acelerador | fracción en punto muerto | gas a fondo |
| --- | --- | --- | --- | --- | --- | --- |
| T1 Rettifilo | 0.040 | 0.040 | 0.048 | 0.020 | 0.153 | 0.027 |
| T3 Curva Grande | NA | NA | 0.029 | NA | NA | NA |
| T4 Roggia | 0.035 | 0.052 | 0.089 | 0.043 | 0.138 | 0.029 |
| T6 Lesmo 1 | 0.076 | 0.122 | 0.091 | 0.090 | 0.121 | 0.058 |
| T7 Lesmo 2 | 0.042 | 0.080 | 0.067 | 0.033 | 0.121 | 0.001 |
| T8 Ascari | 0.053 | 0.008 | 0.104 | 0.004 | 0.124 | 0.018 |
| T11 Parabolica | 0.018 | 0.041 | 0.139 | NA | 0.157 | -0.005 |

Cuota de equipo (fracción de suma de cuadrados entre equipos). Alto = el coche, no el piloto.

| zona | punto de frenada | trail braking | velocidad de ápice | ataque de acelerador | fracción en punto muerto | gas a fondo |
| --- | --- | --- | --- | --- | --- | --- |
| T1 Rettifilo | 0.115 | 0.223 | 0.060 | 0.207 | 0.342 | 0.115 |
| T3 Curva Grande | NA | NA | 0.201 | NA | NA | NA |
| T4 Roggia | 0.062 | 0.147 | 0.382 | 0.046 | 0.231 | 0.038 |
| T6 Lesmo 1 | 0.101 | 0.218 | 0.195 | 0.097 | 0.357 | 0.083 |
| T7 Lesmo 2 | 0.051 | 0.147 | 0.204 | 0.040 | 0.172 | 0.011 |
| T8 Ascari | 0.104 | 0.062 | 0.253 | 0.011 | 0.229 | 0.012 |
| T11 Parabolica | 0.114 | 0.042 | 0.289 | NA | 0.261 | 0.013 |

Figuras: `omega2_zonas.png`, `share_team_zonas.png`.

Las doce curvas con mayor ω²(piloto|equipo), con el resto de criterios:

| feature | omega2_driver_in_team | share_team | p_driver_in_team | spearman_brown | teammate_sign_agreement | omega2_compound_within | rho_tyre_life_within | rho_lap_within | zero_frac | max_abs_rho_existing | most_similar_existing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T11__coast_frac | 0.157 | 0.261 | 0.000 | 0.969 | 0.889 | 0.065 | -0.135 | -0.169 | 0.000 | 0.708 | medium__coast_frac |
| T1__coast_frac | 0.153 | 0.342 | 0.000 | 0.969 | 0.889 | 0.066 | -0.096 | -0.193 | 0.000 | 1.000 | slow__coast_frac |
| T11__apex_speed_rel | 0.139 | 0.289 | 0.000 | 0.995 | 0.889 | 0.467 | 0.240 | 0.714 | 0.048 | 0.887 | medium__apex_speed_rel |
| T4__coast_frac | 0.138 | 0.231 | 0.000 | 0.983 | 1.000 | 0.072 | -0.143 | -0.271 | 0.000 | 0.592 | medium__coast_frac |
| T8__coast_frac | 0.124 | 0.229 | 0.000 | 0.985 | 0.778 | 0.077 | -0.225 | -0.343 | 0.000 | 1.000 | fast__coast_frac |
| T6__trail_brake_frac | 0.122 | 0.218 | 0.000 | 0.975 | 0.667 | 0.006 | 0.049 | 0.031 | 0.000 | 0.863 | medium__trail_brake_frac |
| T6__coast_frac | 0.121 | 0.357 | 0.000 | 0.984 | 0.889 | 0.016 | 0.057 | 0.011 | 0.000 | 0.700 | medium__coast_frac |
| T7__coast_frac | 0.121 | 0.172 | 0.000 | 0.906 | 0.889 | -0.003 | 0.038 | 0.005 | 0.000 | 0.644 | medium__coast_frac |
| T8__apex_speed_rel | 0.104 | 0.253 | 0.000 | 0.993 | 0.889 | 0.368 | 0.344 | 0.725 | 0.031 | 0.954 | fast__apex_speed_rel |
| T6__apex_speed_rel | 0.091 | 0.195 | 0.000 | 0.989 | 1.000 | 0.495 | 0.270 | 0.757 | 0.045 | 0.972 | medium__apex_speed_rel |
| T6__throttle_attack | 0.090 | 0.097 | 0.000 | 0.943 | 0.714 | 0.010 | 0.092 | -0.003 | 0.803 | 0.426 | medium__throttle_attack |
| T4__apex_speed_rel | 0.089 | 0.382 | 0.000 | 0.989 | 1.000 | 0.163 | 0.137 | 0.444 | 0.093 | 0.704 | medium__apex_speed_rel |

Pasan el filtro estricto 8 de 42 columnas de curva. El motivo de descarte de cada una está en `zone_selection.csv`.

Columnas que pasan el filtro estricto:

| feature | omega2_driver_in_team | share_team | p_driver_in_team | spearman_brown | teammate_sign_agreement | omega2_compound_within | rho_tyre_life_within | rho_lap_within | zero_frac | max_abs_rho_existing | most_similar_existing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T6__trail_brake_frac | 0.122 | 0.218 | 0.000 | 0.975 | 0.667 | 0.006 | 0.049 | 0.031 | 0.000 | 0.863 | medium__trail_brake_frac |
| T6__coast_frac | 0.121 | 0.357 | 0.000 | 0.984 | 0.889 | 0.016 | 0.057 | 0.011 | 0.000 | 0.700 | medium__coast_frac |
| T7__coast_frac | 0.121 | 0.172 | 0.000 | 0.906 | 0.889 | -0.003 | 0.038 | 0.005 | 0.000 | 0.644 | medium__coast_frac |
| T6__throttle_attack | 0.090 | 0.097 | 0.000 | 0.943 | 0.714 | 0.010 | 0.092 | -0.003 | 0.803 | 0.426 | medium__throttle_attack |
| T7__trail_brake_frac | 0.080 | 0.147 | 0.000 | 0.930 | 0.667 | 0.019 | 0.063 | 0.098 | 0.000 | 0.704 | medium__trail_brake_frac |
| T6__full_throttle_frac | 0.058 | 0.083 | 0.000 | 0.927 | 1.000 | -0.002 | -0.001 | 0.010 | 0.859 | 0.294 | medium__throttle_attack |
| T4__trail_brake_frac | 0.052 | 0.147 | 0.000 | 0.930 | 0.556 | -0.007 | -0.056 | -0.023 | 0.000 | 0.574 | medium__trail_brake_frac |
| T1__trail_brake_frac | 0.040 | 0.223 | 0.000 | 0.957 | 0.889 | 0.007 | 0.075 | 0.073 | 0.000 | 1.000 | slow__trail_brake_frac |

## ¿La mediana de tipología esconde estilo de una curva?

Para cada métrica se compara el agregado de tipología (las 17 columnas actuales, puntuadas con la misma función) con cada curva de esa tipología. `spearman_con_agregado` es el Spearman entre la curva (normalizada por su propia mediana) y la columna de tipología. `frac_en_par_central` es la fracción de vueltas en las que esa curva ocupa uno de los dos puestos centrales cuya media es la mediana del pipeline (con 4 curvas, los dos valores del medio; con 2, ambos). Si una curva queda siempre en un extremo, su estilo no entra en el agregado.

| métrica | tipología | curva | ω² agregado | ω² curva | Δ ω² | SB agregado | SB curva | cuota equipo curva | ρ vuelta curva | spearman con agregado | frac en par central |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| punto de frenada | slow | T1 | 0.040 | 0.040 | -0.000 | 0.926 | 0.926 | 0.115 | -0.509 | 1.000 | 1.000 |
| punto de frenada | medium | T4 | 0.069 | 0.035 | -0.034 | 0.946 | 0.908 | 0.062 | -0.512 | 0.765 | 0.746 |
| punto de frenada | medium | T6 | 0.069 | 0.076 | 0.007 | 0.946 | 0.931 | 0.101 | -0.286 | 0.611 | 0.764 |
| punto de frenada | medium | T7 | 0.069 | 0.042 | -0.027 | 0.946 | 0.839 | 0.051 | -0.136 | 0.253 | 0.124 |
| punto de frenada | medium | T11 | 0.069 | 0.018 | -0.051 | 0.946 | 0.889 | 0.114 | -0.412 | 0.448 | 0.246 |
| punto de frenada | fast | T3 | 0.053 | NA | NA | 0.941 | NA | NA | NA | NA | 0.000 |
| punto de frenada | fast | T8 | 0.053 | 0.053 | -0.000 | 0.941 | 0.941 | 0.104 | -0.509 | 1.000 | 1.000 |
| trail braking | slow | T1 | 0.040 | 0.040 | -0.000 | 0.957 | 0.957 | 0.223 | 0.073 | 1.000 | 1.000 |
| trail braking | medium | T4 | 0.119 | 0.052 | -0.068 | 0.975 | 0.930 | 0.147 | -0.023 | 0.574 | 0.620 |
| trail braking | medium | T6 | 0.119 | 0.122 | 0.002 | 0.975 | 0.975 | 0.218 | 0.031 | 0.863 | 0.730 |
| trail braking | medium | T7 | 0.119 | 0.080 | -0.039 | 0.975 | 0.930 | 0.147 | 0.098 | 0.704 | 0.612 |
| trail braking | medium | T11 | 0.119 | 0.041 | -0.078 | 0.975 | 0.944 | 0.042 | 0.120 | 0.141 | 0.038 |
| trail braking | fast | T3 | 0.007 | NA | NA | 0.783 | NA | NA | NA | NA | 0.999 |
| trail braking | fast | T8 | 0.007 | 0.008 | 0.001 | 0.783 | 0.795 | 0.062 | 0.149 | 0.995 | 1.000 |
| velocidad de ápice | slow | T1 | 0.048 | 0.048 | -0.000 | 0.892 | 0.892 | 0.060 | 0.199 | 1.000 | 1.000 |
| velocidad de ápice | medium | T4 | 0.085 | 0.089 | 0.004 | 0.990 | 0.989 | 0.382 | 0.444 | 0.704 | 0.000 |
| velocidad de ápice | medium | T6 | 0.085 | 0.091 | 0.006 | 0.990 | 0.989 | 0.195 | 0.757 | 0.972 | 0.924 |
| velocidad de ápice | medium | T7 | 0.085 | 0.067 | -0.018 | 0.990 | 0.979 | 0.204 | 0.740 | 0.965 | 1.000 |
| velocidad de ápice | medium | T11 | 0.085 | 0.139 | 0.054 | 0.990 | 0.995 | 0.289 | 0.714 | 0.887 | 0.076 |
| velocidad de ápice | fast | T3 | 0.096 | 0.029 | -0.067 | 0.983 | 0.946 | 0.201 | 0.383 | 0.296 | 1.000 |
| velocidad de ápice | fast | T8 | 0.096 | 0.104 | 0.008 | 0.983 | 0.993 | 0.253 | 0.725 | 0.954 | 1.000 |
| ataque de acelerador | slow | T1 | 0.020 | 0.020 | -0.000 | 0.953 | 0.953 | 0.207 | -0.037 | 1.000 | 1.000 |
| ataque de acelerador | medium | T4 | 0.108 | 0.043 | -0.065 | 0.995 | 0.969 | 0.046 | -0.322 | 0.387 | 0.013 |
| ataque de acelerador | medium | T6 | 0.108 | 0.090 | -0.018 | 0.995 | 0.943 | 0.097 | -0.003 | 0.426 | 0.797 |
| ataque de acelerador | medium | T7 | 0.108 | 0.033 | -0.075 | 0.995 | 0.752 | 0.040 | -0.035 | 0.787 | 0.967 |
| ataque de acelerador | medium | T11 | 0.108 | NA | NA | 0.995 | NA | NA | NA | NA | 0.223 |
| fracción en punto muerto | slow | T1 | 0.153 | 0.153 | -0.000 | 0.969 | 0.969 | 0.342 | -0.193 | 1.000 | 1.000 |
| fracción en punto muerto | medium | T4 | 0.136 | 0.138 | 0.002 | 0.984 | 0.983 | 0.231 | -0.271 | 0.592 | 0.368 |
| fracción en punto muerto | medium | T6 | 0.136 | 0.121 | -0.015 | 0.984 | 0.984 | 0.357 | 0.011 | 0.700 | 0.335 |
| fracción en punto muerto | medium | T7 | 0.136 | 0.121 | -0.015 | 0.984 | 0.906 | 0.172 | 0.005 | 0.644 | 0.631 |
| fracción en punto muerto | medium | T11 | 0.136 | 0.157 | 0.022 | 0.984 | 0.969 | 0.261 | -0.169 | 0.708 | 0.666 |
| fracción en punto muerto | fast | T3 | 0.124 | NA | NA | 0.985 | NA | NA | NA | NA | 1.000 |
| fracción en punto muerto | fast | T8 | 0.124 | 0.124 | -0.000 | 0.985 | 0.985 | 0.229 | -0.343 | 1.000 | 1.000 |
| gas a fondo | slow | T1 | 0.027 | 0.027 | -0.000 | 0.876 | 0.876 | 0.115 | 0.079 | 1.000 | 1.000 |
| gas a fondo | medium | T4 | 0.002 | 0.029 | 0.026 | -0.168 | 0.887 | 0.038 | 0.541 | -0.007 | 0.152 |
| gas a fondo | medium | T6 | 0.002 | 0.058 | 0.056 | -0.168 | 0.927 | 0.083 | 0.010 | 0.186 | 0.859 |
| gas a fondo | medium | T7 | 0.002 | 0.001 | -0.002 | -0.168 | 0.333 | 0.011 | 0.039 | 0.331 | 0.987 |
| gas a fondo | medium | T11 | 0.002 | -0.005 | -0.007 | -0.168 | -0.237 | 0.013 | NA | 0.496 | 0.002 |
| gas a fondo | fast | T3 | 0.018 | NA | NA | -0.118 | NA | NA | NA | NA | 1.000 |
| gas a fondo | fast | T8 | 0.018 | 0.018 | -0.000 | -0.118 | -0.118 | 0.012 | NA | 1.000 | 1.000 |

Lectura de esa tabla:

- `slow` es sólo Rettifilo. Δ ω² ≈ 0 y Spearman ≈ 1 comprueban que T1 y el agregado son la misma columna, salvo el redondeo de la mediana de sesión.
- Entre columnas con fracción de ceros ≤ 0,50 y |ρ| con la vuelta ≤ 0,35, la mayor ganancia sobre el agregado es T11 / fracción en punto muerto (ω² 0.136 → 0.157, Δ = 0.022, Spearman-Brown = 0.969, cuota de equipo = 0.261, ρ con la vuelta = -0.169).
- Sin ese recorte de deriva, el Δ más alto es T6 / gas a fondo (Δ = 0.056, ρ con la vuelta = 0.010). Ese máximo sale de comparar contra un agregado casi constante o de una velocidad de ápice que sigue al número de vuelta. No es un rasgo de estilo nuevo.
- La mayor pérdida, en el mismo recorte, es T4 / trail braking (Δ = -0.068): esa curva, sola, separa menos a los compañeros que el agregado. Ahí la mediana de tipología está promediando ruido, no escondiendo un rasgo.
- Un Δ grande contra un agregado que ya es casi constante (ataque de acelerador y gas a fondo de `medium`, con más del 95 % de ceros) no cuenta como estilo recuperado: la curva sigue siendo dispersa. Lesmo 1 en gas a fondo sube de 0,002 a 0,058 con un 86 % de ceros; no entra en el vector.
- Curvas que casi nunca ocupan el par central de la mediana (su nivel queda en un extremo y el agregado no las usa): T3 en punto de frenada (fast, 0.00); T4 en velocidad de ápice (medium, 0.00); T11 en gas a fondo (medium, 0.00); T4 en ataque de acelerador (medium, 0.01); T11 en trail braking (medium, 0.04); T11 en velocidad de ápice (medium, 0.08); T7 en punto de frenada (medium, 0.12).

Mediana que queda en cada curva **después** de restar la mediana de tipología (no la de la curva). Si las medianas no se solapan, la mediana entre curvas es una curva fija, no una mezcla de estilos:

| metric | zone | typology | nan_frac | median | q25 | q75 |
| --- | --- | --- | --- | --- | --- | --- |
| punto de frenada | T1 | slow | 0.000 | 0.000 | -13.913 | 15.032 |
| punto de frenada | T11 | medium | 0.001 | 30.131 | 17.794 | 42.248 |
| punto de frenada | T3 | fast | 1.000 | NA | NA | NA |
| punto de frenada | T4 | medium | 0.005 | 15.696 | 4.895 | 26.486 |
| punto de frenada | T6 | medium | 0.011 | -15.129 | -23.507 | -6.474 |
| punto de frenada | T7 | medium | 0.107 | -29.736 | -37.063 | -23.149 |
| punto de frenada | T8 | fast | 0.000 | 0.000 | -9.773 | 13.787 |
| trail braking | T1 | slow | 0.000 | 0.000 | -0.037 | 0.039 |
| trail braking | T11 | medium | 0.000 | -0.346 | -0.346 | -0.346 |
| trail braking | T3 | fast | 0.001 | 0.000 | 0.000 | 0.000 |
| trail braking | T4 | medium | 0.000 | 0.055 | 0.018 | 0.091 |
| trail braking | T6 | medium | 0.000 | -0.010 | -0.094 | 0.093 |
| trail braking | T7 | medium | 0.000 | 0.056 | -0.023 | 0.140 |
| trail braking | T8 | fast | 0.000 | 0.197 | 0.171 | 0.224 |
| velocidad de ápice | T1 | slow | 0.000 | 0.000 | -2.000 | 1.000 |
| velocidad de ápice | T11 | medium | 0.000 | 14.000 | 7.000 | 20.000 |
| velocidad de ápice | T3 | fast | 0.000 | 67.000 | 66.000 | 69.000 |
| velocidad de ápice | T4 | medium | 0.000 | -74.000 | -76.000 | -71.000 |
| velocidad de ápice | T6 | medium | 0.000 | 9.000 | 3.000 | 14.000 |
| velocidad de ápice | T7 | medium | 0.000 | -5.000 | -10.000 | 0.000 |
| velocidad de ápice | T8 | fast | 0.000 | -54.000 | -60.000 | -47.000 |
| fracción en punto muerto | T1 | slow | 0.000 | -0.000 | -0.022 | 0.041 |
| fracción en punto muerto | T11 | medium | 0.000 | -0.006 | -0.029 | 0.016 |
| fracción en punto muerto | T3 | fast | 0.000 | 0.000 | 0.000 | 0.000 |
| fracción en punto muerto | T4 | medium | 0.000 | 0.002 | -0.016 | 0.041 |
| fracción en punto muerto | T6 | medium | 0.000 | 0.007 | -0.029 | 0.040 |
| fracción en punto muerto | T7 | medium | 0.000 | 0.002 | -0.029 | 0.023 |
| fracción en punto muerto | T8 | fast | 0.000 | 0.019 | 0.000 | 0.039 |

Esos niveles, no el estilo, explican qué entra en la mediana. En velocidad de ápice, Roggia queda unos 74 km/h por debajo del agregado medium y no ocupa el par central en ninguna vuelta; Parabolica entra en el 8 %. `medium__apex_speed_rel` es Lesmo 1 y Lesmo 2 (Spearman 0,97 y 0,96 con el agregado). Curva Grande queda unos +67 km/h y Ascari unos −54 km/h: `fast__apex` es la media de dos curvas que no se solapan, y la variación la pone Ascari (Spearman 0,95) y no Curva Grande (0,30; IQR residual de unos 3 km/h). En el punto de frenada, Lesmo 2 queda unos −30 m y entra en el par central el 12 % de las vueltas; Parabolica queda unos +30 m. El agregado medium de frenada es Roggia y Lesmo 1. Nadie frena en la ventana de Curva Grande, así que `fast__brake_point_rel` es Ascari (Spearman 1). En trail braking, Parabolica es un punto (P25 = mediana = P75) y entra en el par central el 4 %; el agregado correlaciona 0,86 con Lesmo 1 y 0,14 con Parabolica. En coast los residuos sí se solapan alrededor de 0: ahí la mediana mezcla curvas de verdad, no se queda con una sola.

## Correlación entre curvas, dentro del piloto y entre pilotos

Dos preguntas distintas. La correlación **dentro** del piloto (Pearson de las series demediadas por piloto; también la media de Spearmans por piloto) dice si, en una vuelta concreta, ir temprano en una curva va con ir temprano en otra. La correlación **entre** pilotos (Spearman de las medianas de piloto) dice si el ranking de estilo se conserva de una curva a otra. `frac_drivers_opposite_sign` es la fracción de pilotos cuya mediana queda por encima del pelotón en una curva y por debajo en la otra. `frac_teams_order_flip` es la fracción de parejas de compañeros cuyo orden se invierte entre las dos curvas (0,5 ≈ azar).

Pares de la **misma** tipología:

| metric | zone_a | zone_b | typology_a | r_within_pooled | r_within_mean_spearman | r_between_spearman | frac_drivers_opposite_sign | frac_teams_order_flip | n_teams_flip |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| velocidad de ápice | T3 | T8 | fast | 0.102 | 0.162 | -0.153 | 0.667 | 0.667 | 3 |
| velocidad de ápice | T4 | T11 | medium | 0.497 | 0.473 | 0.784 | 0.235 | 0.167 | 6 |
| velocidad de ápice | T4 | T6 | medium | 0.580 | 0.536 | 0.753 | 0.278 | 0.167 | 6 |
| velocidad de ápice | T4 | T7 | medium | 0.564 | 0.524 | 0.839 | 0.250 | 0.000 | 4 |
| velocidad de ápice | T6 | T11 | medium | 0.767 | 0.722 | 0.952 | 0.056 | 0.000 | 9 |
| velocidad de ápice | T6 | T7 | medium | 0.833 | 0.762 | 0.923 | 0.118 | 0.143 | 7 |
| velocidad de ápice | T7 | T11 | medium | 0.779 | 0.707 | 0.921 | 0.125 | 0.143 | 7 |
| punto de frenada | T3 | T8 | fast | NA | NA | NA | NA | NA | 0 |
| punto de frenada | T4 | T11 | medium | 0.273 | 0.262 | 0.602 | 0.211 | 0.111 | 9 |
| punto de frenada | T4 | T6 | medium | 0.251 | 0.269 | 0.382 | 0.389 | 0.111 | 9 |
| punto de frenada | T4 | T7 | medium | 0.127 | 0.098 | 0.121 | 0.579 | 0.333 | 9 |
| punto de frenada | T6 | T11 | medium | 0.147 | 0.152 | 0.474 | 0.444 | 0.222 | 9 |
| punto de frenada | T6 | T7 | medium | 0.098 | 0.121 | 0.635 | 0.333 | 0.222 | 9 |
| punto de frenada | T7 | T11 | medium | 0.089 | 0.079 | 0.218 | 0.474 | 0.222 | 9 |
| fracción en punto muerto | T3 | T8 | fast | NA | NA | NA | NA | NA | 0 |
| fracción en punto muerto | T4 | T11 | medium | 0.122 | 0.085 | 0.680 | 0.316 | 0.375 | 8 |
| fracción en punto muerto | T4 | T6 | medium | 0.094 | 0.052 | 0.083 | 0.474 | 0.714 | 7 |
| fracción en punto muerto | T4 | T7 | medium | 0.052 | -0.010 | 0.265 | 0.474 | 0.625 | 8 |
| fracción en punto muerto | T6 | T11 | medium | 0.045 | 0.004 | 0.505 | 0.263 | 0.286 | 7 |
| fracción en punto muerto | T6 | T7 | medium | 0.030 | 0.062 | 0.909 | 0.105 | 0.000 | 7 |
| fracción en punto muerto | T7 | T11 | medium | 0.026 | 0.004 | 0.645 | 0.368 | 0.250 | 8 |
| gas a fondo | T3 | T8 | fast | NA | NA | NA | NA | NA | 0 |
| gas a fondo | T4 | T11 | medium | -0.002 | NA | NA | NA | NA | 0 |
| gas a fondo | T4 | T6 | medium | -0.026 | -0.082 | NA | NA | NA | 0 |
| gas a fondo | T4 | T7 | medium | -0.001 | NA | NA | NA | NA | 0 |
| gas a fondo | T6 | T11 | medium | 0.035 | NA | NA | NA | NA | 0 |
| gas a fondo | T6 | T7 | medium | 0.013 | 0.074 | NA | NA | NA | 0 |
| gas a fondo | T7 | T11 | medium | -0.002 | NA | NA | NA | NA | 0 |
| ataque de acelerador | T3 | T8 | fast | NA | NA | NA | NA | NA | 0 |
| ataque de acelerador | T4 | T11 | medium | NA | NA | NA | NA | NA | 0 |
| ataque de acelerador | T4 | T6 | medium | 0.039 | 0.120 | NA | NA | NA | 0 |
| ataque de acelerador | T4 | T7 | medium | -0.003 | 0.195 | NA | NA | NA | 0 |
| ataque de acelerador | T6 | T11 | medium | NA | NA | NA | NA | NA | 0 |
| ataque de acelerador | T6 | T7 | medium | -0.003 | 0.047 | NA | NA | NA | 0 |
| ataque de acelerador | T7 | T11 | medium | NA | NA | NA | NA | NA | 0 |
| trail braking | T3 | T8 | fast | NA | NA | NA | NA | NA | 0 |
| trail braking | T4 | T11 | medium | 0.016 | -0.006 | NA | NA | NA | 0 |
| trail braking | T4 | T6 | medium | 0.269 | 0.292 | 0.188 | 0.368 | 0.222 | 9 |
| trail braking | T4 | T7 | medium | 0.247 | 0.268 | 0.502 | 0.158 | 0.444 | 9 |
| trail braking | T6 | T11 | medium | 0.034 | 0.029 | NA | NA | NA | 0 |
| trail braking | T6 | T7 | medium | 0.250 | 0.233 | 0.654 | 0.316 | 0.222 | 9 |
| trail braking | T7 | T11 | medium | 0.033 | 0.092 | NA | NA | NA | 0 |

- fracción en punto muerto, pares de la misma tipología: r dentro (pooled) medio = 0.062, r entre pilotos medio = 0.514, fracción media de pilotos con signo opuesto = 0.333, inversión media del orden entre compañeros = 0.375.
- punto de frenada, pares de la misma tipología: r dentro (pooled) medio = 0.164, r entre pilotos medio = 0.405, fracción media de pilotos con signo opuesto = 0.405, inversión media del orden entre compañeros = 0.204.
- trail braking, pares de la misma tipología: r dentro (pooled) medio = 0.141, r entre pilotos medio = 0.448, fracción media de pilotos con signo opuesto = 0.281, inversión media del orden entre compañeros = 0.296.
- velocidad de ápice, pares de la misma tipología: r dentro (pooled) medio = 0.589, r entre pilotos medio = 0.717, fracción media de pilotos con signo opuesto = 0.247, inversión media del orden entre compañeros = 0.184.

Pilotos con signo opuesto en el coast, mediana ya restada la mediana de la curva, y |mediana| ≥ 0,02 en Roggia y en Lesmo 1. Positivo = más punto muerto que el pelotón:

| piloto | equipo | T4 Roggia coast | T6 Lesmo 1 coast | T7 Lesmo 2 coast | T11 Parabolica coast | T1 Rettifilo frenada (m) | T8 Ascari frenada (m) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ANT | Mercedes | 0.052 | -0.035 | -0.020 | 0.023 | -4.947 | -6.493 |
| ALO | Aston Martin | 0.050 | -0.035 | -0.030 | 0.015 | 5.078 | 2.229 |

El hábito de coast no viaja de Roggia a Lesmo 1. Lesmo 1 y Lesmo 2, en cambio, ordenan a los pilotos casi igual (Spearman entre pilotos 0,91; sólo 2 de 19 con signo opuesto). En el punto de frenada el contraste Rettifilo contra Ascari no da un solo piloto con |mediana| > 3 m y signo opuesto en las dos: los cambios de signo que hay son de 1–2 m en una de las dos curvas, del orden del muestreo (~20 m a 300 km/h en una vuelta; la mediana de la carrera afina, pero no hasta convertir 1 m en un estilo). Stroll frena temprano en las dos (+23 m y +18 m); Verstappen, tarde en las dos. Las medianas están en `driver_zone_medians.csv`.

En coast, el par de la misma tipología con el ranking de pilotos **menos** compartido es T4–T6 (medium): Spearman entre pilotos = 0.083, r dentro = 0.094. El más compartido es T6–T7: Spearman entre pilotos = 0.909.

## Reemplazo del vector y clustering

Todos los ajustes son K-means en z-score, sin PCA. La brecha es silueta observada menos silueta del nulo (cada columna permutada por separado, se conservan las marginales). PS es prediction strength (Tibshirani y Walther; por encima de ~0,8 la partición se reproduce en mitades). AMI es información mutua ajustada con el piloto. `teammate_split_rate` es la fracción de equipos de dos pilotos cuya moda de clase no coincide.

Conjuntos, fijados antes de mirar la silueta:

- `base7`: las 7 columnas con ICC(1) ≥ 0,25. Es el vector de referencia (ápice fast/medium, coast slow/medium/fast, trail slow/medium).
- `analogue7`: para cada una de esas 7, la curva de la misma tipología y métrica con mayor ω²(piloto|equipo), siempre que no sea casi constante y tenga cobertura ≥ 0,95. Misma dimensión. Es el test directo de granularidad. Elige la curva con los mismos datos que luego se agrupan: hay un sesgo de selección pequeño.
- `expand`: todas las curvas que componen esas 7 columnas, quitando sólo las casi constantes o con cobertura < 0,95. No elige ganadores. Más columnas: la silueta bruta tiende a bajar; se mira la brecha.
- `strict7`: hasta 7 columnas de curva del filtro estricto, las de mayor ω², con |Spearman| mutuo < 0,75 (voraz). Si el filtro estricto deja menos de 2, el conjunto no se ajusta.
- `strict_dense`: las mismas que pasan el filtro estricto con fracción de ceros ≤ 0,50. Es un corte posterior: `strict7` todavía admite el ataque de acelerador y el gas a fondo de Lesmo 1, que son dispersos. Sirve para no achacar la brecha negativa sólo a esos ceros.
- `base7+cons3` y `cons5`: la consistencia móvil, abajo.

- `base7` (7): fast__apex_speed_rel, medium__apex_speed_rel, fast__coast_frac, medium__coast_frac, slow__coast_frac, medium__trail_brake_frac, slow__trail_brake_frac
- `analogue7` (7): T8__apex_speed_rel, T11__apex_speed_rel, T8__coast_frac, T11__coast_frac, T1__coast_frac, T6__trail_brake_frac, T1__trail_brake_frac
- `expand` (16): T3__apex_speed_rel, T8__apex_speed_rel, T4__apex_speed_rel, T6__apex_speed_rel, T7__apex_speed_rel, T11__apex_speed_rel, T8__coast_frac, T4__coast_frac, T6__coast_frac, T7__coast_frac, T11__coast_frac, T1__coast_frac, T4__trail_brake_frac, T6__trail_brake_frac, T7__trail_brake_frac, T1__trail_brake_frac
- `strict7` (7): T6__trail_brake_frac, T6__coast_frac, T7__coast_frac, T6__throttle_attack, T7__trail_brake_frac, T6__full_throttle_frac, T4__trail_brake_frac
- `strict_dense` (6): T6__coast_frac, T7__coast_frac, T7__trail_brake_frac, T4__trail_brake_frac, T6__trail_brake_frac, T1__trail_brake_frac
- `cons5` (5): T7__coast_frac__roll_mad5, T7__coast_frac__roll_iqr5, T11__coast_frac__roll_mad5, T6__coast_frac__roll_mad5, T6__coast_frac__roll_iqr5
- `base7+cons3` (10): fast__apex_speed_rel, medium__apex_speed_rel, fast__coast_frac, medium__coast_frac, slow__coast_frac, medium__trail_brake_frac, slow__trail_brake_frac, T7__coast_frac__roll_mad5, T7__coast_frac__roll_iqr5, T11__coast_frac__roll_mad5

| set | n_features | n_laps | k | sizes | silhouette | null_silhouette | silhouette_gap | prediction_strength | bootstrap_ari | ami_driver | ami_compound | teammate_split_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base7 | 7 | 842 | 2 | [502, 340] | 0.256 | 0.112 | 0.145 | 0.895 | 0.937 | 0.126 | -0.001 | 0.333 |
| base7 | 7 | 842 | 3 | [311, 281, 250] | 0.204 | 0.109 | 0.094 | 0.688 | 0.838 | 0.198 | 0.009 | 0.556 |
| base7 | 7 | 842 | 4 | [250, 206, 195, 191] | 0.175 | 0.115 | 0.060 | 0.533 | 0.706 | 0.202 | 0.010 | 0.444 |
| analogue7 | 7 | 842 | 2 | [491, 351] | 0.249 | 0.116 | 0.133 | 0.772 | 0.792 | 0.111 | 0.000 | 0.222 |
| analogue7 | 7 | 842 | 3 | [345, 257, 240] | 0.205 | 0.110 | 0.094 | 0.688 | 0.845 | 0.200 | 0.010 | 0.667 |
| analogue7 | 7 | 842 | 4 | [249, 225, 192, 176] | 0.173 | 0.117 | 0.056 | 0.502 | 0.695 | 0.194 | 0.009 | 0.556 |
| expand | 16 | 842 | 2 | [487, 355] | 0.207 | 0.049 | 0.158 | 0.899 | 0.938 | 0.117 | 0.000 | 0.222 |
| expand | 16 | 842 | 3 | [359, 242, 241] | 0.162 | 0.048 | 0.115 | 0.771 | 0.883 | 0.222 | 0.010 | 0.667 |
| expand | 16 | 842 | 4 | [262, 200, 196, 184] | 0.119 | 0.047 | 0.072 | 0.454 | 0.718 | 0.239 | 0.016 | 0.333 |
| strict7 | 7 | 842 | 2 | [426, 416] | 0.217 | 0.223 | -0.007 | 0.840 | 0.935 | 0.129 | 0.006 | 0.222 |
| strict7 | 7 | 842 | 3 | [392, 359, 91] | 0.239 | 0.199 | 0.039 | 0.741 | 0.828 | 0.132 | 0.000 | 0.556 |
| strict7 | 7 | 842 | 4 | [350, 209, 193, 90] | 0.176 | 0.147 | 0.028 | 0.588 | 0.716 | 0.146 | 0.005 | 0.667 |
| strict_dense | 6 | 842 | 2 | [468, 374] | 0.236 | 0.124 | 0.112 | 0.758 | 0.911 | 0.117 | 0.007 | 0.222 |
| strict_dense | 6 | 842 | 3 | [374, 238, 230] | 0.162 | 0.124 | 0.039 | 0.650 | 0.792 | 0.131 | 0.006 | 0.667 |
| strict_dense | 6 | 842 | 4 | [247, 220, 214, 161] | 0.157 | 0.122 | 0.035 | 0.421 | 0.620 | 0.144 | 0.001 | 0.667 |
| cons5 | 5 | 825 | 2 | [458, 367] | 0.303 | 0.179 | 0.124 | 0.793 | 0.855 | 0.108 | 0.003 | 0.667 |
| cons5 | 5 | 825 | 3 | [375, 240, 210] | 0.304 | 0.170 | 0.134 | 0.717 | 0.885 | 0.105 | -0.001 | 0.667 |
| cons5 | 5 | 825 | 4 | [310, 179, 169, 167] | 0.297 | 0.173 | 0.124 | 0.557 | 0.645 | 0.117 | 0.005 | 0.778 |
| base7+cons3 | 10 | 825 | 2 | [520, 305] | 0.222 | 0.078 | 0.144 | 0.848 | 0.893 | 0.142 | -0.002 | 0.444 |
| base7+cons3 | 10 | 825 | 3 | [302, 267, 256] | 0.167 | 0.076 | 0.091 | 0.837 | 0.904 | 0.219 | 0.007 | 0.556 |
| base7+cons3 | 10 | 825 | 4 | [284, 209, 208, 124] | 0.155 | 0.080 | 0.075 | 0.507 | 0.669 | 0.227 | 0.012 | 0.667 |

La base reproduce el diagnóstico ya conocido: k=2 silueta 0.256 (nulo 0.112, brecha 0.145, PS 0.895, AMI piloto 0.126, split de compañeros 0.333). En k=3: silueta 0.204, PS 0.688, AMI 0.198, split 0.556.

`analogue7` en k=2: silueta 0.249, nulo 0.116, brecha 0.133 (base 0.145), PS 0.772 (base 0.895), ARI bootstrap 0.792 (base 0.937), AMI piloto 0.111 (base 0.126), split 0.222 (base 0.333), AMI compuesto 0.000.

`analogue7` en k=3: silueta 0.205, brecha 0.094 (base 0.094), PS 0.688 (base 0.688), AMI piloto 0.200 (base 0.198), split 0.667 (base 0.556).

`expand` (16 columnas) en k=2: silueta 0.207, brecha 0.158, PS 0.899, AMI piloto 0.117, split 0.222 (base 0.333). La brecha sube (0.145 → 0.158) porque el nulo cae (0.112 → 0.049) al pasar a 16 columnas, no porque la silueta observada suba: baja de 0.256 a 0.207. El split de compañeros empeora. No es una partición mejor; es un nulo más bajo en más dimensiones.

`strict7` (sólo curvas con señal de compañero, fiabilidad y poca deriva) en k=2: silueta 0.217, brecha -0.007, PS 0.840, AMI piloto 0.129, split 0.222. Deja fuera el ápice, que arrastra combustible. La brecha en k=2 queda por debajo del nulo: el conjunto estricto mete además `T6__throttle_attack` (80 % de ceros) y `T6__full_throttle_frac` (86 % de ceros), y esas marginales ya forman grumos. `strict_dense` quita esas dos y se comenta abajo.

`strict_dense` (el filtro estricto y, además, fracción de ceros ≤ 0,50; es un corte posterior, para ver si la brecha negativa era sólo la inflación de ceros) en k=2: silueta 0.236, nulo 0.124, brecha 0.112 (base 0.145), PS 0.758 (base 0.895), AMI piloto 0.117, split 0.222. Sigue por debajo de la base. El coast y el trail limpios, por curva, no reconstruyen la partición que arma el ápice junto con el coast agregado.

El evaluador oficial, por su lado, añade a las 7 columnas base las candidatas con `recommended=True` (eso incluye el filtro de redundancia |ρ| < 0,80 con las 17 columnas, que las curvas suelen fallar). Resultado en `candidates_gain.csv`:

| set | n_features | n_laps | k | sizes | silhouette | null_silhouette | silhouette_gap | prediction_strength | bootstrap_ari | ami_driver | ami_compound | teammate_split_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base | 7 | 820 | 2 | [484, 336] | 0.259 | 0.111 | 0.147 | 0.904 | 0.918 | 0.131 | -0.001 | 0.333 |
| base | 7 | 820 | 3 | [305, 271, 244] | 0.207 | 0.110 | 0.097 | 0.655 | 0.811 | 0.205 | 0.005 | 0.556 |
| base | 7 | 820 | 4 | [236, 208, 201, 175] | 0.178 | 0.112 | 0.066 | 0.512 | 0.739 | 0.221 | 0.008 | 0.444 |
| base+extra | 32 | 820 | 2 | [417, 403] | 0.115 | 0.028 | 0.087 | 0.725 | 0.741 | 0.151 | 0.004 | 0.333 |
| base+extra | 32 | 820 | 3 | [325, 252, 243] | 0.071 | 0.033 | 0.038 | 0.593 | 0.721 | 0.258 | 0.005 | 0.556 |
| base+extra | 32 | 820 | 4 | [296, 208, 160, 156] | 0.078 | 0.026 | 0.052 | 0.536 | 0.764 | 0.263 | 0.011 | 0.667 |

Candidatas marcadas `recommended` por el evaluador (25): T7__coast_frac__roll_mad5, T7__coast_frac__roll_iqr5, T6__coast_frac, T7__coast_frac, T6__coast_frac__roll_mad5, T6__coast_frac__roll_iqr5, T11__coast_frac__roll_iqr5, T6__throttle_attack, medium__trail_brake_frac__roll_iqr5, T7__trail_brake_frac, medium__coast_frac__roll_iqr5, medium__coast_frac__roll_mad5, medium__brake_point_rel__roll_mad5, T6__full_throttle_frac, T7__coast_frac__absdev_rollmed5, sector2_time__roll_std5, T4__trail_brake_frac, T6__coast_frac__absdev_rollmed5, slow__coast_frac__absdev_rollmed5, T1__coast_frac__absdev_rollmed5, medium__apex_speed_rel__roll_mad5, T11__coast_frac__absdev_rollmed5, T6__trail_brake_frac__roll_mad5, medium__trail_brake_frac__roll_mad5, T4__brake_point_rel__roll_iqr5.
Meterlas todas encima de las 7 columnas empeora la partición: en k=2 la brecha pasa de 0.147 a 0.087 y la silueta de 0.259 a 0.115 (32 columnas, 820 vueltas). El filtro `recommended` no es un vector de clustering.

## Consistencia como rasgo de estilo

Se puntúan IQR móvil, MAD móvil y desviación absoluta a la mediana móvil. La desviación absoluta describe la vuelta rara, no un nivel estable del piloto: se espera ω² bajo. El IQR y la MAD de ventanas solapadas se parecen a una constante por piloto y por eso inflan ICC y Spearman-Brown.

Quince métricas de consistencia con mayor ω²(piloto|equipo):

| feature | omega2_driver_in_team | share_team | p_driver_in_team | spearman_brown | teammate_sign_agreement | omega2_compound_within | rho_tyre_life_within | rho_lap_within | zero_frac | max_abs_rho_existing | most_similar_existing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T7__coast_frac__roll_mad5 | 0.163 | 0.110 | 0.000 | 0.968 | 1.000 | 0.006 | -0.042 | 0.042 | 0.314 | 0.418 | medium__coast_frac |
| T7__coast_frac__roll_iqr5 | 0.157 | 0.118 | 0.000 | 0.970 | 0.778 | 0.042 | -0.078 | -0.023 | 0.201 | 0.362 | medium__coast_frac |
| T11__trail_brake_frac__roll_iqr5 | 0.124 | 0.116 | 0.000 | 1.000 | 1.000 | -0.019 | 0.304 | 0.304 | 0.980 | 0.196 | medium__trail_brake_frac |
| T11__coast_frac__roll_mad5 | 0.119 | 0.181 | 0.000 | 0.990 | 1.000 | 0.085 | -0.057 | -0.109 | 0.333 | 0.519 | medium__coast_frac |
| T6__coast_frac__roll_mad5 | 0.109 | 0.248 | 0.000 | 0.992 | 1.000 | 0.018 | 0.020 | 0.032 | 0.405 | 0.560 | medium__coast_frac |
| T6__coast_frac__roll_iqr5 | 0.105 | 0.256 | 0.000 | 0.993 | 0.889 | 0.041 | 0.000 | 0.062 | 0.276 | 0.511 | medium__coast_frac |
| T11__coast_frac__roll_iqr5 | 0.093 | 0.189 | 0.000 | 0.982 | 1.000 | 0.044 | -0.062 | -0.100 | 0.207 | 0.455 | medium__coast_frac |
| fast__coast_frac__roll_iqr5 | 0.089 | 0.144 | 0.000 | 0.991 | 1.000 | 0.078 | -0.201 | -0.232 | 0.195 | 0.441 | fast__coast_frac |
| T8__coast_frac__roll_iqr5 | 0.089 | 0.144 | 0.000 | 0.991 | 1.000 | 0.078 | -0.201 | -0.232 | 0.195 | 0.441 | fast__coast_frac |
| medium__trail_brake_frac__roll_iqr5 | 0.089 | 0.050 | 0.000 | 0.925 | 1.000 | 0.044 | -0.045 | 0.049 | 0.020 | 0.161 | medium__coast_frac |
| T1__coast_frac__roll_mad5 | 0.084 | 0.165 | 0.000 | 0.901 | 0.889 | 0.056 | -0.134 | -0.207 | 0.020 | 0.426 | slow__coast_frac |
| slow__coast_frac__roll_mad5 | 0.084 | 0.165 | 0.000 | 0.901 | 0.889 | 0.056 | -0.134 | -0.207 | 0.020 | 0.426 | slow__coast_frac |
| T1__coast_frac__roll_iqr5 | 0.080 | 0.171 | 0.000 | 0.981 | 1.000 | 0.094 | -0.122 | -0.223 | 0.020 | 0.458 | slow__coast_frac |
| slow__coast_frac__roll_iqr5 | 0.080 | 0.171 | 0.000 | 0.981 | 1.000 | 0.094 | -0.122 | -0.223 | 0.020 | 0.458 | slow__coast_frac |
| T8__coast_frac__roll_mad5 | 0.078 | 0.183 | 0.000 | 0.984 | 0.889 | 0.063 | -0.238 | -0.305 | 0.329 | 0.546 | fast__coast_frac |

Pasan el filtro estricto 19 métricas de consistencia (de 124).

- Mejor IQR móvil: `T7__coast_frac__roll_iqr5`, ω² = 0.157, cuota de equipo = 0.118, Spearman-Brown = 0.970, acuerdo de signo = 0.778, ω² compuesto = 0.042, ρ vuelta = -0.023, ρ vida = -0.078, ceros = 0.201.
- Mejor MAD móvil: `T7__coast_frac__roll_mad5`, ω² = 0.163, cuota de equipo = 0.110, Spearman-Brown = 0.968, acuerdo de signo = 1.000, ω² compuesto = 0.006, ρ vuelta = 0.042, ρ vida = -0.042, ceros = 0.314.
- Mejor desviación absoluta a la mediana móvil: `T7__coast_frac__absdev_rollmed5`, ω² = 0.058, cuota de equipo = 0.046, Spearman-Brown = 0.769, acuerdo de signo = 0.889, ω² compuesto = -0.005, ρ vuelta = 0.039, ρ vida = -0.044, ceros = 0.365.

Clustering sólo con las mejores consistencias móviles (`cons5`, 5 columnas) en k=2: silueta 0.303, brecha 0.124, PS 0.793, AMI piloto 0.108, split 0.667. Si la brecha es pequeña y la AMI con el piloto no supera a la base, la dispersión no define clases de estilo.

Añadir las 3 mejores consistencias a las 7 columnas base, k=2: brecha 0.144 (base 0.145), PS 0.848 (base 0.895), AMI piloto 0.142 (base 0.126).

## Tiempos de sector

Todas las 842 vueltas tienen `TrackStatus` 1 y tiempos entre 80,9 s y 86,8 s: no hay coche de seguridad en esta matriz. Aun así, la dispersión del tiempo es rendimiento (tráfico, gestión, coche), no una elección de frenada.

| feature | omega2_driver_in_team | share_team | p_driver_in_team | spearman_brown | teammate_sign_agreement | omega2_compound_within | rho_tyre_life_within | rho_lap_within | zero_frac | max_abs_rho_existing | most_similar_existing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sector2_time__roll_std5 | 0.052 | 0.076 | 0.000 | 0.969 | 0.889 | 0.024 | -0.253 | -0.254 | 0.020 | 0.299 | medium__apex_speed_rel |
| sector3_time__roll_std5 | 0.034 | 0.097 | 0.000 | 0.967 | 0.778 | 0.094 | -0.190 | -0.132 | 0.020 | 0.160 | fast__apex_speed_rel |
| lap_time__roll_std5 | 0.021 | 0.061 | 0.001 | 0.960 | 1.000 | 0.083 | -0.222 | -0.155 | 0.020 | 0.190 | fast__apex_speed_rel |
| sector1_time__roll_std5 | 0.017 | 0.033 | 0.005 | 0.942 | 1.000 | 0.187 | -0.304 | -0.171 | 0.020 | 0.259 | medium__apex_speed_rel |

Spearman entre la mediana por piloto de `lap_time__roll_std5` y la mediana de su tiempo de vuelta: 0.247. Con la posición mediana: 0.519. Una correlación clara con el ritmo indicaría que los coches rápidos son más estables, no que el piloto tenga un estilo más repetible.

## Bloques de 5 vueltas

Hay 161 bloques completos de 5 vueltas observadas (los restos de stint se tiran). La mediana del bloque es la unidad que ya mejoraba la silueta de las 7 columnas en el benchmark de separación. Aquí se repite esa unidad con el vector análogo y con el expandido, y se puntúa el IQR interno del bloque como rasgo de consistencia.

| set | n_features | n_laps | k | sizes | silhouette | null_silhouette | silhouette_gap | prediction_strength | bootstrap_ari | ami_driver | ami_compound | teammate_split_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| block_base7 | 7 | 161 | 2 | [101, 60] | 0.308 | 0.119 | 0.189 | 0.719 | 0.917 | 0.124 | -0.008 | 0.444 |
| block_base7 | 7 | 161 | 3 | [63, 49, 49] | 0.259 | 0.116 | 0.143 | 0.515 | 0.806 | 0.205 | -0.009 | 0.444 |
| block_base7 | 7 | 161 | 4 | [49, 41, 37, 34] | 0.238 | 0.121 | 0.118 | 0.462 | 0.791 | 0.253 | -0.004 | 0.444 |
| block_analogue7 | 7 | 161 | 2 | [100, 61] | 0.289 | 0.122 | 0.167 | 0.701 | 0.818 | 0.149 | -0.010 | 0.333 |
| block_analogue7 | 7 | 161 | 3 | [64, 55, 42] | 0.260 | 0.124 | 0.135 | 0.616 | 0.876 | 0.242 | -0.004 | 0.556 |
| block_analogue7 | 7 | 161 | 4 | [53, 39, 37, 32] | 0.233 | 0.130 | 0.103 | 0.467 | 0.627 | 0.277 | -0.007 | 0.444 |
| block_expand | 16 | 161 | 2 | [103, 58] | 0.250 | 0.059 | 0.191 | 0.752 | 0.906 | 0.124 | -0.010 | 0.111 |
| block_expand | 16 | 161 | 3 | [73, 46, 42] | 0.232 | 0.056 | 0.176 | 0.622 | 0.886 | 0.257 | -0.002 | 0.444 |
| block_expand | 16 | 161 | 4 | [59, 42, 32, 28] | 0.185 | 0.058 | 0.127 | 0.514 | 0.619 | 0.290 | 0.004 | 0.222 |
| block_iqr | 3 | 161 | 2 | [102, 59] | 0.332 | 0.245 | 0.087 | 0.835 | 0.930 | 0.062 | -0.010 | 0.222 |
| block_iqr | 3 | 161 | 3 | [85, 42, 34] | 0.307 | 0.266 | 0.041 | 0.411 | 0.608 | 0.105 | -0.007 | 0.667 |
| block_iqr | 3 | 161 | 4 | [80, 38, 25, 18] | 0.282 | 0.291 | -0.008 | 0.373 | 0.397 | 0.147 | -0.004 | 0.333 |

Doce IQR de bloque con mayor ω²(piloto|equipo). El Spearman-Brown aquí no está inflado por ventanas solapadas:

| feature | omega2_driver_in_team | share_team | p_driver_in_team | spearman_brown | teammate_sign_agreement | omega2_compound_within | rho_tyre_life_within | rho_lap_within | zero_frac | max_abs_rho_existing | most_similar_existing |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T7__coast_frac__block_iqr5 | 0.154 | 0.091 | 0.000 | 0.544 | 0.556 | -0.035 | -0.155 | -0.031 | 0.205 | 0.389 | medium__coast_frac |
| medium__coast_frac__block_iqr5 | 0.132 | 0.240 | 0.000 | 0.798 | 0.778 | -0.048 | -0.031 | -0.090 | 0.118 | 0.360 | medium__coast_frac |
| fast__coast_frac__block_iqr5 | 0.098 | 0.188 | 0.001 | 0.712 | 0.667 | 0.025 | -0.149 | -0.210 | 0.205 | 0.549 | fast__coast_frac |
| T8__coast_frac__block_iqr5 | 0.098 | 0.188 | 0.001 | 0.712 | 0.667 | 0.025 | -0.149 | -0.210 | 0.205 | 0.549 | fast__coast_frac |
| T6__coast_frac__block_iqr5 | 0.093 | 0.245 | 0.001 | 0.911 | 0.375 | -0.030 | -0.091 | -0.018 | 0.317 | 0.579 | medium__coast_frac |
| T4__coast_frac__block_iqr5 | 0.077 | 0.102 | 0.009 | 0.366 | 0.556 | 0.192 | -0.088 | -0.164 | 0.031 | 0.524 | slow__coast_frac |
| medium__trail_brake_frac__block_iqr5 | 0.070 | 0.071 | 0.016 | 0.468 | 0.556 | 0.084 | 0.076 | 0.136 | 0.000 | 0.163 | medium__trail_brake_frac |
| T11__coast_frac__block_iqr5 | 0.062 | 0.193 | 0.014 | 0.778 | 0.778 | -0.003 | -0.115 | -0.148 | 0.230 | 0.547 | medium__coast_frac |
| T11__apex_speed_rel__block_iqr5 | 0.047 | 0.114 | 0.050 | 0.532 | 0.667 | -0.046 | 0.071 | 0.048 | 0.019 | 0.149 | slow__apex_speed_rel |
| slow__brake_point_rel__block_iqr5 | 0.044 | 0.061 | 0.067 | 0.551 | 0.778 | -0.011 | -0.189 | -0.228 | 0.000 | 0.248 | slow__apex_speed_rel |
| T1__brake_point_rel__block_iqr5 | 0.044 | 0.061 | 0.067 | 0.551 | 0.778 | -0.011 | -0.189 | -0.228 | 0.000 | 0.248 | slow__apex_speed_rel |
| T7__trail_brake_frac__block_iqr5 | 0.041 | 0.080 | 0.074 | 0.277 | 0.556 | -0.004 | -0.035 | 0.143 | 0.000 | 0.124 | medium__brake_point_rel |

Pasan el filtro estricto 4 de 40 IQR de bloque.

Clustering de esos IQR de bloque (conjunto `block_iqr`) en k=2: silueta 0.332, brecha 0.087, PS 0.835, AMI piloto 0.062, split 0.222.

## Qué no funciona, y por qué

- Descartes del filtro estricto en las 42 columnas de curva (un mismo rasgo puede acumular varios motivos): compuesto 23, deriva_vuelta 20, sin_senal_companero 16, casi_constante 14, vida_neumatico 12, fiabilidad 10, pasa_estricto 8, cobertura 2.
- Curva Grande es una curva a fondo. Varias de sus métricas salen casi constantes (gas a fondo, coast, trail, a veces el punto de frenada si nadie frena en la ventana). No describen estilo; meten ceros y aíslan la vuelta rara. El agregado `fast` las mezcla con Ascari, que sí se frena.
- La velocidad de ápice y el punto de frenada arrastran el combustible: ρ con el número de vuelta dentro del piloto del orden del diagnóstico ya conocido (~+0,8 y ~−0,5 en el agregado). Bajar a la curva no quita esa pendiente. Por eso el filtro estricto las deja fuera aunque separen compañeros. El vector base7 las conserva: parte de su silueta es ritmo de carrera, no estilo.
- `throttle_attack` y `full_throttle_frac` siguen degeneradas en Curva Grande, Ascari, Parabolica y casi en Roggia. Lesmo 1 es la excepción parcial: ω²(piloto|equipo) = 0,090 en el ataque, con un 80 % de ceros, y 0,058 en el gas a fondo, con un 86 % de ceros. El agregado `medium` las aplasta (95 % y 99 % de ceros) porque la mediana de cuatro curvas casi nulas es cero. Rescatarlas no mejora el K-means: son las que dejan la brecha de `strict7` en −0,007.
- `expand` (16 columnas) sube la brecha de silueta sólo porque el nulo de permutación cae en más dimensiones (0,112 → 0,049 en k=2) mientras la silueta observada baja (0,256 → 0,207). El split de compañeros baja de 0,333 a 0,222. No es una ganancia.
- La desviación absoluta a la mediana móvil describe la vuelta atípica, no un nivel del piloto. Aun así varias pasan el filtro estricto porque la ventana solapada les infla el Spearman-Brown. No se usaron como núcleo del conjunto `cons5`.
- El IQR/MAD móvil de Lesmo 2 coast tiene ω² ≈ 0,16 y Spearman-Brown ≈ 0,97. El mismo IQR en bloques de 5 vueltas no solapados (`T7__coast_frac__block_iqr5`) conserva ω² = 0,154 pero el Spearman-Brown cae a 0,544 y el acuerdo de signo entre compañeros a 0,556. La fiabilidad del rolling no cuenta. Los IQR de bloque que sí mantienen Spearman-Brown ≥ 0,70 (coast medium, fast y Lesmo 1) agrupan con brecha 0,087 y AMI con el piloto 0,062: no definen clases.
- La dispersión de tiempos de sector no es un efecto de coche: la cuota de equipo va de 0,033 a 0,097, por debajo o al lado de ω². Sector 2 tiene la mayor señal entre compañeros (ω² = 0,052, Spearman-Brown 0,969) y el evaluador la marca `recommended`, pero la mediana por piloto de esa dispersión correlaciona 0,52 con la posición en carrera. Es tráfico o ritmo, no una elección de frenada. Sector 1 arrastra compuesto (ω² = 0,187).
- Elegir la curva de mayor ω² y luego agrupar las mismas vueltas infla un poco al conjunto `analogue7` y al `strict7`. El conjunto `expand` no elige ganadores y es el control.

## Recomendación ordenada

1. **Conservar las 7 columnas de tipología como vector de clustering.** En esta carrera el análogo por curva, a igual dimensión y en z-score sin PCA, no mejora a la vez la brecha de silueta, la prediction strength y la AMI con el piloto (véase la tabla; k=2 y k=3). El agregado sigue siendo el mejor compromiso entre señal de compañero y ruido de vuelta, sobre todo en coast.
2. **No interpretar `medium` ni `fast` como un solo hábito.** Para el texto de la tesis, desglosar coast, trail y punto de frenada por curva. La curva que más aporta dentro de cada métrica es la de mayor ω² de la tabla de zonas, siempre que Spearman-Brown ≥ 0,7 y la cuota de equipo no domine. Esas columnas sirven para caracterizar un clúster ya hecho, no para sustituir el vector.
   Curvas que superan a su agregado en al menos 0,02 de ω², con fiabilidad ≥ 0,70, fracción de ceros ≤ 0,50, |ρ| con la vuelta ≤ 0,35 y ω² de compuesto < 0,10: `T11__coast_frac` (ω² 0.157 frente a 0.136 de `medium__coast_frac`, SB 0.969, cuota de equipo 0.261, acuerdo de signo 0.889, ω² compuesto 0.065, ρ vuelta -0.169).
   Aunque no gane en ω², Lesmo 2 coast es más de piloto y menos de coche que el agregado: ω² 0,121 frente a 0,136 de `medium__coast`, cuota de equipo 0,172 frente a 0,452. Roggia y Parabolica coast tienen cuotas de equipo 0,231 y 0,261. La mediana de tipología se queda con la parte común al coche.
3. **No meter el ápice ni el punto de frenada en un vector “de estilo puro” sin residualizar la vuelta.** Siguen correlacionados con el número de vuelta dentro del piloto. Si se usan, hay que decir que el clúster mezcla estilo y carga de combustible. El filtro estricto los quita; la base7 no.
4. **No añadir consistencia móvil al vector.** Como mucho, reportar el IQR de bloque de coast o de trail si su ω²(piloto|equipo) pasa 0,03 y el bloque lo confirma. En caso contrario, la variabilidad vuelta a vuelta es ruido, tráfico o neumático, no un rasgo que separe compañeros.
5. **Dejar fuera los tiempos de sector y Curva Grande como curva de estilo.** El primero es rendimiento; la segunda no se frena.
6. **Siguiente contraste, fuera de este informe:** repetir el análogo de 7 curvas en otra pista donde `medium` no mezcle una parabólica con dos Lesmo. Monza es un caso extremo de tipología mal emparejada; que aquí el clustering no mejore no dice que en una pista con curvas homogéneas el agregado sea inocente. Sí dice que, en Monza 2025, alargar el vector no compra una partición mejor.

## Caveats

- Una sola carrera, 19 pilotos, un equipo con un solo coche. ω²(piloto|equipo) tiene pocos grados de libertad entre compañeros (9 parejas). p < 0,01 con 842 vueltas se alcanza con efectos modestos: por eso el umbral de ω² es 0,03 y no basta el p.
- El freno es booleano, no presión. A ~300 km/h un muestreo de 0,245 s son unos 20 m; a 80 km/h, unos 5 m. El punto de frenada de una vuelta es grosero. La mediana de muchas vueltas afina la media del piloto, pero no crea información que el muestreo no tiene.
- No hay carga de combustible ni setup en FastF1. Restar la mediana de la curva quita el nivel del pelotón, no la pendiente dentro del piloto. Los clústeres son perfiles observables, no estilos causales.
- El compuesto SOFT tiene 22 vueltas. ω²(compuesto|piloto) en esas celdas es inestable; el umbral 0,05 es una guarda, no un contraste fino.
- ALO tiene 19 vueltas y ALB entra en la vuelta 12. Las ventanas del borde y los bloques incompletos se pierden.
- El nulo de silueta usa 5 permutaciones y el ARI bootstrap 10 remuestras. La brecha está en el orden de la centésima de ruido de Monte Carlo; no se interpretan diferencias de 0,01.
- `analogue7` y `strict7` eligen columnas con el mismo criterio que luego se evalúa en clustering. `expand` y la base7 no. La comparación honesta de granularidad es base7 contra analogue7 (misma dimensión) y contra expand (sin elegir la curva ganadora).
- La fiabilidad partida en pares/impares de las features móviles está inflada. Se dice en cada tabla donde aparece.
- Kick Sauber (BOR) no entra en el contraste entre compañeros ni en el split de equipos.

## Archivos

- `run.py`: este análisis, repetible.
- `candidates.csv`: vueltas × candidatas (curvas, rolling, sectores).
- `candidates_scores.csv`, `candidates_gain.csv`: salida del evaluador oficial.
- `baseline_scores.csv`: las 17 columnas actuales, misma función de puntuación.
- `zone_selection.csv`: motivo de descarte de cada candidata.
- `replacement_clustering.csv`: base7, análogo, expand, estricto, consistencia.
- `zone_pair_structure.csv`, `driver_zone_medians.csv`, `zone_vs_typology_spearman.csv`.
- `zone_offsets_after_typology_median.csv`, `typology_median_contribution.csv`.
- `sanity_typology_reconstruction.csv`, `zone_long_raw.csv`.
- `block_scores.csv`, `block_clustering.csv`, `block_candidates.csv`.
- `omega2_zonas.png`, `share_team_zonas.png`.
- `highlights.json`: números que usa el veredicto.

