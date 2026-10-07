# Línea de carrera y dinámica lateral — Monza 2025 (carrera)

Candidatos calculados sobre las 842 vueltas de `lap_matrix.csv`, con la telemetría de posición de `tel.pkl` (X, Y en unidades FastF1 = 1/10 m). No se ha vuelto a cargar FastF1. El evaluador es `scripts/evaluate_candidate_features.py`. Las siete columnas base del clustering son las que selecciona ICC ≥ 0,25: `fast__apex_speed_rel`, `medium__apex_speed_rel`, `fast__coast_frac`, `medium__coast_frac`, `slow__coast_frac`, `medium__trail_brake_frac`, `slow__trail_brake_frac`.

La conclusión corta: **dónde está el mínimo de velocidad dentro de la curva separa compañeros de equipo y no repite las 17 columnas actuales. Cuánto se aparta el coche de la trazada mediana, el radio y la g lateral no aportan estilo.** Meter el ápex en el K-means de las 7 columnas no mejora la partición.

## 1. Línea de referencia

La columna `Distance` es velocidad integrada y no marca el mismo punto de pista en cada vuelta (el frenado definido por `Distance` y el frenado definido sobre la referencia difieren 4 m en mediana y 12 m en el percentil 90; n = 228 pares zona-vuelta, usando `get_corner_fragments`). Por eso toda estación y todo offset se miden sobre una polilínea común.

Construcción:

1. X e Y se pasan a metros dividiendo por 10. A cada vuelta se le aplica un filtro de mediana de 3 muestras (pico aislado de GPS), se tiran pasos &lt; 0,4 m o &gt; 25 m y se reparametriza por su propia longitud de arco cada **2 m**.
2. Semilla: la vuelta cuya longitud de arco es la mediana, suavizada con Savitzky–Golay (ventana 31, polinomio 3).
3. Dos pasadas: se proyectan todos los puntos crudos sobre la polilínea, se descartan los que caen a más de 15 m, y en cada bin de 2 m se toma la mediana de X y de Y. La mediana se suaviza con ventana 11 (22 m), se cierra el bucle y se gira para que la estación 0 quede en la mediana de los inicios de vuelta (línea de meta).
4. Longitud final: **5761,3 m**, 2880 puntos. El `track_length` de `zones.json` es 5735 m: la diferencia es el arco de la trazada mediana, no un error de unidades.

La normal apunta a la **izquierda del sentido de marcha**. El offset firmado \(n\) es positivo a la izquierda. La proyección usa el segmento adyacente al vértice más cercano (los dos candidatos) y se queda con la distancia euclídea menor. Ningún punto de las 842 vueltas quedó a más de 12 m de la referencia (umbral de descarte). Los marcadores de `corners.csv`, proyectados a la misma línea, caen a 0,1–0,4 m: la referencia pasa por el ápex oficial.

Las ventanas de cada zona no se cortan en `Distance`. Se proyecta el XY del marcador geométrico y se trasladan los anchos ya recortados de `zones.json` (metros de frenada antes del primer ápex, pre-ápex, post-ápex y salida). Esos anchos sí vienen del pipeline; la estación, no.

## 2. Suavizado y comprobación física

Sobre la rejilla de 2 m de cada vuelta:

| Uso | Filtro | Ventana |
|---|---|---|
| Posición para el offset y la longitud de arco recorrida | Savitzky–Golay, orden 3, derivada 0, con pad circular | 11 muestras = 22 m |
| Curvatura | derivadas 1 y 2 del mismo filtro | 31 muestras = 62 m |
| Velocidad para \(a_\mathrm{lon}\) | Savitzky–Golay orden 3 | 15 muestras = 30 m |

\[
\kappa = \frac{x' y'' - y' x''}{(x'^2 + y'^2)^{3/2}}
\quad
a_\mathrm{lat} = v^2 \kappa
\quad
a_\mathrm{lon} = v\,\frac{dv}{ds}
\]

\(v\) en m/s. Muestras con \(|\kappa| > 1/8\) (radio &lt; 8 m) se tiran. La g es \(|a|/9{,}81\).

La ventana de 62 m es la que deja la Parabólica en el rango esperado. Con menos suavizado (ventana 22 m) el pico subía de 6 g: era ruido de posición, no grip. Mediana por zona, p95 de \(|a_\mathrm{lat}|\) en la ventana de ápex, y radio \(1/\mathrm{p95}(|\kappa|)\):

| Zona | \(g\) lateral (p95) | Radio mínimo | Caída de velocidad en el ápex | ¿Hay ápex cinemático? |
|---|---:|---:|---:|---|
| T11 Parabólica | 3,81 g | 76 m | 33 km/h | 96 % de las vueltas |
| T8 Ascari | 4,42 g | 69 m | 84 km/h | 100 % |
| T6 Lesmo 1 | 3,77 g | 78 m | 28 km/h | 100 % |
| T7 Lesmo 2 | 3,51 g | 69 m | 52 km/h | 100 % |
| T3 Curva Grande | 2,85 g | 243 m | 13 km/h | 0 % |
| T4 Roggia | 2,00 g | 49 m | 98 km/h | 100 % |
| T1 Rettifilo | 1,92 g | 29 m | 141 km/h | 100 % |

La Parabólica cae en 3–4 g. Ascari a 4,42 g con radio 69 m implica unos 197 km/h en el mínimo: alto, pero coherente con \(v^2/R\), no con una curvatura mal escalada. En el Rettifilo el radio de 29 m está hinchado por la ventana de 62 m (la cuerda real del piano es más corta); 1,9 g a esa velocidad de chicane es el número que corresponde a ese radio suavizado. Curva Grande no tiene mínimo de velocidad interior: la velocidad solo sube (~13 km/h en toda la ventana de ápex) y el argmin se pega al borde. Ahí `apex_late` es NaN en todas las vueltas.

El signo de \(\kappa\) en el pico de la referencia es el de la curva: T1, T4 y T8 positivos (izquierda); T3, T6, T7 y T11 negativos (derecha). Monza se recorre en el sentido en que Curva Grande y la Parabólica son derechas. Encaja.

## 3. Definición de cada métrica

Estación \(s\) en metros sobre la referencia, módulo 5761,3 m. El **ápex cinemático** es el argmin de la velocidad en la ventana de ápex. Solo cuenta si la caída de velocidad en esa ventana es ≥ 15 km/h y el mínimo no es el borde de una traza monótona (regla que anula Curva Grande y conserva la Parabólica).

| Nombre | Definición | Unidad |
|---|---|---|
| `apex_late` | \(s(\text{mín. velocidad}) - s(\text{marcador geométrico más cercano de la zona})\). Positivo = ápex tardío. | m |
| `apex_vs_curv` | \(s(\text{mín. velocidad}) - s(\max\|\kappa\|)\) en frenada→salida. Positivo = el mínimo de velocidad queda después del pico de curvatura. | m |
| `apex_offset` | Mediana de \(n\) en ±10 m del ápex cinemático. Izquierda &gt; 0. | m |
| `entry_offset` | Mediana de \(n\) en la banda fija \([s_\mathrm{primero}-100,\ s_\mathrm{primero}-40]\). | m |
| `exit_offset` | Mediana de \(n\) en \([s_\mathrm{último}+30,\ s_\mathrm{último}+110]\). | m |
| `brake_offset` | Mediana de \(n\) en ±8 m del primer frenado sostenido 4 m dentro de la ventana de frenada. | m |
| `line_width` | \(\max n - \min n\) de frenada a salida, con \(\|n\| \le 12\). | m |
| `mean_offset` | Media de \(n\) en esa misma ventana. | m |
| `inside_*` | El offset correspondiente × signo de \(\kappa\) de la referencia en el pico de la zona. Positivo = hacia el interior de ese pico. | m |
| `min_radius` | \(1 / \mathrm{p95}(\|\kappa\|)\) en la ventana de ápex. | m |
| `peak_lat_g` | \(\mathrm{p95}(\|a_\mathrm{lat}\|)/g\) en la ventana de ápex. | g |
| `mean_gg` | Media de \(\sqrt{a_\mathrm{lat}^2 + a_\mathrm{lon}^2}/g\) en la ventana de ápex. | g |
| `lat_grip_share` | Media de \(\|a_\mathrm{lat}\| / \sqrt{a_\mathrm{lat}^2+a_\mathrm{lon}^2}\) donde la g combinada &gt; 0,5 g. | 0–1 |
| `path_delta` | Longitud de arco suavizada de la vuelta menos el arco de referencia entre los extremos de la zona. Negativo = camino más corto. | m |
| `turnin_dist` | Metros desde el primer punto en que \(\|\kappa\|\) supera \(\max(0{,}0015,\ 0{,}25\,\kappa_\mathrm{pico})\) durante 8 m, hasta el pico de \(\|\kappa\|\). | m |
| `turnin_vs_brake` | Estación de ese turn-in menos la estación del onset de freno. Positivo = gira después de frenar. | m |
| `*_rollstd` | Desviación típica móvil de 5 vueltas (mínimo 4) del mismo piloto, misma zona. | la de la métrica |

Las columnas por zona se dejan en unidades físicas (no se resta la mediana). Las columnas de tipología (`medium__`, `fast__`) son otra cosa: a cada zona se le resta **su** mediana de sesión y luego se toma la mediana entre zonas de esa tipología. El centrado es por zona, no por el bloque de tipología como en `normalize_typology_session_median`, porque si no la mediana la gana la curva cuyo cero está más lejos (en la Parabólica el mínimo de velocidad cae ~40 m antes del marcador; en Ascari ~18 m después). `slow__` no se emite: solo existe T1, y sería la misma columna que `T1__` salvo una constante.

`fast__apex_late` es, en la práctica, `T8__apex_late` centrado (correlación 0,9998). Curva Grande no aporta ápex. No hay que entrar las dos al clustering.

## 4. Qué mide el offset, de verdad

La referencia **es** la trazada mediana, no el eje geométrico de la pista. El balanceo out-in-out ya está dentro de la línea. Lo que queda en \(n\) es el residuo de cada piloto respecto a esa trazada.

La propia referencia se aparta de la cuerda entrada–salida **45 m en T1** y **250 m en T11** (eso es la flecha de la curva, no el ancho de pista). El `line_width` mediano de los pilotos es 0,35 m en T1 y 0,97 m en T11. En el Rettifilo, ALO y STR (la pareja de compañeros con mayor hueco de `apex_offset`) se dibujan encima de la referencia; el panel derecho de `T1_reference_lines.png` es \(n(s)\) y cabe en ±0,2 m. La desviación típica de `T1__apex_offset` entre las 842 vueltas es 8 cm. No es un fallo de proyección: el XY crudo, en el marcador de la curva 1, tiene una dispersión entre medias de piloto del orden de 15–30 cm en la dirección lateral. En Monza la trazada libre es casi común. El estilo lateral, si existe, está en **dónde** se produce el mínimo de velocidad, no en un carril distinto.

## 5. Scores

Umbral `recommended` del evaluador: cobertura ≥ 0,9, fracción de ceros ≤ 0,9, \(\omega^2\) piloto-dentro-de-equipo ≥ 0,03 con p &lt; 0,01, Spearman-Brown ≥ 0,7, \(\omega^2\) de compuesto dentro de piloto &lt; 0,05, y \(|\rho|\) máximo con las 17 columnas actuales &lt; 0,8. El \(\rho\) con el número de vuelta **no** entra en el flag; se mira aparte porque la velocidad de ápex del pipeline deriva con la gasolina (\(\rho \approx +0{,}78\)).

Doce columnas salen recomendadas. Dos pares son la misma variable (`fast__apex_late` ≡ `T8__apex_late`, `fast__apex_vs_curv` ≡ `T8__apex_vs_curv`). p &lt; 0,001 en todas las de la tabla. Nueve escuderías con dos pilotos.

| Métrica | \(\omega^2\) pilotos | share equipo | SB | acuerdo de signo | \(\omega^2\) compuesto | \(\rho\) vida | \(\rho\) vuelta | \(\|\rho\|\) actual | más parecida |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `medium__apex_late` | **0,155** | 0,112 | 0,956 | 0,889 | 0,027 | +0,22 | +0,17 | 0,125 | `medium__brake_point_rel` |
| `T7__apex_late` | 0,102 | 0,090 | 0,931 | 0,889 | 0,003 | +0,20 | +0,24 | 0,169 | `medium__apex_speed_rel` |
| `T11__apex_late` | 0,092 | 0,117 | 0,963 | **1,000** | 0,021 | +0,09 | **+0,04** | 0,093 | `fast__coast_frac` |
| `T6__apex_late` | 0,091 | 0,085 | 0,913 | 0,889 | 0,022 | +0,23 | +0,12 | 0,189 | `medium__brake_point_rel` |
| `T8__apex_late` | 0,074 | 0,084 | 0,933 | 0,667 | 0,012 | −0,03 | **+0,03** | 0,183 | `fast__apex_speed_rel` |
| `medium__apex_vs_curv` | 0,058 | 0,057 | 0,892 | 0,778 | 0,002 | +0,15 | +0,08 | 0,084 | `medium__brake_point_rel` |
| `T11__apex_vs_curv` | 0,050 | 0,057 | 0,820 | 0,889 | 0,009 | +0,05 | −0,02 | 0,092 | `medium__brake_point_rel` |
| `T1__lat_grip_share` | 0,040 | 0,064 | 0,905 | 0,889 | 0,005 | −0,05 | −0,07 | 0,323 | `slow__apex_speed_rel` |

`medium__apex_late` está por encima de `coast_frac` (0,12–0,15 en el diagnóstico de las 17 columnas) y casi no se solapa con el punto de frenada (\(|\rho| = 0{,}13\)). ICC de piloto = 0,27. La deriva con la vuelta (+0,17) y con la vida del neumático (+0,22) existe, pero es mucho menor que la de la velocidad de ápex.

Lectura en metros, mediana por piloto. `medium__apex_late` ya está centrado por zona (0 = la trazada típica de esa curva; positivo = mínimo de velocidad más tarde que el campo):

| Escudería | Más temprano | Más tarde | Hueco |
|---|---|---|---:|
| Alpine | COL −4,9 m | GAS +0,8 m | 5,8 m |
| Aston Martin | ALO −3,4 m | STR +1,6 m | 5,1 m |
| Racing Bulls | LAW +0,2 m | HAD +5,0 m | 4,8 m |
| Ferrari | LEC −1,1 m | HAM +2,7 m | 3,8 m |
| McLaren | NOR −1,0 m | PIA +2,3 m | 3,3 m |
| Haas | BEA −3,0 m | OCO +0,2 m | 3,2 m |
| Williams | ALB −1,5 m | SAI −0,5 m | 1,1 m |
| Mercedes | RUS −0,4 m | ANT −0,6 m | ~0,3 m |
| Red Bull | VER +0,7 m | TSU +0,8 m | ~0,1 m |

En la Parabólica en bruto el mínimo de velocidad cae **antes** del marcador de la curva 11 en todas las medias de piloto: de −46 m (ALB) a −34 m (STR). El marcador FastF1 está más adentro de la curva que el punto lento. El estilo es en qué lado de esos ~12 m se sienta cada piloto. En Ascari el mínimo cae **después** del marcador más cercano: de +8 m (ALO) a +22 m (PIA).

`T7__apex_late` arrastra más la vuelta (\(\rho = +0{,}24\)) que T11 o T8. `T8__apex_late` es el más limpio de combustible y neumático, pero el orden entre compañeros solo se sostiene en 6 de 9 escuderías (acuerdo 0,67).

## 6. Ganancia de clustering

`candidates_gain.csv` es la base de 7 columnas contra esa base más **`medium__apex_late` y `T8__apex_late`** (842 vueltas, K-means sobre z-score, la misma semilla y los mismos permutados/bootstrap que el evaluador). Es el mejor de los conjuntos de 2–4 que se probaron: añadir `T11__apex_vs_curv` o `medium__apex_vs_curv` + `T1__lat_grip_share` baja más la silueta y, en k = 3, la fuerza de predicción. Esos contrastes están en `gain_comparison.csv`.

| Conjunto | k | silueta | nulo | gap | PS | ARI bootstrap | AMI piloto | AMI compuesto | split compañeros |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| base (7) | 2 | 0,256 | 0,112 | 0,145 | 0,895 | 0,937 | 0,126 | −0,001 | 0,333 |
| base + 2 | 2 | 0,209 | 0,087 | 0,122 | 0,878 | 0,933 | 0,125 | −0,000 | **0,444** |
| base (7) | 3 | 0,204 | 0,109 | 0,094 | 0,688 | 0,838 | 0,198 | 0,009 | 0,556 |
| base + 2 | 3 | 0,154 | 0,083 | 0,071 | 0,676 | 0,782 | 0,198 | 0,005 | 0,556 |

La base reproduce el diagnóstico ya conocido (k = 2: silueta 0,256 frente a nulo 0,112 y PS ≈ 0,90; k = 3: silueta 0,204, PS 0,69, AMI piloto 0,198, split 0,556).

Añadir el ápex **no mejora la partición**. La silueta y el gap bajan. El AMI con el piloto no se mueve. El único cambio a favor es el split de compañeros en k = 2: de 3/9 a 4/9 escuderías. En k = 3 se queda en 5/9. El eje nuevo es casi ortogonal a los clusters que ya forman coasting y trail braking (de ahí que \(|\rho|\) con las 17 columnas sea ~0,1). En un K-means con z-score pesa lo mismo que una columna que sí agrupa, y diluye la geometría.

Se probó también **sustituir** las dos `apex_speed_rel` (las que derivan con la gasolina) por `medium__apex_late` y `T8__apex_late`, dejando las cinco de coast y trail. Tampoco arregla el clustering: k = 2 silueta 0,208, PS 0,845, AMI piloto 0,153, split 0,444; k = 3 silueta 0,170, PS 0,444, split 0,444. Más alineado con el piloto en k = 2, peor fuerza de predicción en k = 3. Archivo: `gain_replace_apex_speed.csv`. No es el contraste por defecto del evaluador; es una comprobación.

El \(\omega^2\) alto y la silueta peor no se contradicen. `apex_late` ordena pilotos de forma estable (Spearman-Brown 0,96) a lo largo de un eje continuo de unos 10 m. Eso no es un grupo discreto. Sirve para describir estilo y para separar compañeros. No sirve, en este circuito y con este K-means, para subir la calidad de la partición de las 7 columnas.

## 7. Qué no funcionó

**Offset lateral, ancho de línea, camino más corto, radio.** \(\omega^2\) de piloto ≈ 0 o negativo en `apex_offset`, `entry_offset`, `exit_offset`, `line_width`, `path_delta` y `min_radius` de T1, T11 y de la tipología. El radio de T1 tiene desviación típica de 0,5 m sobre 29 m: la curva, una vez suavizada, es la misma para todos. `path_delta` vale unos −2 m en todas las zonas (el arco suavizado es sistemáticamente más corto que la estación de referencia) y no discrimina. El residuo lateral es real pero de decímetros, por debajo de lo que esta muestra y este GPS distinguen entre pilotos una vez se promedia la vuelta.

**`T8__apex_offset` es la excepción a medias.** \(\omega^2 = 0{,}051\), acuerdo de signo 0,889, share de equipo solo 0,035, Spearman-Brown 0,90. Falla el flag por compuesto (\(\omega^2 = 0{,}058\)) y deriva con la vuelta (\(\rho = -0{,}33\)) y con la velocidad de ápex (\(|\rho| = 0{,}48\)). Además, al quitar las vueltas con coche a menos de 50 m el \(\omega^2\) baja a 0,027. No lo usaría.

**g lateral y g combinada.** `medium__peak_lat_g` tiene \(\omega^2 = 0{,}079\) pero \(|\rho| = 0{,}92\) con `medium__apex_speed_rel`, \(\rho\) con la vuelta +0,76 y \(\omega^2\) de compuesto 0,46. `T11__mean_gg`: \(\omega^2 = 0{,}113\), share de equipo 0,24, \(|\rho| = 0{,}87\), \(\rho\) vuelta +0,71, compuesto 0,48. Con el radio casi fijo, \(v^2\kappa\) es la velocidad de ápex al cuadrado. Es el coche y la gasolina, no la trazada.

**Turn-in.** En T1 la estación del turn-in es casi constante (desviación típica ~2 m): el chicane obliga. `T4__turnin_vs_brake` sí separa (\(\omega^2 = 0{,}044\), SB 0,92) pero es el punto de frenada disfrazado (\(|\rho| = 0{,}66\) con `medium__brake_point_rel`, \(\rho\) vuelta −0,46, compuesto 0,12).

**Chicanes como ápex único.** `T4__apex_late` (Roggia, dos curvas) tiene \(\omega^2 = 0{,}006\) y p = 0,12. `T1__apex_late` se queda en 0,027 (justo bajo el corte), acuerdo de signo 0,67. En el Rettifilo, si se tiran las vueltas con un coche a menos de 50 m en la zona, el \(\omega^2\) sube a **0,107**, pero solo el 46 % de las vueltas están limpias: no pasa la cobertura. El tráfico se come la señal precisamente en la curva donde más se compromete la trazada.

**Consistencia vuelta a vuelta.** `T11__apex_offset_rollstd` pasa el flag (\(\omega^2 = 0{,}034\), SB 0,96) y `T1__apex_offset_rollstd` no, por compuesto (0,057). Es la volatilidad de un offset de centímetros. No es una elección de trazada y no entró en el conjunto de clustering.

**`T1__lat_grip_share`** sí pasa (fila de la tabla: \(\omega^2 = 0{,}040\)). Es la fracción lateral de la g combinada en el ápex del Rettifilo, es decir cuánto queda de freno frente a cuánto ya es apoyo. Señala poco, correlaciona 0,32 con la velocidad de ápex lenta, y al añadirla al K-means la silueta empeora más. La dejo como nota, no como candidata a la matriz.

Tráfico (`DistanceToDriverAhead` &lt; 50 m en algún punto de la zona): T1 54 %, T4 45 %, T8 32 %, T7 32 %, T6 30 %, T11 28 %, T3 16 %. En T6, T7 y T11 el \(\omega^2\) de `apex_late` se mantiene o sube al quitar esas vueltas (T11: 0,092 → 0,110, 72 % limpias). La señal de la Parabólica y de Lesmo no es un artefacto de rebufo. En Ascari baja (0,074 → 0,043) pero sigue por encima de 0,03.

## 8. Caveats

- Posición ~4 Hz interpolada a ~630 muestras por vuelta, ruido del orden de 1 m. La ventana de 62 m que hace creíble la g también borra el piano del chicane. Por eso el radio de T1 no es el radio del bordillo.
- El offset respecto a la trazada mediana comprime diferencias que sí existirían respecto a un eje geométrico. Aquí no había bordes de pista fiables para construir ese eje; los marcadores de curva ya están sobre la trazada (0,2 m).
- `Distance` deriva varios metros (4 m típicos, 12 m en la cola del frenado). Un ápex medido en `Distance` se mezclaría con ese error. Aun así, el hueco entre compañeros en `medium__apex_late` es de 3–6 m: el mismo orden que la deriva. La referencia lo reduce; no lo vuelve nulo.
- 148 columnas y un corte p &lt; 0,01 sin corrección. La familia `apex_late` se repite en T6, T7, T11, T8 y en el agregado, así que no es una columna suelta. `lat_grip_share` y el rollstd están en el filo y no los promovería.
- `apex_late` en una chicane de dos vértices (T1, T4) no tiene un solo significado. En Ascari (T8–T10) el «marcador más cercano al mínimo de velocidad» elige uno de los tres números; el +8 a +22 m es respecto a ese número, no respecto a T8 siempre.
- El acuerdo de signo de T8 es 0,67. La fiabilidad del ranking (SB 0,93) no implica que el orden dentro de cada coche sea estable.
- Monza es un circuito de trazada estrecha. Que el offset no separe pilotos aquí no dice que no lo haga en un circuito con más de una línea (Hungaroring, Mónaco, Interlagos).

## 9. Recomendación, en orden

1. **`medium__apex_late`** — la única métrica de esta familia que yo metería en la discusión de estilo. \(\omega^2 = 0{,}155\), share de equipo 0,11, SB 0,96, acuerdo 0,89, compuesto 0,027, \(\rho\) vuelta +0,17, \(|\rho|\) con lo ya existente 0,13. No la apilaría sobre las 7 columnas del K-means: no sube la silueta.
2. **`T11__apex_late`** — la curva limpia. \(\omega^2 = 0{,}092\), acuerdo de signo 1, \(\rho\) vuelta +0,04, casi nada de solape con las 17. Es parte del agregado medium (\(\rho\) de Spearman ≈ 0,6 con él); no las dos a la vez.
3. **`T6__apex_late` y `T7__apex_late`** — Lesmo, \(\omega^2\) 0,09 y 0,10. T7 deriva más con la vuelta (+0,24). Redundantes con el agregado si el agregado ya está.
4. **`T8__apex_late`** — Ascari, \(\omega^2 = 0{,}074\), sin deriva de vuelta ni de neumático. Acuerdo de signo flojo (0,67) y parte de la señal se va con el tráfico. `fast__apex_late` es la misma columna: usar solo una.
5. **`medium__apex_vs_curv` / `T11__apex_vs_curv`** — más débiles (0,05–0,06), muy poco solape con lo existente, pero correlacionan ~0,5–0,6 con `apex_late`. No añaden un eje nuevo.
6. No usar offset, ancho de línea, radio, `path_delta`, turn-in, ni g lateral / g combinada. La g es la velocidad de ápex. El offset en Monza es centímetros sobre una trazada común.

El archivo de ganancia por defecto (`candidates_gain.csv`) corresponde al punto 1 junto con el punto 4, que es el par menos malo para el clustering y aun así no lo mejora.
