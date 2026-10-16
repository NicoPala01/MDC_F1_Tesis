# Estados Unidos, Austin, 2025

Evento FastF1: `United States Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-usa

Brembo llama al circuito Circuit of the Americas y le da 5.513 m. Índice 3. Nueve frenadas y 16,5 s de freno: 3 altas, 4 medias y 2 leves. En cinco puntos el freno dura más de 2 s.

La curva que Brembo llama Turn 12 baja de 312 km/h a 92 km/h en 2,72 s y 126 m. La ficha agrega 4,2 g (un poco menos que los 4,3 g de Turn 1), 130 kg y 2.131 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_united_states_grand_prix_-_race_directors_event_notes_v2.pdf

- 18. DRS during Free Practice session, Sprint and the Race
  - DRS activation 1: 12, 13, 14
  - DRS activation 2: 20, 1, 2, 3
- 19. DRS during the Sprint Qualifying and Qualifying session
  - DRS activation 1: 12, 13, 14
  - DRS activation 2: 20, 1, 2

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Added a blue line at Turn 8 (apex), Turn 10 (exit) and Turn 13 (exit)
- Resurface from before Turn 3 to before Turn 7.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5447,2 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 636,8 | 274 | 79 | 238 | 3 | 108 | 140 | lenta |
| 2 | 890,4 | 85 | 225 | 272 | 5 | 249 | 253 | rápida |
| 3 | 1150,4 | 263 | 270 | 239 | 7 | 84 | 195 | rápida |
| 4 | 1229,3 | 277 | 260 | 221 | 7 | 70 | 79 | rápida |
| 5 | 1337,4 | 269 | 236 | 212 | 6 | 92 | 108 | rápida |
| 6 | 1466,5 | 240 | 211 | 183 | 6 | 64 | 74 | cerca del corte; no se fija |
| 7 | 1705,7 | 220 | 181 | 159 | 5 | 73 | 90 | media |
| 8 | 1849,8 | 193 | 133 | 228 | 4 | 70 | 82 | media |
| 9 | 1944,6 | 138 | 135 | 253 | 4 | 87 | 95 | media |
| 10 | 2141,1 | 174 | 226 | 277 | 5 | 88 | 194 | rápida |
| 11 | 2527,0 | 264 | 73 | 240 | 3 | 96 | 117 | lenta |
| 12 | 3734,6 | 294 | 81 | 93 | 3 | 136 | 171 | lenta |
| 13 | 3977,4 | 186 | 88 | 82 | 3 | 105 | 125 | lenta |
| 14 | 4043,5 |  | 96 | 125 | 3 |  |  | lenta |
| 15 | 4239,6 | 192 | 77 | 231 | 3 | 109 | 130 | lenta |
| 16 | 4434,8 | 88 | 203 | 254 | 5 | 140 | 190 | cerca del corte; no se fija |
| 17 | 4556,4 | 230 | 231 | 268 | 6 | 86 | 115 | rápida |
| 18 | 4699,6 | 231 | 249 | 206 | 6 | 80 | 80 | rápida |
| 19 | 4979,8 | 268 | 186 | 144 | 5 | 94 | 129 | media |
| 20 | 5291,7 | 234 | 92 | 246 | 3 | 112 | 143 | lenta |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 43,76 % de inicios en el borde o afuera (5 en el borde, 59 por corte, 6039 heredados, 13946 inicios). Pares solapados: 18. Fusiones: 4. Definición histórica de 350 m: 41,03 %. Definición histórica del pipeline: 0,91 %.

Después de las ventanas de esta ficha: 45,96 % en el borde o afuera (172 en el borde, 198 por corte, 6039 heredados, 13946 inicios). Pares solapados: 10. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1 | 1 | 160 | 134 |
| T2 | 2 | 120 | 140 |
| T3_T4_T5 | 3, 4, 5 | 120 | 80 |
| T6 | 6 | 90 | 129 |
| T7 | 7 | 110 | 80 |
| T8_T9 | 8, 9 | 100 | 80 |
| T10 | 10 | 116 | 246 |
| T11 | 11 | 140 | 250 |
| T12 | 12 | 190 | 93 |
| T13_T14 | 13, 14 | 150 | 80 |
| T15 | 15 | 150 | 80 |
| T16 | 16 | 115 | 80 |
| T17 | 17 | 100 | 80 |
| T18 | 18 | 100 | 130 |
| T19 | 19 | 150 | 152 |
| T20 | 20 | 160 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T2: casi sin frenada (15 inicios en 898 fragmentos); ventana 120 m
- T3: casi sin frenada (6 inicios en 898 fragmentos); ventana 120 m
- T6: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 90 m y el caso sigue pendiente
- T6: velocidad de ápice 211 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T10: casi sin frenada (14 inicios en 898 fragmentos); ventana 120 m
- T16: casi sin frenada (23 inicios en 898 fragmentos); ventana 120 m
- T16: velocidad de ápice 203 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T17: casi sin frenada (39 inicios en 898 fragmentos); ventana 120 m
- T18: casi sin frenada (1 inicios en 898 fragmentos); ventana 120 m
- T6: quedan 41 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T8: quedan 36 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T15: quedan 34 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T17: quedan 58 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T18: quedan 37 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
