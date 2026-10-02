# Monza 2025 (carrera) con throttle onset apagado

Corrida: `python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R`.

El CLI terminó con error. No eligió k y no escribió perfiles. No hay clase modal ni fracción por piloto.

## Flag y columnas

`features.include_throttle_onset` está en false. `get_throttle_onset_relative` sigue en el código y no se llama.

La matriz de vueltas tiene 842 filas y 19 pilotos. `feature_cols` son las seis métricas de siempre, sin `throttle_onset_rel`:

- brake_point_rel
- trail_brake_frac
- apex_speed_rel
- throttle_attack
- coast_frac
- full_throttle_frac

Esas seis se parten en slow / medium / fast. Quedan **18 columnas de estilo**. Ninguna se llama `throttle_onset`. El frame completo tiene 25 columnas (las 18 más Driver, LapNumber, Team, FullName, Compound, TyreLife, unit). Tras quitar metadata, el escalado usa esas 18. Como son más de 8, el ajuste entra a PCA: 3 componentes, varianza acumulada 0.9034 (0.6537, 0.1386, 0.1110). Zonas: `key_corners`, 7 grupos.

El auto 27 no entra: FastF1 marcó todas sus vueltas como inaccurate. En la matriz no está HUL.

## Por qué no hay k

El selector pide un clúster de al menos el 5% de las vueltas (`ceil(0.05 * 842) = 43`) y, si eso deja el pool vacío, reintenta con mínimo 3. Los dos intentos lanzan `InvalidKPoolError`. Davies-Bouldin no se usa: solo entra si algún k válido queda por debajo del umbral de silueta 0.25, y aquí no hay k válido.

La tabla es el mismo K-means++ que usa el selector (`n_init=20`, `random_state=42`) sobre el espacio de ajuste. El CLI no la guarda porque aborta antes. El clúster más chico tiene tamaño 1 en todos los k.

| k | tamaño mínimo | tamaños | silueta | Davies-Bouldin |
| --- | ---: | --- | ---: | ---: |
| 2 | 1 | 841, 1 | 0.9869 | 0.0076 |
| 3 | 1 | 840, 1, 1 | 0.9738 | 0.0128 |
| 4 | 1 | 838, 2, 1, 1 | 0.9607 | 0.1315 |
| 5 | 1 | 822, 16, 2, 1, 1 | 0.8352 | 0.2339 |
| 6 | 1 | 681, 141, 16, 2, 1, 1 | 0.5117 | 0.3620 |
| 7 | 1 | 598, 141, 83, 16, 2, 1, 1 | 0.6064 | 0.3447 |

La silueta alta no es una separación de estilos. `fast__throttle_attack` vale 0 en 841 vueltas y 1.5625 solo en ALB, vuelta 49. El IQR crudo es 0. Después de residualizar Team, Compound y TyreLife el IQR baja a 0.004394 y el escalado robusto lleva esa vuelta a 350.65. Su PC1 es 372.13. K-means va aislando esa vuelta y otras puntas; el selector las rechaza.
