# Decisión metodológica 2025

Esta nota lee corridas ya escritas. No reejecuta el pipeline, no agrega un estadístico y no cambia los defaults. El K-means de `config/pipeline_config.yaml` sigue siendo el camino por defecto.

Los números salen de `docs/temporada_2025.md`, `docs/perfil_continuo_2025.md`, `docs/gmm_2025.md` y `docs/modelos_clustering_2025.md`, y de los informes de Monza del mismo ciclo: `docs/separacion_nulo_monza_2025.md`, `docs/vector_por_zona_monza_2025.md`, `docs/compuesto_monza_2025.md` y `docs/metricas_telemetria.md`. Cada cifra de abajo está en el archivo que la acompaña.

## Declarado

Esto es la regla con la que se lee lo medido. Cada bloque quedó escrito en su informe antes de ver el resultado de ese bloque.

Para afirmar estilos discretos en un GP se exigen dos cosas, y las dos vienen de reglas ya fijadas:

1. La silueta real supera el percentil 95 de los tres nulos: permutación por columna, gaussiano y cópula gaussiana. La comparación es estricta y usa el cuantil, no el redondeo del percentil. En `docs/temporada_2025.md` esa regla se aplica al K-means del pipeline, con la selección completa de k en cada réplica. Son 50 réplicas. Las semillas son 42, 43 y 44. El 50 quedó fijo antes de ver los percentiles, porque una elección de k tarda cerca de un segundo y 200 réplicas por tres nulos no terminan la temporada.
2. Hay consenso entre modelos: el GP tiene estructura en al menos la mitad de los modelos de la grilla. Un modelo que no elige cuenta como sin estructura. Está en `docs/modelos_clustering_2025.md`. La grilla también exige superar el percentil 95 de los tres nulos, con la selección completa. En HDBSCAN el estadístico es el DBCV. En el resto es la silueta. No se mezclan. Semilla 42. Permutación 42, gaussiano 43, cópula 44. 50 réplicas, fijadas porque una grilla sintética de 1275 por 16 tarda alrededor de cuatro segundos. No se bajó a 30 después de ver un percentil. El bootstrap de estabilidad de esa grilla son 20 remuestras, semilla 42, y no entra en el nulo.

El GMM por BIC es otra regla, también fijada antes de leer un BIC (`docs/gmm_2025.md`). K va de 1 a 7, `n_init` 20, semilla 42. Los nulos de ese informe son dos, el gaussiano y la cópula, 50 réplicas, semillas 43 y 44. Superar los dos es la conjunción de esas lecturas. No es el criterio de tres nulos ni el de consenso.

El perfil continuo tiene su propia regla, fijada antes de leer sus resultados (`docs/perfil_continuo_2025.md`). El número de componentes es un análisis paralelo secuencial contra 50 permutaciones de columnas, semilla 42: se conserva el componente k solo si su autovalor supera el percentil 95 y todos los anteriores también. El perfil del piloto es la mediana de sus scores, con bootstrap estratificado por compuesto de 2000 réplicas, semilla 42, percentiles 2.5 y 97.5. La congruencia entre GP es el coeficiente de Tucker de los ejes del mismo índice. Los compañeros quedan más cerca que el azar solo si la distancia media es estrictamente menor que el percentil 5 de 50 permutaciones de esas medianas, semilla 42. A ese camino no se le pidieron los tres nulos.

Las predicciones (a) y (b) se escribieron el 2026-10-14, antes de evaluarlas (`docs/temporada_2025.md`). Se confirman solo si los intervalos no se tocan y la dirección es la predicha. Si se tocan, no hay evidencia. Norris contra Piastri queda exploratorio.

## Medido

### K-means y los tres nulos

En la matriz de temporada, sin `fast__brake_point_rel`, hay estructura en 2 de 24 carreras: Bélgica e Italia (`docs/temporada_2025.md`).

Bélgica: 734 vueltas, k=7 por Davies-Bouldin, silueta 0.108, percentiles 100, 98 y 100. Italia: 867 vueltas, k=3 por Davies-Bouldin, silueta 0.140, percentiles 100, 100 y 96. Hungría no elige k: con 1275 vueltas, cada k de 2 a 7 deja una clase de 2 vueltas, y el reintento con piso 3 también las rechaza.

La concordancia de compañeros, en esas dos carreras, no supera el percentil 95 de su permutación. Bélgica: 0.30, percentil 70, 10 pares. Italia: 0.556, percentil 36, 9 pares.

Monza suelta conserva `fast__brake_point_rel`: 842 vueltas, 17 columnas, k=3 por Davies-Bouldin, silueta 0.133, percentiles 100, 100 y 86. No hay estructura. Sin las tres columnas de IQR 0 la silueta es 0.139 y los percentiles son 100, 100 y 92. Tampoco.

Una silueta alta no alcanza. Japón tiene silueta 0.859 y percentil 0 contra la permutación. En Monza, el nulo de una sola familia ya separaba la silueta del k=3 (0.1330 contra un percentil 95 de 0.0756, 200 permutaciones, percentil 100) y aun así la silueta queda por debajo de 0.25, que es el corte con el que la regla pasa a Davies-Bouldin (`docs/separacion_nulo_monza_2025.md`).

### GMM por BIC

Las 25 matrices eligen K mayor que 1 (`docs/gmm_2025.md`). La cópula también: la fracción de réplicas con K mayor que 1 es 0.940 en Miami y 1.000 en las demás. El gaussiano elige K=1 en las 50 réplicas de 24 carreras. La excepción es Las Vegas, con fracción 0.700.

La ganancia supera el percentil 95 de los dos nulos en 8 carreras: Japón, Arabia Saudita, Mónaco, España, Gran Bretaña, Estados Unidos, Las Vegas y Catar. Bélgica queda con percentil de cópula 90. Italia, 82. Monza suelta, 84. Esas tres no entran en las 8. Las 8 no son Bélgica ni Italia.

Diez matrices se sientan en el tope K=7: Australia, China, Mónaco, España, Canadá, Austria, Países Bajos, Monza suelta, Singapur y Catar. La grilla no mira por encima de 7. En Las Vegas el percentil de la cópula es 94.0 y la columna de superar el p95 es sí: el informe usa el cuantil.

### Grilla de nueve modelos

Ninguna de las 25 matrices tiene consenso. El máximo de la tabla es 3 de 9, en Baréin, Italia, Ciudad de México y Abu Dabi (`docs/modelos_clustering_2025.md`). Bélgica, Hungría y Monza suelta quedan en 0 de 9.

Superan los tres nulos, y solo estas filas:

| carrera | modelos | silueta |
| --- | --- | --- |
| Australia | k-medians | 0.171 |
| Baréin | k-medians, k-medoids, fuzzy c-means | 0.134, 0.168, 0.150 |
| Mónaco | fuzzy c-means | 0.152 |
| España | espectral | 0.166 |
| Austria | Ward, espectral | 0.291, 0.291 |
| Italia | K-means, k-medians, fuzzy c-means | 0.123, 0.112, 0.118 |
| Ciudad de México | k-medians, k-medoids, espectral | 0.313, 0.345, 0.302 |
| Abu Dabi | K-means, k-medoids, GMM | 0.711, 0.557, 0.588 |

En Italia el K-means de la grilla tiene percentil de cópula 94.0 y supera el p95. La regla declarada usa el cuantil. En Ciudad de México el ARI contra el K-means de la grilla es −0.005, 0.024 y −0.005. El GMM de Abu Dabi que entra en la tabla es `diag`. Este GMM no es el del apartado anterior: aquí K empieza en 2 y `n_init` es 2.

El K-means de la grilla en Bélgica elige K=2, silueta 0.097, y no supera los tres. El de Italia elige K=2, silueta 0.123. La matriz de la grilla es la escalada, sin el PCA del clustering.

### Patologías

En Baréin, Mónaco e Italia, el fuzzy c-means que supera los tres nulos tiene fracción 1.000 de vueltas con membresía máxima estrictamente menor que 0.8 (`docs/modelos_clustering_2025.md`). La silueta que entra al nulo es la de las etiquetas duras.

HDBSCAN devuelve dos clases en China (DBCV 0.007, fracción de ruido 0.107), Japón (DBCV 0.484, fracción 0.000) y Azerbaiyán (DBCV 0.004, fracción 0.172). En el resto de las filas de esa tabla la fracción de ruido es 1.000 y no hay DBCV. Ninguna fila de HDBSCAN supera los tres nulos.

Average tiene K, siempre 2, en Japón, España, Canadá, Austria, Bélgica, Singapur, Ciudad de México, Las Vegas y Catar. En ninguna supera los tres. En el resto de la tabla no elige.

Una clase queda marcada si una feature concentra más de la mitad de la distancia L1 y su IQR dentro de la clase es a lo sumo 1e-8. Las marcadas son columnas de `throttle_attack` que ya tienen IQR a lo sumo 1e-8 antes del escalador. La columna de parte L1 es el mínimo y el máximo de las filas de ese GP:

| carrera | feature | modelos marcados | parte L1 |
| --- | --- | --- | --- |
| Canadá | `slow__throttle_attack` | k-means, k-medians, GMM, Ward, average, espectral, fuzzy | 0.750 a 0.805 |
| Azerbaiyán | `slow__throttle_attack` | k-means, fuzzy | 0.820 y 0.799 |
| Singapur | `medium__throttle_attack` | k-means, k-medians, GMM, Ward, average, espectral, fuzzy | 0.708 a 0.901 |
| Catar | `slow__throttle_attack` | k-means, k-medians, k-medoids, GMM, Ward, average, espectral, fuzzy | 0.782 a 0.870 |

El IQR dentro de la clase es 0 en todas esas filas. HDBSCAN no aparece en ninguna.

### Perfil continuo

Las 24 carreras conservan entre 1 y 6 componentes por la regla paralela (`docs/perfil_continuo_2025.md`). Hungría conserva 1, con varianza acumulada 0.290. Japón conserva 6, con 0.935. Italia conserva 5, con 0.652, sobre 867 vueltas y 16 features. Bélgica conserva 4, con 0.525, sobre 734 vueltas.

La congruencia de Tucker, en los ejes del mismo índice y con al menos dos features en común, tiene 842 pares definidos. La mediana es 0.248. En PC1 la mediana es 0.239 (n=276, cuartiles 0.095 y 0.398). Los ejes no se trasladan de un GP a otro: el perfil que esta regla sostiene es el de cada carrera.

Los compañeros quedan más cerca que el percentil 5 del nulo en 16 de 24 carreras: Australia, Japón, Baréin, Arabia Saudita, Mónaco, España, Canadá, Austria, Gran Bretaña, Bélgica, Italia, Singapur, Estados Unidos, São Paulo, Catar y Abu Dabi. No lo están en China, Miami, Emilia-Romaña, Hungría, Países Bajos, Azerbaiyán, Ciudad de México y Las Vegas.

En Bélgica la distancia media es 1.582 y el percentil 5 del nulo es 1.651 (percentil de la distancia 2.0, 10 pares). En Italia, 1.528 y 1.690 (percentil 2.0, 9 pares). Esa lectura de compañeros es la del perfil continuo. La concordancia de clases del K-means, citada arriba, es otra cuenta y en esas dos carreras no supera su percentil 95.

### Predicciones a priori

En la carrera suelta de Monza, 173 vueltas de Hamilton, Leclerc, Norris y Piastri quedan en aire limpio y 16 no. Ninguna se fue por falta de onset (`docs/perfil_continuo_2025.md`; el mismo veredicto está en `docs/temporada_2025.md`).

(a) No hay evidencia. En MEDIUM, Hamilton tiene n=30, mediana −0.777, intervalo [−6.278, 3.816], y Leclerc n=27, mediana −10.418, intervalo [−19.911, −5.661]. En HARD, Hamilton tiene n=11, mediana 1.251, intervalo [−9.150, 7.691], y Leclerc n=17, mediana −10.600, intervalo [−20.047, −4.827]. Los intervalos se tocan en los dos compuestos. No comparten SOFT.

(b) No hay evidencia. Leclerc, n=44, mediana 79.178, intervalo [74.829, 81.550]. Hamilton, n=45, mediana 79.928, intervalo [77.158, 82.380]. Los intervalos se tocan.

Norris contra Piastri es exploratorio y no lee el baseline. En el punto de frenada los intervalos no se tocan y Norris queda por debajo: MEDIUM, Norris n=43, mediana −12.028, intervalo [−16.058, −2.952], contra Piastri n=36, mediana 1.054, intervalo [−1.499, 4.093]; SOFT, Norris n=4, mediana −17.312, intervalo [−19.988, −3.441], contra Piastri n=5, mediana 9.649, intervalo [3.016, 23.483]. En la suelta se tocan: Norris n=48, mediana 81.996, intervalo [78.064, 85.513]; Piastri n=48, mediana 85.190, intervalo [83.513, 88.754].

### Tabla por carrera y modelo

«K-means, 3 nulos» es la columna de estructura de `docs/temporada_2025.md`. «GMM, 2 nulos» es superar el percentil 95 del gaussiano y de la cópula en `docs/gmm_2025.md`. Las nueve columnas siguientes son «supera los tres nulos» en `docs/modelos_clustering_2025.md`. El consenso es el de esa grilla: al menos la mitad de 9. Monza suelta no está en la tabla de 24 carreras del K-means; su «no» sale del apartado de la carrera suelta.

| carrera | K-means, 3 nulos | GMM, 2 nulos | k-means | k-medians | k-medoids | gmm | ward | average | espectral | hdbscan | fuzzy | de 9 | consenso |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- |
| Australia | no | no | no | sí | no | no | no | no | no | no | no | 1 | no |
| China | no | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Japón | no | sí | no | no | no | no | no | no | no | no | no | 0 | no |
| Baréin | no | no | no | sí | sí | no | no | no | no | no | sí | 3 | no |
| Arabia Saudita | no | sí | no | no | no | no | no | no | no | no | no | 0 | no |
| Miami | no | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Emilia-Romaña | no | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Mónaco | no | sí | no | no | no | no | no | no | no | no | sí | 1 | no |
| España | no | sí | no | no | no | no | no | no | sí | no | no | 1 | no |
| Canadá | no | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Austria | no | no | no | no | no | no | sí | no | sí | no | no | 2 | no |
| Gran Bretaña | no | sí | no | no | no | no | no | no | no | no | no | 0 | no |
| Bélgica | sí | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Hungría | no | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Países Bajos | no | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Italia | sí | no | sí | sí | no | no | no | no | no | no | sí | 3 | no |
| Monza suelta | no | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Azerbaiyán | no | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Singapur | no | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Estados Unidos | no | sí | no | no | no | no | no | no | no | no | no | 0 | no |
| Ciudad de México | no | no | no | sí | sí | no | no | no | sí | no | no | 3 | no |
| São Paulo | no | no | no | no | no | no | no | no | no | no | no | 0 | no |
| Las Vegas | no | sí | no | no | no | no | no | no | no | no | no | 0 | no |
| Catar | no | sí | no | no | no | no | no | no | no | no | no | 0 | no |
| Abu Dabi | no | no | sí | no | sí | sí | no | no | no | no | no | 3 | no |

Hungría en la primera columna es «no» porque el K-means del pipeline no elige k. Las dos carreras con estructura en esa columna, Bélgica e Italia, no están entre las ocho del GMM. Ninguna fila llega a la mitad de la grilla.

## Propuesta, pendiente de aprobación de Nicolás

La lectura principal de la tesis es el perfil continuo dentro de cada GP: los componentes que conserva la regla paralela, las cargas, la mediana de scores del piloto y la distancia de compañeros. La ausencia de estilos discretos que superen a la vez los tres nulos y el consenso entre modelos se reporta como resultado. El K-means del pipeline queda como análisis de sensibilidad, con el triple nulo al lado.

Esta propuesta no cambia defaults, no mueve el rango de k, no saca columnas y no reemplaza el camino de `scripts/run_pipeline.py`. Queda pendiente de aprobación de Nicolás.

## Limitaciones y amenazas a la validez

Réplicas. Los tres nulos y los dos del GMM usan 50. Cuando una réplica no deja un estadístico finito, la tabla publica un n menor: en la grilla, la permutación de average en Australia tiene n=12 (`docs/modelos_clustering_2025.md`). El bootstrap de estabilidad de la grilla es de 20 remuestras. El de compañeros del perfil continuo es de 50 permutaciones. El nulo de Monza de una sola familia usó 200 permutaciones de columnas, sin gaussiano ni cópula (`docs/separacion_nulo_monza_2025.md`).

Tope de K. El K-means del pipeline busca de 2 a 7. El GMM por BIC busca de 1 a 7 y diez matrices eligen 7. La grilla busca de 2 a 10. En las filas que superan los tres nulos el K es 2, salvo k-medians en Italia, que es 3. No se corrió un tope más alto.

Columnas apiladas. Sacar las de IQR 0 mueve quién pasa el triple nulo (`docs/temporada_2025.md`). Bélgica sigue con estructura. Italia deja de tenerla: la cópula baja a percentil 94, el percentil 95 de ese nulo sube a 0.479 y la silueta queda en 0.147. Abu Dabi, Canadá y Catar pasan solo en esa sensibilidad. En la grilla, las clases marcadas de Canadá, Azerbaiyán, Singapur y Catar son una columna de `throttle_attack` con IQR 0 dentro de la clase.

Ventanas fijas. El issue #10 se midió solo en Monza (`docs/vector_por_zona_monza_2025.md`, citado en `docs/temporada_2025.md`). En la ventana de 350 m, 261 de 5114 inicios caen en el borde (5.10 %), y 250 de esos 261 son de Lesmo 2. En las ventanas que el pipeline usa en Monza, 13 de 5074 (0.26 %). La expectativa escrita antes de medir era menos del 0.2 % en el borde de 350 m. Solo Italia, Gran Bretaña y Mónaco usan `key_corners`. El resto usa el fallback de 350 m / ±60 m / 250 m. Esa cuenta no se repitió en las otras carreras.

Tráfico y compuesto. La dispersión de tiempos del sector 2 correlaciona 0.52 con la posición final (`docs/metricas_telemetria.md`). En ese estudio, excluir tráfico no mueve el eje de combustible: las clases siguen en la vuelta 19 contra la 35, y el tráfico explica el 16 % de la velocidad de entrada a la T1. El corte de aire limpio de 50 m se usó en las predicciones de Monza, no como residual de la matriz de temporada. El compuesto y la vida del neumático se estiman dentro de cada piloto y se restan (README, configuración por defecto). En las clases de Monza, la clase 2 tiene 153 de 227 vueltas en HARD, fracción 0.674 (`docs/compuesto_monza_2025.md`). En el estudio de métricas, después de ese ajuste la AMI con el compuesto queda en 0.037 (`docs/metricas_telemetria.md`). Son dos corridas distintas.

Perfil de temporada. La tendencia modal del K-means, con piso de 8 carreras, es «No dominant trait» para los 20 pilotos que llegan (`docs/temporada_2025.md`). El Tucker mediano de 0.248 no define un eje común. La regla declarada del perfil continuo empareja ejes del mismo índice y no declara una segunda alineación.

## Próximos pasos

1. Nicolás aprueba o rechaza la propuesta de arriba. Hasta esa aprobación los defaults quedan como están.
2. Si se aprueba, el resultado principal se escribe por GP con el perfil continuo, y la ausencia de estilos discretos robustos se escribe con la tabla de esta nota.
3. Bélgica e Italia se mantienen en el análisis de sensibilidad del K-means. Su concordancia de compañeros no supera el percentil 95, y en la grilla quedan en 0 de 9 y 3 de 9.
4. No se reabren el tope de K, el `min_cluster_size` de HDBSCAN, el corte 0.8 ni el número de réplicas a la luz de estos percentiles.
5. Queda sin medir, y esta nota no lo mide: el borde de la ventana de frenada fuera de Monza; un residual de tráfico en la matriz de temporada; una regla de alineación, que habría que fijar antes de calcularla, para un perfil de temporada.
