# Azerbaiyán, Bakú, 2025

Evento FastF1: `Azerbaijan Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-baku

La ficha escribe «the 6.003-meter-long Baku City Circuit». No se reinterpreta la unidad. Índice 4. El freno se usa 12 veces por vuelta durante casi 20,5 s. Siete frenadas altas, 2 medias y 3 leves.

La curva que Brembo llama Turn 1 baja de 329 km/h a 119 km/h en 2,12 s y 108 m, con 5 g. El pedal llega a 176 kg y la potencia a 2.758 kW. La ficha dice que la desaceleración de Turn 3 también es de 5 g.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_azerbaijan_grand_prix_-_race_directors_event_notes_v2.pdf

- 18. DRS during all Free Practice sessions and the race
  - DRS activation 1: 3, 4, 5
  - DRS activation 2: 20, 21,1, 2
- 19. DRS during the qualifying sessions
  - DRS activation 1: 3, 4, 5
  - DRS activation 2: 20, 21, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- A few resurfacing patches work:
- From Turn 2 to Turn 3 mainly on the LHS
- Before Turn 4 LHS
- Between Turn 7 and Turn 8 on the LHS
- Turn 12 RHS.
- Turn 14 LHS.
- Between Turn 14 and Turn 15 on the LHS
- Turn 18 LHS.
- Realignment of the TecPro barrier at the exit of Turn 1 RHS

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5931,6 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 296,0 | 306 | 113 | 231 | 3 | 127 | 167 | lenta |
| 2 | 639,8 | 232 | 97 | 255 | 3 | 98 | 121 | lenta |
| 3 | 1493,4 | 295 | 96 | 96 | 3 | 127 | 167 | lenta |
| 4 | 1716,7 | 195 | 86 | 230 | 3 | 75 | 96 | lenta |
| 5 | 2057,7 | 229 | 86 | 230 | 3 | 94 | 116 | lenta |
| 6 | 2118,3 | 97 | 85 | 245 | 3 | 60 | 60 | lenta |
| 7 | 2496,7 | 241 | 69 | 135 | 2 | 96 | 119 | lenta |
| 8 | 2693,8 | 188 | 112 | 169 | 3 | 65 | 79 | lenta |
| 9 | 2722,4 |  | 103 | 190 | 3 |  |  | lenta |
| 10 | 2748,1 |  | 91 | 206 | 3 |  |  | lenta |
| 11 | 2797,8 |  | 91 | 228 | 3 |  |  | lenta |
| 12 | 2856,4 |  | 92 | 247 | 3 |  |  | lenta |
| 13 | 3257,4 | 109 | 270 | 294 | 7 | 397 | 401 | rápida |
| 14 | 3472,1 | 275 | 292 | 96 | 7 | 185 | 201 | rápida |
| 15 | 3696,7 | 288 | 85 | 243 | 3 | 129 | 158 | lenta |
| 16 | 4049,2 | 240 | 112 | 250 | 3 | 95 | 121 | lenta |
| 17 | 4246,1 | 119 | 212 | 285 | 5 | 186 | 197 | cerca del corte; no se fija |
| 18 | 4487,9 | 259 | 280 | 300 | 7 | 70 | 70 | rápida |
| 19 | 4642,1 |  | 294 | 311 | 8 |  |  | rápida |
| 20 | 4950,2 | 299 | 312 | 321 | 8 | 184 | 266 | rápida |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 42,91 % de inicios en el borde o afuera (21 en el borde, 85 por corte, 4690 heredados, 11177 inicios). Pares solapados: 17. Fusiones: 5. Definición histórica de 350 m: 20,11 %. Definición histórica del pipeline: 1,68 %.

Después de las ventanas de esta ficha: 43,63 % en el borde o afuera (40 en el borde, 147 por corte, 4690 heredados, 11177 inicios). Pares solapados: 7. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1 | 1 | 190 | 204 |
| T2 | 2 | 140 | 250 |
| T3 | 3 | 190 | 103 |
| T4 | 4 | 120 | 201 |
| T5_T6 | 5, 6 | 140 | 238 |
| T7 | 7 | 140 | 97 |
| T8_T9_T10_T11_T12 | 8, 9, 10, 11, 12 | 100 | 250 |
| T13 | 13 | 120 | 95 |
| T14 | 14 | 120 | 80 |
| T15 | 15 | 180 | 212 |
| T16 | 16 | 140 | 80 |
| T17 | 17 | 117 | 122 |
| T18 | 18 | 120 | 80 |
| T19 | 19 | 100 | 188 |
| T20 | 20 | 120 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T13: casi sin frenada (31 inicios en 796 fragmentos); ventana 120 m
- T14: casi sin frenada (11 inicios en 796 fragmentos); ventana 120 m
- T17: casi sin frenada (5 inicios en 796 fragmentos); ventana 120 m
- T17: velocidad de ápice 212 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T18: casi sin frenada (1 inicios en 796 fragmentos); ventana 120 m
- T19: casi sin frenada (0 inicios en 796 fragmentos); ventana 120 m
- T20: casi sin frenada (30 inicios en 796 fragmentos); ventana 120 m
- T15: quedan 35 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T19: quedan 26 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
