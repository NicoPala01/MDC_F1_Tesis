# Bélgica, Spa-Francorchamps, 2025

Evento FastF1: `Belgian Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-belgium

Brembo llama al circuito Circuit de Spa-Francorchamps y le da 7,004 km. Índice 4. Cinco frenadas altas, una media y dos leves.

La curva que Brembo llama Turn 5, al final de la recta de Kemmel, baja de 327 km/h a 176 km/h en 1,48 s y 93 m.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_belgian_grand_prix_-_race_directors_event_notes_v2.pdf

- 19. DRS during all free Practice Session, Sprint and the Race
  - DRS activation 1: 5, 6, 7
  - DRS activation 2: 21, 1, 2
- 20. DRS during sprint qualifying and qualifying sessions
  - DRS activation 1: 5, 6, 7
  - DRS activation 2: 21, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Resurface racing line from 50 m brake marker board before Turn 1 to the exit of Turn 1
- Replace the apex kerb at Turn 3
- Grinding asphalt halfway down from endurance pit lane to Turn 2.
- Resurfacing after T15 on the RHS (to correct a bump).

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 6941,5 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 360,3 | 266 | 71 | 243 | 2 | 102 | 146 | lenta |
| 2 | 1056,2 | 75 | 311 | 308 | 8 | 685 | 695 | rápida |
| 3 | 1158,7 | 304 | 305 | 312 | 8 | 84 | 98 | rápida |
| 4 | 1259,5 |  | 305 | 316 | 8 |  |  | rápida |
| 5 | 2394,4 | 305 | 145 | 197 | 4 | 115 | 179 | media |
| 6 | 2468,3 | 124 | 145 | 226 | 4 | 69 | 70 | media |
| 7 | 2627,5 | 156 | 191 | 262 | 5 | 71 | 159 | media |
| 8 | 3016,1 | 255 | 107 | 183 | 3 | 123 | 149 | lenta |
| 9 | 3268,9 | 200 | 181 | 269 | 5 | 74 | 98 | media |
| 10 | 3781,9 | 286 | 257 | 281 | 7 | 80 | 118 | rápida |
| 11 | 4033,6 | 254 | 277 | 295 | 7 | 206 | 240 | rápida |
| 12 | 4444,3 | 287 | 153 | 195 | 4 | 99 | 136 | media |
| 13 | 4595,4 | 152 | 164 | 203 | 4 | 120 | 138 | media |
| 14 | 4893,0 | 232 | 156 | 251 | 4 | 78 | 104 | media |
| 15 | 5147,3 | 165 | 242 | 288 | 6 | 132 | 246 | rápida |
| 16 | 5866,4 | 265 | 314 | 316 | 8 | 491 | 608 | rápida |
| 17 | 6141,1 | 304 | 312 | 311 | 8 | 81 | 250 | rápida |
| 18 | 6665,7 | 297 | 74 | 219 | 2 | 109 | 179 | lenta |
| 19 | 6737,0 | 72 | 72 | 243 | 2 | 65 | 69 | lenta |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 45,08 % de inicios en el borde o afuera (6 en el borde, 148 por corte, 4129 heredados, 9500 inicios). Pares solapados: 16. Fusiones: 4. Definición histórica de 350 m: 18,74 %. Definición histórica del pipeline: 5,26 %.

Después de las ventanas de esta ficha: 45,56 % en el borde o afuera (22 en el borde, 177 por corte, 4129 heredados, 9500 inicios). Pares solapados: 9. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1 | 1 | 170 | 80 |
| T2_T3_T4 | 2, 3, 4 | 660 | 250 |
| T5_T6 | 5, 6 | 200 | 80 |
| T7 | 7 | 100 | 219 |
| T8 | 8 | 170 | 133 |
| T9 | 9 | 120 | 250 |
| T10 | 10 | 140 | 132 |
| T11 | 11 | 120 | 250 |
| T12 | 12 | 160 | 80 |
| T13 | 13 | 120 | 178 |
| T14 | 14 | 120 | 80 |
| T15 | 15 | 220 | 89 |
| T16 | 16 | 630 | 155 |
| T17 | 17 | 120 | 250 |
| T18_T19 | 18, 19 | 200 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T2: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 660 m y el caso sigue pendiente
- T7: casi sin frenada (24 inicios en 734 fragmentos); ventana 120 m
- T11: casi sin frenada (7 inicios en 734 fragmentos); ventana 120 m
- T13: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 120 m y el caso sigue pendiente
- T15: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 220 m y el caso sigue pendiente
- T17: casi sin frenada (3 inicios en 734 fragmentos); ventana 120 m
- T2: quedan 44 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T7: quedan 21 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T13: quedan 49 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T15: quedan 46 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
