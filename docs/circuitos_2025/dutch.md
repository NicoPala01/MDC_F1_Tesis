# Países Bajos, Zandvoort, 2025

Evento FastF1: `Dutch Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-dutch

Brembo llama al circuito Zandvoort Circuit y le da 4,259 km. Índice 2. Nueve frenadas: 6 leves, 2 altas y 1 media.

La curva que Brembo llama Turn 1 baja de 315 km/h a 124 km/h en 2,29 s y 119 m.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_dutch_grand_prix_-_race_directors_event_notes_.pdf

- 19. DRS during all Free Practice sessions and the race
  - DRS activation 1: 12, 13, 14
  - DRS activation 2: 16, 17, 18, 1, 2
- 20. DRS during Qualifying:
  - DRS activation 1: 12, 13, 14
  - DRS activation 2: 16, 17, 18, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Reprofile the end of the kerb at the apex of Turn 6.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 4238,8 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 349,1 | 297 | 104 | 235 | 3 | 141 | 177 | lenta |
| 2 | 649,8 | 233 | 172 | 162 | 5 | 66 | 296 | media |
| 3 | 810,4 | 177 | 126 | 242 | 3 | 67 | 79 | cerca del corte; no se fija |
| 4 | 1030,9 | 132 | 213 | 279 | 5 | 215 | 220 | rápida |
| 5 | 1242,7 |  | 272 | 287 | 7 |  |  | rápida |
| 6 | 1384,6 |  | 283 | 237 | 7 |  |  | rápida |
| 7 | 1697,2 | 283 | 223 | 243 | 6 | 156 | 187 | rápida |
| 8 | 2010,3 | 254 | 193 | 104 | 5 | 82 | 101 | media |
| 9 | 2232,3 | 214 | 102 | 113 | 3 | 95 | 112 | lenta |
| 10 | 2497,5 | 183 | 105 | 239 | 3 | 107 | 125 | lenta |
| 11 | 3076,3 | 267 | 95 | 218 | 3 | 106 | 138 | lenta |
| 12 | 3155,6 | 114 | 89 | 221 | 3 | 64 | 75 | lenta |
| 13 | 3468,6 | 233 | 174 | 254 | 5 | 79 | 100 | media |
| 14 | 3747,6 | 184 | 250 | 288 | 6 | 273 | 274 | rápida |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 42,57 % de inicios en el borde o afuera (4 en el borde, 51 por corte, 5452 heredados, 12937 inicios). Pares solapados: 12. Fusiones: 1. Definición histórica de 350 m: 32,71 %. Definición histórica del pipeline: 2,00 %.

Después de las ventanas de esta ficha: 42,79 % en el borde o afuera (17 en el borde, 67 por corte, 5452 heredados, 12937 inicios). Pares solapados: 8. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1 | 1 | 200 | 80 |
| T2 | 2 | 270 | 80 |
| T3 | 3 | 100 | 101 |
| T4 | 4 | 120 | 92 |
| T5 | 5 | 120 | 80 |
| T6 | 6 | 100 | 103 |
| T7 | 7 | 210 | 193 |
| T8 | 8 | 120 | 92 |
| T9 | 9 | 130 | 115 |
| T10 | 10 | 150 | 250 |
| T11_T12 | 11, 12 | 160 | 193 |
| T13 | 13 | 120 | 159 |
| T14 | 14 | 120 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T2: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 270 m y el caso sigue pendiente
- T3: velocidad de ápice 126 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T4: casi sin frenada (26 inicios en 998 fragmentos); ventana 120 m
- T5: casi sin frenada (0 inicios en 998 fragmentos); ventana 120 m
- T6: casi sin frenada (0 inicios en 998 fragmentos); ventana 120 m
- T14: casi sin frenada (5 inicios en 998 fragmentos); ventana 120 m
- T2: quedan 49 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T3: quedan 19 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T6: quedan 38 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
