# Catar, Lusail, 2025

Evento FastF1: `Qatar Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

No hay ficha Brembo citada. La URL indexada `https://www.brembo.com/en/motorsport/formula1/facts-formula1-gp-las-qatar` respondió 404 el 16 de octubre de 2026, y las variantes con Lusail o Qatar en el path de 2025 también. El largo oficial y las frenadas de Brembo quedan vacíos.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_qatar_grand_prix_-_race_directors_event_notes_v2.pdf

- 18. DRS during Free Practice sessions, Sprint and the Race
  - DRS activation 1: 20, 1, 2, 3
- 19. DRS during the Sprint Qualifying and Qualifying session
  - DRS activation 1: 20, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Additional gravel strip at the exit of Turn 6.
- Additional gravel strip at Turn 10 on the right-hand side.
- Gravel strip at the exit of Turn 14 starts earlier.
- Additional gravel strip at the exit of Turn 16.
- Gravel beds have been painted.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5394,6 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 789,5 | 298 | 143 | 185 | 4 | 154 | 190 | media |
| 2 | 1086,6 | 225 | 161 | 252 | 4 | 101 | 117 | media |
| 3 | 1294,0 |  | 229 | 279 | 5 |  |  | rápida |
| 4 | 1726,5 | 273 | 186 | 222 | 5 | 111 | 132 | media |
| 5 | 1879,9 | 206 | 197 | 138 | 5 | 68 | 83 | media |
| 6 | 2187,5 | 234 | 89 | 239 | 3 | 113 | 130 | lenta |
| 7 | 2582,7 | 236 | 131 | 245 | 4 | 122 | 138 | cerca del corte; no se fija |
| 8 | 2777,3 | 144 | 211 | 242 | 5 | 115 | 195 | cerca del corte; no se fija |
| 9 | 2891,2 | 230 | 241 | 139 | 6 | 68 | 109 | rápida |
| 10 | 3137,9 | 241 | 137 | 251 | 4 | 113 | 137 | media |
| 11 | 3462,9 | 166 | 258 | 290 | 6 | 254 | 277 | rápida |
| 12 | 3758,3 | 291 | 279 | 269 | 7 | 77 | 113 | rápida |
| 13 | 3950,9 | 279 | 268 | 250 | 7 | 76 | 110 | rápida |
| 14 | 4163,9 | 267 | 248 | 268 | 7 | 79 | 105 | rápida |
| 15 | 4457,7 | 270 | 234 | 272 | 6 | 69 | 89 | rápida |
| 16 | 4935,1 | 270 | 152 | 252 | 4 | 113 | 139 | media |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 40,85 % de inicios en el borde o afuera (1 en el borde, 12 por corte, 4751 heredados, 11662 inicios). Pares solapados: 15. Fusiones: 1. Definición histórica de 350 m: 13,98 %. Definición histórica del pipeline: 0,51 %.

Después de las ventanas de esta ficha: 41,29 % en el borde o afuera (19 en el borde, 45 por corte, 4751 heredados, 11662 inicios). Pares solapados: 7. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1 | 1 | 210 | 157 |
| T2 | 2 | 140 | 87 |
| T3 | 3 | 120 | 250 |
| T4 | 4 | 150 | 80 |
| T5 | 5 | 100 | 158 |
| T6 | 6 | 150 | 235 |
| T7 | 7 | 160 | 80 |
| T8_T9 | 8, 9 | 115 | 87 |
| T10 | 10 | 160 | 205 |
| T11 | 11 | 120 | 165 |
| T12 | 12 | 130 | 80 |
| T13 | 13 | 130 | 83 |
| T14 | 14 | 130 | 184 |
| T15 | 15 | 110 | 250 |
| T16 | 16 | 160 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T3: casi sin frenada (0 inicios en 904 fragmentos); ventana 120 m
- T5: casi sin frenada (29 inicios en 904 fragmentos); ventana 120 m
- T7: velocidad de ápice 131 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T8: casi sin frenada (17 inicios en 904 fragmentos); ventana 120 m
- T8: velocidad de ápice 211 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T11: casi sin frenada (4 inicios en 904 fragmentos); ventana 120 m
- T5: quedan 27 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T13: quedan 17 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
