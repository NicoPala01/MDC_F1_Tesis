# Monza 2025 (carrera): onset apagado, sin throttle attack en fast

Corrida: `python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R`.

`include_throttle_onset` sigue en false. `fast__throttle_attack` salió de la matriz de vueltas. Siguen `slow__throttle_attack`, `medium__throttle_attack`, `brake_point_rel` y `trail_brake_frac` en las tres tipologías.

El CLI volvió a terminar con `InvalidKPoolError`. No hay k elegido ni clase modal ni fracción por piloto.

## Matriz de esta corrida

842 vueltas, 19 pilotos (el auto 27 no entra: FastF1 marcó todas sus vueltas como inaccurate; HUL no está). **17 columnas de estilo.** No hay `throttle_onset` ni `fast__throttle_attack`. Sí están `fast__brake_point_rel` y `fast__trail_brake_frac`.

El escalado usa esas 17. PCA: 3 componentes, varianza acumulada 0.9094 (0.4644, 0.3156, 0.1294).

## Por qué el selector rechaza todos los k

Pide un clúster de al menos `ceil(0.05 * 842) = 43` vueltas y, si el pool queda vacío, reintenta con mínimo 3. Los dos intentos fallan. Davies-Bouldin no elige k: solo se usa si algún k válido tiene silueta bajo 0.25.

La tabla es el mismo K-means++ del selector (`n_init=20`, `random_state=42`) sobre el espacio de ajuste. El CLI no la escribe.

| k | tamaño mínimo | tamaños | silueta | Davies-Bouldin |
| --- | ---: | --- | ---: | ---: |
| 2 | 2 | 840, 2 | 0.9722 | 0.1526 |
| 3 | 2 | 836, 4, 2 | 0.9552 | 0.5504 |
| 4 | 2 | 817, 19, 4, 2 | 0.8604 | 0.6189 |
| 5 | 1 | 817, 19, 3, 2, 1 | 0.8614 | 0.3535 |
| 6 | 1 | 676, 141, 19, 3, 2, 1 | 0.6231 | 0.4299 |
| 7 | 1 | 676, 141, 19, 2, 2, 1, 1 | 0.6237 | 0.3046 |

En k=2, 3 y 4 el clúster chico es ALB vuelta 49 y ALO vuelta 16. En k≥5 aparece además un clúster de una sola vuelta (HAM vuelta 31).

## Columna que se dispara

`fast__full_throttle_frac`. IQR crudo 0. Es 0 en 840 vueltas. Las otras dos:

| vuelta | valor crudo | residual (Team, Compound, TyreLife) | escalado robusto |
| --- | ---: | ---: | ---: |
| ALB 49 | −0.37992026 | −0.37357873 | −128.265926 |
| ALO 16 | −0.50000000 | −0.49080328 | −168.395776 |

El IQR después de residualizar es 0.002921. Esas dos vueltas son el clúster de tamaño 2, por debajo del mínimo 3.

Las dos puntas siguientes, que no se tocaron:

- `medium__throttle_attack`: 0 en 801 de 842 vueltas, IQR crudo 0. HAM vuelta 31 vale 13.428571 en crudo y 103.438545 escalado.
- `medium__full_throttle_frac`: 0 en 838 vueltas, IQR crudo 0. PIA vuelta 34 vale −0.071666788 en crudo y −100.204659 escalado.

## Corrida anterior

Antes de sacar `fast__throttle_attack`, esa columna era 0 en 841 de 842 vueltas y 1.5625 solo en ALB vuelta 49. El escalado robusto la llevaba a 350.65 y todos los k tenían un clúster de tamaño 1. Esa hipótesis se confirma con la matriz de esa corrida. Quitarla no alcanza: el selector sigue sin pool válido.
