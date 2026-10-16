# Gran Bretaña, Silverstone, 2025

Evento FastF1: `British Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-uk

Brembo llama al circuito Silverstone Circuit y le da 5,891 km. Índice 1. Ocho frenadas por vuelta, 11 s en total.

La curva que Brembo llama Turn 3 baja de 295 km/h a 130 km/h en 2,33 s y 115 m.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_british_grand_prix_-_race_directors_event_notes_v2.pdf

- 16. DRS during all free practice sessions, qualifying and the race
  - DRS activation 1: 5, 6, 7
  - DRS activation 2: 13, 14, 15

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Removed the kerb at Turn 1 runoff on the left-hand side.
- The gravel in the gravel trap at the exit of T18 has been changed to a lighter material.
- 1 red kerb element in Turn 1 (apex) replaced by a flat kerb element.
- 2 red kerb elements in Turn 6 (apex) replaced by a flat kerb element.
- 1 red kerb element in Turn 7 (apex) replaced by a flat kerb element.
- 3 red kerbs elements in Turn 9 (apex) replaced by a flat kerb element.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5819,1 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 444,9 | 285 | 250 | 270 | 7 | 118 | 148 | rápida |
| 2 | 604,4 | 209 | 263 | 131 | 7 | 160 | 160 | rápida |
| 3 | 866,0 | 264 | 87 | 132 | 3 | 106 | 130 | lenta |
| 4 | 1029,4 | 124 | 69 | 230 | 3 | 65 | 146 | lenta |
| 5 | 1230,3 | 74 | 188 | 275 | 4 | 199 | 201 | media |
| 6 | 1953,9 | 289 | 121 | 98 | 4 | 132 | 166 | cerca del corte; no se fija |
| 7 | 2175,7 | 144 | 86 | 234 | 3 | 102 | 120 | lenta |
| 8 | 2530,5 | 134 | 250 | 293 | 6 | 255 | 347 | rápida |
| 9 | 3042,4 | 294 | 214 | 264 | 6 | 105 | 151 | rápida |
| 10 | 3604,6 | 218 | 276 | 208 | 7 | 549 | 557 | rápida |
| 11 | 3690,2 | 295 | 246 | 181 | 6 | 73 | 84 | rápida |
| 12 | 3847,8 | 250 | 191 | 192 | 5 | 74 | 93 | media |
| 13 | 3974,9 | 199 | 151 | 245 | 4 | 72 | 91 | media |
| 14 | 4126,8 | 155 | 179 | 278 | 4 | 145 | 151 | media |
| 15 | 4984,1 | 301 | 168 | 239 | 5 | 121 | 166 | media |
| 16 | 5431,6 | 256 | 87 | 173 | 3 | 81 | 114 | lenta |
| 17 | 5523,1 | 89 | 81 | 209 | 3 | 66 | 66 | lenta |
| 18 | 5676,1 | 96 | 135 | 263 | 3 | 134 | 150 | media |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 24,82 % de inicios en el borde o afuera (0 en el borde, 11 por corte, 409 heredados, 1692 inicios). Pares solapados: 1. Fusiones: 0. Definición histórica de 350 m: 0,00 %. Definición histórica del pipeline: 0,00 %.

Después de las ventanas de esta ficha: 24,82 % en el borde o afuera (0 en el borde, 11 por corte, 409 heredados, 1692 inicios). Pares solapados: 1. Fusiones: 0.

Monza, Silverstone y Mónaco no se reescribieron. La tabla de abajo es la que ya estaba.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T3_Village_The_Loop | 3, 4 |  |  |
| T9_Copse | 9 |  |  |
| Maggotts_Becketts_Chapel | 10, 11, 12, 13, 14 |  |  |
| T16_Stowe | 15 |  |  |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.
