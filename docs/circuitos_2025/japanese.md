# Japón, Suzuka, 2025

Evento FastF1: `Japanese Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-japan

Brembo llama al circuito Suzuka Circuit y le da 5,807 km. Índice 1, el más bajo del campeonato en esa ficha: 10 s de freno por vuelta, 11 % del tiempo de vuelta. Frenadas: 2 altas, 4 medias y 2 leves.

La curva que Brembo llama Corner 16 baja de 303 km/h a 103 km/h en 2,17 s y 106 m, con 166 kg y 4,5 g. Potencia 2.360 kW. La ficha dice que se llega a fondo desde la 130R.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_japanese_grand_prix_-_race_directors_event_notes_v3.pdf

- 15) DRS during all free practice sessions and the race
  - DRS activation 1: 1, 2, 22
- 16) DRS during qualifying sessions
  - DRS activation 1: 1, 22

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Resurfacing between Turn 1 until entry Turn 8.
- Gravel was brought to the back of the double kerb at Turn 2, Turn 8 and Turn 9.
- Marshal posts were protected with debris fences.
- Driver exit aperture sign installed throughout the circuit.
- Extinguishers signals supported by plastic posts instead of wooden.
- New double kerb at Turn 9.
- Realignment of the white line and add a blue line at the exit of turns 1, 2, 8, 9, 13, 14, 15
- Grinding asphalt exit T14 RHS

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5766,3 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 691,0 | 307 | 220 | 199 | 6 | 85 | 125 | rápida |
| 2 | 818,2 | 278 | 157 | 239 | 4 | 119 | 127 | media |
| 3 | 1080,3 | 165 | 228 | 217 | 6 | 255 | 258 | rápida |
| 4 | 1196,9 | 235 | 203 | 209 | 5 | 95 | 116 | cerca del corte; no se fija |
| 5 | 1353,9 | 208 | 198 | 192 | 5 | 102 | 156 | cerca del corte; no se fija |
| 6 | 1540,5 | 212 | 182 | 228 | 5 | 74 | 89 | media |
| 7 | 1841,1 | 220 | 229 | 278 | 6 | 151 | 293 | rápida |
| 8 | 2260,1 | 279 | 230 | 175 | 6 | 66 | 78 | rápida |
| 9 | 2410,9 | 234 | 130 | 243 | 4 | 66 | 79 | cerca del corte; no se fija |
| 10 | 2722,7 | 136 | 242 | 138 | 6 | 299 | 308 | rápida |
| 11 | 2877,9 | 241 | 67 | 233 | 2 | 98 | 120 | lenta |
| 12 | 3136,3 | 74 | 219 | 281 | 5 | 254 | 258 | rápida |
| 13 | 3771,4 | 284 | 205 | 175 | 6 | 76 | 99 | cerca del corte; no se fija |
| 14 | 3927,3 | 203 | 150 | 247 | 4 | 73 | 95 | media |
| 15 | 4955,2 | 306 | 302 | 297 | 8 | 97 | 97 | rápida |
| 16 | 5354,5 | 283 | 85 | 228 | 3 | 109 | 136 | lenta |
| 17 | 5431,4 | 94 | 87 | 251 | 3 | 65 | 74 | lenta |
| 18 | 5582,5 | 144 | 194 | 281 | 4 | 119 | 121 | media |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 60,75 % de inicios en el borde o afuera (34 en el borde, 188 por corte, 8041 heredados, 13601 inicios). Pares solapados: 15. Fusiones: 2. Definición histórica de 350 m: 33,32 %. Definición histórica del pipeline: 18,57 %.

Después de las ventanas de esta ficha: 64,27 % en el borde o afuera (186 en el borde, 515 por corte, 8041 heredados, 13601 inicios). Pares solapados: 9. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1 | 1 | 150 | 80 |
| T2 | 2 | 90 | 142 |
| T3_T4 | 3, 4 | 120 | 80 |
| T5 | 5 | 100 | 80 |
| T6 | 6 | 110 | 80 |
| T7 | 7 | 270 | 250 |
| T8 | 8 | 100 | 80 |
| T9 | 9 | 100 | 192 |
| T10 | 10 | 120 | 80 |
| T11 | 11 | 140 | 138 |
| T12 | 12 | 120 | 250 |
| T13 | 13 | 120 | 80 |
| T14 | 14 | 110 | 250 |
| T15 | 15 | 120 | 239 |
| T16_T17 | 16, 17 | 160 | 80 |
| T18 | 18 | 100 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T2: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 90 m y el caso sigue pendiente
- T3: casi sin frenada (5 inicios en 989 fragmentos); ventana 120 m
- T5: casi sin frenada (10 inicios en 989 fragmentos); ventana 120 m
- T5: velocidad de ápice 198 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T7: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 270 m y el caso sigue pendiente
- T9: velocidad de ápice 130 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T10: casi sin frenada (9 inicios en 989 fragmentos); ventana 120 m
- T12: casi sin frenada (17 inicios en 989 fragmentos); ventana 120 m
- T13: velocidad de ápice 205 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T15: casi sin frenada (1 inicios en 989 fragmentos); ventana 120 m
- T18: casi sin frenada (8 inicios en 989 fragmentos); ventana 120 m
- T2: quedan 43 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T5: quedan 23 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T6: quedan 3 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T7: quedan 49 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T9: quedan 29 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T11: quedan 65 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T14: quedan 34 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T18: quedan 29 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
