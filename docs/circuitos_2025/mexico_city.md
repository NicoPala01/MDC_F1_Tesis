# Ciudad de México, 2025

Evento FastF1: `Mexico City Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-messico

Brembo llama al circuito Autódromo Hermanos Rodríguez y le da 4.304 m. Índice 4. La ficha lo atribuye a la altura y a la menor refrigeración, y no publica en ese párrafo el conteo de frenadas.

La curva que Brembo llama Turn 1 baja de 342 km/h a 112 km/h en 2,68 s y 141 m.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_mexico_city_grand_prix_-_race_directors_event_notes_v3.pdf

- 17. DRS during Free Practice sessions, Qualifying Sessions and the Race
  - DRS activation 1: 11, 12, 13
  - DRS activation 2: 1, 2, 3
  - DRS activation 3: 4, 5, 6

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Asphalt grinding at Turn 12 near the 150 meters brake marker.
- Blue line behind the white line added at the turns: 3 apex, 5 apex and exit, 6 apex and exit, 9 apex.
- Double the white line at the apex of Turn 2
- The bollard at the apex of Turn 2 was moved closer to the track.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 4239,7 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 1192,5 | 309 | 94 | 194 | 3 | 141 | 180 | lenta |
| 2 | 1263,2 | 98 | 93 | 229 | 3 | 68 | 71 | lenta |
| 3 | 1323,2 | 101 | 96 | 250 | 3 | 60 | 61 | lenta |
| 4 | 2016,9 | 283 | 76 | 92 | 2 | 126 | 159 | lenta |
| 5 | 2090,2 | 86 | 67 | 171 | 2 | 70 | 74 | lenta |
| 6 | 2226,0 | 144 | 74 | 236 | 3 | 64 | 76 | lenta |
| 7 | 2544,9 | 236 | 163 | 214 | 5 | 66 | 308 | media |
| 8 | 2664,5 | 169 | 172 | 171 | 5 | 101 | 107 | media |
| 9 | 2744,0 | 200 | 204 | 171 | 5 | 73 | 76 | cerca del corte; no se fija |
| 10 | 2927,1 | 223 | 156 | 248 | 4 | 71 | 86 | media |
| 11 | 3020,6 | 158 | 159 | 270 | 4 | 85 | 91 | media |
| 12 | 3585,7 | 281 | 123 | 103 | 4 | 111 | 137 | cerca del corte; no se fija |
| 13 | 3756,6 | 173 | 61 | 127 | 2 | 68 | 82 | lenta |
| 14 | 3817,7 | 67 | 61 | 181 | 2 | 61 | 61 | lenta |
| 15 | 3868,7 |  | 94 | 209 | 2 |  |  | lenta |
| 16 | 3937,9 | 146 | 93 | 236 | 3 | 63 | 68 | lenta |
| 17 | 4045,6 | 98 | 114 | 265 | 3 | 100 | 108 | lenta |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 28,58 % de inicios en el borde o afuera (0 en el borde, 38 por corte, 2167 heredados, 7714 inicios). Pares solapados: 15. Fusiones: 10. Definición histórica de 350 m: 21,33 %. Definición histórica del pipeline: 0,36 %.

Después de las ventanas de esta ficha: 29,27 % en el borde o afuera (17 en el borde, 74 por corte, 2167 heredados, 7714 inicios). Pares solapados: 4. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_T2_T3 | 1, 2, 3 | 200 | 250 |
| T4_T5 | 4, 5 | 180 | 80 |
| T6 | 6 | 100 | 80 |
| T7_T8_T9 | 7, 8, 9 | 280 | 80 |
| T10_T11 | 10, 11 | 110 | 250 |
| T12 | 12 | 160 | 80 |
| T13_T14_T15_T16_T17 | 13, 14, 15, 16, 17 | 100 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T6: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 100 m y el caso sigue pendiente
- T7: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 280 m y el caso sigue pendiente
- T12: velocidad de ápice 123 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T6: quedan 44 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T7: quedan 41 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T10: quedan 7 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T13: quedan 9 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
