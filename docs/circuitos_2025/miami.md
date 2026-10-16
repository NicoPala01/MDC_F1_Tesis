# Miami, 2025

Evento FastF1: `Miami Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-miami

Brembo llama al circuito Miami International Autodrome y le da 5,412 km. Índice 3. De 8 frenadas, 3 son altas y están separadas. El freno se usa menos de 14,5 s por vuelta y solo 4 frenadas piden más de 65 m.

La curva que Brembo llama Turn 17 baja de 319 km/h a 76 km/h en 2,81 s y 121 m, con 4,6 g, 169 kg y 2.462 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_miami_grand_prix_-_race_directors_event_notes_v2.pdf

- 16) DRS during free practice session and the sprint and race
  - DRS activation 1: 10, 11, 12
  - DRS activation 2: 16, 17, 18
  - DRS activation 3: 20, 1, 2
- 17) DRS during sprint qualifying and qualifying sessions
  - DRS activation 1: 10, 11, 12
  - DRS activation 2: 16, 17, 18
  - DRS activation 3: 20, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- 27.1 Repositioned the white and added blue line at turn 6.
- 27.2 Manholes at Turns 3, 6 and between T8 and T9.
- 27.3 Realigned the wall at Turn 16 RHS.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5323,6 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 371,1 | 287 | 90 | 217 | 3 | 99 | 124 | lenta |
| 2 | 481,0 | 99 | 109 | 248 | 3 | 97 | 106 | lenta |
| 3 | 560,9 |  | 165 | 264 | 4 |  |  | media |
| 4 | 1124,0 | 287 | 241 | 226 | 6 | 71 | 92 | rápida |
| 5 | 1254,8 | 246 | 210 | 206 | 6 | 92 | 128 | cerca del corte; no se fija |
| 6 | 1409,7 | 212 | 219 | 129 | 6 | 138 | 152 | rápida |
| 7 | 1533,9 | 222 | 134 | 217 | 4 | 70 | 110 | media |
| 8 | 1632,3 | 142 | 118 | 251 | 4 | 70 | 91 | cerca del corte; no se fija |
| 9 | 2164,6 | 144 | 292 | 312 | 7 | 483 | 529 | rápida |
| 10 | 2439,4 | 322 | 311 | 319 | 8 | 69 | 69 | rápida |
| 11 | 3064,6 | 301 | 86 | 157 | 3 | 95 | 130 | lenta |
| 12 | 3190,4 | 94 | 92 | 90 | 3 | 94 | 112 | lenta |
| 13 | 3311,3 | 101 | 106 | 112 | 3 | 109 | 121 | lenta |
| 14 | 3386,0 | 159 | 84 | 190 | 3 | 64 | 73 | lenta |
| 15 | 3409,0 |  | 84 | 203 | 3 |  |  | lenta |
| 16 | 3502,9 | 92 | 70 | 243 | 2 | 72 | 88 | lenta |
| 17 | 4811,5 | 300 | 65 | 231 | 2 | 106 | 148 | lenta |
| 18 | 4963,6 | 72 | 137 | 268 | 3 | 131 | 147 | media |
| 19 | 5162,3 |  | 249 | 295 | 6 |  |  | rápida |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 67,19 % de inicios en el borde o afuera (49 en el borde, 119 por corte, 6575 heredados, 10035 inicios). Pares solapados: 17. Fusiones: 6. Definición histórica de 350 m: 20,86 %. Definición histórica del pipeline: 33,46 %.

Después de las ventanas de esta ficha: 70,58 % en el borde o afuera (91 en el borde, 417 por corte, 6575 heredados, 10035 inicios). Pares solapados: 8. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_T2_T3 | 1, 2, 3 | 140 | 250 |
| T4 | 4 | 110 | 80 |
| T5 | 5 | 100 | 80 |
| T6 | 6 | 100 | 80 |
| T7_T8 | 7, 8 | 90 | 250 |
| T9 | 9 | 120 | 155 |
| T10 | 10 | 120 | 250 |
| T11 | 11 | 150 | 80 |
| T12 | 12 | 100 | 80 |
| T13_T14_T15_T16 | 13, 14, 15, 16 | 90 | 250 |
| T17 | 17 | 170 | 80 |
| T18 | 18 | 100 | 80 |
| T19 | 19 | 119 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T5: casi sin frenada (35 inicios en 857 fragmentos); ventana 120 m
- T5: velocidad de ápice 210 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T6: casi sin frenada (9 inicios en 857 fragmentos); ventana 120 m
- T7: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 90 m y el caso sigue pendiente
- T9: casi sin frenada (4 inicios en 857 fragmentos); ventana 120 m
- T10: casi sin frenada (1 inicios en 857 fragmentos); ventana 120 m
- T12: casi sin frenada (12 inicios en 857 fragmentos); ventana 120 m
- T13: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 90 m y el caso sigue pendiente
- T18: casi sin frenada (11 inicios en 857 fragmentos); ventana 120 m
- T19: casi sin frenada (0 inicios en 857 fragmentos); ventana 120 m
- T5: quedan 49 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T6: quedan 25 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T7: quedan 46 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T12: quedan 54 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T13: quedan 49 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T18: quedan 28 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
