# Australia, Albert Park, 2025

Evento FastF1: `Australian Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-australia

Brembo llama al circuito Albert Park GP Circuit y le da 5,278 km. Índice de dificultad 3 sobre 5. En una vuelta el freno se usa menos de 8,5 s (11 % de la carrera). Cuenta siete frenadas: 4 altas, 2 medias y 1 leve.

La curva que Brembo llama turn 11 baja de 317 km/h a 133 km/h. El pedal carga 153 kg, la desaceleración es de 4,8 g, el tramo dura 1,8 s y cubre 96 m. La potencia de frenado que publican es 2.508 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_australian_grand_prix_-_race_directors_event_notes_v2.pdf

- 15) DRS during all free practice sessions and the race
  - DRS activation 1: 11, 12, 13, 14
  - DRS activation 2: 15, 16, 17
  - DRS activation 3: 20, 1, 2
  - DRS activation 4: 3, 4, 5
- 16) DRS during qualifying sessions
  - DRS activation 1: 11, 12, 13, 14
  - DRS activation 2: 15, 16, 17
  - DRS activation 3: 20, 1
  - DRS activation 4: 3, 4, 5

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Exit Turn 6/Apex Turn 7: kerb replaced by a negative kerb.
- Gravel was brought back to the kerb at exit Turn 6/apex Turn 7
- Reprofile the barrier at Turn 6 on LHS.
- Repainted pit exit line, highlighted in blue (back to 2018 configuration).
- Exit Turn 4 blue line added behind the white line.
- Reposition of the white line at exit Turn 10 and added a blue line.
- Reposition of the white line at the exit 11 and added a blue line.
- Exit turn 12 added blue line.
- Highlight blue the safety car line 1 and 2.
- Remove the black paint from Turns 10 and 11 and repaint in white color. (the position of the white line stays the same).
- Remove the green concrete patch in the gravel at the apex of Turn 7.
- Blue line added at Turns 3 and 6.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5239,9 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 350,7 | 288 | 127 | 233 | 4 | 129 | 169 | cerca del corte; no se fija |
| 2 | 445,6 | 128 | 131 | 258 | 4 | 86 | 89 | cerca del corte; no se fija |
| 3 | 1082,8 | 277 | 78 | 186 | 3 | 157 | 188 | lenta |
| 4 | 1238,8 | 131 | 119 | 199 | 3 | 67 | 77 | cerca del corte; no se fija |
| 5 | 1427,7 | 206 | 193 | 260 | 5 | 64 | 76 | media |
| 6 | 1870,4 | 260 | 164 | 256 | 5 | 113 | 140 | media |
| 7 | 1974,5 | 170 | 186 | 270 | 5 | 81 | 86 | media |
| 8 | 2163,2 | 226 | 256 | 288 | 6 | 101 | 106 | rápida |
| 9 | 3279,9 | 294 | 178 | 230 | 5 | 106 | 142 | media |
| 10 | 3392,8 | 182 | 179 | 261 | 5 | 70 | 102 | media |
| 11 | 4086,1 | 282 | 90 | 186 | 3 | 129 | 167 | lenta |
| 12 | 4360,8 | 211 | 171 | 79 | 5 | 72 | 95 | media |
| 13 | 4605,3 | 211 | 73 | 190 | 2 | 94 | 116 | lenta |
| 14 | 4767,9 | 132 | 133 | 254 | 4 | 76 | 161 | media |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 36,99 % de inicios en el borde o afuera (0 en el borde, 28 por corte, 2195 heredados, 6009 inicios). Pares solapados: 10. Fusiones: 3. Definición histórica de 350 m: 24,67 %. Definición histórica del pipeline: 0,50 %.

Después de las ventanas de esta ficha: 37,74 % en el borde o afuera (18 en el borde, 55 por corte, 2195 heredados, 6009 inicios). Pares solapados: 5. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_T2 | 1, 2 | 190 | 250 |
| T3 | 3 | 210 | 80 |
| T4 | 4 | 100 | 80 |
| T5 | 5 | 109 | 250 |
| T6_T7 | 6, 7 | 160 | 80 |
| T8 | 8 | 109 | 250 |
| T9_T10 | 9, 10 | 160 | 250 |
| T11 | 11 | 190 | 165 |
| T12 | 12 | 110 | 104 |
| T13 | 13 | 140 | 80 |
| T14 | 14 | 130 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T1: velocidad de ápice 127 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T4: velocidad de ápice 119 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T5: casi sin frenada (24 inicios en 547 fragmentos); ventana 120 m
- T8: casi sin frenada (5 inicios en 547 fragmentos); ventana 120 m
- T14: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 130 m y el caso sigue pendiente
- T4: quedan 24 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T14: quedan 47 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
