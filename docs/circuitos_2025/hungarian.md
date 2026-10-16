# Hungría, Hungaroring, 2025

Evento FastF1: `Hungarian Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-hungary

Brembo llama al circuito Hungaroring y le da 4,381 km. Índice 3. El freno está activo el 20 % de la vuelta. Diez frenadas: 2 altas, 4 medias y 4 leves.

La curva que Brembo llama Turn 1 es la única donde el auto pasa de 300 km/h: llega a 307 km/h y baja a 95 km/h en 2,65 s y 122 m, con 4,4 g, 156 kg y 2.243 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_hungarian_grand_prix_-_race_directors_event_notes_v2.pdf

- 18. DRS during all Free Practice sessions and the race
  - DRS activation 1: 19, 1, 2, 3
  - DRS activation 2: 3, 4, 5
- 19. DRS during Qualifying:
  - DRS activation 1: 19, 1, 2
  - DRS activation 2: 3, 4, 5

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- Resurfaced the main straight
- Changed the grass strip exit turn 5 to a gravel strip.
- New concrete blocks with fences at Turn 14 LHS until the bridge
- Resurfaced the pit lane
- Alignment of the white line and added a blue line at the exit of Turn 7

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 4354,8 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 626,1 | 86 | 120 | 211 | 3 | 189 | 192 | cerca del corte; no se fija |
| 1 | 819,9 | 86 | 120 | 211 | 3 | 189 | 192 | cerca del corte; no se fija |
| 2 | 1130,5 | 258 | 111 | 233 | 3 | 120 | 145 | lenta |
| 3 | 1313,0 | 117 | 190 | 271 | 4 | 176 | 182 | media |
| 4 | 1799,5 | 276 | 218 | 141 | 6 | 74 | 99 | rápida |
| 5 | 2028,7 | 234 | 138 | 231 | 4 | 90 | 110 | media |
| 6 | 2365,2 | 227 | 99 | 159 | 3 | 83 | 104 | lenta |
| 7 | 2411,7 |  | 100 | 165 | 3 |  |  | lenta |
| 8 | 2580,2 | 198 | 156 | 206 | 4 | 66 | 85 | media |
| 9 | 2718,3 | 170 | 142 | 246 | 4 | 72 | 87 | media |
| 10 | 2923,8 |  | 224 | 227 | 5 |  |  | rápida |
| 11 | 3118,8 | 249 | 211 | 268 | 6 | 104 | 126 | cerca del corte; no se fija |
| 12 | 3506,4 | 109 | 118 | 136 | 3 | 117 | 117 | cerca del corte; no se fija |
| 12 | 3641,1 | 109 | 118 | 136 | 3 | 117 | 117 | cerca del corte; no se fija |
| 13 | 3775,0 | 206 | 95 | 140 | 3 | 103 | 124 | lenta |
| 14 | 4066,6 | 200 | 128 | 249 | 4 | 125 | 147 | cerca del corte; no se fija |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 27,88 % de inicios en el borde o afuera (161 en el borde, 252 por corte, 4208 heredados, 16575 inicios). Pares solapados: 13. Fusiones: 1. Definición histórica de 350 m: 26,62 %. Definición histórica del pipeline: 4,85 %.

Después de las ventanas de esta ficha: 27,88 % en el borde o afuera (161 en el borde, 252 por corte, 4208 heredados, 16575 inicios). Pares solapados: 13. Fusiones: 1.

Este circuito sigue en el fallback de 350 m, ±60 m y 250 m. No entró a `key_corners`.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- FastF1 repite el Number 1, 12. `key_corners` se queda con la primera distancia y el fallback pisa `Turn_N` y se queda con la última. No se escribe ficha para no mover el ápice sin cambiar el algoritmo.
