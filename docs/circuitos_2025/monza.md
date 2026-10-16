# Italia, Monza, 2025

Evento FastF1: `Italian Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-monza

Brembo llama al circuito Autodromo Nazionale Monza y le da 5.793 m. Índice 5. Siete frenadas por vuelta, cinco de ellas altas.

La curva que Brembo llama Turn 1 (Rettifilo) baja de 337 km/h a 89 km/h en 2,75 s y 129 m.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_italian_grand_prix_-_race_directors_event_notes_.pdf

- 18. DRS during all Free Practice sessions and the race
  - DRS activation 1: 9, 10, 11, 12, 13
  - DRS activation 2: 1, 2, 3

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- New gate in the pit wall in front of garage 32.
- Asphalt repair by application of bitumen coating at Turn 1 and Turn 4.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5739,5 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 878,8 | 315 | 73 | 223 | 2 | 109 | 160 | lenta |
| 2 | 940,3 |  | 69 | 247 | 2 |  |  | lenta |
| 3 | 1463,0 | 76 | 293 | 316 | 7 | 521 | 523 | rápida |
| 4 | 2095,2 | 301 | 101 | 235 | 3 | 108 | 145 | lenta |
| 5 | 2151,7 |  | 101 | 245 | 3 |  |  | lenta |
| 6 | 2506,2 | 243 | 184 | 246 | 5 | 89 | 110 | media |
| 7 | 2831,7 | 243 | 170 | 265 | 5 | 75 | 92 | media |
| 8 | 3889,4 | 307 | 173 | 251 | 5 | 88 | 136 | media |
| 9 | 3987,2 | 167 | 178 | 273 | 5 | 74 | 96 | media |
| 10 | 4095,6 | 205 | 225 | 292 | 5 | 97 | 103 | rápida |
| 11 | 5185,1 | 306 | 189 | 274 | 5 | 191 | 225 | media |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 16,17 % de inicios en el borde o afuera (0 en el borde, 16 por corte, 962 heredados, 6048 inicios). Pares solapados: 2. Fusiones: 0. Definición histórica de 350 m: 9,84 %. Definición histórica del pipeline: 0,16 %.

Después de las ventanas de esta ficha: 16,17 % en el borde o afuera (0 en el borde, 16 por corte, 962 heredados, 6048 inicios). Pares solapados: 2. Fusiones: 0.

Monza, Silverstone y Mónaco no se reescribieron. La tabla de abajo es la que ya estaba.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_Variante_del_Rettifilo | 1, 2 | 350 | 250 |
| T3_Curva_Grande | 3 | 180 | 200 |
| T4_Variante_della_Roggia | 4, 5 | 300 | 250 |
| T6_Curva_di_Lesmo | 6 | 220 |  |
| T7_Seconda_di_Lesmo | 7 | 200 |  |
| T8_Variante_Ascari | 8, 9, 10 | 280 | 260 |
| T11_Curva_Parabolica_Alboreto | 11 | 320 | 300 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.
