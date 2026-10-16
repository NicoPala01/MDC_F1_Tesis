# Canadá, Gilles Villeneuve, 2025

Evento FastF1: `Canadian Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-canada

Brembo llama al circuito Circuit Gilles-Villeneuve y le da 4,361 km. Índice 4. Seis frenadas altas y dos leves. Cinco piden más de 80 m y en cuatro la desaceleración es de al menos 5 g. El freno se usa poco menos de 12,5 s por vuelta.

La curva que Brembo llama Turn 10 baja de 292 km/h a 69 km/h en 2,82 s y 107 m.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_canadian_grand_prix_-_race_directors_event_notes_v2.pdf

- 15. DRS during all free practice sessions and the race
  - DRS activation 1: 7, 8, 9
  - DRS activation 2: 12,13,14
  - DRS activation 3: 15,1
- 16. DRS during qualifying sessions
  - DRS activation 1: 7, 8, 9
  - DRS activation 2: 12,13, 14
  - DRS activation 3: 15

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Improvement to the drainage at turns 2, 8, 10 and 13 (by making small cuts in the kerbs).
- Track surface grinded to remove bump at T12 (area prior to DRS Line).
- Run-off behind Turn 8 and Turn 9 apex was regraded and a paved path was created.
- Realignment of the width of the white line at Turn 4 and Turn 8 with 1,8 meters to the wall.
- Concrete wall at Turn 10 RHS was extended.
- Realignment of the width of the white line at Turn 14 with 1,8 meters to the wall and add a blue line.
- Black the end of the orange paint at the rejoin of the runoff area of Turn 13

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 4298,3 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 222,1 | 278 | 108 | 201 | 3 | 89 | 131 | lenta |
| 2 | 323,9 | 129 | 72 | 239 | 2 | 64 | 75 | lenta |
| 3 | 694,5 | 238 | 130 | 241 | 4 | 79 | 100 | cerca del corte; no se fija |
| 4 | 771,5 | 128 | 131 | 249 | 4 | 65 | 71 | cerca del corte; no se fija |
| 5 | 976,9 | 210 | 237 | 99 | 6 | 117 | 117 | rápida |
| 6 | 1201,4 | 250 | 96 | 226 | 3 | 80 | 99 | lenta |
| 7 | 1279,0 | 108 | 96 | 252 | 3 | 65 | 76 | lenta |
| 8 | 1987,9 | 281 | 121 | 249 | 4 | 121 | 156 | cerca del corte; no se fija |
| 9 | 2063,4 | 140 | 137 | 265 | 4 | 62 | 62 | media |
| 10 | 2648,0 | 271 | 57 | 239 | 2 | 111 | 140 | lenta |
| 11 | 2761,5 | 61 | 113 | 267 | 2 | 104 | 112 | lenta |
| 12 | 3133,3 | 226 | 281 | 305 | 7 | 229 | 361 | rápida |
| 13 | 3823,8 | 296 | 123 | 240 | 4 | 90 | 147 | cerca del corte; no se fija |
| 14 | 3849,1 |  | 123 | 248 | 4 |  |  | cerca del corte; no se fija |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 27,73 % de inicios en el borde o afuera (0 en el borde, 17 por corte, 2514 heredados, 9126 inicios). Pares solapados: 10. Fusiones: 6. Definición histórica de 350 m: 14,01 %. Definición histórica del pipeline: 0,15 %.

Después de las ventanas de esta ficha: 28,58 % en el borde o afuera (21 en el borde, 73 por corte, 2514 heredados, 9126 inicios). Pares solapados: 1. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_T2 | 1, 2 | 150 | 250 |
| T3_T4 | 3, 4 | 120 | 85 |
| T5 | 5 | 120 | 105 |
| T6_T7 | 6, 7 | 120 | 250 |
| T8_T9 | 8, 9 | 180 | 250 |
| T10_T11 | 10, 11 | 160 | 250 |
| T12 | 12 | 120 | 250 |
| T13_T14 | 13, 14 | 170 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T3: velocidad de ápice 130 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T5: casi sin frenada (1 inicios en 1154 fragmentos); ventana 120 m
- T8: velocidad de ápice 121 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T12: casi sin frenada (34 inicios en 1154 fragmentos); ventana 120 m
- T13: velocidad de ápice 123 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
