# Abu Dabi, Yas Marina, 2025

Evento FastF1: `Abu Dhabi Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-las-abu-dhabi

Brembo llama al circuito Yas Marina Circuit y le da 5.281 m. Índice 3. Nueve frenadas: 4 altas y 2 medias. Solo en dos curvas el freno dura al menos 2 s, y en toda la vuelta queda activo menos de 13 s.

La curva que Brembo llama Turn 6 baja de 321 km/h a 78 km/h en 2,67 s y 114 m, con 4,7 g, 148 kg y 2.403 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_abu_dhabi_grand_prix_-_race_directors_event_notes_v2.pdf

- 17. DRS during Free Practice sessions, Qualifying session and the Race
  - DRS activation 1: 11, 12, 13, 14
  - DRS activation 2: 16, 17, 18, 19, 20

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Resurface between Turn 1 and Turn 4.
- Grind down the kerb at Turn 4 apex.
- Grind the apex kerb at Turn 6.
- New patch of asphalt to remove a bump at the exit of turn 6 right-hand side
- Debris fence extension at the exit of Turn 1 left-hand side
- Debris fence extension at Turn 3 left-hand side
- New debris fence at Turn 16 left-hand side
- Extended guardrail after Turn 5 on the left-hand side
- Extended Tecpro barrier at the exit of Turn 3 left-hand side
- Support pit entry Tecpro adjusted
- Reposition of the bollard at Turn 6.
- Widen white line and reposition of the blue line at the exit of Turns 1 and 7.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5214,1 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 384,8 | 269 | 148 | 241 | 4 | 91 | 112 | media |
| 2 | 628,8 | 153 | 232 | 262 | 6 | 230 | 242 | rápida |
| 3 | 838,0 | 257 | 259 | 283 | 7 | 80 | 93 | rápida |
| 4 | 1038,6 | 264 | 274 | 287 | 7 | 141 | 183 | rápida |
| 5 | 1426,3 | 278 | 92 | 242 | 3 | 122 | 145 | lenta |
| 6 | 2615,4 | 298 | 60 | 223 | 2 | 123 | 166 | lenta |
| 7 | 2678,4 | 65 | 60 | 246 | 2 | 61 | 63 | lenta |
| 8 | 2887,6 | 95 | 210 | 285 | 5 | 205 | 210 | cerca del corte; no se fija |
| 9 | 3699,0 | 294 | 154 | 246 | 4 | 173 | 217 | media |
| 10 | 4025,7 | 184 | 253 | 151 | 6 | 262 | 315 | rápida |
| 11 | 4182,5 | 267 | 206 | 130 | 7 | 90 | 141 | cerca del corte; no se fija |
| 12 | 4307,2 | 254 | 96 | 140 | 3 | 99 | 121 | lenta |
| 13 | 4414,8 | 112 | 114 | 207 | 3 | 96 | 108 | lenta |
| 14 | 4534,7 | 147 | 136 | 245 | 4 | 70 | 118 | media |
| 15 | 4813,6 | 146 | 241 | 120 | 6 | 170 | 277 | rápida |
| 16 | 5040,4 | 245 | 116 | 246 | 4 | 94 | 120 | lenta |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 57,20 % de inicios en el borde o afuera (79 en el borde, 222 por corte, 7456 heredados, 13562 inicios). Pares solapados: 14. Fusiones: 3. Definición histórica de 350 m: 17,95 %. Definición histórica del pipeline: 10,26 %.

Después de las ventanas de esta ficha: 60,82 % en el borde o afuera (113 en el borde, 679 por corte, 7456 heredados, 13562 inicios). Pares solapados: 8. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1 | 1 | 130 | 124 |
| T2 | 2 | 120 | 89 |
| T3 | 3 | 120 | 81 |
| T4 | 4 | 120 | 228 |
| T5 | 5 | 160 | 250 |
| T6_T7 | 6, 7 | 190 | 89 |
| T8 | 8 | 120 | 250 |
| T9 | 9 | 240 | 207 |
| T10 | 10 | 120 | 80 |
| T11 | 11 | 100 | 80 |
| T12_T13_T14 | 12, 13, 14 | 140 | 159 |
| T15 | 15 | 120 | 87 |
| T16 | 16 | 140 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T2: casi sin frenada (9 inicios en 1044 fragmentos); ventana 120 m
- T3: casi sin frenada (17 inicios en 1044 fragmentos); ventana 120 m
- T4: casi sin frenada (30 inicios en 1044 fragmentos); ventana 120 m
- T8: casi sin frenada (16 inicios en 1044 fragmentos); ventana 120 m
- T8: velocidad de ápice 210 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T10: casi sin frenada (15 inicios en 1044 fragmentos); ventana 120 m
- T11: casi sin frenada (39 inicios en 1044 fragmentos); ventana 120 m
- T11: velocidad de ápice 206 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T15: casi sin frenada (38 inicios en 1044 fragmentos); ventana 120 m
- T11: quedan 23 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T12: quedan 95 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
