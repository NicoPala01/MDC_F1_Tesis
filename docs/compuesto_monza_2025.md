# Compuesto por clase y contrastes dentro de compuesto (Monza 2025)

Corrida de referencia, ya escrita en `results/2025/italian_grand_prix/`: `python scripts/run_pipeline.py --year 2025 --circuit "Italian Grand Prix" --session R`.

Este documento solo lee esa matriz y esas clases. No cambia K-means, RobustScaler, PCA automático, la regla de k ni las columnas del vector por defecto. El reajuste dentro de un compuesto es una sensibilidad: mismas piezas, otras filas. No se movió ningún parámetro para acercar un contraste a un baseline.

Vueltas emparejadas por piloto y número de vuelta: 842. Solo en la matriz: 0. Solo en las clases: 0.

## Fracción de compuesto por clase

La fracción de la clase es vueltas de ese compuesto sobre las vueltas de la clase. La fracción del compuesto es vueltas de esa clase sobre las vueltas de ese compuesto.

| clase | nombre | compuesto | vueltas | vueltas de la clase | vueltas del compuesto | fracción de la clase | fracción del compuesto |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Late braking + high apex speed | HARD | 131 | 349 | 439 | 0.375 | 0.298 |
| 0 | Late braking + high apex speed | MEDIUM | 207 | 349 | 381 | 0.593 | 0.543 |
| 0 | Late braking + high apex speed | SOFT | 11 | 349 | 22 | 0.032 | 0.500 |
| 1 | Sharper throttle pickup + less full throttle on exit | HARD | 155 | 266 | 439 | 0.583 | 0.353 |
| 1 | Sharper throttle pickup + less full throttle on exit | MEDIUM | 107 | 266 | 381 | 0.402 | 0.281 |
| 1 | Sharper throttle pickup + less full throttle on exit | SOFT | 4 | 266 | 22 | 0.015 | 0.182 |
| 2 | Low apex speed + more coasting | HARD | 153 | 227 | 439 | 0.674 | 0.349 |
| 2 | Low apex speed + more coasting | MEDIUM | 67 | 227 | 381 | 0.295 | 0.176 |
| 2 | Low apex speed + more coasting | SOFT | 7 | 227 | 22 | 0.031 | 0.318 |

## Sensibilidad dentro de un solo compuesto

Se vuelve a ajustar el pipeline de clustering sobre las filas de `features_raw.csv` de un solo compuesto. Esa matriz ya trae la mediana de sesión, la mediana del campo en la misma vuelta y el ajuste de compuesto y vida dentro de piloto. El piso de tamaño es `max(3, ceil(0.05 × n))` de esas vueltas, no el piso de 43 de la sesión completa. Si ningún k de 2 a 7 lo cumple, no se baja el piso a 3.

SOFT tiene 22 vueltas. No se reajustó: el pedido era MEDIUM, y HARD si el piso lo permite.

### MEDIUM

Vueltas: 381. Piso: 20.
k elegido: 2 (regla `davies_bouldin`). Silueta 0.1953, Davies-Bouldin 2.2180. PCA: 9 componentes, varianza 0.8533. Tamaños: 0=121, 1=260.

Nombres, con la misma función de medianas: 0: Sharper throttle pickup + less full throttle on exit; 1: No dominant trait.

| k | silueta | Davies-Bouldin | tamaño mínimo | entra al pool |
| --- | --- | --- | --- | --- |
| 2 | 0.1953 | 2.2180 | 121 | sí |
| 3 | 0.1917 | 1.4889 | 1 | no |
| 4 | 0.1250 | 1.6126 | 1 | no |
| 5 | 0.1151 | 1.5966 | 1 | no |
| 6 | 0.1246 | 1.5044 | 1 | no |
| 7 | 0.1222 | 1.4705 | 1 | no |

### HARD

Vueltas: 439. Piso: 22.
k elegido: 3 (regla `davies_bouldin`). Silueta 0.1594, Davies-Bouldin 1.8194. PCA: 9 componentes, varianza 0.8649. Tamaños: 0=143, 1=129, 2=167.

Nombres, con la misma función de medianas: 0: Low apex speed + more coasting; 1: Sharper throttle pickup + less full throttle on exit; 2: Late braking + high apex speed.

| k | silueta | Davies-Bouldin | tamaño mínimo | entra al pool |
| --- | --- | --- | --- | --- |
| 2 | 0.1777 | 1.9732 | 167 | sí |
| 3 | 0.1594 | 1.8194 | 129 | sí |
| 4 | 0.1598 | 1.3994 | 1 | no |
| 5 | 0.1450 | 1.6003 | 1 | no |
| 6 | 0.1265 | 1.6688 | 1 | no |
| 7 | 0.1344 | 1.5961 | 1 | no |

## Contrastes en `slow__brake_point_rel` dentro de compuesto

La columna es la que entró al escalado: ya restada de la mediana de sesión, de la mediana del campo en la misma vuelta, y de la parte de compuesto y vida estimada dentro de cada piloto. Más chico es frenar más tarde que el campo en esa vuelta, en metros. La diferencia es la mediana del primer piloto menos la mediana del segundo, dentro de un compuesto. No se juntan compuestos. Cada lado se remuestrea con reposición, a su propio tamaño, 2000 veces, semilla 42. El intervalo es el percentil 2.5 y el 97.5 de esas diferencias. Con menos de 2 vueltas finitas de un lado, la celda queda vacía.

| compuesto | piloto A | piloto B | n A | n B | mediana A | mediana B | A − B | percentil 2.5 | percentil 97.5 | alcanza |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HARD | HAM | LEC | 13 | 17 | 3.61 | -10.60 | 14.21 | 5.68 | 26.51 | sí |
| HARD | NOR | PIA | 0 | 0 |  |  |  |  |  | no |
| MEDIUM | HAM | LEC | 35 | 29 | -1.76 | -11.49 | 9.73 | 0.08 | 21.69 | sí |
| MEDIUM | NOR | PIA | 43 | 41 | -12.03 | 0.68 | -12.71 | -17.64 | -1.67 | sí |
| SOFT | HAM | LEC | 0 | 0 |  |  |  |  |  | no |
| SOFT | NOR | PIA | 5 | 6 | -16.09 | 9.93 | -26.02 | -37.00 | -7.75 | sí |

Leer el intervalo: si el 0 cae entre los dos percentiles, esta muestra no aparta la diferencia de 0 al 95 % percentil. Eso no mueve k ni las columnas.

## Lectura

La mezcla no es pareja. En la clase 0, 59.3 % de las vueltas son MEDIUM. En la clase 2, 67.4 % son HARD. Es la misma tabla que ya está en `docs/monza_2025_throttle_onset_off.md`.

Dentro de MEDIUM el único k que pasa el piso de 20 es k=2 (silueta 0.1953, todavía bajo 0.25, así que la regla usa Davies-Bouldin). k=3 queda afuera: su clase más chica tiene 1 vuelta. El k=3 de la sesión completa no se sostiene en las 381 vueltas de MEDIUM.

Dentro de HARD entran k=2 y k=3. La silueta máxima de ese pool es la de k=2 (0.1777), bajo 0.25, y el Davies-Bouldin mínimo es el de k=3 (1.8194). Los nombres salen otra vez de las medianas; no son las mismas clases de la sesión, aunque algunas frases coincidan. «No dominant trait» es el texto de la función cuando ningún rasgo llega a 0.25 IQR.

En `slow__brake_point_rel`, un valor más chico es frenar más tarde que el campo. La diferencia es mediana(A) − mediana(B).

- HAM − LEC en HARD: 14.21 m (intervalo 5.68 a 26.51; el intervalo no incluye el 0; n=13 y 17).
- NOR − PIA en HARD: no alcanza. n=0 y n=0.
- HAM − LEC en MEDIUM: 9.73 m (intervalo 0.08 a 21.69; el intervalo no incluye el 0; n=35 y 29).
- NOR − PIA en MEDIUM: -12.71 m (intervalo -17.64 a -1.67; el intervalo no incluye el 0; n=43 y 41).
- HAM − LEC en SOFT: no alcanza. n=0 y n=0.
- NOR − PIA en SOFT: -26.02 m (intervalo -37.00 a -7.75; el intervalo no incluye el 0; n=5 y 6).

HAM − LEC es positivo en HARD y en MEDIUM: la mediana de Hamilton queda por encima de la de Leclerc, o sea que Leclerc frena más tarde en esos dos compuestos. NOR − PIA es negativo en MEDIUM y en SOFT: Norris frena más tarde que Piastri. SOFT son 5 y 6 vueltas. NOR y PIA no tienen vueltas en HARD; HAM y LEC no tienen vueltas en SOFT. El baseline anotado en `docs/monza_2025_throttle_onset_off.md` esperaba a Hamilton más tarde que Leclerc. Estos intervalos no se calcularon para acercarse a esa expectativa, y no la reproducen.

