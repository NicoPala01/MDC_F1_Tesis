# Candidatos de telemetría: aplicación de acelerador, marcha/RPM y forma de la traza de velocidad

Carrera: Gran Premio de Italia 2025 (Monza), 842 vueltas canónicas, 19 pilotos, 10 equipos. Fuente: `car.pkl` (dato de coche a ~4 Hz; Δt mediano 0.245 s), no la telemetría interpolada. Zonas: las 7 de `zones.json`, cortadas con `get_corner_fragments`. No se recargó FastF1.

El agregado **fast es solo Ascari (T8)**. Curva Grande (T3) se toma plana en las 842 vueltas (acelerador al 100 %, sin freno): esas métricas se dejan en NaN y la mediana de la tipología las ignora. `fast__*` y `T8__*` son idénticos; las columnas T8 duplicadas no se exportan. **slow es solo la Variante del Rettifilo (T1)**. **medium** es la mediana de Roggia (T4), Lesmo 1 (T6), Lesmo 2 (T7) y Parabolica (T11).

La mediana de sesión restada a una columna ya agregada es un desplazamiento constante y **no cambia** ω², Spearman-Brown ni ρ. No se exporta. Lo que sí cambia el score es:

- `_zmed`: restar la mediana de esa zona en toda la sesión y luego agregar por tipología (iguala curvas con distinta línea base; no quita la deriva común de la vuelta).
- `_lapsync`: restar la mediana de todos los pilotos en la **misma zona y el mismo LapNumber**, y luego agregar. Quita el efecto común de combustible y pista.

Criterio de estilo: `omega2_driver_in_team` (señal de compañero por encima del azar). El flag `recommended` del evaluador no mira `share_team`: una columna casi constante en una curva plana puede salir recomendada siendo un sello del coche. Abajo se descartan esos casos.

## Definiciones

Ápice cinemático: muestra central de la meseta de `Speed` mínima dentro de la ventana de ápice (`Speed` es entero, en km/h). Los cruces de umbral se interpolan linealmente entre muestras. Esquina **inactiva** (métricas de aplicación = NaN): el acelerador no baja de 10 y no hay freno. Unidades entre paréntesis.

Fracción espacial: la misma de `spatial_fraction` del pipeline (el peso de cada muestra es el ΔDistance hasta la siguiente, no el conteo de muestras).

| Métrica | Ventana | Fórmula |
|---|---|---|
| `t_full_s` (s) | desde el ápice hacia adelante, ápice∪salida | Tiempo hasta el cruce de Throttle = 95. 0 si en el ápice ya es ≥ 95. NaN si no llega a 95 dentro de la zona. |
| `ramp_s` (s) | aplicación final | Desde el cruce de Throttle = 10 posterior a la **última** muestra ≤ 10 antes del primer ≥ 95 en o después del ápice, hasta el cruce de 95. |
| `t_pickup_to_apex_s` (s) | igual | t(ápice) − t(cruce de 10). Positivo = empieza a acelerar antes del ápice. |
| `d_full_m` (m) | igual | Distancia del ápice al cruce de 95. En fast, Spearman 0.99 con `t_full_s`: es la misma información. |
| `t_brake_to_full_s` (s) | frenada∪ápice∪salida | t(cruce de 95) − t(última muestra con Brake antes de ese cruce). |
| `thr_at_apex` (%) | muestra del ápice | Throttle en el ápice cinemático. |
| `partial_thr_frac` | ápice∪salida | Fracción espacial con 10 < Throttle < 90. |
| `partial_thr_apex` | ápice | Igual, solo ápice. La salida en Monza está casi siempre al 100 % y diluye la fracción. |
| `thr_apex_mean`, `thr_exit_mean` (%) | ápice o salida | Media trapezoidal ponderada por distancia (integral del acelerador por metro). |
| `thr_lifts` (conteo) | desde el cruce de 10 hasta el final de la salida | Caídas de ≥ 10 puntos que luego recuperan ≥ 10 puntos. Sin suavizado: una mediana de 3 muestras a 4 Hz borraría un lift real de una muestra. |
| `thr_mod_per_m` (%/m) | ápice∪salida | (Σ\|ΔThrottle\| − \|Throttle_fin − Throttle_inicio\|) / longitud. Cero si el pedal solo se mueve en un sentido. |
| `overlap_frac` | frenada∪ápice | Fracción espacial con Brake y Throttle > 10. |
| `overlap_soft_frac` | frenada∪ápice | Igual con Throttle > 2. El solape real en estos datos está sobre todo entre 2 % y 20 %, no por encima de 10. |
| `pickup_rate` (%/s) | muestras entre el cruce de 10 y el de 95 | Percentil 95 de `ThrottleRate` positivo. Esa columna ya viene suavizada (es idéntica a `ThrottleRate_smooth`). |
| `min_gear` | ápice | Mínimo de `nGear`. |
| `gear_at_apex` | muestra del ápice | Marcha en el ápice. En T1, T4, T6, T11 y Ascari coincide con `min_gear`. |
| `rpm_at_apex` | muestra del ápice | RPM en el ápice. |
| `upshift_rpm` | ápice∪salida, desde el ápice | RPM de la muestra anterior al primer aumento de marcha. |
| `n_downshifts` | frenada∪ápice | Suma de los escalones negativos de `nGear` (marchas bajadas). En T1, Spearman con `min_gear` = −0.99. |
| `exit_gain_100`, `exit_gain_200` (km/h) | vuelta completa | Velocidad interpolada en d_ápice + 100 m (o + 200 m) menos la velocidad mínima. |
| `dwell_m` (m) | frenada∪ápice∪salida | Longitud de la región **contigua** al ápice con Speed ≤ v_min + 5. Solo si la caída de velocidad hasta el ápice es ≥ 15 km/h y la traza sale de la banda por los dos lados dentro de la zona (si no, NaN: no se usa el borde de la ventana como si fuera un ápice). |
| `dwell_m_3pct` (m) | igual | Banda v_min × 1.03 en lugar de +5 km/h. |
| `decel_accel_ratio` | banda de +5 km/h | Distancia de entrada a la banda hasta el ápice, dividida por la distancia del ápice hasta la salida de la banda. Ambos lados ≥ 2 m. |

Escalas físicas (mediana por zona, dato crudo): tiempo freno→lleno T1 3.16 s, T4 2.75 s, T6 1.62 s, T7 1.36 s, T11 1.78 s, Ascari 1.23 s. Tiempo ápice→95 %: T1 2.26 s, T4 2.14 s, Lesmos ~0.6–0.8 s, Ascari 0.58 s. Dwell +5 km/h: Rettifilo ~20 m, Roggia ~22 m, Lesmo 1 ~44 m, Parabolica ~49 m (la curva larga es más «U»). Marcha mínima modal: T1 = 2, T4 = 3, T6/T7/T11/T8 = 5, T3 = 7. Comprobación VER vuelta 20: T1 `t_full_s` 1.87 s, marcha 2, throttle en el ápice 13 %; T3 inactiva, throttle 100, ganancia a +100 m ≈ 10 km/h.

## Puntuaciones

Tabla completa: `candidates_scores.csv` (323 columnas; 123 con `recommended` automático). Aquí, la mejor normalización de cada familia que importa. ω² = `omega2_driver_in_team`. ρ_exist = máximo |Spearman| contra las 17 columnas actuales.

| Feature | rec. | ω² | share_team | SB | signo eq. | ω² comp. | ρ_lap | \|ρ\| exist. | parecida a |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `medium__t_brake_to_full_s_lapsync` | sí | **0.393** | 0.128 | 0.993 | 1.00 | 0.027 | −0.003 | 0.329 | `medium__trail_brake_frac` |
| `slow__min_gear` | sí | **0.379** | 0.313 | 0.996 | 1.00 | −0.006 | n/a | 0.344 | `medium__coast_frac` |
| `slow__upshift_rpm` | no | 0.304 | 0.315 | 0.993 | 0.889 | 0.055 | 0.121 | 0.271 | `slow__full_throttle_frac` |
| `fast__thr_mod_per_m_lapsync` | sí | **0.260** | 0.137 | 0.979 | 0.889 | 0.041 | 0.059 | 0.211 | `medium__coast_frac` |
| `T4__thr_mod_per_m` | sí | 0.243 | 0.294 | 0.993 | 0.889 | 0.016 | −0.071 | 0.264 | `medium__apex_speed_rel` |
| `medium__rpm_at_apex_lapsync` | sí | 0.214 | **0.455** | 0.994 | 1.00 | 0.034 | −0.028 | 0.412 | `medium__apex_speed_rel` |
| `slow__thr_mod_per_m` | sí | 0.181 | 0.068 | 0.930 | 1.00 | 0.010 | 0.033 | 0.284 | `slow__apex_speed_rel` |
| `medium__overlap_soft_frac_zmed` | sí | 0.170 | **0.599** | 0.997 | 0.778 | 0.023 | 0.172 | 0.609 | `medium__coast_frac` |
| `medium__partial_thr_apex_lapsync` | sí | 0.158 | 0.427 | 0.989 | 0.778 | 0.029 | 0.045 | 0.424 | `medium__coast_frac` |
| `fast__t_full_s_lapsync` | sí | 0.148 | **0.023** | 0.963 | 0.889 | 0.010 | −0.044 | 0.138 | `fast__apex_speed_rel` |
| `fast__ramp_s_lapsync` | sí | 0.145 | 0.044 | 0.965 | 0.778 | 0.007 | −0.003 | 0.169 | `slow__throttle_attack` |
| `medium__dwell_m_3pct_lapsync` | sí | 0.130 | 0.213 | 0.970 | 1.00 | 0.043 | −0.006 | 0.331 | `medium__apex_speed_rel` |
| `medium__dwell_m` | sí | 0.113 | 0.205 | 0.976 | 0.889 | 0.027 | −0.214 | 0.244 | `medium__coast_frac` |
| `medium__exit_gain_100_lapsync` | sí* | 0.120 | 0.421 | 0.978 | 0.778 | 0.022 | 0.032 | 0.549 | `medium__apex_speed_rel` |
| `medium__decel_accel_ratio` | no | −0.005 | 0.062 | 0.757 | 0.444 | −0.005 | −0.066 | 0.144 | `medium__apex_speed_rel` |
| `T3__exit_gain_100` | no | 0.003 | 0.055 | 0.701 | 0.667 | 0.036 | −0.115 | 0.295 | `fast__brake_point_rel` |
| `T3__thr_apex_mean` | sí* | 0.248 | **0.688** | 1.000 | 1.00 | 0.034 | 0.151 | 0.331 | `medium__coast_frac` |

\* El flag automático no basta: ver la interpretación. p(`omega2_driver_in_team`) < 10⁻²⁶ en todas las filas con ω² ≥ 0.13. Cobertura ≥ 0.99 salvo donde se indica lo contrario. El mejor rasgo actual de referencia es `coast_frac` con ω² ≈ 0.12–0.15.

La versión **cruda** de `medium__t_brake_to_full_s` tiene ω² 0.326 pero ω² de compuesto 0.138 y ρ_lap −0.31: no pasa el filtro. `_lapsync` sube ω² a 0.393 y deja ρ_lap ≈ 0 y el compuesto en 0.027. Lo mismo con la modulación de Ascari: el crudo tiene ρ_lap −0.24 y compuesto 0.067; `_lapsync` lo deja usable (ρ_lap 0.06, compuesto 0.041) sin perder ω² (0.254 → 0.260). `_zmed` no quita esa deriva.

## Ganancia de clustering

Base = las 7 columnas con ICC ≥ 0.25: `fast/medium__apex_speed_rel`, `fast/medium/slow__coast_frac`, `medium/slow__trail_brake_frac`. K-means sobre z-score, las mismas semillas que `evaluate_candidate_features.py`. Extra = las tres métricas continuas con mejor compromiso estilo/coche y poca colinealidad entre sí (Spearman cruzado: freno→lleno vs modulación 0.04, freno→lleno vs `t_full` 0.08, modulación vs `t_full` −0.24).

| set | k | silueta | nula | gap | PS | ARI boot | AMI piloto | AMI compuesto | split compañeros |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| base (7) | 2 | 0.256 | 0.112 | 0.145 | 0.895 | 0.937 | 0.126 | −0.001 | 0.333 |
| base+extra (10) | 2 | 0.191 | 0.125 | 0.066 | 0.829 | 0.872 | 0.128 | −0.000 | 0.333 |
| base (7) | 3 | 0.204 | 0.109 | 0.094 | 0.688 | 0.838 | 0.198 | 0.009 | 0.556 |
| base+extra (10) | 3 | 0.158 | 0.087 | 0.072 | 0.679 | 0.855 | 0.206 | 0.004 | **0.667** |

842 vueltas en los dos ajustes. Extra: `medium__t_brake_to_full_s_lapsync`, `fast__thr_mod_per_m_lapsync`, `fast__t_full_s_lapsync`.

Lectura: en k = 2 la partición no se mueve (mismo split) y la silueta baja, como cabe esperar al añadir dimensiones ruidosas a un eje que ya estaba bien separado. En k = 3 el split de compañeros pasa de 5/9 a 6/9 equipos y el AMI con el piloto sube de 0.198 a 0.206; la silueta y el gap bajan. El compuesto no entra en la partición (AMI ≈ 0). No es una mejora clara del clustering lap a lap. Sí es una mejora del **diagnóstico de estilo**: estas columnas separan compañeros mejor que cualquiera de las 17 actuales y casi no repiten la matriz existente (\|ρ\| ≤ 0.33).

Por qué el K-means apenas se entera. `fast__t_full_s_lapsync` tiene share de vuelta 0.82 e ICC de piloto 0.17: el orden de pilotos es estable al promediar ~45 vueltas (SB 0.96), pero una vuelta suelta es ruido. `t_brake_to_full` es el más limpio (ICC 0.53, 40 % de la varianza entre pilotos del mismo equipo) y, aun así, pesa 1 de 10 ejes z-score. Añadida sola, el AMI en k = 3 no sube (0.198 → 0.193).

Ablaciones (`ablation_gain.csv`), solo k = 3, base+extra frente a la misma base:

| Extra | silueta | gap | PS | AMI piloto | split |
|---|---:|---:|---:|---:|---:|
| base sola | 0.204 | 0.094 | 0.688 | 0.198 | 0.556 |
| solo `t_brake_to_full` lapsync | 0.189 | 0.093 | 0.631 | 0.193 | 0.556 |
| freno→lleno + modulación Ascari | 0.176 | 0.092 | 0.674 | 0.205 | **0.667** |
| esas dos + `t_full` (la tabla de arriba) | 0.158 | 0.072 | 0.679 | 0.206 | **0.667** |
| freno→lleno + modulación + dwell 3 % + `t_full` | 0.155 | 0.079 | **0.713** | **0.218** | 0.556 |
| solo `slow__min_gear` | **0.265** | **0.154** | **0.900** | 0.218 | 0.556 |

La subida de `slow__min_gear` no es un estilo distribuido. En T1, 767 vueltas van en 2ª, 4 muestras sueltas en 1ª y **71 vueltas en 3ª: 32 de Hamilton y 39 de Ocon**. El resto de pilotos, incluidos Leclerc y Gasly, van siempre en 2ª. En k = 3 el tercer grupo tiene 72 vueltas: es esa elección de marcha. En k = 2 el gap se hunde (0.145 → 0.020) porque la columna ya es bimodal y la silueta nula sube a 0.211. ω² 0.38 y acuerdo de signo 1.0 son reales (Hamilton y Ocon no hacen lo mismo que su compañero), pero es un marcador binario de dos pilotos, no un eje para el K-means continuo.

## Interpretación

**Tiempo desde que se suelta el freno hasta el acelerador a fondo, en medium, sincronizado por vuelta.** Es el mejor rasgo de la familia. ω² 0.39 frente a ~0.12–0.15 del mejor rasgo actual, coche solo el 13 % de la suma de cuadrados, acuerdo de signo 9/9, y la sincronización por número de vuelta elimina la deriva de combustible que tumbaba la versión cruda. No es el `coast_frac` ni el trail braking (\|ρ\| 0.33). En medias de piloto (residuo): Ocon −0.44 s (entra al gas mucho antes que el pelotón), Verstappen −0.21 s; Hamilton +0.21 s y Bearman +0.17 s esperan. Dentro de Haas y de Ferrari el orden no se invierte entre mitades de carrera. Físicamente es la paciencia —o la prisa— entre el release y el 95 %, del orden de 1.2–3.2 s según la curva, así que cubre varias muestras de 0.24 s.

**Modulación de acelerador en Ascari, sincronizada por vuelta.** ω² 0.26, coche 0.14, casi ortogonal al tiempo freno→lleno (ρ 0.04). Mide los lifts de más de un camino monótono en la chicane, no el attack de la salida (ese es ~0 porque la salida ya va a fondo). Verstappen, Bearman, Bortoleto y Sainz modulan más; Russell, Ocon, Lawson y Tsunoda, menos. El conteo de lifts en Ascari dice lo mismo (ρ 0.74) con un 50 % de ceros y, en crudo, deriva con la vuelta (ρ_lap −0.28) y compuesto 0.064: se queda fuera. En Rettifilo el conteo de lifts es **cero en las 842 vueltas**: después del pickup final no hay otra caída de 10 puntos; el lift de la chicane ocurre antes y no entra en la definición. La modulación continua de T1 sí existe (ω² 0.18, coche solo 0.07) y no se parece a la de Ascari (ρ 0.03), pero añadirla como cuarta columna no movió el split.

**Tiempo del ápice cinemático al 95 % en Ascari, sincronizado.** El rasgo con menos coche de todos (share_team 0.023). ω² 0.15, \|ρ\| con la matriz actual 0.14. Piastri, Alonso y Albon tardan más; Norris va al revés que Piastri. La rampa (`ramp_s`, ρ 0.66) y la distancia al 95 % (ρ 0.99) son el mismo eje: no hace falta más de una. En medium la rampa es sobre todo coche (share_team 0.50–0.56): la agregación mezcla curvas cuyo tiempo típico va de 1.0 a 2.3 s y el residual de equipo pesa más que el del piloto.

**Forma V/U.** El dwell en la banda del +3 % , sincronizado, pasa el filtro (ω² 0.13, SB 0.97, acuerdo de signo 1.0, ρ_lap ≈ 0) y solo se solapa moderadamente con la velocidad de ápice (\|ρ\| 0.33). Es la única forma de traza que merece guardarse. El **ratio deceleración/aceleración no funciona**: ω² ≈ 0, el 93–97 % de la varianza es ruido de vuelta, acuerdo de signo 0.44 y SB 0.56–0.76. Con velocidad entera y Δt de 0.24 s, cada lado de la banda de +5 km/h se mueve de una muestra a otra (~10–20 m) y el cociente de dos distancias cortas es inestable. La suma (dwell) sí; el cociente no.

**Marcha y RPM.** `slow__min_gear` es el caso de las 71 vueltas en 3ª de Hamilton y Ocon, descrito arriba. `n_downshifts` en T1 es la misma variable cambiada de signo. `upshift_rpm` en T1 tiene ω² 0.30 y SB 0.99 (Leclerc ~8400 rpm, Hamilton ~10800; Gasly ~8800, Ocon ~10400; McLaren los dos ~11040; Russell 11540). Es un short-shift real dentro del equipo, pero el compuesto queda en 0.055 (justo por encima del corte 0.05), el coche explica tanto como el piloto (share_team 0.31: relaciones y mapa de la UP) y no entra en el conjunto recomendado. `rpm_at_apex` sincronizado conserva ω² 0.21, pero el 46 % de la varianza es de equipo; el crudo además deriva con la vuelta (ρ_lap 0.62) y con el compuesto (0.37). La sincronización quita el combustible y deja el motor.

**Solape freno–acelerador.** Existe y separa pilotos (Lesmo 1: Leclerc 0.36, Ocon 0.23, Hamilton 0.23 de la frenada con Throttle > 2; Lawson y Tsunoda ~0). El agregado medium tiene ω² 0.17 pero **share_team 0.60**: los dos Ferrari van altos. El umbral > 10 que se pidió es más escaso (ω² 0.085, 68 % ceros) y también tira a coche. Sirve para describir; meterlo al clustering agruparía coches.

**Ganancia de velocidad a +100/+200 m.** Tal como se temía, es potencia y velocidad de ápice. Tras quitar la deriva de vuelta, medium sigue con share_team 0.42 y \|ρ\| 0.55 con `medium__apex_speed_rel`. El flag automático la deja pasar porque 0.55 < 0.80; no debería usarse como estilo. En Curva Grande, donde el coche ya va lanzado, la ganancia a +100 m **ni siquiera separa equipos** (ω² 0.003, 93 % ruido de vuelta, desviación ~1.3 km/h).

**Falsos positivos del flag.** `T3__thr_apex_mean` (recomendado, ω² 0.25, ICC 0.94) es un acelerador clavado al 100 % con diferencias de ~1 punto: sello de sensor o de mapa, share_team 0.69 y share de vuelta 0.06. `T11__thr_exit_mean` tiene share_team 0.81 y acuerdo de signo 0.40: la salida de Parabolica está a fondo y el orden entre compañeros no se sostiene.

## Qué no aporta, y por qué

- Curva Grande plana: cualquier fracción de acelerador, rampa o dwell es constante o NaN. Agregar «fast» sin enmascararla diluye Ascari con un cero estructural.
- `throttle_attack` de la salida sigue siendo el problema conocido. Medir el p95 de `ThrottleRate` **durante la rampa** (`pickup_rate`) recupera señal (ω² ≈ 0.10 en medium, \|ρ\| con las 17 columnas solo 0.18), pero es más débil y más ruidoso que el tiempo hasta el 95 %.
- Lifts de ≥ 10 puntos: cero en Rettifilo y en los Lesmo; en Ascari son la versión discreta y cero-inflada de `thr_mod_per_m`.
- Acelerador parcial: señal real (ω² 0.14–0.16) pero share_team ~0.40 y ρ ~0.42 con `coast_frac`. T6 suelto es algo más limpio (ω² 0.16, coche 0.28) que la mediana de las cuatro curvas medium.
- Marcha mínima agregada en medium o fast: casi todo el mundo va en la marcha modal de cada curva, así que al centrar por zona el zero_frac supera 0.88 y el compuesto se dispara (0.16). El único contraste estable es el binario de T1.
- Ratio V/U, ganancia de salida como estilo, y RPM de ápice sin residuo de equipo.

## Muestreo a 4 Hz

Δt mediano 0.24 s (rango aproximado 0.16–0.32 s). A 150 km/h una muestra son ~10 m; a 70 km/h, ~5 m. La interpolación del cruce reduce el sesgo de «la muestra cae antes o después», pero una aplicación que pasa de 0 a 100 entre dos muestras tiene una rampa aparente de ~0.2 s dictada por el reloj, no por el pie. Por eso `t_full_s` y `t_brake_to_full_s`, que en estas curvas duran varios décimos o segundos, salen fiables (SB ≥ 0.96), y el ratio de dos flancos de una banda de 5 km/h no. `Speed` y `Throttle` llegan como enteros. No se usó `tel.pkl`: está interpolada a ~630 muestras y puede fabricar solape freno–acelerador que el dato de coche no tiene.

## Recomendación (orden)

1. **Incorporar `medium__t_brake_to_full_s_lapsync`.** Mejor ω² de la familia (0.39), poco coche (0.13), SB 0.99, signo 1.0, sin deriva de vuelta ni de compuesto, \|ρ\| 0.33 con el trail braking. Es el único candidato que claramente supera a `coast_frac` en el criterio de estilo y no es un artefacto de dos pilotos.
2. **Incorporar `fast__thr_mod_per_m_lapsync` como descripción de Ascari** (no de «fast» en abstracto: Curva Grande no entra). ω² 0.26, coche 0.14, SB 0.98, independiente del anterior. No sustituye a `throttle_attack`; mide otra cosa, en la ventana donde el pedal de verdad se mueve.
3. **Guardar `fast__t_full_s_lapsync` como eje de timing en Ascari** (ω² 0.15, coche 0.02, \|ρ\| 0.14). No añadir también `d_full_m` ni `ramp_s`.
4. **Guardar `medium__dwell_m_3pct_lapsync` como forma**, con modestia (ω² 0.13). Descartar `decel_accel_ratio`.
5. **Reportar `slow__min_gear` como marcador binario** (Hamilton y Ocon en 3ª en la Rettifilo; ω² 0.38) y `slow__upshift_rpm` como short-shift dentro del equipo (ω² 0.30, justo fuera por compuesto y por coche). No meter la marcha al K-means z-score: fabrica un grupo de ~70 vueltas y destroza el gap en k = 2.
6. **No incorporar** solape (coche), RPM de ápice (coche, aunque el lapsync quite el combustible), ganancia de velocidad a +100/200 m (potencia y velocidad de ápice), ni nada de Curva Grande.
7. **No esperar que estas columnas suban la silueta.** En k = 3 el trío del punto 1–3 sube el split de compañeros de 0.556 a 0.667 y el AMI con el piloto de 0.198 a 0.206, y baja la silueta de 0.204 a 0.158. El valor está en medir estilo entre compañeros, no en rehacer la partición de 7 columnas.

Archivos: `extract.py`, `zone_metrics.csv` (largo, por zona), `candidates.csv`, `candidates_scores.csv`, `candidates_gain.csv`, `ablation_gain.csv`.
