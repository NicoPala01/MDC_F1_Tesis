# Las Vegas, 2025

Evento FastF1: `Las Vegas Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-las-vegas

Brembo llama al circuito Las Vegas Strip Circuit y le da 6,201 km. Índice 3. Siete frenadas y 14,5 s de freno. En https://www.brembo.com/en/motorsport/formula1/2025-numbers dice que la frenada de Turn 14 de Verstappen, de 350 km/h a 102 km/h en 143 m, fue la más larga de la temporada.

La curva que Brembo llama Turn 14 baja de 350 km/h a 102 km/h en 2,74 s y 143 m.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_las_vegas_grand_prix_-_race_directors_event_notes_v2.pdf

- 17. DRS during Free Practice sessions, Qualifying Sessions and the Race
  - DRS activation 1: 3, 4, 5, 6
  - DRS activation 2: 16, 17, 18

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Turn 3: adjust right -hand side Inside painted kerb and white line (the wall is in the same position)
- Turn 4: Exit Left-Hand side adjust left track edge. The painted kerb was removed.
- Two patches of Asphalt: one 50m before MP4.8 and the second one 20m after over whole track width
- Patch of Asphalt 40m before Turn 5 over whole track width
- Turn 5 and Turn 6 left-hand side adjustment of painted kerb and white line (the wall is in the same position)
- Turn 8: widening Run Off on the left-hand side for better access for vehicles and pedestrians during track build
- Two patches of Asphalt: one at MP12.9 and the second one at 30 meters after the MP over the whole track width
- MP 12.9 changed location.
- MP15.1 moved to opposite track site for better line of sight and MP16.0 move closer to T15.
- Distance boards updated to new size and 100 m boards printed in blue.
- Reprofiling the manhole between Turn 16 and Turn 17 under the bridge.
- Reprofiling of the concrete barrier before pit entry (after the speed limit board) at the right hand side.
- Remove paint from the apex Turn 16

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 6139,2 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 286,7 | 308 | 107 | 201 | 3 | 123 | 150 | lenta |
| 2 | 386,4 | 117 | 111 | 220 | 3 | 87 | 99 | lenta |
| 3 | 575,1 | 209 | 198 | 272 | 5 | 90 | 107 | cerca del corte; no se fija |
| 4 | 677,8 |  | 218 | 291 | 5 |  |  | rápida |
| 5 | 1539,6 | 306 | 103 | 247 | 3 | 134 | 171 | lenta |
| 6 | 1802,4 | 103 | 238 | 101 | 6 | 260 | 263 | rápida |
| 7 | 2024,6 | 252 | 93 | 149 | 3 | 117 | 156 | lenta |
| 8 | 2078,7 |  | 93 | 194 | 3 |  |  | lenta |
| 9 | 2216,8 | 134 | 88 | 253 | 3 | 73 | 91 | lenta |
| 10 | 2678,0 | 198 | 286 | 302 | 7 | 270 | 291 | rápida |
| 11 | 2962,9 | 296 | 295 | 102 | 8 | 145 | 175 | rápida |
| 12 | 3189,7 | 285 | 95 | 251 | 3 | 136 | 179 | lenta |
| 13 | 3940,8 | 96 | 319 | 331 | 8 | 747 | 751 | rápida |
| 14 | 5122,2 | 320 | 89 | 240 | 3 | 138 | 178 | lenta |
| 15 | 5180,3 |  | 89 | 258 | 3 |  |  | lenta |
| 16 | 5245,1 | 128 | 129 | 273 | 3 | 65 | 65 | cerca del corte; no se fija |
| 17 | 5981,3 | 301 | 322 | 320 | 8 | 307 | 395 | rápida |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 43,83 % de inicios en el borde o afuera (49 en el borde, 172 por corte, 3454 heredados, 8384 inicios). Pares solapados: 13. Fusiones: 5. Definición histórica de 350 m: 26,65 %. Definición histórica del pipeline: 6,05 %.

Después de las ventanas de esta ficha: 45,36 % en el borde o afuera (128 en el borde, 221 por corte, 3454 heredados, 8384 inicios). Pares solapados: 6. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_T2 | 1, 2 | 170 | 80 |
| T3_T4 | 3, 4 | 130 | 250 |
| T5 | 5 | 190 | 143 |
| T6 | 6 | 120 | 80 |
| T7_T8 | 7, 8 | 180 | 80 |
| T9 | 9 | 110 | 250 |
| T10 | 10 | 120 | 95 |
| T11 | 11 | 190 | 80 |
| T12 | 12 | 200 | 250 |
| T13 | 13 | 120 | 250 |
| T14_T15_T16 | 14, 15, 16 | 200 | 250 |
| T17 | 17 | 120 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T3: velocidad de ápice 198 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T6: casi sin frenada (5 inicios en 760 fragmentos); ventana 120 m
- T10: casi sin frenada (11 inicios en 760 fragmentos); ventana 120 m
- T13: casi sin frenada (8 inicios en 759 fragmentos); ventana 120 m
- T17: casi sin frenada (18 inicios en 760 fragmentos); ventana 120 m
- T3: quedan 21 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T7: quedan 38 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T9: quedan 52 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T12: quedan 53 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
