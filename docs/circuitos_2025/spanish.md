# España, Barcelona-Catalunya, 2025

Evento FastF1: `Spanish Grand Prix`.

La numeración de la tabla medida es la de FastF1 (`CornerNumber`). Brembo numera por su lado: una curva que la ficha llama Turn 14 no se identifica acá con ese número de FastF1. La distancia de frenada de Brembo es el largo del tramo en el que el auto desacelera, no los metros desde el inicio hasta el ápice de FastF1, y no se usa para fijar la ventana.

Lo que no tiene fuente queda vacío o marcado como medido con FastF1.

## Documentado

### Largo y frenadas

Fuente: https://www.brembo.com/en/motorsport/formula1/2025/facts-formula1-gp-spagna

Brembo llama al circuito Circuit de Barcelona-Catalunya y le da 4,657 km. Índice 2. Seis frenadas por vuelta, 11,5 s en total: 3 altas, 2 medias y 1 leve.

La curva que Brembo llama Turn 10 baja de 310 km/h a 106 km/h en 2,46 s y 125 m.

### Zonas DRS

Las notas del director de carrera listan paneles de luz, no el metro de detección ni el de activación. No se completa ese metro.

Fuente: https://www.fia.com/system/files/decision-document/2025_spanish_grand_prix_-_race_directors_event_notes_.pdf

- 14) DRS during all free practice sessions and the race
  - DRS activation 1: 10, 11, 12
  - DRS activation 2: 16,1,2
- 15) DRS during qualifying sessions
  - DRS activation 1: 10, 11, 12
  - DRS activation 2: 16,1

### Cambios de trazado 2025

Son los ítems de «Changes to the Circuit» en la misma nota. En esta temporada son cordones, líneas, grava o reasfaltado, no un rediseño del recorrido.

- The guardrail on the RHS approaching Turn 1 was replaced by a concrete wall with debris fences.
- Turn 2 exit: realigned the white line.
- Turn 5 exit: realigned the white line and paint a blue line behind the white line.
- Turn 9 exit: realigned the white line and paint a blue line behind the white line.
- Turn 10 exit: realigned the white line and paint a blue line behind the white line.
- Turn 12 exit: realigned the white line and paint a blue line behind the white line.
- Turn 14: realigned the white line and paint a blue line behind the white line.
- New fences to protect the Marshals Posts

## Medido con FastF1

Carrera 2025, vueltas canónicas, piso de tres vueltas por piloto. La telemetría es el export TracingInsights-Archive/2025 de `Lap.get_telemetry()` y `corners.json` de FastF1, no `get_car_data().add_distance()`. livetiming.formula1.com respondió 401 en el entorno de esta corrida y el mirror de FastF1 respondió 404. La entrada es la velocidad en el último 0→1 dentro de los 800 m previos al ápice, si ese inicio es de esta curva. El ápice es la velocidad mínima en ±60 m. La salida es la velocidad del último sample de los 250 m posteriores al ápice. La marcha es la mediana de la marcha en el mínimo de velocidad. El p50 y el p95 son metros de ese inicio antes del ápice. El cubo usa los cortes del proyecto (125 km/h y 205 km/h) sobre la mediana de ápice: es una estimación de esta carrera, no una clasificación publicada.

Distancia máxima de la vuelta canónica más rápida: 4633,0 m. No es el largo oficial.

| n | ápice (m) | entrada | ápice (km/h) | salida | marcha | p50 (m) | p95 (m) | cubo estimado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 815,6 | 295 | 129 | 211 | 4 | 113 | 146 | cerca del corte; no se fija |
| 2 | 887,2 | 136 | 129 | 205 | 4 | 64 | 69 | cerca del corte; no se fija |
| 3 | 1148,8 | 209 | 204 | 260 | 5 | 88 | 149 | cerca del corte; no se fija |
| 4 | 1727,2 | 270 | 128 | 237 | 4 | 147 | 169 | cerca del corte; no se fija |
| 5 | 2160,8 | 232 | 92 | 251 | 3 | 171 | 188 | lenta |
| 6 | 2337,2 |  | 220 | 161 | 5 |  |  | rápida |
| 7 | 2510,6 | 247 | 133 | 241 | 4 | 85 | 108 | media |
| 8 | 2609,0 | 129 | 139 | 221 | 4 | 84 | 84 | media |
| 9 | 2867,0 | 242 | 218 | 268 | 6 | 86 | 108 | rápida |
| 10 | 3459,3 | 274 | 100 | 131 | 3 | 123 | 152 | lenta |
| 11 | 3611,4 | 107 | 144 | 167 | 3 | 144 | 151 | media |
| 12 | 3736,3 | 192 | 108 | 229 | 4 | 95 | 115 | lenta |
| 13 | 4020,6 | 113 | 226 | 241 | 5 | 280 | 283 | rápida |
| 14 | 4317,0 | 261 | 231 | 275 | 6 | 108 | 136 | rápida |

## Ventanas

Línea de base (YAML de antes de esta propuesta, salvo que el circuito ya tuviera ficha): 43,01 % de inicios en el borde o afuera (58 en el borde, 137 por corte, 4862 heredados, 11758 inicios). Pares solapados: 13. Fusiones: 2. Definición histórica de 350 m: 34,59 %. Definición histórica del pipeline: 3,37 %.

Después de las ventanas de esta ficha: 49,49 % en el borde o afuera (145 en el borde, 812 por corte, 4862 heredados, 11758 inicios). Pares solapados: 7. Fusiones: 0.

| zona | números | frenada (m) | salida (m) |
| --- | --- | ---: | ---: |
| T1_T2 | 1, 2 | 170 | 142 |
| T3 | 3 | 120 | 250 |
| T4 | 4 | 190 | 224 |
| T5 | 5 | 210 | 80 |
| T6 | 6 | 100 | 80 |
| T7_T8 | 7, 8 | 130 | 128 |
| T9 | 9 | 130 | 250 |
| T10 | 10 | 170 | 80 |
| T11 | 11 | 100 | 80 |
| T12 | 12 | 130 | 164 |
| T13 | 13 | 120 | 136 |
| T14 | 14 | 160 | 250 |

Donde la frenada o la salida están vacías, el pipeline usa 350 m y 250 m. El ápice es ±60 m en todos los casos.

La nota dice por qué se movió la ventana. El metro de la tabla es el que queda después de acortar el solape.

Notas de la propuesta, para revisar:

- T1: velocidad de ápice 129 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T3: casi sin frenada (40 inicios en 980 fragmentos); ventana 120 m
- T3: velocidad de ápice 204 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T4: velocidad de ápice 128 km/h, a menos de 8 km/h de un corte; el cubo queda para la sesión
- T6: casi sin frenada (0 inicios en 980 fragmentos); ventana 120 m
- T11: casi sin frenada (34 inicios en 980 fragmentos); ventana 120 m
- T13: casi sin frenada (27 inicios en 980 fragmentos); ventana 120 m
- T6: quedan 4 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T7: quedan 37 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T11: quedan 28 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
- T12: quedan 85 m de solape con la zona anterior después de acortar salida y frenada hasta el piso
