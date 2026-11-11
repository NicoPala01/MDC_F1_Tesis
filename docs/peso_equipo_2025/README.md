# Peso del equipo y compañeros, tres GP de 2025

La base del código es `feat/zoi-por-circuito` (PR 13). `main` no tiene esas ventanas ni la corrida OpenF1. `monza-test` está contenido en `main`. El nulo del PR 11 ya está en esa base.

## Reglas, anteriores a la corrida

V de Cramér con corrección de Bergsma, AMI, ARI y su percentil se calculan solo si el nulo triple del PR 11 marca structure: la silueta real es estrictamente mayor que el percentil 95 de la permutación de columnas, del gaussiano y de la cópula, con 50 réplicas. Si no, esas cifras quedan vacías con motivo estructura_no_supera_nulo, no en 0. La regla es anterior a la corrida.

El efecto piloto general no es identificable: en un GP cada piloto corre para un solo equipo, así que piloto y equipo están anidados. El único componente que se lee como estilo es piloto_dentro_de_equipo.

Semilla del sorteo: `20251111`. Se sortean `3` carreras de `iter_race_event_names(2025)`, en el orden del calendario, con `numpy.random.Generator.choice` sin reposición. Numpy `2.5.4`.

Piso de un par: `15` vueltas limpias y `2` stints. Una carrera con menos del 50 % de vueltas conservadas por safety car, VSC o lluvia sale de la capa. No se filtra por `Status` ni por posición.

Permutación de pilotos: `200` réplicas, semilla `42`. Bootstrap por stint: `100`, semilla `45`. El percentil del test es el rango medio. El nulo de silueta del PR 11 sigue usando la proporción de réplicas menores o iguales.

Familia auto: `brake_point_rel`, `apex_speed_rel`, `full_throttle_frac`. Familia estilo: tasas y transiciones (`throttle_attack`, `trail_brake_frac`, `coast_frac`, `throttle_onset_rel` y las métricas de tiempo). Una columna de otro stem se reporta como `otra`. No se borra ninguna.

## Sorteo

Población:

- Australian Grand Prix
- Chinese Grand Prix ← sorteado
- Japanese Grand Prix
- Bahrain Grand Prix
- Saudi Arabian Grand Prix ← sorteado
- Miami Grand Prix
- Emilia Romagna Grand Prix
- Monaco Grand Prix
- Spanish Grand Prix
- Canadian Grand Prix ← sorteado
- Austrian Grand Prix
- British Grand Prix
- Belgian Grand Prix
- Hungarian Grand Prix
- Dutch Grand Prix
- Italian Grand Prix
- Azerbaijan Grand Prix
- Singapore Grand Prix
- United States Grand Prix
- Mexico City Grand Prix
- São Paulo Grand Prix
- Las Vegas Grand Prix
- Qatar Grand Prix
- Abu Dhabi Grand Prix

Sorteados, en el orden que devolvió el generador:

- Saudi Arabian Grand Prix
- Canadian Grand Prix
- Chinese Grand Prix

## Resultados

La corrida todavía no está. Este archivo no contiene cifras de telemetría.
