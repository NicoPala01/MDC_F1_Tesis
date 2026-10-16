# Diagnóstico de ventanas ZOI, 2025 (despues)

FastF1 3.8.3. Carrera (`R`), vueltas canónicas, piso de 3 vueltas por piloto. La ventana extendida de 800 m solo se usa para encontrar el inicio; no entra al pipeline.

Fuente de la telemetría: export de TracingInsights-Archive/2025, carrera R. Cada archivo `{vuelta}_tel.json` es `Lap.get_telemetry()` de FastF1 (canal del auto fusionado con la posición), no `get_car_data().add_distance()`, que es lo que usa el pipeline. `corners.json` trae la distancia FastF1 de cada número. El filtro replica pick_accurate, pick_wo_box, pick_not_deleted y track status igual a 1. livetiming.formula1.com respondió 401 en este entorno y el mirror de FastF1 respondió 404, así que estas cifras no tienen por qué cerrar al entero con las publicadas para Monza.

Un inicio es la última puesta de freno (0→1) dentro de esos 800 m antes del ápice. Queda **fuera por corte** si ese inicio está antes de la ventana de frenada que el pipeline usa después de `clip_and_merge_zones`, y después del ápice de la zona anterior. Queda **fuera heredado** si cae antes de ese ápice anterior. Queda **en el borde** si está a 5 m o menos del arranque de la ventana. El porcentaje de la tabla suma los tres, sobre los inicios.

La columna histórica es la de `docs/vector_por_zona_monza_2025.md`: el primer sample de la ventana ya tiene el freno puesto. En 350 m es una ventana fija, no la del YAML de cada curva.

| circuito | % borde o fuera | en borde | fuera por corte | fuera heredado | inicios | pares solapados | fusiones | % histórico 350 m | % histórico pipeline |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Abu Dhabi Grand Prix | 60,82 | 113 | 679 | 7456 | 13562 | 8 | 0 | 17,95 | 17,75 |
| Australian Grand Prix | 37,74 | 18 | 55 | 2195 | 6009 | 5 | 0 | 24,67 | 3,08 |
| Austrian Grand Prix | 33,26 | 24 | 47 | 3201 | 9837 | 3 | 0 | 7,35 | 2,49 |
| Azerbaijan Grand Prix | 43,63 | 40 | 147 | 4690 | 11177 | 7 | 0 | 20,11 | 3,75 |
| Bahrain Grand Prix | 32,70 | 71 | 92 | 2556 | 8315 | 4 | 0 | 15,23 | 5,54 |
| Belgian Grand Prix | 45,56 | 22 | 177 | 4129 | 9500 | 9 | 0 | 18,74 | 3,35 |
| British Grand Prix | 24,82 | 0 | 11 | 409 | 1692 | 1 | 0 | 0,00 | 0,00 |
| Canadian Grand Prix | 28,58 | 21 | 73 | 2514 | 9126 | 1 | 0 | 14,01 | 2,51 |
| Chinese Grand Prix | 44,01 | 53 | 386 | 4934 | 12209 | 8 | 0 | 26,96 | 11,44 |
| Dutch Grand Prix | 42,79 | 17 | 67 | 5452 | 12937 | 8 | 0 | 32,71 | 1,50 |
| Emilia Romagna Grand Prix | 62,10 | 100 | 148 | 7784 | 12934 | 6 | 0 | 18,01 | 7,90 |
| Hungarian Grand Prix | 27,88 | 161 | 252 | 4208 | 16575 | 13 | 1 | 26,62 | 4,85 |
| Italian Grand Prix | 16,17 | 0 | 16 | 962 | 6048 | 2 | 0 | 9,84 | 0,16 |
| Japanese Grand Prix | 64,27 | 186 | 515 | 8041 | 13601 | 9 | 0 | 33,32 | 25,23 |
| Las Vegas Grand Prix | 45,36 | 128 | 221 | 3454 | 8384 | 6 | 0 | 26,65 | 8,56 |
| Mexico City Grand Prix | 29,27 | 17 | 74 | 2167 | 7714 | 4 | 0 | 21,33 | 2,58 |
| Miami Grand Prix | 70,58 | 91 | 417 | 6575 | 10035 | 8 | 0 | 20,86 | 9,54 |
| Monaco Grand Prix | 4,33 | 0 | 201 | 1 | 4660 | 1 | 0 | 26,80 | 9,39 |
| Qatar Grand Prix | 41,29 | 19 | 45 | 4751 | 11662 | 7 | 0 | 13,98 | 2,51 |
| Saudi Arabian Grand Prix | 67,74 | 73 | 260 | 8202 | 12599 | 10 | 0 | 20,18 | 9,92 |
| Singapore Grand Prix | 32,68 | 144 | 267 | 4645 | 15469 | 8 | 0 | 23,23 | 6,15 |
| Spanish Grand Prix | 49,49 | 145 | 812 | 4862 | 11758 | 7 | 0 | 34,59 | 15,61 |
| São Paulo Grand Prix | 58,55 | 56 | 186 | 7335 | 12940 | 7 | 0 | 18,58 | 6,48 |
| United States Grand Prix | 45,96 | 172 | 198 | 6039 | 13946 | 10 | 0 | 41,03 | 7,16 |

## Monza, cifras publicadas

Las cifras publicadas y esta corrida **no coinciden**.

Publicado, ventana de 350 m: 261/5114 (5,10 %). Medido: 506/5141 (9,84 %).
Publicado, Lesmo 2 en 350 m: 250/811. Medido: 480/838.
Publicado, ventanas del pipeline: 13/5074 (0,26 %). Medido: 8/5074 (0,16 %).

