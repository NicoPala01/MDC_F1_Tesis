# China, Shanghái, 2025

Evento FastF1: `Chinese Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-cina

Brembo llama al circuito Shanghai International Circuit y le da 5,451 km. Índice 3. Hay tres frenadas altas, separadas por al menos una leve. En una vuelta el freno se usa 16,6 s (18 % de la carrera, en la redacción de la ficha).

La curva que Brembo llama Turn 14 está después de una recta de 1,2 km. El auto llega a 318 km/h y baja a 72 km/h (pierde 246 km/h) en 2,66 s y 113 m. Pedal 174 kg, 4,7 g, potencia 2.450 kW.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_chinese_grand_prix_-_race_directors_event_notes_v3.pdf

- 14) DRS during all free practice session and the race
  - DRS Activation 1: Panels 16, 17
  - DRS Activation 2: Panels 19, 20, 1
- 15) DRS during sprint qualifying and qualifying sessions
  - DRS Activation 1: Panels 16, 17
  - DRS Activation 2: Panels 19, 20

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- The track has been fully resurfaced.
- Combination kerb at Turns 2, 6, 10, 11 and 16 apex.
- Blue line added to turns 6, 9, 10, 14 and 16.
- Reposition the white line at turns 10 and 16.

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 5393,3 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 577,3 | 292 | 176 | 111 | 4 | 108 | 146 | media |
| 2 | 741,6 | 167 | 86 | 163 | 3 | 92 | 134 | lenta |
| 3 | 879,3 | 95 | 86 | 234 | 3 | 117 | 136 | lenta |
| 4 | 1020,6 | 93 | 141 | 268 | 3 | 140 | 142 | media |
| 5 | 1335,5 |  | 270 | 85 | 7 |  |  | rápida |
| 6 | 1571,2 | 268 | 73 | 245 | 3 | 118 | 142 | lenta |
| 7 | 2046,4 | 260 | 242 | 182 | 6 | 134 | 158 | rápida |
| 8 | 2316,9 | 249 | 163 | 133 | 5 | 117 | 138 | media |
| 9 | 2506,1 | 181 | 105 | 236 | 3 | 76 | 94 | lenta |
| 10 | 2620,3 | 111 | 134 | 263 | 4 | 112 | 115 | media |
| 11 | 3100,2 | 262 | 86 | 203 | 3 | 109 | 133 | lenta |
| 12 | 3173,4 | 115 | 100 | 229 | 3 | 61 | 61 | lenta |
| 13 | 3388,4 | 112 | 198 | 274 | 5 | 210 | 215 | cerca del corte; no se fija |
| 14 | 4744,1 | 295 | 60 | 243 | 2 | 143 | 186 | lenta |
| 15 | 4823,3 | 64 | 99 | 180 | 2 | 71 | 71 | lenta |
| 16 | 5110,7 | 243 | 162 | 262 | 4 | 86 | 113 | media |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 42,32 % de inicios en el borde o afuera (63 en el borde, 170 por corte, 4934 heredados, 12209 inicios). Pares solapados: 14. Fusiones: 3. Definición histórica de 350 m: 26,96 %. Definición histórica del pipeline: 11,20 %.

Después de las ventanas de esta ficha: 44,01 % en el borde o afuera (53 en el borde, 386 por corte, 4934 heredados, 12209 inicios). Pares solapados: 8. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1 | 1 | 170 | 80 |
| T2 | 2 | 150 | 80 |
| T3 | 3 | 100 | 80 |
| T4 | 4 | 100 | 195 |
| T5 | 5 | 120 | 80 |
| T6 | 6 | 160 | 250 |
| T7 | 7 | 180 | 111 |
| T8 | 8 | 160 | 80 |
| T9_T10 | 9, 10 | 110 | 250 |
| T11_T12 | 11, 12 | 150 | 95 |
| T13 | 13 | 120 | 250 |
| T14_T15 | 14, 15 | 210 | 157 |
| T16 | 16 | 130 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T3: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 100 m y el caso sigue pendiente
- T4: casi sin frenada (9 inicios en 942 fragmentos); ventana 120 m
- T5: casi sin frenada (0 inicios en 942 fragmentos); ventana 120 m
- T13: casi sin frenada (7 inicios en 942 fragmentos); ventana 120 m
- T13: velocidad de ápice 198 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T2: quedan 66 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T3: quedan 42 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T4: quedan 39 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T6: quedan 4 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
