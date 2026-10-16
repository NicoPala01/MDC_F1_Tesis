# Singapur, Marina Bay, 2025

Evento FastF1: `Singapore Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-singapore

La ficha escribe «the 4.940-meter Marina Bay Street Circuit». No se reinterpreta la unidad. Índice 4. Once frenadas, más de 17 s: 5 altas, 3 medias y 3 leves. En 7 curvas la desaceleración pasa de 4 g y el pedal de 125 kg.

La curva que Brembo llama Turn 7 (Memorial) baja de 308 km/h a 128 km/h en 1,9 s y 96 m, con 4,9 g y 151 kg. La potencia que publican en esa ficha llega a 2.542 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_singapore_grand_prix_-_race_directors_event_notes_v2.pdf

- 19. DRS during all Free Practice sessions and the race
  - DRS activation 1: 4, 5, 6
  - DRS activation 2: 11, 12,13
  - DRS activation 3: 13, 14, 15
  - DRS activation 4: 16, 1, 2
- 20. DRS during the qualifying sessions
  - DRS activation 1: 4, 5, 6
  - DRS activation 2: 11, 12,13
  - DRS activation 3: 13, 14, 15
  - DRS activation 4: 16, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Resurfacing areas: from Turn 2 until the exit of Turn 3 from entry Turn 6 until the exit of Turn 7 from entry Turn 9 until before Turn 11 from exit Turn 14 until the exit of Turn 16 from exit Turn 16 until the exit of Turn 19
- Localized patching at Turns 5, 6, 13 and 14.
- Repair the edge of the working lane with the fast lane.
- The Safety Car Lines and Pit Entry lines are highlighted blue.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 4893,2 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 407,0 | 274 | 128 | 165 | 3 | 98 | 124 | cerca del corte; no se fija |
| 2 | 466,2 |  | 109 | 203 | 3 |  |  | lenta |
| 3 | 541,0 | 150 | 81 | 233 | 3 | 65 | 73 | lenta |
| 4 | 700,3 | 84 | 158 | 140 | 3 | 155 | 158 | media |
| 5 | 957,5 | 239 | 137 | 251 | 4 | 97 | 115 | media |
| 6 | 1399,6 | 219 | 277 | 288 | 7 | 263 | 311 | rápida |
| 7 | 1761,2 | 278 | 110 | 84 | 3 | 98 | 136 | lenta |
| 8 | 1999,9 | 188 | 73 | 161 | 3 | 88 | 105 | lenta |
| 9 | 2182,7 | 178 | 124 | 247 | 3 | 71 | 87 | cerca del corte; no se fija |
| 10 | 2608,7 | 250 | 130 | 168 | 4 | 82 | 106 | cerca del corte; no se fija |
| 11 | 2768,9 | 159 | 100 | 65 | 3 | 69 | 85 | lenta |
| 12 | 2856,3 | 107 | 136 | 145 | 3 | 79 | 79 | media |
| 13 | 3021,2 | 196 | 60 | 239 | 2 | 101 | 121 | lenta |
| 14 | 3583,0 | 257 | 82 | 248 | 3 | 141 | 171 | lenta |
| 15 | 3815,0 | 193 | 230 | 282 | 5 | 150 | 150 | rápida |
| 16 | 4297,7 | 272 | 101 | 232 | 3 | 120 | 156 | lenta |
| 17 | 4369,3 | 96 | 109 | 207 | 3 | 63 | 70 | lenta |
| 18 | 4633,9 | 235 | 188 | 254 | 5 | 69 | 100 | media |
| 19 | 4752,0 | 200 | 200 | 274 | 5 | 112 | 119 | cerca del corte; no se fija |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 30,29 % de inicios en el borde o afuera (13 en el borde, 27 por corte, 4645 heredados, 15469 inicios). Pares solapados: 19. Fusiones: 5. Definición histórica de 350 m: 23,23 %. Definición histórica del pipeline: 0,89 %.

Después de las ventanas de esta ficha: 32,68 % en el borde o afuera (144 en el borde, 267 por corte, 4645 heredados, 15469 inicios). Pares solapados: 8. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_T2_T3 | 1, 2, 3 | 140 | 80 |
| T4 | 4 | 100 | 127 |
| T5 | 5 | 130 | 250 |
| T6 | 6 | 120 | 202 |
| T7 | 7 | 160 | 109 |
| T8 | 8 | 130 | 80 |
| T9 | 9 | 110 | 250 |
| T10 | 10 | 130 | 80 |
| T11_T12 | 11, 12 | 110 | 80 |
| T13 | 13 | 140 | 250 |
| T14 | 14 | 190 | 112 |
| T15 | 15 | 120 | 250 |
| T16_T17 | 16, 17 | 180 | 145 |
| T18_T19 | 18, 19 | 120 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T1: velocidad de ápice 128 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T4: casi sin frenada (13 inicios en 1106 fragmentos); ventana 120 m
- T6: casi sin frenada (3 inicios en 1106 fragmentos); ventana 120 m
- T9: velocidad de ápice 124 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T10: velocidad de ápice 130 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T15: casi sin frenada (1 inicios en 1106 fragmentos); ventana 120 m
- T4: quedan 21 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T9: quedan 7 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T11: quedan 30 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T13: quedan 55 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
