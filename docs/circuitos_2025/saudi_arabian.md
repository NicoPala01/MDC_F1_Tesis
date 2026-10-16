# Arabia Saudita, Yeda, 2025

Evento FastF1: `Saudi Arabian Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-saudi-arabia

Brembo llama al circuito Jeddah Corniche Circuit, le da 6,174 km y dice que tiene 27 curvas y tres zonas de DRS. Índice 4. Cuenta 8 frenadas, 6 de ellas altas. El freno se usa más de 11 s por vuelta.

La primera curva baja de 317 km/h a 110 km/h en 122 m y 2,47 s, con 159 kg, 4,4 g y 2.339 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_saudi_arabian_grand_prix_-_race_directors_event_notes_v2.pdf

- 16) DRS during all free practice sessions and the race
  - DRS activation 1: 13, 14, 15
  - DRS activation 2: 17, 18, 19, 20
  - DRS activation 3: 21, 22, 1, 2
- 17) DRS during qualifying sessions
  - DRS activation 1: 13, 14, 15
  - DRS activation 2: 17, 18, 19, 20
  - DRS activation 3: 21, 22, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- 26.1 The pit entry and pit exit white lines are highlighted blue.
- 26.2 The safety car lines are highlighted blue.
- 26.3 Blue line behind the white line at the apex of turns 2, 5, 8, 9, 14, 17.
- 26.4 Blue line behind the white line at the exit of turns 8, 19, 23.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 6076,0 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 473,4 | 296 | 89 | 216 | 3 | 95 | 140 | lenta |
| 2 | 537,8 | 96 | 81 | 239 | 3 | 61 | 61 | lenta |
| 3 | 671,6 | 89 | 141 | 250 | 3 | 133 | 134 | media |
| 4 | 983,1 | 253 | 144 | 229 | 4 | 72 | 94 | media |
| 5 | 1087,5 | 146 | 159 | 239 | 4 | 93 | 95 | media |
| 6 | 1221,5 | 186 | 208 | 236 | 5 | 108 | 122 | cerca del corte; no se fija |
| 7 | 1338,6 | 232 | 235 | 210 | 6 | 70 | 76 | rápida |
| 8 | 1426,0 | 232 | 233 | 218 | 6 | 75 | 81 | rápida |
| 9 | 1569,2 | 235 | 202 | 250 | 5 | 69 | 141 | cerca del corte; no se fija |
| 10 | 1679,2 | 204 | 204 | 273 | 5 | 88 | 108 | cerca del corte; no se fija |
| 11 | 1781,5 | 221 | 225 | 287 | 6 | 89 | 100 | rápida |
| 12 | 1857,9 | 229 | 248 | 292 | 6 | 72 | 74 | rápida |
| 13 | 2390,5 | 284 | 139 | 239 | 4 | 131 | 157 | media |
| 14 | 2703,3 | 150 | 245 | 277 | 6 | 301 | 311 | rápida |
| 15 | 2900,8 | 272 | 273 | 203 | 7 | 64 | 64 | rápida |
| 16 | 3035,2 | 274 | 171 | 247 | 5 | 78 | 108 | media |
| 17 | 3143,6 | 180 | 179 | 271 | 5 | 95 | 100 | media |
| 18 | 3366,4 | 204 | 256 | 299 | 6 | 219 | 219 | rápida |
| 19 | 3576,5 |  | 291 | 311 | 7 |  |  | rápida |
| 20 | 3781,9 |  | 308 | 310 | 8 |  |  | rápida |
| 21 | 3966,7 | 289 | 311 | 187 | 8 | 111 | 115 | rápida |
| 22 | 4216,1 | 299 | 168 | 250 | 5 | 84 | 124 | media |
| 23 | 4303,2 | 174 | 169 | 267 | 5 | 80 | 84 | media |
| 24 | 4451,9 | 193 | 233 | 290 | 6 | 131 | 146 | rápida |
| 25 | 4740,5 | 269 | 289 | 312 | 7 | 179 | 179 | rápida |
| 26 | 5103,8 |  | 314 | 305 | 8 |  |  | rápida |
| 27 | 5472,6 | 297 | 98 | 234 | 3 | 105 | 152 | lenta |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 65,82 % de inicios en el borde o afuera (19 en el borde, 72 por corte, 8202 heredados, 12599 inicios). Pares solapados: 26. Fusiones: 9. Definición histórica de 350 m: 20,18 %. Definición histórica del pipeline: 2,56 %.

Después de las ventanas de esta ficha: 67,74 % en el borde o afuera (73 en el borde, 260 por corte, 8202 heredados, 12599 inicios). Pares solapados: 10. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_T2 | 1, 2 | 160 | 80 |
| T3 | 3 | 100 | 201 |
| T4_T5 | 4, 5 | 110 | 80 |
| T6_T7_T8 | 6, 7, 8 | 100 | 80 |
| T9_T10_T11_T12 | 9, 10, 11, 12 | 110 | 250 |
| T13 | 13 | 180 | 193 |
| T14 | 14 | 120 | 80 |
| T15 | 15 | 117 | 80 |
| T16_T17 | 16, 17 | 130 | 103 |
| T18 | 18 | 120 | 90 |
| T19 | 19 | 120 | 85 |
| T20 | 20 | 120 | 80 |
| T21 | 21 | 105 | 109 |
| T22_T23 | 22, 23 | 140 | 80 |
| T24 | 24 | 100 | 169 |
| T25 | 25 | 120 | 243 |
| T26 | 26 | 120 | 199 |
| T27 | 27 | 170 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T3: casi sin frenada (16 inicios en 798 fragmentos); ventana 120 m
- T6: casi sin frenada (6 inicios en 798 fragmentos); ventana 120 m
- T6: velocidad de ápice 208 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T9: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 110 m y el caso sigue pendiente
- T9: velocidad de ápice 202 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T14: casi sin frenada (11 inicios en 798 fragmentos); ventana 120 m
- T15: casi sin frenada (1 inicios en 798 fragmentos); ventana 120 m
- T18: casi sin frenada (2 inicios en 798 fragmentos); ventana 120 m
- T19: casi sin frenada (0 inicios en 798 fragmentos); ventana 120 m
- T20: casi sin frenada (0 inicios en 798 fragmentos); ventana 120 m
- T21: casi sin frenada (2 inicios en 798 fragmentos); ventana 120 m
- T24: casi sin frenada (14 inicios en 798 fragmentos); ventana 120 m
- T25: casi sin frenada (1 inicios en 798 fragmentos); ventana 120 m
- T26: casi sin frenada (0 inicios en 798 fragmentos); ventana 120 m
- T3: quedan 46 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T6: quedan 46 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T9: quedan 47 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T16: quedan 76 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T24: quedan 31 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
