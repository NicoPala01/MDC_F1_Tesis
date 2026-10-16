# San Pablo, Interlagos, 2025

Evento FastF1: `São Paulo Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-san-paolo

Brembo llama al circuito Autódromo José Carlos Pace y le da 4,309 km. Índice 3. El freno se usa menos de 12 s por vuelta. La ficha no da el conteo de frenadas en ese párrafo.

La curva que Brembo llama Turn 1 baja de 325 km/h a 123 km/h en 2,39 s y 126 m.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_sao_paulo_grand_prix_-_race_directors_event_notes_.pdf

- 18. DRS during Free Practice sessions, Qualifying Sessions, Sprint and the Race
  - DRS activation 1: 3, 4, 5
  - DRS activation 2: 15, 16, 1, 2
- 19. DRS during the Sprint Qualifying and Qualifying session
  - DRS activation 1: 3, 4, 5
  - DRS activation 2: 15, 16, 1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- It was removed the hatched zone between pit exit road (RHS) and track edge.
- Resurface from Turn 12 to Turn 1
- Resurface from Turn 3 to Turn 4
- Realign the white line at the exit of Turn 4
- Grooving at Turn 2
- Grooving from pit exit road until Turn 4
- Grooving between in the straight after Turn 5
- Grooving in the straight between Turn 11 and Turn 12
- Grooving from the Start Line until Grid Position 21

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 4231,7 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 364,5 | 298 | 101 | 226 | 3 | 130 | 169 | lenta |
| 2 | 455,8 | 106 | 107 | 250 | 3 | 86 | 92 | lenta |
| 3 | 652,0 | 150 | 222 | 286 | 5 | 191 | 196 | rápida |
| 4 | 1389,8 | 300 | 148 | 246 | 4 | 103 | 145 | media |
| 5 | 1571,6 | 156 | 205 | 277 | 5 | 173 | 180 | cerca del corte; no se fija |
| 6 | 1999,2 | 280 | 206 | 177 | 5 | 70 | 95 | cerca del corte; no se fija |
| 7 | 2140,8 | 208 | 195 | 121 | 5 | 86 | 129 | media |
| 8 | 2298,0 | 208 | 81 | 168 | 3 | 75 | 88 | lenta |
| 9 | 2428,4 | 89 | 100 | 126 | 3 | 110 | 121 | lenta |
| 10 | 2711,9 | 203 | 78 | 222 | 3 | 90 | 108 | lenta |
| 11 | 2924,0 | 84 | 196 | 140 | 4 | 204 | 211 | media |
| 12 | 3213,9 | 249 | 109 | 241 | 3 | 103 | 126 | lenta |
| 13 | 3324,0 | 114 | 140 | 264 | 3 | 103 | 109 | media |
| 14 | 3589,6 |  | 258 | 293 | 6 |  |  | rápida |
| 15 | 3997,7 |  | 301 | 310 | 8 |  |  | rápida |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 57,48 % de inicios en el borde o afuera (11 en el borde, 92 por corte, 7335 heredados, 12940 inicios). Pares solapados: 14. Fusiones: 2. Definición histórica de 350 m: 18,58 %. Definición histórica del pipeline: 19,04 %.

Después de las ventanas de esta ficha: 58,55 % en el borde o afuera (56 en el borde, 186 por corte, 7335 heredados, 12940 inicios). Pares solapados: 7. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_T2 | 1, 2 | 190 | 80 |
| T3 | 3 | 116 | 250 |
| T4 | 4 | 160 | 80 |
| T5 | 5 | 102 | 250 |
| T6 | 6 | 120 | 80 |
| T7 | 7 | 100 | 80 |
| T8 | 8 | 110 | 80 |
| T9 | 9 | 100 | 154 |
| T10 | 10 | 130 | 92 |
| T11 | 11 | 120 | 140 |
| T12_T13 | 12, 13 | 150 | 146 |
| T14 | 14 | 120 | 250 |
| T15 | 15 | 120 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T3: casi sin frenada (24 inicios en 1032 fragmentos); ventana 120 m
- T5: casi sin frenada (16 inicios en 1032 fragmentos); ventana 120 m
- T5: velocidad de ápice 205 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T6: velocidad de ápice 206 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T7: casi sin frenada (38 inicios en 1032 fragmentos); ventana 120 m
- T9: más de la mitad de los inicios caen antes del ápice anterior; la frenada queda en 100 m y el caso sigue pendiente
- T11: casi sin frenada (28 inicios en 1032 fragmentos); ventana 120 m
- T14: casi sin frenada (0 inicios en 1032 fragmentos); ventana 120 m
- T15: casi sin frenada (0 inicios en 1032 fragmentos); ventana 120 m
- T7: quedan 38 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T8: quedan 33 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T9: quedan 50 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
