# Emilia-Romaña, Imola, 2025

Evento FastF1: `Emilia Romagna Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-imola

Brembo llama al circuito Autodromo Internazionale Enzo e Dino Ferrari y le da 4,909 km. Índice 3. Hay 9 frenadas y solo una pide al menos 90 m de desaceleración. El freno se usa menos de 10,5 s: 3 altas, 4 medias y 2 leves.

La curva que Brembo llama turn 17 (Rivazza) baja de 292 km/h a 122 km/h en 2,09 s y 105 m, con 4,1 g, 145 kg y 2.026 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_emilia_romagna_grand_prix_-_race_directors_event_notes_.pdf

- 14) DRS during all free practice sessions, qualifying and the race
  - DRS activation 1: 19, 1, 2, 3, 4

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Turn 4 apex: realign white line and blue line at the back, 1,5m from the kerb.
- Turn 4 exit: realign white line and blue line at the back, 1,5m from the gravel.
- Turn 6 apex: realign white line and blue line at the back, 1,5m from the gravel.
- Turn 6 exit: realign white line and blue line at the back, 1,5m from the gravel.
- Turn 7 exit: realign white line and blue line at the back, 1,5m from the grass.
- Turn 9 exit: realign white line and blue line at the back, 1,5m from the gravel.
- Turn 11 exit: realign white line and blue line at the back, 1,5m from the back of the kerb.
- Turn 12 apex: realign white line and blue line at the back, 1,5m from the back of the kerb.
- Turn 12 exit/ Turn 13 apex: realign white line and blue line at the back, 1,5m from the gravel.
- Turn 14 apex: realign white line and the bollard behind the kerb
- Turn 15 exit: realign white line and blue line at the back, 1,5m from the gravel.
- Turn 17 exit: realign white line and blue line at the back, 1,5m from the gravel.
- Turn 18 exit: realign white line and blue line at the back, 1,5m from the gravel.
- Turn 19 apex: realign white line to 1,5 meters from the wall.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 4881,1 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 258,6 | 266 | 297 | 308 | 8 | 269 | 269 | rápida |
| 2 | 874,8 | 290 | 145 | 234 | 4 | 83 | 140 | media |
| 3 | 943,4 | 151 | 145 | 251 | 4 | 65 | 65 | media |
| 4 | 1079,5 | 171 | 202 | 274 | 5 | 85 | 127 | cerca del corte; no se fija |
| 5 | 1500,7 | 275 | 204 | 218 | 6 | 65 | 91 | cerca del corte; no se fija |
| 6 | 1612,6 | 236 | 161 | 137 | 4 | 94 | 113 | media |
| 7 | 1895,4 | 220 | 91 | 236 | 3 | 84 | 98 | lenta |
| 8 | 2284,4 | 98 | 259 | 189 | 6 | 386 | 388 | rápida |
| 9 | 2538,1 | 271 | 188 | 264 | 5 | 105 | 126 | media |
| 10 | 2676,4 |  | 221 | 257 | 5 |  |  | rápida |
| 11 | 2930,7 | 269 | 184 | 205 | 6 | 69 | 84 | media |
| 12 | 3024,0 | 248 | 122 | 241 | 4 | 79 | 93 | cerca del corte; no se fija |
| 13 | 3087,6 | 129 | 122 | 256 | 4 | 60 | 60 | cerca del corte; no se fija |
| 14 | 3530,6 | 254 | 94 | 234 | 3 | 85 | 107 | lenta |
| 15 | 3578,9 |  | 94 | 249 | 3 |  |  | lenta |
| 16 | 4122,4 |  | 289 | 143 | 7 |  |  | rápida |
| 17 | 4316,3 | 281 | 111 | 209 | 3 | 116 | 141 | lenta |
| 18 | 4456,1 | 158 | 139 | 254 | 4 | 67 | 83 | media |
| 19 | 4763,2 | 200 | 256 | 292 | 6 | 224 | 253 | rápida |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 60,77 % de inicios en el borde o afuera (23 en el borde, 53 por corte, 7784 heredados, 12934 inicios). Pares solapados: 18. Fusiones: 5. Definición histórica de 350 m: 18,01 %. Definición histórica del pipeline: 2,61 %.

Después de las ventanas de esta ficha: 62,10 % en el borde o afuera (100 en el borde, 148 por corte, 7784 heredados, 12934 inicios). Pares solapados: 6. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1 | 1 | 120 | 250 |
| T2_T3 | 2, 3 | 160 | 80 |
| T4 | 4 | 100 | 250 |
| T5_T6 | 5, 6 | 120 | 163 |
| T7 | 7 | 120 | 250 |
| T8 | 8 | 120 | 104 |
| T9 | 9 | 150 | 80 |
| T10 | 10 | 100 | 154 |
| T11_T12_T13 | 11, 12, 13 | 100 | 250 |
| T14_T15 | 14, 15 | 130 | 250 |
| T16 | 16 | 120 | 80 |
| T17 | 17 | 160 | 80 |
| T18 | 18 | 100 | 187 |
| T19 | 19 | 120 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T1: casi sin frenada (1 inicios en 939 fragmentos); ventana 120 m
- T4: casi sin frenada (5 inicios en 939 fragmentos); ventana 120 m
- T4: velocidad de ápice 202 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T5: casi sin frenada (46 inicios en 939 fragmentos); ventana 120 m
- T5: velocidad de ápice 204 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T8: casi sin frenada (20 inicios en 939 fragmentos); ventana 120 m
- T10: casi sin frenada (0 inicios en 939 fragmentos); ventana 120 m
- T16: casi sin frenada (0 inicios en 939 fragmentos); ventana 120 m
- T18: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 100 m y el caso sigue pendiente
- T19: casi sin frenada (7 inicios en 939 fragmentos); ventana 120 m
- T4: quedan 44 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T10: quedan 42 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T17: quedan 46 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T18: quedan 40 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
