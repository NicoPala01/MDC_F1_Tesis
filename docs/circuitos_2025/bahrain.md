# Baréin, Sakhir, 2025

Evento FastF1: `Bahrain Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-bahrein

Brembo llama al circuito Bahrain International Circuit y le da 5,412 km. Índice 4. En una vuelta el freno se usa 15,8 s (18 % de la carrera). En cinco curvas la desaceleración es de al menos 4,1 g y el freno dura más de 2 s. Cuenta 4 frenadas altas, 3 medias y 1 leve.

La primera curva, después de una recta de 1,1 km, llega a 313 km/h y baja a 66 km/h en 2,89 s y 124 m, con 4,2 g, 133 kg y 2.112 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_bahrain_grand_prix_-_race_directors_event_notes_v2.pdf

- 15) DRS during all free practice sessions and the race
  - DRS activation 1: 3, 4
  - DRS activation 2: 11, 12
  - DRS activation 3: 18, 1, 2
- 16) DRS during qualifying sessions
  - DRS activation 1: 3, 4
  - DRS activation 2: 11, 12
  - DRS activation 3: 18, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Exit turn 4 gravel bed has been extended.
- U-drains close to the racing line were closed off by cement and moved away from the white line into the runoff areas.
- Repair of the bumps at the start line straight and turn 9.
- Remove the kerb at turn 3 RHS (another version of the track).
- Replace the glasses at the start and finish platforms.
- Blue line added behind the white line at the entrance of turns 4 and 6.
- Blue line added behind the white line at the exit of turns 2, 4, 10, 11, 13, 14 and 15.
- Widened the white line at the exit of turn 4 and repositioned the blue line behind the white line.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5376,5 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 710,5 | 290 | 58 | 221 | 2 | 128 | 164 | lenta |
| 2 | 813,5 | 65 | 93 | 253 | 2 | 97 | 103 | lenta |
| 3 | 921,3 |  | 176 | 273 | 4 |  |  | media |
| 4 | 1509,1 | 276 | 106 | 235 | 4 | 134 | 164 | lenta |
| 5 | 1780,8 | 160 | 184 | 209 | 5 | 173 | 267 | media |
| 6 | 1881,1 | 229 | 172 | 197 | 5 | 93 | 100 | media |
| 7 | 1966,8 |  | 183 | 74 | 5 |  |  | media |
| 8 | 2214,4 | 225 | 69 | 232 | 3 | 107 | 126 | lenta |
| 9 | 2592,4 | 243 | 103 | 203 | 3 | 68 | 204 | lenta |
| 10 | 2682,9 | 177 | 68 | 242 | 2 | 77 | 86 | lenta |
| 11 | 3450,6 | 284 | 135 | 244 | 4 | 167 | 200 | media |
| 12 | 3863,1 | 248 | 240 | 135 | 6 | 124 | 193 | rápida |
| 13 | 4071,5 | 245 | 119 | 246 | 4 | 130 | 155 | cerca del corte; no se fija |
| 14 | 4879,7 | 280 | 114 | 248 | 3 | 136 | 167 | lenta |
| 15 | 4967,1 |  | 134 | 266 | 4 |  |  | media |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 32,13 % de inicios en el borde o afuera (47 en el borde, 69 por corte, 2556 heredados, 8315 inicios). Pares solapados: 12. Fusiones: 6. Definición histórica de 350 m: 15,23 %. Definición histórica del pipeline: 3,40 %.

Después de las ventanas de esta ficha: 32,70 % en el borde o afuera (71 en el borde, 92 por corte, 2556 heredados, 8315 inicios). Pares solapados: 4. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_T2_T3 | 1, 2, 3 | 180 | 250 |
| T4 | 4 | 180 | 152 |
| T5_T6_T7 | 5, 6, 7 | 120 | 98 |
| T8 | 8 | 150 | 158 |
| T9_T10 | 9, 10 | 220 | 250 |
| T11 | 11 | 220 | 203 |
| T12 | 12 | 210 | 80 |
| T13 | 13 | 180 | 250 |
| T14_T15 | 14, 15 | 190 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T5: casi sin frenada (4 inicios en 924 fragmentos); ventana 120 m
- T13: velocidad de ápice 119 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T13: quedan 52 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
