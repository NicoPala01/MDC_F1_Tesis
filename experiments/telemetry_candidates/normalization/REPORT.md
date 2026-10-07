# Normalización y control de confundidores (Monza 2025)

Comparación, sobre las métricas que ya entran en el clustering, de formas de quitar el reloj común de la carrera (combustible, evolución de pista, temperatura) y el neumático, sin convertir la métrica en ruido de vuelta. Carrera: Gran Premio de Italia 2025, 842 vueltas canónicas, 19 pilotos, 10 equipos. Una parada; el compuesto está casi alineado con el número de vuelta.

El criterio de «mejor métrica de estilo» es el de `feature_evaluation`:

- sube \(\omega^2\) del piloto dentro del equipo (señal entre compañeros, por encima del azar);
- no sigue el compuesto, la vida del neumático ni el número de vuelta *dentro* del piloto;
- mantiene la fiabilidad partida (Spearman-Brown alto);
- y, al **reemplazar** las 7 columnas base, el K-means deja de separar stints (mediana de `TyreLife` y de `LapNumber` parecidas entre clusters) sin caer al nivel del nulo de silueta.

Añadir la columna renormalizada al lado de la original no es el contraste correcto: está correlacionada con ella por construcción. Ese anexo está en `candidates_gain.csv` y sale peor. El contraste que importa es el reemplazo (`replacement_clustering.csv`).

## 1. Reconstrucción

Las métricas crudas se recalcularon con `extract_style_features_from_telemetry` sobre `car.pkl` y las zonas de `zones.json` (842 × 7 zonas). El agregado por (piloto, vuelta, tipología) reproduce la matriz exportada **salvo una constante por columna** (Pearson = 1, desviación estándar del residuo = 0; `reconstruction_check.csv`).

Esa constante es el cero que restó el pipeline. No coincide siempre con la mediana de las 842 vueltas que sobrevivieron: en `fast__apex_speed_rel` el export está 29 km/h por debajo del recentrado por mediana de zona, en todas las vueltas. Para velocidad de apex lenta la constante sí es la mediana (69 km/h). Un desplazamiento fijo no cambia \(\omega^2\), las correlaciones de Spearman ni el K-means sobre z-scores. Las columnas `__session` de este experimento son **exactamente** las del export, no el recentrado recalculado.

Comprobación de la línea base (z-score, K-means, `n_init=20`, `random_state=42`), 7 columnas ICC:

| k | silueta | nulo (5 perm.) | gap | PS | ARI bootstrap | AMI piloto | AMI compuesto | split compañeros | TyreLife (por cluster, ordenado por vuelta) | LapNumber |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 0.256 | 0.108–0.112 | 0.149 | 0.895 | 0.937 | 0.126 | −0.001 | 0.333 | 13.0 (n=340) vs 18.5 (n=502) | 15 vs 33.5 |
| 3 | 0.204 | 0.113 | 0.091 | 0.688 | 0.838 | 0.198 | 0.009 | 0.556 | 13, 17, 17 | 15, 22, 38 |

El nulo se mueve unas milésimas entre tandas de 5 permutaciones; la segunda pasada del evaluador oficial dio 0.112 en k=2. El corte k=2 es el que ya se había descrito (vida 13 vs 18.5). En k=3 las medianas de vuelta son 15, 22 y 38: la partición lee el reloj de la carrera.

`raw` y `session` tienen \(\omega^2\), \(\rho\) y fiabilidad idénticos. Restar la mediana de sesión por tipología es un desplazamiento. No toca la tendencia dentro del piloto. Por eso el apex y el punto de frenada siguen a la vuelta (\(\rho \approx +0.78\) y \(\approx -0.51\)) después de la normalización actual.

## 2. Definiciones

Notación: piloto \(d\), vuelta \(\ell\), zona \(z\), tipología \(t\), métrica cruda \(x\) (mínimo de velocidad, fracción, metros al apex, etc.). \(\tilde x_{d,\ell,t}\) es la mediana de las zonas de esa tipología en esa vuelta. \(L\) = `LapNumber`, \(T\) = `TyreLife`, \(c\) = compuesto (HARD de referencia, dummies MEDIUM y SOFT).

**1. Sesión (pipeline actual).** En la tabla larga, por tipología:

\[
x^{\mathrm{ses}}_{d,\ell,z} = x_{d,\ell,z} - \mathrm{med}(x \mid t(z))
\]

y después la mediana por \((d,\ell,t)\). Equivale a \(\tilde x_{d,\ell,t} - c_t\).

**2. Síncrona por vuelta (tipología).** Referencia = mediana del campo en esa misma vuelta:

\[
y^{\mathrm{ls}}_{d,\ell,t} = \tilde x_{d,\ell,t} - \mathrm{med}_{d'}(\tilde x_{d',\ell,t})
\]

Quita lo que hacen todos a la vez (combustible, goma en pista, temperatura). El piloto que frena más tarde que el resto en esa vuelta conserva el contraste. La vuelta 40 solo tiene 2 pilotos en la matriz; el resto de las vueltas tiene al menos 8. Variante `lapsync_roll`: la mediana usa las vueltas en \([\ell-2,\ell+2]\).

**3. Síncrona por zona, y después mediana de tipología.**

\[
y^{\mathrm{zona}}_{d,\ell,t} = \mathrm{med}_{z \in t}\Big(x_{d,\ell,z} - \mathrm{med}_{d'}(x_{d',\ell,z})\Big)
\]

No es lo mismo que (2) cuando hay varias zonas: Curva Grande y Ascari no comparten referencia. Roggia, Lesmo y Parabólica tampoco.

**4. Regresión pooled (sin efectos fijos de piloto).** Mínimos cuadrados sobre las 842 vueltas. El residuo es la métrica. El término independiente absorbe el nivel; la media de piloto solo se conserva en la parte ortogonal a las covariables.

- `reg_lap`: \(x = \beta_0 + \beta_L L + \varepsilon\)
- `reg_lin`: \(x = \beta_0 + \beta_L L + \beta_T T + \gamma_c + \varepsilon\)
- `reg_int`: lo anterior más \(T \times \mathbf{1}_{c}\)

**5. Misma pendiente, estimada dentro del piloto (efectos fijos).** Se demedia \(x\) y \(X\) dentro de \(d\), se estima \(\beta\) por mínimos cuadrados, y la métrica es

\[
y^{\mathrm{FE}}_{d,\ell} = x_{d,\ell} - X_{d,\ell}\hat\beta = \hat\alpha_d + \hat\varepsilon_{d,\ell}
\]

Se elimina solo la parte de covariable. El nivel de piloto se queda. Especificaciones: `reg_lap_fe`, `reg_lin_fe`, `reg_int_fe`, y `reg_spline_fe` (spline cúbico de \(L\), 4 nudos por cuantiles, sin intercepto en la base, más \(T\) y compuesto; 6 columnas de spline). `statsmodels` no está instalado; el ajuste es `numpy.linalg.lstsq`.

**6. Después de la síncrona, neumático dentro del piloto** (`lapsync_tyre_fe`): se toma \(y^{\mathrm{ls}}\) y se residualiza con efectos fijos solo en \(T\) y compuesto (la vuelta común ya salió).

**7. Tráfico.** En `tel.pkl`, hueco al coche de delante en el inicio de frenada de cada zona (muestra más cercana con `DriverAhead` no vacío; hueco vacío = aire limpio, no se marca). Para la tipología se usa el mínimo de sus zonas.

- Exclusión: el valor de sesión pasa a NaN si ese mínimo es < 30, 50 o 100 m (`session_xgap30/50/100`).
- Recta previa: mediana del hueco en los 200 m anteriores al inicio de la zona de frenada; exclusión a 50 m (`session_xslip50`).
- Covariable: \(\log(1+g)\) del hueco mediano, imputado con su mediana si falta, dentro del modelo FE lineal (`reg_lin_fe_gap`).
- Combinación: residuo FE con NaN si el hueco < 50 m (`reg_lin_fe_xgap50`).

**8. Relativo al compañero** (otra pregunta). En la misma vuelta, si los dos pilotos del equipo están en la matriz:

\[
y^{\mathrm{comp}}_{d,\ell,t} = \tilde x_{d,\ell,t} - \mathrm{mean}_{d' \in \mathrm{equipo}(d)}(\tilde x_{d',\ell,t})
\]

Si no hay compañero (Kick Sauber, o el compañero ya no está), el valor queda vacío. Por construcción la varianza entre equipos es 0.

**9. Tendencia propia del piloto.**

- `detrend`: dentro de cada piloto, \(y = x - \hat b_d (L - \bar L_d)\). Quita la pendiente de ese piloto y conserva su media.
- `z_driver`: \((x - \bar x_d)/s_d\). Quita el nivel. Es el control que debía salir mal.

## 3. Tráfico en Monza

Hueco observado en el inicio de frenada (aire limpio o muestra ausente no entra en el porcentaje):

| grano | tipología | n | % < 30 m | % < 50 m | % < 100 m | % recta < 50 m | mediana del hueco (m) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| zona | slow (T1) | 842 | 5.3 | 17.9 | 48.7 | 9.0 | 98 |
| zona | medium | 3368 | 5.5 | 20.8 | 45.1 | 16.6 | 102 |
| zona | fast | 1684 | 1.8 | 8.6 | 21.5 | 13.2 | 114 |
| tipología (mínimo de sus zonas) | slow | 842 | 5.3 | 17.9 | 48.7 | 9.0 | 98 |
| tipología | medium | 842 | 4.8 | 22.7 | 46.4 | 27.6 | 105 |
| tipología | fast | 842 | 3.6 | 17.2 | 43.0 | 20.0 | 114 |
| vuelta, alguna tipología | any | 842 | 8.6 | 26.8 | 50.6 | 29.3 | — |

Menos de 30 m en alguna zona de frenada: 72 vueltas (8.6 %). Menos de 50 m: 226 vueltas (26.8 %). Menos de 100 m: la mitad de la carrera (50.6 %). En Monza el rebufo es real, pero un umbral de 100 m se lleva el pelotón, no solo el coche de delante.

El coeficiente dentro de piloto de \(\log(1+g)\) en el apex medio es +2.6 km/h por unidad de log: entre 30 m y 300 m hay del orden de 6 km/h. El rebufo mueve la velocidad de entrada. Aun así, quitar esas vueltas **no** quita la correlación con el número de vuelta (sección 5).

## 4. Ajuste de las regresiones

\(R^2\) *dentro* del piloto (fracción de la varianza intra-piloto que se lleva la covariable):

| métrica | solo \(L\) (FE) | \(L+T+c\) (FE) | + hueco | spline FE |
| --- | --- | --- | --- | --- |
| fast apex | 0.60 | 0.61 | 0.68 | 0.62 |
| medium apex | 0.64 | 0.67 | 0.79 | 0.70 |
| fast brake | 0.28 | 0.30 | 0.35 | 0.34 |
| medium brake | 0.24 | 0.25 | 0.33 | 0.28 |
| slow brake | 0.27 | 0.27 | 0.34 | 0.29 |

Casi todo lo que se puede quitar con una recta ya lo quita el número de vuelta. Añadir vida y compuesto suma unos 0.03 de \(R^2\) en el apex medio. El número de condición del diseño demediado es 1 con solo \(L\), ~115 con \(L+T+c\), ~260 con la interacción y ~1660 con el spline. La pendiente de compuesto MEDIUM en el apex medio es −0.07 km/h: no está identificada aparte de la vuelta. Por eso el residuo FE sigue teniendo medias de compuesto dentro del piloto de varios km/h (p. ej. Bearman: +2.0 km/h en HARD y −3.9 en MEDIUM) y \(\omega^2\) de compuesto del apex medio se queda en 0.12.

Pendiente de vuelta, apex, efectos fijos: +0.18 km/h por vuelta (rápido) y +0.32 km/h por vuelta (medio). Es el efecto de ir vaciando el depósito, común y grande.

## 5. Resultados por métrica

Medias de las 7 columnas base y de los 3 puntos de frenada. \(\omega^2\) de piloto es la señal de estilo; \(\omega^2\) de compuesto y \(|\rho|\) con la vuelta son los confundidores. Spearman-Brown de la base se mantiene en 0.97–0.98 en todas las normalizaciones de muestra completa.

| normalización | \(\omega^2\) piloto, base 7 | \(\omega^2\) compuesto | \(\|\rho\|\) vuelta | \(\omega^2\) piloto, frenos | \(\omega^2\) compuesto, frenos | \(\|\rho\|\) vuelta, frenos |
| --- | --- | --- | --- | --- | --- | --- |
| session (= raw) | 0.108 | 0.172 | 0.340 | 0.054 | 0.176 | 0.502 |
| lapsync | 0.135 | 0.048 | 0.079 | 0.095 | 0.061 | 0.044 |
| lapsync_roll | 0.136 | 0.049 | 0.086 | 0.094 | 0.061 | 0.053 |
| lapsync_zone | 0.141 | 0.040 | 0.086 | 0.106 | 0.069 | 0.046 |
| lapsync_tyre_fe | 0.132 | 0.036 | 0.025 | 0.095 | 0.056 | 0.020 |
| reg_lap / reg_lap_fe | 0.134 | 0.046–0.048 | 0.056 | 0.091 | 0.064 | 0.02–0.03 |
| reg_lin (pooled) | 0.125 | 0.072 | 0.059 | 0.083 | 0.070 | 0.019 |
| reg_lin_fe | 0.129 | 0.033 | 0.054 | 0.089 | 0.055 | 0.028 |
| reg_int_fe | 0.129 | 0.034 | 0.055 | 0.090 | 0.053 | 0.029 |
| reg_spline_fe | 0.132 | 0.033 | 0.046 | 0.092 | 0.050 | 0.023 |
| reg_lin_fe_gap | 0.144 | 0.037 | 0.053 | 0.087 | 0.050 | 0.029 |
| detrend | 0.142 | 0.009 | 0.042 | 0.081 | 0.005 | 0.013 |
| session_xgap30 | 0.113 | 0.176 | 0.337 | 0.052 | 0.166 | 0.483 |
| session_xgap50 | 0.127 | 0.164 | 0.305 | 0.072 | 0.092 | 0.402 |
| session_xgap100 | 0.138 | 0.167 | 0.270 | 0.065 | 0.065 | 0.269 |
| teammate | 0.374 | 0.048 | 0.000 | 0.218 | 0.051 | 0.000 |
| z_driver | −0.011 | 0.160 | 0.340 | −0.011 | 0.134 | 0.502 |

Detalle de las métricas que estaban rotas (apex y frenada) y de las que ya eran de estilo (coast, trail). Columnas: sesión → lapsync → FE lineal → FE + hueco.

| métrica | \(\omega^2\) piloto | \(\omega^2\) compuesto | \(\rho\) con la vuelta |
| --- | --- | --- | --- |
| fast apex | 0.096 → 0.168 → 0.169 → **0.219** | 0.413 → **0.043** → 0.040 → 0.026 | +0.778 → −0.131 → +0.003 → −0.005 |
| medium apex | 0.085 → 0.159 → 0.146 → **0.201** | 0.558 → 0.122 → 0.115 → 0.150 | +0.785 → −0.082 → −0.047 → −0.052 |
| slow brake | 0.040 → **0.073** → 0.071 → 0.069 | 0.211 → 0.077 → 0.076 → 0.067 | −0.509 → −0.058 → +0.045 → +0.043 |
| medium brake | 0.069 → **0.114** → 0.099 → 0.090 | 0.146 → 0.027 → **0.013** → 0.013 | −0.489 → −0.004 → +0.004 → +0.018 |
| fast brake | 0.053 → 0.097 → 0.097 → **0.102** | 0.170 → 0.080 → 0.076 → 0.070 | −0.509 → −0.070 → +0.037 → +0.027 |
| slow coast | 0.153 → 0.160 → 0.157 → 0.157 | 0.066 → 0.071 → 0.023 → 0.025 | −0.193 → +0.110 → +0.076 → +0.077 |
| medium coast | 0.136 → **0.150** → 0.145 → 0.145 | 0.070 → 0.037 → 0.027 → 0.029 | −0.175 → +0.039 → +0.122 → +0.109 |
| fast coast | 0.124 → **0.139** → 0.134 → 0.134 | 0.077 → 0.026 → 0.012 → 0.012 | −0.343 → +0.123 → +0.105 → +0.107 |
| slow trail | 0.040 → 0.047 → 0.039 → 0.038 | 0.007 → 0.017 → 0.004 → 0.004 | +0.073 → −0.067 → +0.017 → +0.018 |
| medium trail | 0.119 → 0.122 → 0.114 → 0.115 | 0.014 → 0.020 → 0.012 → 0.012 | +0.033 → +0.002 → +0.007 → +0.006 |

Lectura:

- El apex deja de ser un medidor de combustible. La señal entre compañeros casi se dobla (0.09 → 0.16) y \(\rho\) con la vuelta pasa de ~0.78 a ~0. En zona rápida el compuesto cae de 0.41 a 0.04, por debajo del umbral 0.05 del evaluador.
- El apex **medio** no queda limpio de compuesto: 0.56 → 0.12 con lapsync y 0.12 con el FE. El mejor de esta familia es `lapsync_zone` (0.083) y `detrend` (0.073). Ninguno baja de 0.05. La razón está en la sección 4: a la misma vuelta hay pilotos en compuestos distintos, y la pendiente de compuesto no se separa de la de la vuelta.
- El punto de frenada era débil como estilo (\(\omega^2\) 0.04–0.07) y fuerte como reloj (\(\rho \approx -0.51\)). La síncrona lo deja en \(|\rho| < 0.07\) y sube \(\omega^2\) a 0.07–0.11. Sigue siendo una señal pequeña, ya no es el nivel de depósito. En frenada media, `lapsync_zone` llega a \(\omega^2 = 0.148\).
- Coast y trail ya tenían señal de piloto y poca vida de neumático. La síncrona los deja igual o un poco mejor. No eran el problema. El trail lento sigue en \(\omega^2 \approx 0.04\): normalizar no crea señal donde no la hay.
- La fiabilidad no se rompe (Spearman-Brown ≥ 0.93 en la muestra completa; acuerdo de signo entre compañeros 0.86–0.94).
- La fracción de varianza entre equipos **sube** (base 7: 0.27 → 0.32) porque cae el ruido intra-piloto. El coche sigue dentro de la métrica. Esto no es un contraste piloto-contra-coche.

El flag `recommended` del evaluador es poco útil aquí: exige \(|\rho| < 0.8\) con alguna de las 17 columnas actuales, y una renormalización del apex está correlacionada con el apex. `fast__apex_speed_rel__lapsync` sí sale recomendada (\(\omega^2 = 0.168\), compuesto 0.043, \(\rho\) con la columna actual 0.67). El apex medio síncrono no, por el compuesto residual de 0.12.

## 6. Clustering de reemplazo

K-means sobre las mismas 7 columnas, cada una renormalizada, z-score, k = 2 y 3. Misma semilla que el evaluador. Medianas de `TyreLife` y `LapNumber` de los clusters, ordenados por mediana de vuelta.

### k = 2

| conjunto | n | silueta | nulo | gap | PS | ARI boot | AMI piloto | AMI comp. | split | TyreLife | LapNumber |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| session | 842 | 0.256 | 0.108 | 0.149 | 0.895 | 0.937 | 0.126 | −0.001 | 0.333 | 13 / 18.5 | 15 / 33.5 |
| lapsync | 842 | 0.219 | 0.102 | 0.117 | 0.826 | 0.914 | 0.164 | 0.024 | 0.222 | 16 / 15 | 25 / 26 |
| lapsync_zone | 842 | 0.225 | 0.104 | 0.120 | 0.770 | 0.913 | 0.173 | 0.030 | 0.222 | 17 / 15 | 25.5 / 26 |
| reg_lap_fe | 842 | 0.229 | 0.105 | 0.125 | 0.683 | 0.878 | 0.187 | 0.020 | 0.222 | 15 / 16 | 24 / 26 |
| reg_lin_fe | 842 | 0.214 | 0.104 | 0.111 | 0.729 | 0.875 | 0.176 | 0.003 | 0.444 | 15 / 16 | 23 / 26.5 |
| reg_lin_fe_gap | 842 | 0.214 | 0.107 | 0.108 | 0.786 | 0.857 | 0.185 | 0.002 | 0.444 | 15 / 16 | 24 / 26 |
| lapsync_tyre_fe | 842 | 0.212 | 0.104 | 0.109 | 0.815 | 0.889 | 0.174 | 0.003 | 0.444 | 15 / 16 | 24 / 27 |
| detrend | 842 | 0.230 | 0.104 | 0.126 | 0.744 | 0.874 | 0.203 | 0.015 | 0.333 | 15 / 16 | 25 / 26 |
| session_xgap50 | 616 | 0.263 | 0.112 | 0.151 | 0.805 | 0.892 | 0.145 | 0.013 | 0.444 | 15.5 / 19 | 19 / 35 |
| teammate | 698 | 0.177 | 0.101 | 0.076 | 0.705 | 0.828 | 0.141 | 0.004 | 1.000 | 15 / 15 | 24.5 / 25 |
| z_driver | 842 | 0.199 | 0.105 | 0.094 | 0.844 | 0.914 | −0.003 | 0.057 | 0.111 | 12 / 21 | 13 / 36 |

### k = 3

| conjunto | silueta | PS | ARI boot | AMI piloto | AMI comp. | split | span TyreLife | span LapNumber |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| session | 0.204 | 0.688 | 0.838 | 0.198 | 0.009 | 0.556 | 4 | 23 (15 / 22 / 38) |
| lapsync | 0.190 | 0.744 | 0.917 | 0.258 | 0.048 | 0.222 | 2 | 1 (25 / 25 / 26) |
| lapsync_zone | 0.192 | 0.645 | 0.908 | 0.254 | 0.049 | 0.333 | 2 | 1 |
| reg_lin_fe | 0.201 | 0.760 | 0.873 | 0.279 | 0.031 | 0.333 | 2 | 3.5 |
| reg_lin_fe_gap | 0.205 | 0.763 | 0.886 | 0.290 | 0.029 | 0.333 | 1 | 4 |
| detrend | 0.199 | 0.764 | 0.914 | 0.282 | 0.037 | 0.222 | 3 | 1 |
| z_driver | 0.142 | 0.476 | 0.597 | −0.005 | 0.036 | 0.556 | 10 | 24.5 |
| teammate | 0.147 | 0.537 | 0.406 | 0.189 | 0.004 | 1.000 | 3 | 1 |

La silueta baja de 0.256 a ~0.22 porque el eje fácil era el stint, no porque la estructura desaparezca: el gap contra el nulo sigue en torno a 0.11 y la PS de `lapsync` en k=2 sigue por encima de 0.8. El AMI con el piloto sube (k=2: 0.126 → 0.164; k=3: 0.198 → 0.258). El split de compañeros baja (k=3: 0.556 → 0.222): en la matriz actual los compañeros caían en clases distintas porque no iban en la misma fase de stint dentro de la muestra, no porque el clustering viera dos estilos.

Anexo del evaluador oficial (`candidates_gain.csv`): las 7 columnas actuales más las 7 síncronas, en vez de reemplazarlas. k=2: silueta 0.256 → 0.223, PS 0.895 → 0.721. Meter la versión renormalizada al lado de la original diluye la partición. Hay que sustituir.

## 7. Qué no funciona

**Mediana de sesión.** No es un control de confundidores. Es un cambio de origen. `raw` y `session` dan los mismos \(\omega^2\) y los mismos \(\rho\). El K-means resultante separa vuelta 15 de vuelta 33.

**Z-score dentro del piloto.** Hace lo que se esperaba, y peor: \(\omega^2\) de piloto ≈ 0, AMI con el piloto ≈ 0, y la correlación con la vuelta **no se mueve** (el z-score es monótono dentro del piloto, así que Spearman con \(L\) se conserva). Los clusters siguen en TyreLife 12 vs 21 y vuelta 13 vs 36. Spearman-Brown explota (medias de piloto ≈ 0, correlación de medias inestable, del orden de −10³): el número no se interpreta, el fallo sí.

**Excluir vueltas con tráfico, sin más.** A 30 m se caen el 8.6 % de las vueltas y el \(\rho\) con la vuelta sigue en 0.34. A 50 m se caen 226 vueltas y el reloj sigue (span de vuelta 19 vs 35, \(|\rho|\) base 0.31). A 100 m se cae la mitad de la carrera, Spearman-Brown de los frenos baja a 0.57, y el compuesto del apex sigue por encima de 0.35. El tráfico no es el eje que ordena estas columnas; el combustible sí.

**Regresión pooled como sustituto del FE.** En esta parrilla casi todos hacen las mismas vueltas, así que la diferencia es pequeña, pero va en la dirección mala: \(\omega^2\) de piloto 0.125 frente a 0.129 del FE, y el compuesto del apex medio queda en 0.214 (pooled) frente a 0.115 (FE). El pooled se come parte del nivel de piloto que está alineado con la estrategia de parada.

**Spline e interacción.** No mejoran el lineal dentro del piloto. El spline tiene número de condición ~1660. No compensa.

**FE + tirar las vueltas con hueco < 50 m.** Cobertura 0.80, \(|\rho|\) de la base sube otra vez a 0.13 y la PS cae a 0.69. Seleccionar vueltas después de residualizar no ayuda.

**Relativo al compañero, como matriz de clustering.** La pregunta pasa a ser «cómo difiere este piloto de su compañero en esta vuelta». \(\omega^2\) alto (0.37) porque el denominador ya no tiene varianza de equipo (`share_team` = 0) y \(\rho\) con la vuelta es 0 (el compañero comparte el shock de esa vuelta). El acuerdo de signo entre mitades es 0.89: el contraste es estable. Pero el clustering es débil (gap 0.076, PS 0.71, y en k=3 el ARI bootstrap cae a 0.41). El split = 1 es tautológico: los dos compañeros tienen residuos de signo opuesto. Cobertura 0.83 (698/842): faltan las vueltas sin pareja y todo Kick Sauber. No sustituye a la normalización del pipeline. Sirve como análisis aparte de estilo relativo al coche.

**Detrend por piloto: no fracasa en los números, y aun así no es el control que hay que dejar puesto.** Conserva la media del piloto, así que \(\omega^2\) sube a 0.142 y el compuesto medio de la base cae a 0.009, el mejor de la tabla. La fuga de stint desaparece (TyreLife 15 vs 16). El problema es de definición: \(\hat b_d\) es la pendiente de ese piloto, y en una estrategia de stint parte de esa pendiente es decisión (cuidar goma, empujar al final), no solo combustible. En Monza las pendientes son parecidas entre pilotos, por eso el resultado se parece a la síncrona. En una temporada con estrategias distintas se comería estilos que la mediana del campo habría dejado fuera. La PS (0.74) también queda por debajo de la síncrona (0.83).

## 8. Recomendación

Orden para el pipeline, con lo que esta carrera sostiene:

1. **`lapsync` — mediana del campo en el mismo `LapNumber`, sobre el agregado por tipología.** Es el cambio que hay que hacer. En las 7 columnas, \(\omega^2\) de piloto 0.108 → 0.135; en el apex, 0.096/0.085 → 0.168/0.159; \(|\rho|\) con la vuelta 0.34 → 0.08; compuesto medio de la base 0.172 → 0.048. k=2: silueta 0.219 frente a nulo 0.102, PS 0.83, ARI bootstrap 0.91, AMI piloto 0.16, TyreLife 16 vs 15, vuelta 25 vs 26 (antes 13 vs 18.5 y 15 vs 33.5). k=3: AMI piloto 0.26, span de vuelta 1, PS 0.74. Se implementa sobre la matriz ya agregada, sin reabrir la telemetría. No estima una pendiente por piloto, así que no se come la gestión de stint de cada uno.

2. **`lapsync_zone`, si el pipeline todavía tiene la fila por zona.** Misma idea, referencia por curva. Sube un poco la media de \(\omega^2\) (0.141) y es claramente mejor en apex medio (0.182, compuesto 0.083) y en frenada media (0.148). La PS de k=2 baja a 0.77. Si solo se dispone de la matriz ancha, quedarse en (1).

3. **No añadir vida ni compuesto a la especificación por defecto.** `reg_lin_fe` es la versión «limpia» sobre el papel (pendientes dentro del piloto, se resta solo \(X\beta\)). En esta carrera no gana: el \(R^2\) extra sobre la vuelta sola es ~0.03, \(\beta_{\mathrm{MEDIUM}} \approx 0\) en el apex medio, el compuesto de ese apex sigue en 0.12, y la PS cae a 0.73. `lapsync_tyre_fe` sí deja \(|\rho|\) en 0.025 y el AMI de compuesto en 0.003, con \(\omega^2\) casi igual (0.132) y PS 0.81. Es un segundo paso razonable **si** se acepta que la asociación con la vida del neumático no es estilo. En Monza, ir soltando el acelerador según se degrada la goma puede serlo. Por eso no lo pondría en el camino por defecto.

4. **Hueco al coche de delante, solo como control extra del apex, y solo si la telemetría de posición está en el pipeline.** `reg_lin_fe_gap` es el máximo de señal en los dos apex (0.219 y 0.201) y el \(R^2\) intra-piloto del apex medio sube de 0.67 a 0.79. El compuesto del apex medio empeora (0.150). No usarlo como normalización única de las 10 columnas. Excluir vueltas por umbral, sin residualizar, no arregla el combustible.

5. **No usar** mediana de sesión como si controlara el stint, ni z-score por piloto, ni el contraste con el compañero como matriz del mismo clustering, ni spline. El relativo al compañero queda como análisis separado (señal estable, otra pregunta, clustering débil).

La mediana de sesión puede quedarse como presentación («por encima o por debajo del fin de semana»). No es el input del K-means.

## 9. Límites

- Una carrera, un circuito con rebufo grande y una sola parada. La colinealidad vuelta–compuesto–vida es la de este fin de semana. En una temporada con dos paradas o estrategias cruzadas, el FE puede separarse de la síncrona; aquí no se separa.
- La síncrona no quita el coche (la varianza entre equipos sigue siendo ~0.32) ni el compuesto del apex medio (0.12). Los clusters resultantes siguen siendo perfiles de telemetría, no estilos causales.
- El cero del export no es la mediana de las 842 vueltas en todas las columnas (apex rápido: 29 km/h de diferencia constante). Los contrastes por vuelta sí coinciden. Conviene recomputar la mediana de sesión sobre las mismas filas que entran en la matriz, aunque para el K-means el cero no importe.
- El nulo de silueta usa 5 permutaciones; canta en la milésima.
- `recommended` castiga la correlación con la columna actual. En esta familia hay que leer \(\omega^2\), compuesto, \(\rho\) y la fuga de stint, no ese flag.
- Queda compuesto residual en el apex medio por debajo de cualquier control lineal de esta lista. Hace falta otro diseño (más carreras, o una referencia de compuesto que no esté colineal con la vuelta) para bajarlo de 0.05.

## 10. Archivos

Todo en `experiments/telemetry_candidates/normalization/`:

| archivo | contenido |
| --- | --- |
| `run.py` | extracción, normalizaciones, scores, clustering de reemplazo, llamada al evaluador |
| `raw_zones.csv` | métricas crudas por zona + hueco en frenada y en la recta previa |
| `candidates.csv` | 842 vueltas × 220 columnas `<tipología>__<métrica>__<normalización>` |
| `candidates_scores.csv` | salida de `score_features` (evaluador oficial) |
| `candidates_gain.csv` | base 7 vs base 7 + 7 columnas lapsync (anexo, no reemplazo) |
| `per_feature_key_metrics.csv` | \(\omega^2\), \(\rho\), fiabilidad de las 10 métricas × normalización |
| `strategy_summary.csv` | medias de la base 7 y de los frenos, más métricas de clustering |
| `replacement_clustering.csv` | silueta, nulo, gap, PS, ARI, AMI, split, k=2 y 3 |
| `cluster_leakage.csv` | mediana de TyreLife, LapNumber y mezcla de compuesto por cluster |
| `regression_diagnostics.csv` | \(R^2\), condición y coeficientes |
| `traffic_summary.csv` | fracciones de vueltas/zonas bajo cada umbral |
| `reconstruction_check.csv` | Pearson y desplazamiento constante frente al export |
