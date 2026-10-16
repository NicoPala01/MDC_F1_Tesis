# Austria, Red Bull Ring, 2025

Evento FastF1: `Austrian Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-austria

Brembo llama al circuito Red Bull Ring y le da 4,318 km. Índice 3. Seis frenadas por vuelta y una carga total de pedal de poco menos de 650 kg.

La curva que Brembo llama Turn 3 baja de 306 km/h a 78 km/h en 2,58 s y 112 m, con 4,6 g, 142 kg y 2.355 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_austrian_grand_prix_-_race_directors_event_notes_v2.pdf

- 14. DRS during all free practice sessions and the race
  - DRS activation 1: 3, 4, 5, 6
  - DRS activation 2: 7, 8, 9
  - DRS activation 3: 16,1, 2
- 15. DRS during qualifying sessions
  - DRS activation 1: 3, 4, 5, 6
  - DRS activation 2: 7, 8, 9
  - DRS activation 3: 16, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Resurface from Turn 2 to exit Turn 3
- Turn 1 exit: realigned the white line and added a blue line behind the white line.
- Turn 3 exit: realigned the white line and added a blue line behind the white line.
- Turn 4 exit: realigned the white line and added a blue line behind the white line.
- Turn 6 exit: realigned the white line and added a blue line behind the white line.
- Turn 7 entry: realigned the white line and added a blue line behind the white line.
- Turn 8 exit: realigned the white line and added a blue line behind the white line.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 4294,9 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 423,0 | 286 | 122 | 248 | 4 | 101 | 125 | cerca del corte; no se fija |
| 2 | 1068,1 | 126 | 299 | 151 | 8 | 640 | 645 | rápida |
| 3 | 1361,3 | 281 | 66 | 242 | 2 | 115 | 145 | lenta |
| 4 | 2180,8 | 282 | 96 | 243 | 3 | 131 | 163 | lenta |
| 5 | 2358,4 | 99 | 192 | 227 | 4 | 167 | 172 | media |
| 6 | 2697,7 | 257 | 166 | 217 | 5 | 124 | 149 | media |
| 7 | 3018,0 | 232 | 190 | 259 | 5 | 101 | 124 | media |
| 8 | 3214,7 | 228 | 235 | 286 | 6 | 79 | 79 | rápida |
| 9 | 3751,8 | 284 | 216 | 174 | 6 | 101 | 132 | rápida |
| 10 | 3942,5 | 233 | 163 | 257 | 4 | 72 | 92 | media |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 32,69 % de inicios en el borde o afuera (0 en el borde, 15 por corte, 3201 heredados, 9837 inicios). Pares solapados: 7. Fusiones: 0. Definición histórica de 350 m: 7,35 %. Definición histórica del pipeline: 0,21 %.

Después de las ventanas de esta ficha: 33,26 % en el borde o afuera (24 en el borde, 47 por corte, 3201 heredados, 9837 inicios). Pares solapados: 3. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1 | 1 | 150 | 250 |
| T2 | 2 | 120 | 123 |
| T3 | 3 | 170 | 250 |
| T4 | 4 | 180 | 80 |
| T5 | 5 | 100 | 169 |
| T6 | 6 | 170 | 180 |
| T7 | 7 | 140 | 80 |
| T8 | 8 | 117 | 250 |
| T9 | 9 | 150 | 81 |
| T10 | 10 | 110 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T1: velocidad de ápice 122 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T2: casi sin frenada (6 inicios en 984 fragmentos); ventana 120 m
- T5: casi sin frenada (5 inicios en 984 fragmentos); ventana 120 m
- T8: casi sin frenada (1 inicios en 984 fragmentos); ventana 120 m
- T5: quedan 2 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
