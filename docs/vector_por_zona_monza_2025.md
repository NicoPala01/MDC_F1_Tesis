# Vector por zona y ventanas de frenado (Monza 2025)

Corrida de referencia, configuración por defecto: `python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R`.

El vector por zona y las ventanas escaladas por velocidad están apagados en `config/pipeline_config.yaml` (`vector_unit: typology`, `speed_scaled_windows: false`). Los números de este documento salen de una corrida aparte con `vector_unit: zone` y de un recorrido de la telemetría canónica. El K-means, el RobustScaler, el PCA automático y la regla de k no cambian.

## Issue #10: inicios de frenada en el borde de 350 m

Definición medida: un inicio cae en el borde si el primer sample dentro de la ventana ya tiene el freno puesto. La ventana de 350 m empieza 350 m antes del ápice y termina donde empieza la ventana de ápice. No es la ventana que usa el YAML de Monza en cada curva (Curva Grande está en 180 m, Lesmo 2 en 200 m, Rettifilo en 350 m). La otra definición, también medida, cuenta un inicio si está a 5 m o menos del arranque geométrico de la ventana.

Ventana de 350 m, todas las zonas: 5114 inicios en 6081 fragmentos. En el borde: 261 (5.10 % de los inicios). A 5 m o menos: 128 (2.50 % de los inicios).

Ventanas que realmente usa el pipeline en Monza: 5074 inicios, 13 en el borde (0.26 % de los inicios), 0 a 5 m o menos (0.00 %).

Se esperaba, antes de medir, menos del 0.2 % en el borde de 350 m. Lo medido es 5.10 %. De esos 261 inicios, 250 son de la Seconda di Lesmo (T7): 30.83 % de los 811 inicios de esa curva en la ventana de 350 m, y 121 a 5 m o menos (14.92 %). Las otras seis curvas suman 11 inicios en el borde. La expectativa no se cumple, y el incumplimiento está concentrado en Lesmo 2.

En la ventana que usa el pipeline, Lesmo 2 tiene 7 de 774 inicios en el borde (0.90 %). Sobre los fragmentos de esa curva, 774 de 869 tienen inicio y 95 no (10.93 % sin frenada). Esa es la fracción de fragmentos. La cobertura de `brake_point_rel` de más abajo (0.783) usa otro denominador: las vueltas que aparecen en alguna zona de la tabla larga, no solo los fragmentos de T7. Curva Grande, en la ventana del pipeline, tiene 0 inicios en 869 fragmentos. En la de 350 m tiene 2, y 1 de esos 2 cae en el borde.

| ventana | zona | fragmentos | inicios | en el borde | fracción borde | fracción a ≤5 m | velocidad de entrada |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pipeline | T1_Variante_del_Rettifilo | 869 | 867 | 0 | 0.0000 | 0.0000 | 336.0 |
| pipeline | T3_Curva_Grande | 869 | 0 | 0 |  |  | 275.0 |
| pipeline | T4_Variante_della_Roggia | 869 | 864 | 0 | 0.0000 | 0.0000 | 317.0 |
| pipeline | T6_Curva_di_Lesmo | 869 | 859 | 3 | 0.0035 | 0.0000 | 238.0 |
| pipeline | T7_Seconda_di_Lesmo | 869 | 774 | 7 | 0.0090 | 0.0000 | 243.0 |
| pipeline | T8_Variante_Ascari | 868 | 843 | 1 | 0.0012 | 0.0000 | 322.0 |
| pipeline | T11_Curva_Parabolica_Alboreto | 868 | 867 | 2 | 0.0023 | 0.0000 | 319.0 |
| 350m | T1_Variante_del_Rettifilo | 869 | 867 | 0 | 0.0000 | 0.0000 | 336.0 |
| 350m | T3_Curva_Grande | 869 | 2 | 1 | 0.5000 | 0.0000 | 223.0 |
| 350m | T4_Variante_della_Roggia | 869 | 864 | 0 | 0.0000 | 0.0000 | 317.0 |
| 350m | T6_Curva_di_Lesmo | 869 | 860 | 8 | 0.0093 | 0.0058 | 124.0 |
| 350m | T7_Seconda_di_Lesmo | 869 | 811 | 250 | 0.3083 | 0.1492 | 192.0 |
| 350m | T8_Variante_Ascari | 868 | 843 | 1 | 0.0012 | 0.0012 | 322.0 |
| 350m | T11_Curva_Parabolica_Alboreto | 868 | 867 | 1 | 0.0012 | 0.0012 | 320.0 |

### Riesgo fuera de Monza

No se midió otro circuito. Lo que el código hace, y el riesgo que eso deja abierto:

- Monza, Silverstone y Mónaco usan `key_corners`. El resto de la temporada cae en `_zones_from_speed_threshold_fallback`: una zona por curva de FastF1, con los 350 m / ±60 m / 250 m de `default_zoi_offsets`.
- En una frenada que empieza antes de la ventana, el primer sample ya trae el freno puesto y `brake_point_rel` mide un onset cortado. En Monza eso pasa sobre todo en Lesmo 2 con la ventana fija de 350 m (tabla de arriba). No se midió si en otros circuitos el mismo recorte aparece en frenadas largas después de una recta larga.
- En sectores trabados (Mónaco, y el fallback cuando dos curvas quedan cerca) las ventanas se solapan y `clip_and_merge_zones` las recorta. Ese recorte no está contado en esta corrida.
- La intensidad de frenado no entra al vector. `get_max_deceleration` existe y no se usa.

### Ventanas escaladas por velocidad (apagadas)

La opción `speed_scaled_windows` multiplica los metros pre-ápice de cada zona por `(velocidad de entrada / 300 km/h)^2`, con piso 80 m y techo 700 m. La velocidad de entrada es la mediana de la velocidad del primer sample de la ventana que el pipeline usa hoy. Esta tabla es esa cuenta. No se volvió a clusterizar con las ventanas escaladas. En Lesmo 2 la fórmula acorta la ventana del pipeline de 137.8 m a 90.4 m, porque la velocidad de entrada de esa ventana es 243 km/h, por debajo de la referencia de 300 km/h. No alarga la ventana de 350 m donde se midió el recorte.

| zona | metros actuales | velocidad de entrada | metros escalados |
| --- | --- | --- | --- |
| T1_Variante_del_Rettifilo | 350.0 | 336.0 | 439.0 |
| T3_Curva_Grande | 180.0 | 275.0 | 151.2 |
| T4_Variante_della_Roggia | 300.0 | 317.0 | 335.0 |
| T6_Curva_di_Lesmo | 162.3 | 238.0 | 102.1 |
| T7_Seconda_di_Lesmo | 137.8 | 243.0 | 90.4 |
| T8_Variante_Ascari | 280.0 | 322.0 | 322.6 |
| T11_Curva_Parabolica_Alboreto | 320.0 | 319.0 | 361.8 |

## Vector por zona

Hoy el bloque `medium` junta Lesmo 1, Lesmo 2, la Parabólica y la Roggia. Con `vector_unit: zone` hay un bloque por curva. La mediana de sesión se resta dentro de la zona, no de la tipología. Después siguen la mediana del campo en la misma vuelta, el ajuste de compuesto y vida, el RobustScaler, el PCA automático y el K-means.

Regla declarada, no medida: una columna de frenada (`brake_point_rel`, `trail_brake_frac`) entra solo si al menos el 95 % de las vueltas tiene valor. Por debajo de eso no se inventa una distancia. Si frenó entre el 2 % y ese piso, la columna `{zona}__braked` vale 1 o 0. Si no frena casi nadie, no se agrega ni esa columna: sería otra columna de IQR 0.

Vueltas que sobrevivirían a `dropna(how='any')` con todas las columnas de frenada: 0. Vueltas que quedan con la regla de arriba: 868. Vueltas que entran al K-means después del filtro de pilotos: 868. Columnas: 34. Pilotos: 19. k elegido: 2 (regla `silhouette`). PCA: 5 componentes, varianza 0.8722.

Cobertura de `brake_point_rel` por zona (fracción de filas del vector ancho con valor finito, antes de omitir columnas). El denominador son las vueltas presentes en alguna zona, no los fragmentos de esa curva:

| zona | cobertura |
| --- | --- |
| T1_Variante_del_Rettifilo | 0.878 |
| T3_Curva_Grande | 0.000 |
| T4_Variante_della_Roggia | 0.874 |
| T6_Curva_di_Lesmo | 0.869 |
| T7_Seconda_di_Lesmo | 0.783 |
| T8_Variante_Ascari | 0.853 |
| T11_Curva_Parabolica_Alboreto | 0.878 |

Columnas de frenada omitidas: `T1_Variante_del_Rettifilo__brake_point_rel`, `T3_Curva_Grande__brake_point_rel`, `T4_Variante_della_Roggia__brake_point_rel`, `T6_Curva_di_Lesmo__brake_point_rel`, `T7_Seconda_di_Lesmo__brake_point_rel`, `T8_Variante_Ascari__brake_point_rel`, `T11_Curva_Parabolica_Alboreto__brake_point_rel`, `T1_Variante_del_Rettifilo__trail_brake_frac`, `T3_Curva_Grande__trail_brake_frac`, `T4_Variante_della_Roggia__trail_brake_frac`, `T6_Curva_di_Lesmo__trail_brake_frac`, `T7_Seconda_di_Lesmo__trail_brake_frac`, `T8_Variante_Ascari__trail_brake_frac`, `T11_Curva_Parabolica_Alboreto__trail_brake_frac`.
Columnas `braked`: `T1_Variante_del_Rettifilo__braked`, `T4_Variante_della_Roggia__braked`, `T6_Curva_di_Lesmo__braked`, `T7_Seconda_di_Lesmo__braked`, `T8_Variante_Ascari__braked`, `T11_Curva_Parabolica_Alboreto__braked`.

## Separación del vector por zona

El mismo nulo que en `docs/separacion_nulo_monza_2025.md`: columnas permutadas una por una, escalador y PCA reajustados, 200 permutaciones, k de 2 a 7. Criterio de lectura declarado: la real se separa si el percentil es mayor que 95.

| k | silueta | nulo media | nulo p50 | nulo p95 | percentil | separa del nulo | permutaciones | PCs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 0.7145 | 0.7320 | 0.7316 | 0.7372 | 0.0 | no | 200 | 5 |
| 3 | 0.6417 | 0.7178 | 0.7402 | 0.7447 | 0.0 | no | 200 | 5 |
| 4 | 0.6550 | 0.6818 | 0.6827 | 0.6893 | 0.0 | no | 200 | 5 |
| 5 | 0.6424 | 0.6891 | 0.6908 | 0.6967 | 0.0 | no | 200 | 5 |
| 6 | 0.3149 | 0.6893 | 0.6919 | 0.6981 | 0.0 | no | 200 | 5 |
| 7 | 0.3343 | 0.6330 | 0.6326 | 0.6556 | 0.0 | no | 200 | 5 |

En los seis k la silueta real queda por debajo de las 200 réplicas (percentil 0). En el k que elige la regla (k=2, silueta 0.7145) la media del nulo es 0.7320 y el percentil 5 del nulo es 0.7282. La silueta absoluta es alta y no dice que las columnas se armen juntas: el nulo, que rompe la dependencia entre columnas, da siluetas más altas. Esta variante no se separa del nulo. El vector por tipología, en `docs/separacion_nulo_monza_2025.md`, sí queda por encima de las 200 réplicas; el resultado de esta sección es el de la matriz por zona.

Opciones, sin cambiar el algoritmo por defecto y sin implementar la tercera:

1. **Partición descriptiva.** Conservar las clases como resumen de la sesión.
2. **Perfil continuo por piloto.** Usar los scores de las PC del espacio de ajuste en lugar de una clase.
3. **Asignación blanda.** Probabilidad de clase por vuelta. No está implementada.

