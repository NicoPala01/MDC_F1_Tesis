# Mónaco, 2025

Evento FastF1: `Monaco Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-monaco

Brembo llama al circuito Circuit de Monaco y le da 3,337 km. Índice 3. Quince frenadas por vuelta: 2 altas, 6 medias y 7 leves. El freno se usa 19 s, el 27 % del tiempo de vuelta.

La curva que Brembo llama Turn 10, la chicana después del túnel, baja de 290 km/h a 96 km/h en 2,06 s y 91 m.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_monaco_grand_prix_-_race_directors_event_notes_v2.pdf

- 18) DRS during all free practice sessions and the race
  - DRS activation 1: 18, 19, 1, 2
- 19) DRS during qualifying sessions
  - DRS activation 1: 18, 19, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Resurfacing between Turn 12 until Turn 3.
- Turn 1: painted flat section of the kerb behind temporary kerb at apex T1 omitted.
- Realign guardrail on the LHS of Turn 3
- Turn 4: painted flat section of kerb omitted.
- Turn 10/11: painted flat section of kerb before temporary kerb at apex T10 omitted.
- Painted flat section of kerb from T10 apex kerb to T11 apex kerb omitted.
- Turn 12: painted flat section of kerb at apex T12 omitted.
- Turn 13: painted flat section of kerb before T13 apex temporary kerb omitted.
- Turn 14: painted flat section of kerb before and after T14 apex temporary kerb omitted.
- Turn 15: painted flat section of kerb at Apex T15 omitted.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 3284,2 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 186,5 | 262 | 106 | 241 | 3 | 98 | 129 | lenta |
| 2 | 581,7 | 180 | 237 | 155 | 7 | 271 | 393 | rápida |
| 3 | 744,1 | 254 | 149 | 200 | 4 | 129 | 158 | media |
| 4 | 873,2 | 155 | 128 | 78 | 4 | 62 | 125 | cerca del corte; no se fija |
| 5 | 1102,8 | 202 | 72 | 111 | 2 | 86 | 104 | lenta |
| 6 | 1222,9 | 128 | 44 | 159 | 1 | 65 | 120 | lenta |
| 7 | 1304,2 | 52 | 53 | 213 | 1 | 79 | 82 | lenta |
| 8 | 1389,7 | 85 | 78 | 244 | 2 | 69 | 82 | lenta |
| 9 | 1714,8 | 82 | 250 | 247 | 6 | 320 | 324 | rápida |
| 10 | 2047,8 | 268 | 62 | 184 | 2 | 106 | 142 | lenta |
| 11 | 2103,4 |  | 62 | 156 | 2 |  |  | lenta |
| 12 | 2326,7 | 216 | 153 | 219 | 4 | 67 | 84 | media |
| 13 | 2486,3 | 158 | 204 | 155 | 5 | 135 | 144 | cerca del corte; no se fija |
| 14 | 2524,9 |  | 208 | 183 | 5 |  |  | cerca del corte; no se fija |
| 15 | 2647,1 | 218 | 112 | 83 | 3 | 73 | 96 | lenta |
| 16 | 2679,1 |  | 112 | 99 | 3 |  |  | lenta |
| 17 | 2740,8 | 112 | 113 | 116 | 3 | 61 | 62 | lenta |
| 18 | 2861,0 | 184 | 59 | 215 | 2 | 73 | 91 | lenta |
| 19 | 2950,0 | 64 | 75 | 246 | 2 | 83 | 89 | lenta |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 4,33 % de inicios en el borde o afuera (0 en el borde, 201 por corte, 1 heredados, 4660 inicios). Pares solapados: 1. Fusiones: 0. Definición histórica de 350 m: 26,80 %. Definición histórica del pipeline: 9,39 %.

Después de las ventanas de esta ficha: 4,33 % en el borde o afuera (0 en el borde, 201 por corte, 1 heredados, 4660 inicios). Pares solapados: 1. Fusiones: 0.

Monza, Silverstone y Mónaco no se reescribieron. La tabla de abajo es la que ya estaba.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_Sainte_Devote | 1 |  |  |
| T6_Grand_Hotel_Hairpin | 6 |  |  |
| T10_Nouvelle_Chicane | 10, 11 |  |  |
| T15_Swimming_Pool | 15, 16 |  |  |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.
