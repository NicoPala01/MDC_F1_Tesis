# Dinámica de frenada en Monza 2025: métricas candidatas

Evaluación de métricas nuevas de **dinámica de frenada** sobre las 842 vueltas ya exportadas del Gran Premio de Italia 2025 (19 pilotos, 10 equipos). El freno de FastF1 es booleano: no hay presión de pedal. Toda deceleración sale de la velocidad del canal de coche (`car.pkl`, ~4 Hz, Δt mediano 0,245 s). `tel.pkl` solo se usa como proxy de tráfico (`DistanceToDriverAhead`).

Código: `extract.py`. Matriz de candidatos: `candidates.csv` (842 × 362 métricas). Puntuación completa: `candidates_scores.csv`. Tabla larga por zona: `long_zone_metrics.csv`. Comprobación física: `sanity.txt`.

## 1. Definiciones

### 1.1 Ventana y evento de frenada

Para cada zona de `zones.json` se cortan los fragmentos con `get_corner_fragments`. El freno se busca en **braking ∪ apex** (el onset de la Variante del Rettifilo cae al final de la ventana de braking y el pico de deceleración ya está dentro del apex; quedarse solo en braking deja 2–3 muestras). La salida no entra: el siguiente frenado pertenece a otra zona.

Un *run* es un tramo contiguo con `Brake == True`. Dos runs separados por un hueco de freno suelto menor de **0,40 s** se funden (un fallo de una muestra). En T1 los huecos reales duran ~1,2 s (mínimo observado 0,36 s): no son dropouts, son dos aplicaciones en la chicane.

**Evento primario** (pico, media, duración, ataque, reparto inicial, velocidad de entrada, *effort*, *lift*): el primer run con al menos dos muestras y una caída de velocidad ≥ 8 km/h. Si ninguno cumple la caída, el run de mayor caída. Así se ignora un toque de freno de una muestra.

**Suelta de freno** (punto respecto al apex y velocidad de suelta): la última muestra con freno en braking ∪ apex, que en una chicane puede ser la segunda aplicación. El apex cinemático es el `argmin` de `Speed` en la ventana de apex, igual que en el pipeline.

Si no hay freno (toda la Curva Grande, T3), la métrica es NaN. La tipología *fast* queda entonces igual a T8 (Ascari), y *slow* igual a T1. La mediana de pandas ignora NaN.

Derivada. Con muestras no equiespaciadas no se usa Savitzky–Golay sobre el índice. Cada pendiente es un ajuste lineal:

- escalón: \(a_i = (v_{i+1}-v_i)/(t_{i+1}-t_i)\) si \(\Delta t \in [0{,}12,\ 0{,}50]\) s; si no, NaN;
- media: pendiente de mínimos cuadrados de \(v\) sobre \(t\) en el evento primario.

`tel.pkl` no recupera un pico más alto: `get_telemetry` interpola en línea el mismo canal de ~4 Hz, y la pendiente entre muestras de coche es exactamente esa diferencia finita. Los escalones más bruscos que **8 g** (78,5 m/s²) se descartan como artefacto; la mediana no depende de ese corte.

### 1.2 Métricas (unidades en la zona, antes de agregar)

| Métrica | Fórmula | Unidad |
|---|---|---|
| `peak_decel` | \(-\min a_i\) en el evento primario, tras el filtro de \(\Delta t\) y el corte de 8 g | m/s² |
| `peak_decel_med3` | Igual, después de una mediana móvil de 3 muestras de velocidad | m/s² |
| `mean_decel` | Menos la pendiente MCO de \(v(t)\) en el evento primario | m/s² |
| `brake_effort` | \((v_0^2 - v_{\min}^2)/(2d)\). \(v_0\): velocidad al onset. \(v_{\min}\): mínima desde el onset hasta el final del apex. \(d\): distancia por pista entre ambas (solo si \(d>5\) m y hay caída) | m/s² |
| `brake_duration_s`, `brake_duration_m` | Duración del evento primario, tiempo y distancia por pista | s, m |
| `brake_on_time_s` | Suma de la duración de todos los runs en braking ∪ apex | s |
| `entry_speed` | Velocidad en la primera muestra del evento primario | km/h |
| `speed_drop_ratio` | \(v_{\min}/v_0\) | — |
| `brake_attack_s` | Tiempo desde el onset hasta el punto medio del escalón más pronunciado válido | s |
| `attack_frac` | `brake_attack_s` / `brake_duration_s` | — |
| `decel_first_0_5` | Media de \(-a_i\) en los intervalos que empiezan dentro de los primeros 0,50 s | m/s² |
| `frontload_ratio` | Esa media dividida por la media del resto. NaN si el resto frena a menos de 2 m/s². Recortado a [0, 8] | — |
| `frontload_speed_frac` | \((v_0 - v_{0{,}5}) / (v_0 - \min(v_{\mathrm{fin}}, v_{\min}))\), con \(v_{0{,}5}\) la primera muestra a ≥ 0,45 s del onset. Recortado a [−0,5, 1,5] | — |
| `release_to_apex_m` | Distancia por pista del apex cinemático menos la distancia de la última muestra con freno. **Positivo = soltó antes del apex** | m |
| `release_to_apex_s` | Tiempo del apex cinemático menos el tiempo de esa suelta | s |
| `release_speed` | Velocidad en esa misma muestra | km/h |
| `lift_coast_s`, `lift_coast_m` | Desde la primera muestra con acelerador ≤ 5 % posterior a la última con acelerador ≥ 95 %, hasta el onset. La búsqueda hacia atrás se corta en una aplicación de freno anterior o 100 m antes del inicio de la ventana de braking. **0** si el piloto frena sin una muestra ≤ 5 %. **NaN** si en ese tramo no hay acelerador ≥ 95 % (el *lift* empezó fuera y estaría censurado) | s, m |
| `brake_stabs` | Número de runs tras fundir huecos < 0,40 s. NaN si no hay freno | conteo |

Tráfico. `min_dtd` es el mínimo de `DistanceToDriverAhead` en los 150 m anteriores al onset, solo con un coche nombrado por delante; \(+\infty\) si no hay nadie (aire limpio). `traffic_50` es cierto si ese mínimo es < 50 m (14–23 % de las vueltas según la zona). Las columnas `_clear` ponen NaN en esas vueltas. El residuo de rebufo (`_slipresid`) es el residuo, por zona, de la regresión \(y = a + b\exp(-\mathrm{min\_dtd}/40\,\mathrm{m})\).

### 1.3 Agregación y normalización

- `{tipología}__{métrica}`: se resta la mediana de sesión **de esa zona** y luego se toma la mediana de las zonas de la misma tipología. Centrar cada zona importa en *medium* (Lesmo no frena igual que la Roggia). Restar una sola mediana de tipología, como hace el pipeline, es una constante después de la mediana y **no cambia** ningún rango ni ningún \(\omega^2\). Las columnas `_rawmed` son la mediana cruda; sus puntuaciones coinciden con esa resta constante, no con el centrado por zona.
- `{tipología}__{métrica}_lapsync`: en cada zona se resta la mediana de todos los pilotos en el **mismo** `LapNumber` (solo si hay ≥ 8 valores finitos) y luego se agrega por tipología. Quita el efecto común de combustible y de evolución de pista; no quita el compuesto, porque en una misma vuelta los pilotos no comparten goma.
- `{zona}__{métrica}`: valor crudo de T1, T4, T8 o T11 (metros, m/s², …). En T1 coincide, salvo una constante, con *slow*.
- `_lapsync` por zona: el mismo centrado por número de vuelta, sin agregar.

## 2. Comprobación física

Mediana del pico de deceleración (magnitud):

| Zona | Pico | *Effort* | Duración del evento | Stabs (mediana) | Tráfico < 50 m |
|---|---:|---:|---:|---:|---:|
| T1 Rettifilo | 4,25 g | 2,08 g | 3,04 s | 2 | 0,17 |
| T4 Roggia | 4,25 g | 2,37 g | 2,40 s | 1 | 0,19 |
| T8 Ascari | 4,07 g | 2,15 g | 1,36 s | 1 | 0,15 |
| T11 Parabólica | 3,42 g | 1,62 g | 1,44 s | 1 | 0,14 |
| T7 Lesmo 2 | 2,73 g | 1,37 g | 0,92 s | 1 | 0,23 |
| T6 Lesmo 1 | 1,86 g | 0,98 g | 0,96 s | 1 | 0,23 |
| T3 Curva Grande | — | — | — | — | sin freno (0/842) |

El pico de T1 cae en la banda de 4–5 g que se esperaba (p10 = 3,44 g, p90 = 5,49 g, n = 842). No es el pico instantáneo de 5–6 g de un pedal de F1: cada escalón promedia 0,12–0,50 s de un canal a 4 Hz cuantizado al km/h. El ejemplo VER, vuelta 10, T1 reproduce el escalón 307 → 262 km/h en 0,32 s: **39,2 m/s² = 4,00 g**. La media MCO de esa frenada es 2,19 g y el *effort* hasta la velocidad mínima es 2,03 g: el pico dura poco y el resto es *trail*. El *lift* de esa vuelta es 0,28 s y 24 m (acelerador de 96 % a 1 % y luego freno). La mediana del *lift* en T1 es 0 s: en más de la mitad de las vueltas no hay una muestra ≤ 5 % entre el pleno gas y el freno, porque 0,2 s cabe mal en un muestreo de 0,25 s.

## 3. Puntuación

Criterio de estilo: \(\omega^2\) del piloto dentro del equipo (por encima del azar). También se exige, para el flag `recommended` del evaluador, cobertura ≥ 0,9, fracción de ceros ≤ 0,9, \(p < 0{,}01\), Spearman–Brown ≥ 0,7, \(\omega^2\) de compuesto dentro del piloto < 0,05 y \(|\rho| < 0{,}8\) con las 17 columnas actuales. Ese flag **no** mira la deriva con el número de vuelta ni cuántos equipos entran en el acuerdo de signo. Por eso más abajo se separa el flag del criterio sustantivo. La columna «sin OCO» es el mismo \(\omega^2\) recalculado quitando a Ocon (47 vueltas): hace falta porque dos métricas de la Roggia son casi exclusivamente suyas.

Todas las filas de abajo tienen \(p < 0{,}001\) salvo `T1__peak_decel` (\(p = 0{,}049\)).

### 3.1 Las que sí describen estilo

| Métrica | \(\omega^2\) piloto | sin OCO | cuota equipo | SB | acuerdo de signo | \(\omega^2\) compuesto | \(\rho\) vuelta | \(\|\rho\|\) actual | más parecida |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `fast__lift_coast_s_lapsync` | 0,214 | 0,221 | 0,187 | 0,982 | 1,00 (9/9) | 0,017 | +0,066 | 0,697 | `fast__coast_frac` |
| `medium__release_to_apex_m_lapsync` | 0,284 | 0,119 | 0,384 | 0,993 | 0,89 (9) | −0,002 | +0,057 | 0,547 | `medium__trail_brake_frac` |
| `T1__release_to_apex_m` | 0,167 | 0,163 | 0,307 | 0,986 | 1,00 (9) | 0,027 | +0,055 | 0,573 | `slow__trail_brake_frac` |
| `T1__brake_stabs` | 0,132 | 0,124 | 0,244 | 0,982 | 1,00 (7) | 0,001 | +0,025 | 0,502 | `slow__trail_brake_frac` |
| `medium__frontload_speed_frac_lapsync` | 0,110 | 0,101 | 0,090 | 0,935 | 0,67 (9) | 0,009 | +0,005 | 0,344 | `medium__brake_point_rel` |
| `slow__brake_effort_lapsync` | 0,056 | 0,053 | 0,142 | 0,914 | 0,89 (9) | 0,013 | −0,042 | 0,348 | `slow__coast_frac` |
| `T8__release_to_apex_m` | 0,083 | 0,054 | 0,074 | 0,928 | 0,78 (9) | 0,002 | −0,042 | 0,288 | `fast__trail_brake_frac` |

`fast__lift_coast_s_lapsync` es T8: T3 no frena. Fracción de ceros = 0,58 (muchas vueltas no tienen *coast* medible). Aun así el orden de compañeros es el mismo en vueltas pares e impares en los 9 equipos. Quien levanta el pie en Ascari, en mediana de la temporada de esa carrera: Lawson (+0,40 s sobre el campo de esa vuelta), Antonelli (+0,36), Alonso (+0,22), Colapinto (+0,16), Tsunoda (+0,08). Su compañero de equipo no lo hace. La versión **sin** centrar por vuelta (`fast__lift_coast_s`) tiene \(\rho\) con el número de vuelta = −0,38 y \(|\rho| = 0{,}81\) con `fast__coast_frac`: el *lift* crece a lo largo de la carrera junto con el *coast* ya medido. Restar la mediana de cada vuelta deja el hábito del piloto (\(\rho = +0{,}07\), \(|\rho| = 0{,}70\)).

`medium__release_to_apex_m_lapsync` es la mejor geometría de frenada. El centrado por zona antes de la mediana sube el \(\omega^2\) de 0,229 (`_rawmed`) a 0,284. La deriva con la vuelta ya era pequeña en crudo (\(\rho = +0{,}09\)); el *lapsync* la deja en +0,06 y no cambia el fondo. Ocon suelta el freno unos 30 m **después** del apex mediano de las zonas *medium* (en T4, −35 m frente a una mediana de campo de +16 m). Sin él, \(\omega^2\) baja a 0,119: sigue en el rango de los mejores `coast_frac` actuales (0,12–0,15), ya no es un efecto de un solo piloto. Lesmo 1 por separado (`T6__release_to_apex_m`, calculado sobre la tabla larga, no exportado como columna) da \(\omega^2 = 0{,}164\) y 0,109 sin Ocon, acuerdo de signo 1,00. La Roggia aislada no: ver abajo.

`T1__release_to_apex_m` no depende de Ocon. Gasly, Stroll y Piastri sueltan ~45 m antes del apex del Rettifilo; sus compañeros, ~15 m. Va con `T1__brake_stabs` (\(\rho = 0{,}75\)): mediana 2 aplicaciones (chicane) frente a 1. Equipos partidos de forma estable: Alpine, Aston Martin, McLaren, Racing Bulls y Red Bull. Ferrari, Haas, Mercedes y Williams van los dos a dos aplicaciones. No hace falta llevar las dos columnas: dicen casi lo mismo, y la distancia es continua.

`medium__frontload_speed_frac_lapsync` (cuánta velocidad se pierde en el primer medio segundo) tiene poco efecto de coche (cuota de equipo 0,09) y no deriva, pero el orden de compañeros solo se sostiene en 6 de 9 equipos. Señal real y secundaria.

### 3.2 Las que el flag marca y no hay que usar

| Métrica | \(\omega^2\) | sin OCO | por qué no |
|---|---:|---:|---|
| `T4__brake_stabs` | 0,394 | 0,009 | 796 vueltas valen 1 y 43 valen 2; esas 43 son Ocon. Acuerdo de signo con **1** equipo (Haas). SB = 0,995 porque Ocon es estable y el resto es constante. |
| `T4__release_to_apex_m` | 0,311 | 0,026 | El mismo piloto. Desviación típica 13,7 m con él y 7,7 m sin él. Añadirlo al K-means de k = 3 aísla un grupo de ~44 vueltas. |
| `medium__mean_decel_lapsync` | 0,152 | 0,031 | Pasa el flag (deriva ~0, compuesto ~0, \(\|\rho\| = 0{,}19\)). Sin Ocon cae al umbral 0,03 y el acuerdo de signo a 0,63. La media de deceleración no separa compañeros en el resto de la parrilla. |
| `T11__lift_coast_s_lapsync` | 0,247 | 0,253 | \(\omega^2\) alto y menos redundante con el *coast* (0,46), pero \(\rho\) con la vuelta = −0,30 **después** del *lapsync*: cada piloto que ahorra combustible lo hace más al final, no es un nivel fijo. Ceros = 0,78. |
| `medium__entry_speed_lapsync` | 0,061 | — | Pasa el umbral por poco. Acuerdo de signo 0,67. Sigue siendo en parte coche (cuota de equipo 0,21, como las trampas de velocidad). |
| `medium__brake_on_time_s_lapsync` | 0,175 | 0,080 | \(\omega^2\) de compuesto = 0,051, justo por encima del corte, y \(\|\rho\| = 0{,}47\) con la velocidad de apex. |

### 3.3 Lo que no funciona

**Pico de deceleración.** El mejor caso es `medium__peak_decel_lapsync`: \(\omega^2 = 0{,}029\) (bajo el corte de 0,03), acuerdo de signo 0,67, pese a SB = 0,97. En T1 crudo, \(\omega^2 = 0{,}009\), cuota de equipo = 0,06, \(\rho\) con la vuelta = +0,29. El pico de un solo escalón a 4 Hz es ruido de vuelta, no estilo y tampoco un efecto de coche limpio. Suavizar con mediana de 3 muestras no cambia nada. El rebufo tampoco: \(R^2\) del pico contra \(\exp(-d/40)\) es ≤ 0,04 en todas las zonas. Enmascarar el tráfico (< 50 m) baja la cobertura por debajo de 0,9 y no sube el \(\omega^2\).

**Tiempo hasta el pico (`brake_attack_s`).** La resolución es una muestra (~0,16–0,25 s). `medium__brake_attack_s_lapsync`: \(\omega^2 = 0{,}027\), SB = 0,70, acuerdo 0,56.

**Caída de velocidad.** `speed_drop_ratio` es la velocidad de apex disfrazada: \(|\rho| = 0{,}75\) con `medium__apex_speed_rel`, \(\omega^2\) de compuesto = 0,23, \(\rho\) con la vuelta = +0,41 en la versión de aire limpio. El *lapsync* quita la deriva (\(\rho = +0{,}01\)) pero deja compuesto 0,08 y \(|\rho| = 0{,}56\).

**Duración.** `medium__brake_duration_m_lapsync` tiene \(\omega^2 = 0{,}145\) y acuerdo 0,89, pero compuesto 0,055 y \(|\rho| = 0{,}43\) con el apex. El rebufo sí alarga la frenada (\(R^2 = 0{,}25\)–0,27 en T1, T4, T8 y T11 para la duración en segundos; 0,16 para la velocidad de entrada en T1). El residuo de ese ajuste **no** crea estilo: el \(\omega^2\) de compuesto del residuo de duración sigue en 0,15 y la deriva con la vuelta en −0,36. Quitar el rebufo no quita goma ni combustible.

**Velocidad de suelta y *effort* crudo.** Van con la velocidad mínima y heredan su deriva (en T1, \(\rho\) de `mean_decel` con la vuelta = +0,38 y compuesto 0,12). El *effort* de T1 solo se acerca a un estilo débil después del *lapsync* (\(\omega^2 = 0{,}056\)).

**Lift en T1.** \(\omega^2 = 0{,}210\), pero \(|\rho| = 0{,}89\) con `slow__coast_frac` y \(\rho\) con la vuelta = −0,31. El pipeline ya lo tiene.

## 4. Ganancia de clustering

K-means sobre las mismas 838 vueltas (las que tienen las dos candidatas finitas), z-score, `random_state = 42`. Base = las 7 columnas de ICC ≥ 0,25: apex *fast* y *medium*, *coast* en las tres tipologías, *trail* *medium* y *slow*. Fuente: `gain_summary.csv`. `candidates_gain.csv` es la fila «base» contra «ambas» que escribe el evaluador con `--extra`.

| Conjunto | k | Silueta | Nula | Gap | Fuerza de predicción | ARI bootstrap | AMI piloto | AMI compuesto | Equipos partidos |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| base (7) | 2 | 0,256 | 0,112 | 0,144 | 0,900 | 0,957 | 0,125 | −0,001 | 0,333 |
| base | 3 | 0,204 | 0,112 | 0,092 | 0,710 | 0,808 | 0,198 | 0,010 | 0,556 |
| base + `fast__lift_coast_s_lapsync` | 2 | **0,284** | 0,094 | **0,190** | **0,923** | 0,954 | **0,141** | −0,001 | 0,333 |
| base + lift | 3 | 0,194 | 0,097 | 0,097 | 0,627 | 0,674 | 0,185 | 0,010 | 0,556 |
| base + `medium__release_to_apex_m_lapsync` | 2 | 0,229 | 0,100 | 0,129 | 0,878 | 0,902 | 0,134 | ~0 | 0,333 |
| base + release | 3 | 0,214 | 0,092 | 0,121 | 0,620 | 0,876 | 0,209 | 0,002 | 0,556 |
| base + las dos | 2 | 0,255 | 0,088 | 0,166 | 0,893 | 0,927 | 0,146 | ~0 | 0,333 |
| base + las dos | 3 | 0,201 | 0,093 | 0,108 | 0,628 | 0,812 | 0,200 | 0,002 | 0,444 |

La única mejora clara es **añadir solo el lift de Ascari, y solo en k = 2** (la solución que el baseline ya prefiere): silueta 0,256 → 0,284, gap 0,144 → 0,190, fuerza de predicción 0,900 → 0,923, AMI con el piloto 0,125 → 0,141. El compuesto no entra. La tasa de equipos partidos no sube (sigue en 3/9): cambian *cuáles*. En k = 2 base se parten Alpine, Mercedes y Red Bull. Con el lift se parten Mercedes, Red Bull y Racing Bulls (Lawson levanta el pie, Hadjar no) y Alpine deja de partirse. k = 3 empeora (fuerza de predicción 0,710 → 0,627).

El punto de suelta *medium* sube el gap en k = 3 (0,092 → 0,121) y el AMI (0,198 → 0,209), pero la fuerza de predicción cae a 0,620 y la tasa de equipos partidos no se mueve. En k = 2 empeora silueta y fuerza de predicción. Juntar las dos columnas no supera al lift solo en k = 2 y en k = 3 baja la tasa de equipos partidos a 0,444. Añadir además el reparto de velocidad del primer medio segundo, o el punto de suelta de T1, diluye: T1 ya está representado por `slow__trail_brake_frac` (\(|\rho| = 0{,}57\)).

`T4__release_to_apex_m` junto con `medium__mean_decel_lapsync` produce en k = 3 un grupo de 44 vueltas. Es Ocon, no una familia de estilo.

## 5. Recomendación, por este orden

1. **`fast__lift_coast_s_lapsync`** — incorporarla al vector de k = 2. Es un hábito de piloto (levantar el pie antes de Ascari), repetible en las dos mitades de la carrera en los 9 equipos, poco ligado al compuesto y, una vez centrado por número de vuelta, poco ligado al combustible. Mejora la partición de k = 2. Coste: 58 % de ceros y \(|\rho| = 0{,}70\) con `fast__coast_frac`. No usarla en crudo: sin el *lapsync* es deriva de carrera (\(\rho = -0{,}38\)) y redundante por encima de 0,8.

2. **`medium__release_to_apex_m_lapsync`** — guardarla como descriptor de *trail*, no como columna extra del K-means actual. \(\omega^2 = 0{,}28\) en la muestra completa y 0,12 sin Ocon; acuerdo de signo 0,89; casi nada de compuesto ni de deriva; \(|\rho| = 0{,}55\) con `medium__trail_brake_frac`, por debajo del corte de 0,8 pero bastante solape. No estabiliza el clustering.

3. **`T1__release_to_apex_m`** (equivale a *slow*) — el mismo papel en la chicane lenta. \(\omega^2 = 0{,}17\) con o sin Ocon, acuerdo de signo 1,00, deriva +0,05. Mecanismo discreto equivalente: **`T1__brake_stabs`** (una aplicación frente a dos; \(\omega^2 = 0{,}13\)). Elegir una de las dos. No mejora el K-means porque el *trail* lento ya está en las 7 columnas.

4. **`medium__frontload_speed_frac_lapsync`** — candidata de reserva. \(\omega^2 = 0{,}11\) también sin Ocon, sin deriva, poco solape con el punto de frenada (0,34), pero el orden de compañeros solo se replica en dos tercios de los equipos y no mueve el clustering.

No incorporar: pico de deceleración, tiempo hasta el pico, velocidad de entrada, ratio de caída de velocidad, duración, *effort* salvo como control, stabs o suelta de la Roggia, media de deceleración, y el *lift* de la Parabólica sin tratar su deriva de −0,30.

## 6. Caveats

- **4 Hz y freno booleano.** Un frenado de T1 tiene unas 13 muestras con freno. No hay presión: no se separa el pedal del drag ni del freno motor. El pico de 4,25 g es el escalón más brusco de un cuarto de segundo, no el pico de g del coche. Por eso el pico no clasifica pilotos y la media MCO, que promedia el *trail*, tampoco lo hace una vez se quita a un piloto extremo.
- **Chicanes.** `brake_stabs` en T1 cuenta las dos partes de la Variante, no un *stab* de cadence braking. En T4, T7 y T11 casi todo el mundo frena una vez; el conteo no tiene varianza.
- **Un piloto puede inflar \(\omega^2\).** El flag `recommended` no lo detecta. Cualquier métrica de la Roggia hay que leerla sin Ocon.
- **Rebufo en Monza.** Mueve la velocidad de entrada (T1, \(R^2 = 0{,}16\)) y la duración ( \(R^2 \approx 0{,}25\)). No mueve el punto de suelta ni el pico (\(R^2 < 0{,}04\)). El aire limpio (< 50 m en los 150 m previos) no mejora las métricas de estilo y cuesta cobertura.
- **Normalizar.** La mediana de sesión por tipología del pipeline no cambia los rangos. El centrado por zona sí, cuando se mezclan curvas heterogéneas. El centrado por número de vuelta es el que quita la deriva común de combustible; no quita el compuesto ni una deriva que cada piloto haga a su ritmo (el *lift* de la Parabólica).
