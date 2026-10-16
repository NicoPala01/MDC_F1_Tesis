# Diagnóstico de ventanas ZOI, 2025 (baseline)

FastF1 3.8.3. Carrera (`R`), vueltas canónicas, piso de 3 vueltas por piloto. La ventana extendida de 800 m solo se usa para encontrar el inicio; no entra al pipeline.

Fuente de la telemetría: export de TracingInsights-Archive/2025, carrera R. Cada archivo `{vuelta}_tel.json` es `Lap.get_telemetry()` de FastF1 (canal del auto fusionado con la posición), no `get_car_data().add_distance()`, que es lo que usa el pipeline. `corners.json` trae la distancia FastF1 de cada número. El filtro replica pick_accurate, pick_wo_box, pick_not_deleted y track status igual a 1. livetiming.formula1.com respondió 401 en este entorno y el mirror de FastF1 respondió 404, así que estas cifras no tienen por qué cerrar al entero con las publicadas para Monza.

Un inicio es la última puesta de freno (0→1) dentro de esos 800 m antes del ápice. Queda **fuera por corte** si ese inicio está antes de la ventana de frenada que el pipeline usa después de `clip_and_merge_zones`, y después del ápice de la zona anterior. Queda **fuera heredado** si cae antes de ese ápice anterior. Queda **en el borde** si está a 5 m o menos del arranque de la ventana. El porcentaje de la tabla suma los tres, sobre los inicios.

La columna histórica es la de `docs/vector_por_zona_monza_2025.md`: el primer sample de la ventana ya tiene el freno puesto. En 350 m es una ventana fija, no la del YAML de cada curva.

| circuito | % borde o fuera | en borde | fuera por corte | fuera heredado | inicios | pares solapados | fusiones | % histórico 350 m | % histórico pipeline |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Abu Dhabi Grand Prix | 57,20 | 79 | 222 | 7456 | 13562 | 14 | 3 | 17,95 | 10,26 |
| Australian Grand Prix | 36,99 | 0 | 28 | 2195 | 6009 | 10 | 3 | 24,67 | 0,50 |
| Austrian Grand Prix | 32,69 | 0 | 15 | 3201 | 9837 | 7 | 0 | 7,35 | 0,21 |
| Azerbaijan Grand Prix | 42,91 | 21 | 85 | 4690 | 11177 | 17 | 5 | 20,11 | 1,68 |
| Bahrain Grand Prix | 32,13 | 47 | 69 | 2556 | 8315 | 12 | 6 | 15,23 | 3,40 |
| Belgian Grand Prix | 45,08 | 6 | 148 | 4129 | 9500 | 16 | 4 | 18,74 | 5,26 |
| British Grand Prix | 24,82 | 0 | 11 | 409 | 1692 | 1 | 0 | 0,00 | 0,00 |
| Canadian Grand Prix | 27,73 | 0 | 17 | 2514 | 9126 | 10 | 6 | 14,01 | 0,15 |
| Chinese Grand Prix | 42,32 | 63 | 170 | 4934 | 12209 | 14 | 3 | 26,96 | 11,20 |
| Dutch Grand Prix | 42,57 | 4 | 51 | 5452 | 12937 | 12 | 1 | 32,71 | 2,00 |
| Emilia Romagna Grand Prix | 60,77 | 23 | 53 | 7784 | 12934 | 18 | 5 | 18,01 | 2,61 |
| Hungarian Grand Prix | 27,88 | 161 | 252 | 4208 | 16575 | 13 | 1 | 26,62 | 4,85 |
| Italian Grand Prix | 16,17 | 0 | 16 | 962 | 6048 | 2 | 0 | 9,84 | 0,16 |
| Japanese Grand Prix | 60,75 | 34 | 188 | 8041 | 13601 | 15 | 2 | 33,32 | 18,57 |
| Las Vegas Grand Prix | 43,83 | 49 | 172 | 3454 | 8384 | 13 | 5 | 26,65 | 6,05 |
| Mexico City Grand Prix | 28,58 | 0 | 38 | 2167 | 7714 | 15 | 10 | 21,33 | 0,36 |
| Miami Grand Prix | 67,19 | 49 | 119 | 6575 | 10035 | 17 | 6 | 20,86 | 33,46 |
| Monaco Grand Prix | 4,33 | 0 | 201 | 1 | 4660 | 1 | 0 | 26,80 | 9,39 |
| Qatar Grand Prix | 40,85 | 1 | 12 | 4751 | 11662 | 15 | 1 | 13,98 | 0,51 |
| Saudi Arabian Grand Prix | 65,82 | 19 | 72 | 8202 | 12599 | 26 | 9 | 20,18 | 2,56 |
| Singapore Grand Prix | 30,29 | 13 | 27 | 4645 | 15469 | 19 | 5 | 23,23 | 0,89 |
| Spanish Grand Prix | 43,01 | 58 | 137 | 4862 | 11758 | 13 | 2 | 34,59 | 3,37 |
| São Paulo Grand Prix | 57,48 | 11 | 92 | 7335 | 12940 | 14 | 2 | 18,58 | 19,04 |
| United States Grand Prix | 43,76 | 5 | 59 | 6039 | 13946 | 18 | 4 | 41,03 | 0,91 |

## Monza, cifras publicadas

Las cifras publicadas y esta corrida **no coinciden**.

Publicado, ventana de 350 m: 261/5114 (5,10 %). Medido: 506/5141 (9,84 %).
Publicado, Lesmo 2 en 350 m: 250/811. Medido: 480/838.
Publicado, ventanas del pipeline: 13/5074 (0,26 %). Medido: 8/5074 (0,16 %).

