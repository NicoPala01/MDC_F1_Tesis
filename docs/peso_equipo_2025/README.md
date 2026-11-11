# Peso del equipo y compañeros, tres GP de 2025

La base del código es `feat/zoi-por-circuito` (PR 13). `main` no tiene esas ventanas ni la corrida OpenF1. `monza-test` está contenido en `main`. El nulo del PR 11 ya está en esa base.

## Lectura

Estas cifras salen de la corrida OpenF1 de los tres GP sorteados. FastF1 no se usó para la telemetría: sin `F1_USERNAME` el cliente se queda esperando un mail. El `TrackStatus` se reconstruyó con los mensajes de `race_control`. `IsAccurate` es duración finita, vuelta no borrada y que no entra ni sale de boxes. La lluvia no se pudo alinear al reloj de la vuelta.

Ninguna carrera quedó fuera por safety car o VSC: la fracción conservada está por encima de 0,50.

El nulo triple no autoriza leer V, AMI ni ARI como estilo en ninguno de los tres. En China el percentil de la silueta real dentro de la cópula es 52, y en Canadá es 54, ambos en la matriz que conserva las columnas de IQR 0. Hace falta superar el percentil 95 de los tres nulos. En Arabia Saudita la silueta sí supera los tres, pero 652 de 656 vueltas caen en una sola clase, así que la asociación queda vacía con motivo `clase_dominante`, no en 0. Esa clase chica tiene mediana de tiempo 161,1 s y la otra 94,6 s: el η² del tiempo de vuelta es 0,944. La separación ordena unas pocas vueltas lentas, no un estilo.

En las columnas comunes, la proporción media del piloto dentro del equipo queda por debajo de la del equipo en Arabia Saudita y no se separa de ella en China. En Canadá la matriz completa tiene 76 vueltas y ningún par llega al piso de 15 vueltas y 2 stints.

Lawson sí cambia de equipo dentro de la muestra: en China corre con Verstappen en Red Bull y en Arabia Saudita con Hadjar en Racing Bulls. La distancia euclídea de su mediana de estilo a la del compañero de esa carrera pasa de 2,438 a 1,802. Canadá no entra en ese promedio: Lawson no tiene vueltas completas en esa matriz. Tsunoda no tiene distancia al compañero de Red Bull en Arabia Saudita ni en Canadá porque Verstappen no tiene vueltas completas ahí. El detalle está en las tablas de abajo.

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

Retención (safety car, VSC, lluvia):

- Chinese Grand Prix: conservada 1.000, excluida False, motivo `nan`, SC 0, VSC 0, lluvia no verde 0.
- Saudi Arabian Grand Prix: conservada 0.961, excluida False, motivo `nan`, SC 34, VSC 0, lluvia no verde 0.
- Canadian Grand Prix: conservada 1.000, excluida False, motivo `nan`, SC 0, VSC 0, lluvia no verde 0.

Estructura frente al nulo triple:

- Chinese Grand Prix (sin_iqr0): structure False, k 4, silueta 0.100, percentil permutación 100.0, gaussiano 100.0, cópula 46.0.
- Chinese Grand Prix (con_iqr0): structure False, k 4, silueta 0.100, percentil permutación 100.0, gaussiano 100.0, cópula 52.0.
- Saudi Arabian Grand Prix (sin_iqr0): structure True, k 2, silueta 0.931, percentil permutación 100.0, gaussiano 100.0, cópula 100.0.
- Saudi Arabian Grand Prix (con_iqr0): structure True, k 2, silueta 0.931, percentil permutación 100.0, gaussiano 100.0, cópula 100.0.
- Canadian Grand Prix (con_iqr0): structure False, k 2, silueta 0.786, percentil permutación 100.0, gaussiano 100.0, cópula 54.0.
- Canadian Grand Prix (sin_iqr0): structure False, k 2, silueta 0.786, percentil permutación 100.0, gaussiano 100.0, cópula 46.0.

Pares. `V_cramer_bc`, `AMI` y `ARI` son de la carrera (clase × escudería, nivel vuelta) y se repiten en cada fila. El AMI de la columna `AMI` es clase contra escudería. `AMI_clase_piloto` es clase contra piloto.

- Chinese Grand Prix / Aston Martin / ALO-STR / estratificado / sin_iqr0: n 0/49, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / crudo / sin_iqr0: n 49/48, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / MEDIUM|vida_26_mas / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / MEDIUM|vida_11_25 / sin_iqr0: n 2/4, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / MEDIUM|vida_1_10 / sin_iqr0: n 7/6, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / HARD|vida_26_mas / sin_iqr0: n 0/15, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / HARD|vida_11_25 / sin_iqr0: n 20/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / HARD|vida_1_10 / sin_iqr0: n 18/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / crudo / sin_iqr0: n 47/49, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Aston Martin / ALO-STR / crudo / sin_iqr0: n 0/49, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / MEDIUM|vida_26_mas / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / MEDIUM|vida_11_25 / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / MEDIUM|vida_1_10 / sin_iqr0: n 7/6, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / HARD|vida_26_mas / sin_iqr0: n 18/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / HARD|vida_11_25 / sin_iqr0: n 14/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / HARD|vida_1_10 / sin_iqr0: n 9/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / crudo / sin_iqr0: n 48/45, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / HARD|vida_1_10 / sin_iqr0: n 7/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / MEDIUM|vida_26_mas / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / MEDIUM|vida_11_25 / sin_iqr0: n 8/6, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / MEDIUM|vida_1_10 / sin_iqr0: n 7/7, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / HARD|vida_26_mas / sin_iqr0: n 9/12, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / HARD|vida_11_25 / sin_iqr0: n 14/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / HARD|vida_1_10 / sin_iqr0: n 9/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / crudo / sin_iqr0: n 47/49, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / MEDIUM|vida_26_mas / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Kick Sauber / BOR-HUL / HARD|vida_26_mas / sin_iqr0: n 3/8, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / HARD|vida_1_10 / sin_iqr0: n 9/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / crudo / sin_iqr0: n 50/50, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / MEDIUM|vida_26_mas / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / MEDIUM|vida_11_25 / sin_iqr0: n 4/3, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / MEDIUM|vida_1_10 / sin_iqr0: n 6/7, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / HARD|vida_26_mas / sin_iqr0: n 15/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / HARD|vida_11_25 / sin_iqr0: n 14/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / HARD|vida_1_10 / sin_iqr0: n 9/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / crudo / sin_iqr0: n 48/49, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / HARD|vida_11_25 / sin_iqr0: n 15/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Kick Sauber / BOR-HUL / HARD|vida_11_25 / sin_iqr0: n 29/14, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Kick Sauber / BOR-HUL / HARD|vida_1_10 / sin_iqr0: n 16/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Kick Sauber / BOR-HUL / crudo / sin_iqr0: n 48/47, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / MEDIUM|vida_26_mas / sin_iqr0: n 4/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / MEDIUM|vida_11_25 / sin_iqr0: n 15/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / MEDIUM|vida_1_10 / sin_iqr0: n 9/7, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / HARD|vida_26_mas / sin_iqr0: n 0/18, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / HARD|vida_11_25 / sin_iqr0: n 14/14, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / MEDIUM|vida_1_10 / sin_iqr0: n 7/10, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / MEDIUM|vida_11_25 / sin_iqr0: n 0/2, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / MEDIUM|vida_1_10 / sin_iqr0: n 9/6, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / HARD|vida_26_mas / sin_iqr0: n 0/17, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / HARD|vida_11_25 / sin_iqr0: n 22/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / HARD|vida_1_10 / sin_iqr0: n 16/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / crudo / sin_iqr0: n 47/49, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / MEDIUM|vida_26_mas / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / MEDIUM|vida_11_25 / sin_iqr0: n 1/4, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / HARD|vida_26_mas / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / HARD|vida_11_25 / sin_iqr0: n 20/13, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / HARD|vida_1_10 / sin_iqr0: n 18/17, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / crudo / sin_iqr0: n 46/44, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / MEDIUM|vida_26_mas / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / MEDIUM|vida_11_25 / sin_iqr0: n 1/3, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / MEDIUM|vida_1_10 / sin_iqr0: n 7/7, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / HARD|vida_26_mas / sin_iqr0: n 18/16, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / MEDIUM|vida_1_10 / con_iqr0: n 7/6, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / crudo / con_iqr0: n 48/45, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / HARD|vida_1_10 / con_iqr0: n 9/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / HARD|vida_11_25 / con_iqr0: n 14/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / HARD|vida_26_mas / con_iqr0: n 18/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / MEDIUM|vida_11_25 / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Alpine / DOO-GAS / MEDIUM|vida_26_mas / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Aston Martin / ALO-STR / crudo / con_iqr0: n 0/49, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Aston Martin / ALO-STR / estratificado / con_iqr0: n 0/49, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / crudo / con_iqr0: n 47/49, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / HARD|vida_1_10 / con_iqr0: n 18/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / HARD|vida_11_25 / con_iqr0: n 20/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / HARD|vida_26_mas / con_iqr0: n 0/15, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / MEDIUM|vida_1_10 / con_iqr0: n 7/6, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / MEDIUM|vida_11_25 / con_iqr0: n 2/4, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Ferrari / HAM-LEC / MEDIUM|vida_26_mas / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / crudo / con_iqr0: n 49/48, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / MEDIUM|vida_26_mas / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / HARD|vida_1_10 / con_iqr0: n 18/17, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / HARD|vida_11_25 / con_iqr0: n 20/13, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / HARD|vida_26_mas / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / MEDIUM|vida_1_10 / con_iqr0: n 7/10, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / MEDIUM|vida_11_25 / con_iqr0: n 1/4, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / MEDIUM|vida_26_mas / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / crudo / con_iqr0: n 47/49, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / HARD|vida_1_10 / con_iqr0: n 16/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / HARD|vida_11_25 / con_iqr0: n 22/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / HARD|vida_26_mas / con_iqr0: n 0/17, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / MEDIUM|vida_1_10 / con_iqr0: n 9/6, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Red Bull Racing / LAW-VER / MEDIUM|vida_11_25 / con_iqr0: n 0/2, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / HARD|vida_11_25 / con_iqr0: n 14/14, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / crudo / con_iqr0: n 47/49, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / HARD|vida_1_10 / con_iqr0: n 9/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / HARD|vida_11_25 / con_iqr0: n 14/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / HARD|vida_26_mas / con_iqr0: n 9/12, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / MEDIUM|vida_1_10 / con_iqr0: n 7/7, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / MEDIUM|vida_11_25 / con_iqr0: n 8/6, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Williams / ALB-SAI / MEDIUM|vida_26_mas / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / MEDIUM|vida_26_mas / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Racing Bulls / HAD-TSU / crudo / con_iqr0: n 46/44, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / HARD|vida_1_10 / con_iqr0: n 7/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / HARD|vida_26_mas / con_iqr0: n 0/18, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / MEDIUM|vida_1_10 / con_iqr0: n 9/7, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / MEDIUM|vida_11_25 / con_iqr0: n 15/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Haas F1 Team / BEA-OCO / MEDIUM|vida_26_mas / con_iqr0: n 4/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Kick Sauber / BOR-HUL / crudo / con_iqr0: n 48/47, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Kick Sauber / BOR-HUL / HARD|vida_1_10 / con_iqr0: n 16/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Kick Sauber / BOR-HUL / HARD|vida_11_25 / con_iqr0: n 29/14, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Kick Sauber / BOR-HUL / HARD|vida_26_mas / con_iqr0: n 3/8, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / crudo / con_iqr0: n 48/49, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / HARD|vida_1_10 / con_iqr0: n 9/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / HARD|vida_26_mas / con_iqr0: n 15/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / HARD|vida_11_25 / con_iqr0: n 14/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / MEDIUM|vida_11_25 / con_iqr0: n 1/3, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / MEDIUM|vida_1_10 / con_iqr0: n 7/7, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / HARD|vida_26_mas / con_iqr0: n 18/16, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / HARD|vida_11_25 / con_iqr0: n 15/15, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / HARD|vida_1_10 / con_iqr0: n 9/9, motivo `nan`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / Mercedes / ANT-RUS / crudo / con_iqr0: n 50/50, motivo `nan`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / MEDIUM|vida_26_mas / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / MEDIUM|vida_11_25 / con_iqr0: n 4/3, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Chinese Grand Prix / McLaren / NOR-PIA / MEDIUM|vida_1_10 / con_iqr0: n 6/7, motivo `nan`, compuesto `MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Kick Sauber / BOR-HUL / crudo / sin_iqr0: n 39/32, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Red Bull Racing / TSU-VER / crudo / sin_iqr0: n 0/31, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Red Bull Racing / TSU-VER / estratificado / sin_iqr0: n 0/31, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Williams / ALB-SAI / crudo / sin_iqr0: n 43/40, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Williams / ALB-SAI / estratificado / sin_iqr0: n 43/40, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / McLaren / NOR-PIA / crudo / con_iqr0: n 40/42, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Alpine / DOO-GAS / crudo / con_iqr0: n 43/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Alpine / DOO-GAS / estratificado / con_iqr0: n 43/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Aston Martin / ALO-STR / crudo / con_iqr0: n 34/40, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Aston Martin / ALO-STR / estratificado / con_iqr0: n 34/40, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Ferrari / HAM-LEC / crudo / con_iqr0: n 37/25, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Ferrari / HAM-LEC / estratificado / con_iqr0: n 37/25, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Haas F1 Team / BEA-OCO / crudo / con_iqr0: n 37/43, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Haas F1 Team / BEA-OCO / estratificado / con_iqr0: n 37/43, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Kick Sauber / BOR-HUL / crudo / con_iqr0: n 39/32, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Kick Sauber / BOR-HUL / estratificado / con_iqr0: n 39/32, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / McLaren / NOR-PIA / estratificado / con_iqr0: n 40/42, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Mercedes / ANT-RUS / crudo / con_iqr0: n 36/28, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Mercedes / ANT-RUS / estratificado / con_iqr0: n 36/28, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Racing Bulls / HAD-LAW / crudo / con_iqr0: n 32/34, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Racing Bulls / HAD-LAW / estratificado / con_iqr0: n 32/34, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Red Bull Racing / TSU-VER / crudo / con_iqr0: n 0/31, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Red Bull Racing / TSU-VER / estratificado / con_iqr0: n 0/31, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Williams / ALB-SAI / crudo / con_iqr0: n 43/40, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Williams / ALB-SAI / estratificado / con_iqr0: n 43/40, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Alpine / DOO-GAS / crudo / sin_iqr0: n 43/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Racing Bulls / HAD-LAW / estratificado / sin_iqr0: n 32/34, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Racing Bulls / HAD-LAW / crudo / sin_iqr0: n 32/34, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Mercedes / ANT-RUS / estratificado / sin_iqr0: n 36/28, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Mercedes / ANT-RUS / crudo / sin_iqr0: n 36/28, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / McLaren / NOR-PIA / estratificado / sin_iqr0: n 40/42, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / McLaren / NOR-PIA / crudo / sin_iqr0: n 40/42, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Kick Sauber / BOR-HUL / estratificado / sin_iqr0: n 39/32, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Haas F1 Team / BEA-OCO / crudo / sin_iqr0: n 37/43, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Ferrari / HAM-LEC / estratificado / sin_iqr0: n 37/25, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Ferrari / HAM-LEC / crudo / sin_iqr0: n 37/25, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Aston Martin / ALO-STR / estratificado / sin_iqr0: n 34/40, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Aston Martin / ALO-STR / crudo / sin_iqr0: n 34/40, motivo `clase_dominante`, compuesto `HARD+MEDIUM`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Alpine / DOO-GAS / estratificado / sin_iqr0: n 43/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Saudi Arabian Grand Prix / Haas F1 Team / BEA-OCO / estratificado / sin_iqr0: n 37/43, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `clase_dominante`, V modal —, AMI piloto —.
- Canadian Grand Prix / Williams / ALB-SAI / crudo / sin_iqr0: n 0/7, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Williams / ALB-SAI / estratificado / sin_iqr0: n 0/7, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Red Bull Racing / TSU-VER / estratificado / sin_iqr0: n 15/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Racing Bulls / HAD-LAW / estratificado / sin_iqr0: n 14/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Racing Bulls / HAD-LAW / crudo / sin_iqr0: n 14/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Mercedes / ANT-RUS / estratificado / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Mercedes / ANT-RUS / crudo / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / McLaren / NOR-PIA / estratificado / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / McLaren / NOR-PIA / crudo / sin_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Kick Sauber / BOR-HUL / estratificado / sin_iqr0: n 6/3, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Haas F1 Team / BEA-OCO / estratificado / sin_iqr0: n 13/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Red Bull Racing / TSU-VER / crudo / sin_iqr0: n 15/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Alpine / COL-GAS / crudo / con_iqr0: n 0/3, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Ferrari / HAM-LEC / estratificado / con_iqr0: n 3/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Williams / ALB-SAI / estratificado / con_iqr0: n 0/7, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Williams / ALB-SAI / crudo / con_iqr0: n 0/7, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Red Bull Racing / TSU-VER / estratificado / con_iqr0: n 15/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Red Bull Racing / TSU-VER / crudo / con_iqr0: n 15/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Alpine / COL-GAS / estratificado / con_iqr0: n 0/3, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Aston Martin / ALO-STR / crudo / con_iqr0: n 6/6, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Aston Martin / ALO-STR / estratificado / con_iqr0: n 6/6, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Ferrari / HAM-LEC / crudo / con_iqr0: n 3/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Haas F1 Team / BEA-OCO / crudo / con_iqr0: n 13/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Haas F1 Team / BEA-OCO / estratificado / con_iqr0: n 13/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Kick Sauber / BOR-HUL / crudo / con_iqr0: n 6/3, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Kick Sauber / BOR-HUL / estratificado / con_iqr0: n 6/3, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / McLaren / NOR-PIA / crudo / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / McLaren / NOR-PIA / estratificado / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Mercedes / ANT-RUS / crudo / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Mercedes / ANT-RUS / estratificado / con_iqr0: n 0/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Racing Bulls / HAD-LAW / crudo / con_iqr0: n 14/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Racing Bulls / HAD-LAW / estratificado / con_iqr0: n 14/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Haas F1 Team / BEA-OCO / crudo / sin_iqr0: n 13/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Ferrari / HAM-LEC / estratificado / sin_iqr0: n 3/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Ferrari / HAM-LEC / crudo / sin_iqr0: n 3/0, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Aston Martin / ALO-STR / estratificado / sin_iqr0: n 6/6, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Aston Martin / ALO-STR / crudo / sin_iqr0: n 6/6, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Alpine / COL-GAS / estratificado / sin_iqr0: n 0/3, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Alpine / COL-GAS / crudo / sin_iqr0: n 0/3, motivo `pocas_vueltas`, compuesto `nan`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.
- Canadian Grand Prix / Kick Sauber / BOR-HUL / crudo / sin_iqr0: n 6/3, motivo `pocas_vueltas`, compuesto `HARD`, V — [—, —], AMI —, ARI —, percentil —, asociación `estructura_no_supera_nulo`, V modal —, AMI piloto —.

Pares con motivo de NA: 228.

- Chinese Grand Prix Red Bull Racing LAW-VER HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=17).
- Chinese Grand Prix Red Bull Racing LAW-VER MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Red Bull Racing LAW-VER MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=0, n_b=2).
- Chinese Grand Prix Williams ALB-SAI MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Racing Bulls HAD-TSU MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Racing Bulls HAD-TSU HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Aston Martin ALO-STR estratificado: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Chinese Grand Prix Ferrari HAM-LEC MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Ferrari HAM-LEC HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=15).
- Chinese Grand Prix Aston Martin ALO-STR crudo: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Chinese Grand Prix Alpine DOO-GAS MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Alpine DOO-GAS MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=0, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=4, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=15, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=18).
- Chinese Grand Prix Ferrari HAM-LEC MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Ferrari HAM-LEC HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=15).
- Chinese Grand Prix Aston Martin ALO-STR estratificado: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Chinese Grand Prix Aston Martin ALO-STR crudo: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Chinese Grand Prix Alpine DOO-GAS MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix McLaren NOR-PIA MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Mercedes ANT-RUS MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Aston Martin ALO-STR estratificado: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Chinese Grand Prix Aston Martin ALO-STR crudo: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Chinese Grand Prix Alpine DOO-GAS MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Alpine DOO-GAS MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=0, n_b=0).
- Chinese Grand Prix Williams ALB-SAI MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=4, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=15, n_b=0).
- Chinese Grand Prix Red Bull Racing LAW-VER MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=18).
- Chinese Grand Prix Ferrari HAM-LEC MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Ferrari HAM-LEC HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=15).
- Chinese Grand Prix McLaren NOR-PIA MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=4, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=15, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=18).
- Chinese Grand Prix Red Bull Racing LAW-VER MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=0, n_b=2).
- Chinese Grand Prix Red Bull Racing LAW-VER HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=17).
- Chinese Grand Prix Racing Bulls HAD-TSU MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Alpine DOO-GAS MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=0, n_b=0).
- Chinese Grand Prix Racing Bulls HAD-TSU HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Mercedes ANT-RUS MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix McLaren NOR-PIA MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Alpine DOO-GAS MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=0, n_b=0).
- Chinese Grand Prix Alpine DOO-GAS MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Aston Martin ALO-STR crudo: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Chinese Grand Prix Aston Martin ALO-STR estratificado: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Chinese Grand Prix Ferrari HAM-LEC HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=15).
- Chinese Grand Prix Ferrari HAM-LEC MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Williams ALB-SAI MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Red Bull Racing LAW-VER MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Red Bull Racing LAW-VER MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=0, n_b=2).
- Chinese Grand Prix Red Bull Racing LAW-VER HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=17).
- Chinese Grand Prix Racing Bulls HAD-TSU MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Racing Bulls HAD-TSU HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Mercedes ANT-RUS MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Red Bull Racing LAW-VER MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Racing Bulls HAD-TSU HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Racing Bulls HAD-TSU MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Red Bull Racing LAW-VER HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=17).
- Chinese Grand Prix Red Bull Racing LAW-VER MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=0, n_b=2).
- Chinese Grand Prix Williams ALB-SAI MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Mercedes ANT-RUS MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO HARD|vida_26_mas: `pocas_vueltas` (estrato HARD|vida_26_mas: n_a=0, n_b=18).
- Chinese Grand Prix Haas F1 Team BEA-OCO MEDIUM|vida_11_25: `pocas_vueltas` (estrato MEDIUM|vida_11_25: n_a=15, n_b=0).
- Chinese Grand Prix Haas F1 Team BEA-OCO MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=4, n_b=0).
- Chinese Grand Prix McLaren NOR-PIA MEDIUM|vida_26_mas: `pocas_vueltas` (estrato MEDIUM|vida_26_mas: n_a=0, n_b=0).
- Saudi Arabian Grand Prix Aston Martin ALO-STR estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix McLaren NOR-PIA crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Haas F1 Team BEA-OCO estratificado: `pocas_vueltas` (stints_b=1<2).
- Saudi Arabian Grand Prix Mercedes ANT-RUS crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Mercedes ANT-RUS estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Racing Bulls HAD-LAW crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Racing Bulls HAD-LAW estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Red Bull Racing TSU-VER crudo: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Saudi Arabian Grand Prix Red Bull Racing TSU-VER estratificado: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Saudi Arabian Grand Prix Williams ALB-SAI crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Williams ALB-SAI estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Kick Sauber BOR-HUL crudo: `pocas_vueltas` (stints_a=1<2).
- Saudi Arabian Grand Prix Ferrari HAM-LEC crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Red Bull Racing TSU-VER crudo: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Saudi Arabian Grand Prix Red Bull Racing TSU-VER estratificado: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Saudi Arabian Grand Prix Williams ALB-SAI crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Williams ALB-SAI estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Alpine DOO-GAS crudo: `pocas_vueltas` (vueltas_b=0<15,stints_b=0<2).
- Saudi Arabian Grand Prix Alpine DOO-GAS estratificado: `pocas_vueltas` (vueltas_b=0<15,stints_b=0<2).
- Saudi Arabian Grand Prix Aston Martin ALO-STR crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Aston Martin ALO-STR estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Ferrari HAM-LEC crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Haas F1 Team BEA-OCO crudo: `pocas_vueltas` (stints_b=1<2).
- Saudi Arabian Grand Prix McLaren NOR-PIA crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Ferrari HAM-LEC estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Alpine DOO-GAS crudo: `pocas_vueltas` (vueltas_b=0<15,stints_b=0<2).
- Saudi Arabian Grand Prix Alpine DOO-GAS estratificado: `pocas_vueltas` (vueltas_b=0<15,stints_b=0<2).
- Saudi Arabian Grand Prix Aston Martin ALO-STR crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Aston Martin ALO-STR estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Ferrari HAM-LEC crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Ferrari HAM-LEC estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Haas F1 Team BEA-OCO crudo: `pocas_vueltas` (stints_b=1<2).
- Saudi Arabian Grand Prix Haas F1 Team BEA-OCO estratificado: `pocas_vueltas` (stints_b=1<2).
- Saudi Arabian Grand Prix Kick Sauber BOR-HUL crudo: `pocas_vueltas` (stints_a=1<2).
- Saudi Arabian Grand Prix Kick Sauber BOR-HUL estratificado: `pocas_vueltas` (stints_a=1<2).
- Saudi Arabian Grand Prix Aston Martin ALO-STR crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix McLaren NOR-PIA estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Mercedes ANT-RUS crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Mercedes ANT-RUS estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Racing Bulls HAD-LAW crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Racing Bulls HAD-LAW estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Red Bull Racing TSU-VER crudo: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Saudi Arabian Grand Prix Red Bull Racing TSU-VER estratificado: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Saudi Arabian Grand Prix Williams ALB-SAI crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Williams ALB-SAI estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Alpine DOO-GAS crudo: `pocas_vueltas` (vueltas_b=0<15,stints_b=0<2).
- Saudi Arabian Grand Prix Alpine DOO-GAS estratificado: `pocas_vueltas` (vueltas_b=0<15,stints_b=0<2).
- Saudi Arabian Grand Prix Alpine DOO-GAS crudo: `pocas_vueltas` (vueltas_b=0<15,stints_b=0<2).
- Saudi Arabian Grand Prix Kick Sauber BOR-HUL crudo: `pocas_vueltas` (stints_a=1<2).
- Saudi Arabian Grand Prix Racing Bulls HAD-LAW estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Racing Bulls HAD-LAW crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Mercedes ANT-RUS estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Mercedes ANT-RUS crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix McLaren NOR-PIA estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix McLaren NOR-PIA crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Kick Sauber BOR-HUL estratificado: `pocas_vueltas` (stints_a=1<2).
- Saudi Arabian Grand Prix Kick Sauber BOR-HUL estratificado: `pocas_vueltas` (stints_a=1<2).
- Saudi Arabian Grand Prix Haas F1 Team BEA-OCO crudo: `pocas_vueltas` (stints_b=1<2).
- Saudi Arabian Grand Prix Ferrari HAM-LEC estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Ferrari HAM-LEC crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Aston Martin ALO-STR estratificado: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Aston Martin ALO-STR crudo: `clase_dominante` (clase_dominante).
- Saudi Arabian Grand Prix Alpine DOO-GAS estratificado: `pocas_vueltas` (vueltas_b=0<15,stints_b=0<2).
- Saudi Arabian Grand Prix Haas F1 Team BEA-OCO estratificado: `pocas_vueltas` (stints_b=1<2).
- Saudi Arabian Grand Prix Williams ALB-SAI estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Williams ALB-SAI crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Red Bull Racing TSU-VER estratificado: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Saudi Arabian Grand Prix Red Bull Racing TSU-VER crudo: `pocas_vueltas` (vueltas_a=0<15,stints_a=0<2).
- Saudi Arabian Grand Prix Racing Bulls HAD-LAW estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Racing Bulls HAD-LAW crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Mercedes ANT-RUS estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Mercedes ANT-RUS crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix McLaren NOR-PIA estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix McLaren NOR-PIA crudo: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix Kick Sauber BOR-HUL estratificado: `pocas_vueltas` (stints_a=1<2).
- Saudi Arabian Grand Prix Kick Sauber BOR-HUL crudo: `pocas_vueltas` (stints_a=1<2).
- Saudi Arabian Grand Prix Haas F1 Team BEA-OCO estratificado: `pocas_vueltas` (stints_b=1<2).
- Saudi Arabian Grand Prix Haas F1 Team BEA-OCO crudo: `pocas_vueltas` (stints_b=1<2).
- Saudi Arabian Grand Prix Ferrari HAM-LEC estratificado: `una_sola_clase` (una_sola_clase).
- Saudi Arabian Grand Prix McLaren NOR-PIA estratificado: `una_sola_clase` (una_sola_clase).
- Canadian Grand Prix Williams ALB-SAI crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=7<15,stints_a=0<2,stints_b=1<2).
- Canadian Grand Prix McLaren NOR-PIA crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Kick Sauber BOR-HUL estratificado: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=3<15,stints_b=1<2).
- Canadian Grand Prix Kick Sauber BOR-HUL crudo: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=3<15,stints_b=1<2).
- Canadian Grand Prix Haas F1 Team BEA-OCO estratificado: `pocas_vueltas` (vueltas_a=13<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Aston Martin ALO-STR estratificado: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=6<15).
- Canadian Grand Prix Aston Martin ALO-STR crudo: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=6<15).
- Canadian Grand Prix Alpine COL-GAS estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=3<15,stints_a=0<2).
- Canadian Grand Prix Alpine COL-GAS crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=3<15,stints_a=0<2).
- Canadian Grand Prix Williams ALB-SAI estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=7<15,stints_a=0<2,stints_b=1<2).
- Canadian Grand Prix McLaren NOR-PIA estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Red Bull Racing TSU-VER estratificado: `pocas_vueltas` (vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Haas F1 Team BEA-OCO crudo: `pocas_vueltas` (vueltas_a=13<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Racing Bulls HAD-LAW estratificado: `pocas_vueltas` (vueltas_a=14<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Racing Bulls HAD-LAW crudo: `pocas_vueltas` (vueltas_a=14<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Mercedes ANT-RUS estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Mercedes ANT-RUS crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix McLaren NOR-PIA estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix McLaren NOR-PIA crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Kick Sauber BOR-HUL estratificado: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=3<15,stints_b=1<2).
- Canadian Grand Prix Kick Sauber BOR-HUL estratificado: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=3<15,stints_b=1<2).
- Canadian Grand Prix Williams ALB-SAI crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=7<15,stints_a=0<2,stints_b=1<2).
- Canadian Grand Prix Red Bull Racing TSU-VER estratificado: `pocas_vueltas` (vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Red Bull Racing TSU-VER crudo: `pocas_vueltas` (vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Racing Bulls HAD-LAW estratificado: `pocas_vueltas` (vueltas_a=14<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Racing Bulls HAD-LAW crudo: `pocas_vueltas` (vueltas_a=14<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Mercedes ANT-RUS estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Mercedes ANT-RUS crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix McLaren NOR-PIA estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix McLaren NOR-PIA crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Haas F1 Team BEA-OCO estratificado: `pocas_vueltas` (vueltas_a=13<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Red Bull Racing TSU-VER crudo: `pocas_vueltas` (vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Kick Sauber BOR-HUL crudo: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=3<15,stints_b=1<2).
- Canadian Grand Prix Ferrari HAM-LEC crudo: `pocas_vueltas` (vueltas_a=3<15,vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Mercedes ANT-RUS crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Haas F1 Team BEA-OCO estratificado: `pocas_vueltas` (vueltas_a=13<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Alpine COL-GAS crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=3<15,stints_a=0<2).
- Canadian Grand Prix Haas F1 Team BEA-OCO crudo: `pocas_vueltas` (vueltas_a=13<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Ferrari HAM-LEC estratificado: `pocas_vueltas` (vueltas_a=3<15,vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Ferrari HAM-LEC crudo: `pocas_vueltas` (vueltas_a=3<15,vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Ferrari HAM-LEC estratificado: `pocas_vueltas` (vueltas_a=3<15,vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Alpine COL-GAS crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=3<15,stints_a=0<2).
- Canadian Grand Prix Williams ALB-SAI estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=7<15,stints_a=0<2,stints_b=1<2).
- Canadian Grand Prix Williams ALB-SAI crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=7<15,stints_a=0<2,stints_b=1<2).
- Canadian Grand Prix Red Bull Racing TSU-VER estratificado: `pocas_vueltas` (vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Red Bull Racing TSU-VER crudo: `pocas_vueltas` (vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Alpine COL-GAS estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=3<15,stints_a=0<2).
- Canadian Grand Prix Aston Martin ALO-STR crudo: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=6<15).
- Canadian Grand Prix Aston Martin ALO-STR estratificado: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=6<15).
- Canadian Grand Prix Ferrari HAM-LEC crudo: `pocas_vueltas` (vueltas_a=3<15,vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Alpine COL-GAS estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=3<15,stints_a=0<2).
- Canadian Grand Prix Haas F1 Team BEA-OCO crudo: `pocas_vueltas` (vueltas_a=13<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Haas F1 Team BEA-OCO estratificado: `pocas_vueltas` (vueltas_a=13<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Kick Sauber BOR-HUL crudo: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=3<15,stints_b=1<2).
- Canadian Grand Prix Kick Sauber BOR-HUL estratificado: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=3<15,stints_b=1<2).
- Canadian Grand Prix McLaren NOR-PIA crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix McLaren NOR-PIA estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Mercedes ANT-RUS crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Mercedes ANT-RUS estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Racing Bulls HAD-LAW crudo: `pocas_vueltas` (vueltas_a=14<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Williams ALB-SAI crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=7<15,stints_a=0<2,stints_b=1<2).
- Canadian Grand Prix Racing Bulls HAD-LAW estratificado: `pocas_vueltas` (vueltas_a=14<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Haas F1 Team BEA-OCO crudo: `pocas_vueltas` (vueltas_a=13<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Ferrari HAM-LEC estratificado: `pocas_vueltas` (vueltas_a=3<15,vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Ferrari HAM-LEC crudo: `pocas_vueltas` (vueltas_a=3<15,vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Aston Martin ALO-STR estratificado: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=6<15).
- Canadian Grand Prix Aston Martin ALO-STR crudo: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=6<15).
- Canadian Grand Prix Alpine COL-GAS estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=3<15,stints_a=0<2).
- Canadian Grand Prix Alpine COL-GAS crudo: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=3<15,stints_a=0<2).
- Canadian Grand Prix Williams ALB-SAI estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=7<15,stints_a=0<2,stints_b=1<2).
- Canadian Grand Prix Kick Sauber BOR-HUL crudo: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=3<15,stints_b=1<2).
- Canadian Grand Prix Red Bull Racing TSU-VER estratificado: `pocas_vueltas` (vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Red Bull Racing TSU-VER crudo: `pocas_vueltas` (vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Racing Bulls HAD-LAW estratificado: `pocas_vueltas` (vueltas_a=14<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Racing Bulls HAD-LAW crudo: `pocas_vueltas` (vueltas_a=14<15,vueltas_b=0<15,stints_b=0<2).
- Canadian Grand Prix Mercedes ANT-RUS estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=0<15,stints_a=0<2,stints_b=0<2).
- Canadian Grand Prix Ferrari HAM-LEC estratificado: `pocas_vueltas` (vueltas_a=3<15,vueltas_b=0<15,stints_a=1<2,stints_b=0<2).
- Canadian Grand Prix Williams ALB-SAI estratificado: `pocas_vueltas` (vueltas_a=0<15,vueltas_b=7<15,stints_a=0<2,stints_b=1<2).
- Canadian Grand Prix Aston Martin ALO-STR estratificado: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=6<15).
- Canadian Grand Prix Aston Martin ALO-STR crudo: `pocas_vueltas` (vueltas_a=6<15,vueltas_b=6<15).

Proporción de varianza del piloto dentro del equipo, por feature. El intervalo es el bootstrap por stint.

- Chinese Grand Prix medium__throttle_attack (estilo, sin_iqr0): piloto 0.115 [0.092, 0.180], equipo 0.000, stint 0.000, residual 0.885, R² fijos 0.001.
- Chinese Grand Prix slow__throttle_attack (estilo, sin_iqr0): piloto 0.053 [0.021, 0.132], equipo 0.104, stint 0.035, residual 0.808, R² fijos 0.000.
- Chinese Grand Prix medium__trail_brake_frac (estilo, sin_iqr0): piloto 0.130 [0.037, 0.269], equipo 0.264, stint 0.073, residual 0.533, R² fijos 0.002.
- Chinese Grand Prix slow__trail_brake_frac (estilo, sin_iqr0): piloto 0.281 [0.197, 0.378], equipo 0.032, stint 0.012, residual 0.675, R² fijos 0.001.
- Chinese Grand Prix slow__apex_speed_rel (auto, sin_iqr0): piloto 0.223 [0.140, 0.434], equipo 0.035, stint 0.170, residual 0.573, R² fijos 0.000.
- Chinese Grand Prix medium__brake_point_rel (auto, sin_iqr0): piloto 0.051 [0.054, 0.195], equipo 0.052, stint 0.080, residual 0.817, R² fijos 0.002.
- Chinese Grand Prix slow__brake_point_rel (auto, sin_iqr0): piloto 0.175 [0.125, 0.258], equipo 0.021, stint 0.011, residual 0.793, R² fijos 0.002.
- Chinese Grand Prix medium__coast_frac (estilo, sin_iqr0): piloto 0.211 [0.167, 0.350], equipo 0.261, stint 0.065, residual 0.463, R² fijos 0.001.
- Chinese Grand Prix slow__coast_frac (estilo, sin_iqr0): piloto 0.206 [0.091, 0.441], equipo 0.221, stint 0.150, residual 0.423, R² fijos 0.005.
- Chinese Grand Prix fast__full_throttle_frac (auto, sin_iqr0): piloto 0.051 [0.041, 0.139], equipo 0.159, stint 0.025, residual 0.765, R² fijos 0.001.
- Chinese Grand Prix medium__full_throttle_frac (auto, sin_iqr0): piloto 0.006 [0.005, 0.052], equipo 0.015, stint 0.000, residual 0.980, R² fijos 0.001.
- Chinese Grand Prix slow__full_throttle_frac (auto, sin_iqr0): piloto 0.101 [0.043, 0.175], equipo 0.074, stint 0.019, residual 0.805, R² fijos 0.000.
- Chinese Grand Prix slow__full_throttle_frac (auto, con_iqr0): piloto 0.101 [0.047, 0.191], equipo 0.074, stint 0.019, residual 0.805, R² fijos 0.000.
- Chinese Grand Prix medium__throttle_attack (estilo, con_iqr0): piloto 0.115 [0.092, 0.179], equipo 0.000, stint 0.000, residual 0.885, R² fijos 0.001.
- Chinese Grand Prix slow__throttle_attack (estilo, con_iqr0): piloto 0.053 [0.027, 0.117], equipo 0.104, stint 0.035, residual 0.808, R² fijos 0.000.
- Chinese Grand Prix fast__trail_brake_frac (estilo, con_iqr0): piloto 0.000 [0.000, 0.222], equipo 0.030, stint 0.086, residual 0.885, R² fijos 0.000.
- Chinese Grand Prix medium__trail_brake_frac (estilo, con_iqr0): piloto 0.130 [0.069, 0.271], equipo 0.264, stint 0.073, residual 0.533, R² fijos 0.002.
- Chinese Grand Prix slow__trail_brake_frac (estilo, con_iqr0): piloto 0.281 [0.194, 0.368], equipo 0.032, stint 0.012, residual 0.675, R² fijos 0.001.
- Chinese Grand Prix fast__apex_speed_rel (auto, sin_iqr0): piloto 0.000 [0.000, 0.283], equipo 0.212, stint 0.279, residual 0.508, R² fijos 0.006.
- Chinese Grand Prix medium__apex_speed_rel (auto, sin_iqr0): piloto 0.207 [0.123, 0.331], equipo 0.210, stint 0.047, residual 0.536, R² fijos 0.008.
- Chinese Grand Prix fast__apex_speed_rel (auto, con_iqr0): piloto 0.000 [0.000, 0.277], equipo 0.212, stint 0.279, residual 0.508, R² fijos 0.006.
- Chinese Grand Prix medium__apex_speed_rel (auto, con_iqr0): piloto 0.207 [0.135, 0.358], equipo 0.210, stint 0.047, residual 0.536, R² fijos 0.008.
- Chinese Grand Prix slow__apex_speed_rel (auto, con_iqr0): piloto 0.223 [0.161, 0.419], equipo 0.035, stint 0.170, residual 0.573, R² fijos 0.000.
- Chinese Grand Prix medium__brake_point_rel (auto, con_iqr0): piloto 0.051 [0.061, 0.191], equipo 0.052, stint 0.080, residual 0.817, R² fijos 0.002.
- Chinese Grand Prix slow__brake_point_rel (auto, con_iqr0): piloto 0.175 [0.113, 0.258], equipo 0.021, stint 0.011, residual 0.793, R² fijos 0.002.
- Chinese Grand Prix fast__coast_frac (estilo, con_iqr0): piloto 0.085 [0.062, 0.427], equipo 0.228, stint 0.141, residual 0.546, R² fijos 0.030.
- Chinese Grand Prix medium__coast_frac (estilo, con_iqr0): piloto 0.211 [0.156, 0.340], equipo 0.261, stint 0.065, residual 0.463, R² fijos 0.001.
- Chinese Grand Prix slow__coast_frac (estilo, con_iqr0): piloto 0.206 [0.089, 0.421], equipo 0.221, stint 0.150, residual 0.423, R² fijos 0.005.
- Chinese Grand Prix fast__full_throttle_frac (auto, con_iqr0): piloto 0.051 [0.043, 0.131], equipo 0.159, stint 0.025, residual 0.765, R² fijos 0.001.
- Chinese Grand Prix medium__full_throttle_frac (auto, con_iqr0): piloto 0.006 [0.004, 0.056], equipo 0.015, stint 0.000, residual 0.980, R² fijos 0.001.
- Saudi Arabian Grand Prix slow__throttle_attack (estilo, sin_iqr0): piloto 0.020 [0.008, 0.103], equipo 0.183, stint 0.042, residual 0.755, R² fijos 0.004.
- Saudi Arabian Grand Prix medium__trail_brake_frac (estilo, sin_iqr0): piloto 0.038 [0.024, 0.142], equipo 0.202, stint 0.020, residual 0.740, R² fijos 0.026.
- Saudi Arabian Grand Prix slow__full_throttle_frac (auto, sin_iqr0): piloto 0.065 [0.032, 0.200], equipo 0.055, stint 0.041, residual 0.840, R² fijos 0.003.
- Saudi Arabian Grand Prix medium__throttle_attack (estilo, sin_iqr0): piloto 0.050 [0.019, 0.164], equipo 0.087, stint 0.026, residual 0.837, R² fijos 0.002.
- Saudi Arabian Grand Prix slow__coast_frac (estilo, sin_iqr0): piloto 0.026 [0.000, 0.215], equipo 0.434, stint 0.080, residual 0.461, R² fijos 0.001.
- Saudi Arabian Grand Prix medium__full_throttle_frac (auto, sin_iqr0): piloto 0.101 [0.076, 0.280], equipo 0.136, stint 0.063, residual 0.700, R² fijos 0.003.
- Saudi Arabian Grand Prix slow__brake_point_rel (auto, sin_iqr0): piloto 0.000 [0.000, 0.163], equipo 0.303, stint 0.126, residual 0.571, R² fijos 0.018.
- Saudi Arabian Grand Prix medium__coast_frac (estilo, sin_iqr0): piloto 0.153 [0.067, 0.284], equipo 0.371, stint 0.025, residual 0.451, R² fijos 0.001.
- Saudi Arabian Grand Prix slow__apex_speed_rel (auto, con_iqr0): piloto 0.000 [0.000, 0.088], equipo 0.071, stint 0.078, residual 0.851, R² fijos 0.000.
- Saudi Arabian Grand Prix medium__brake_point_rel (auto, con_iqr0): piloto 0.188 [0.147, 0.244], equipo 0.000, stint 0.000, residual 0.812, R² fijos 0.006.
- Saudi Arabian Grand Prix medium__full_throttle_frac (auto, con_iqr0): piloto 0.101 [0.071, 0.365], equipo 0.136, stint 0.063, residual 0.700, R² fijos 0.003.
- Saudi Arabian Grand Prix fast__full_throttle_frac (auto, con_iqr0): piloto 0.000 [0.000, 0.072], equipo 0.000, stint 0.032, residual 0.968, R² fijos 0.009.
- Saudi Arabian Grand Prix medium__throttle_attack (estilo, con_iqr0): piloto 0.050 [0.027, 0.134], equipo 0.087, stint 0.026, residual 0.837, R² fijos 0.002.
- Saudi Arabian Grand Prix slow__trail_brake_frac (estilo, sin_iqr0): piloto 0.000 [0.000, 0.119], equipo 0.205, stint 0.066, residual 0.728, R² fijos 0.004.
- Saudi Arabian Grand Prix fast__trail_brake_frac (estilo, con_iqr0): piloto — [—, —], equipo —, stint —, residual —, R² fijos —.
- Saudi Arabian Grand Prix slow__throttle_attack (estilo, con_iqr0): piloto 0.020 [0.016, 0.104], equipo 0.183, stint 0.042, residual 0.755, R² fijos 0.004.
- Saudi Arabian Grand Prix slow__trail_brake_frac (estilo, con_iqr0): piloto 0.000 [0.000, 0.113], equipo 0.205, stint 0.066, residual 0.728, R² fijos 0.004.
- Saudi Arabian Grand Prix medium__trail_brake_frac (estilo, con_iqr0): piloto 0.038 [0.020, 0.145], equipo 0.202, stint 0.020, residual 0.740, R² fijos 0.026.
- Saudi Arabian Grand Prix medium__apex_speed_rel (auto, sin_iqr0): piloto 0.000 [0.000, 0.109], equipo 0.336, stint 0.071, residual 0.594, R² fijos 0.026.
- Saudi Arabian Grand Prix fast__apex_speed_rel (auto, sin_iqr0): piloto 0.011 [0.009, 0.062], equipo 0.028, stint 0.000, residual 0.961, R² fijos 0.001.
- Saudi Arabian Grand Prix medium__brake_point_rel (auto, sin_iqr0): piloto 0.188 [0.137, 0.251], equipo 0.000, stint 0.000, residual 0.812, R² fijos 0.006.
- Saudi Arabian Grand Prix slow__apex_speed_rel (auto, sin_iqr0): piloto 0.000 [0.000, 0.076], equipo 0.071, stint 0.078, residual 0.851, R² fijos 0.000.
- Saudi Arabian Grand Prix fast__coast_frac (estilo, con_iqr0): piloto 0.000 [0.000, 0.092], equipo 0.000, stint 0.050, residual 0.950, R² fijos 0.005.
- Saudi Arabian Grand Prix slow__brake_point_rel (auto, con_iqr0): piloto 0.000 [0.000, 0.167], equipo 0.303, stint 0.126, residual 0.571, R² fijos 0.018.
- Saudi Arabian Grand Prix slow__coast_frac (estilo, con_iqr0): piloto 0.026 [0.000, 0.239], equipo 0.434, stint 0.080, residual 0.461, R² fijos 0.001.
- Saudi Arabian Grand Prix medium__coast_frac (estilo, con_iqr0): piloto 0.153 [0.068, 0.290], equipo 0.371, stint 0.025, residual 0.451, R² fijos 0.001.
- Saudi Arabian Grand Prix medium__apex_speed_rel (auto, con_iqr0): piloto 0.000 [0.000, 0.094], equipo 0.336, stint 0.071, residual 0.594, R² fijos 0.026.
- Saudi Arabian Grand Prix fast__apex_speed_rel (auto, con_iqr0): piloto 0.011 [0.007, 0.068], equipo 0.028, stint 0.000, residual 0.961, R² fijos 0.001.
- Saudi Arabian Grand Prix slow__full_throttle_frac (auto, con_iqr0): piloto 0.065 [0.040, 0.183], equipo 0.055, stint 0.041, residual 0.840, R² fijos 0.003.
- Canadian Grand Prix slow__apex_speed_rel (auto, con_iqr0): piloto 0.000 [0.000, 0.410], equipo 0.113, stint 0.008, residual 0.879, R² fijos 0.027.
- Canadian Grand Prix medium__coast_frac (estilo, con_iqr0): piloto 0.000 [0.000, 0.145], equipo 0.254, stint 0.000, residual 0.746, R² fijos 0.041.
- Canadian Grand Prix slow__coast_frac (estilo, con_iqr0): piloto 0.008 [0.000, 0.464], equipo 0.290, stint 0.000, residual 0.702, R² fijos 0.033.
- Canadian Grand Prix fast__apex_speed_rel (auto, sin_iqr0): piloto 0.000 [0.000, 0.441], equipo 0.000, stint 0.123, residual 0.877, R² fijos 0.021.
- Canadian Grand Prix medium__apex_speed_rel (auto, sin_iqr0): piloto 0.200 [0.114, 0.491], equipo 0.000, stint 0.057, residual 0.743, R² fijos 0.008.
- Canadian Grand Prix slow__apex_speed_rel (auto, sin_iqr0): piloto 0.000 [0.000, 0.436], equipo 0.113, stint 0.008, residual 0.879, R² fijos 0.027.
- Canadian Grand Prix medium__brake_point_rel (auto, sin_iqr0): piloto 0.235 [0.000, 0.482], equipo 0.000, stint 0.061, residual 0.704, R² fijos 0.006.
- Canadian Grand Prix medium__coast_frac (estilo, sin_iqr0): piloto 0.000 [0.000, 0.122], equipo 0.254, stint 0.000, residual 0.746, R² fijos 0.041.
- Canadian Grand Prix slow__brake_point_rel (auto, sin_iqr0): piloto 0.000 [0.000, 0.461], equipo 0.181, stint 0.172, residual 0.646, R² fijos 0.009.
- Canadian Grand Prix slow__coast_frac (estilo, sin_iqr0): piloto 0.008 [0.000, 0.570], equipo 0.290, stint 0.000, residual 0.702, R² fijos 0.033.
- Canadian Grand Prix fast__full_throttle_frac (auto, sin_iqr0): piloto 0.000 [0.000, 0.764], equipo 0.171, stint 0.496, residual 0.333, R² fijos 0.074.
- Canadian Grand Prix slow__throttle_attack (estilo, sin_iqr0): piloto 0.000 [0.000, 0.296], equipo 0.000, stint 0.330, residual 0.670, R² fijos 0.001.
- Canadian Grand Prix medium__throttle_attack (estilo, sin_iqr0): piloto 0.000 [0.000, 0.515], equipo 0.140, stint 0.252, residual 0.608, R² fijos 0.000.
- Canadian Grand Prix slow__full_throttle_frac (auto, sin_iqr0): piloto 0.000 [0.000, 0.252], equipo 0.077, stint 0.024, residual 0.899, R² fijos 0.007.
- Canadian Grand Prix medium__full_throttle_frac (auto, sin_iqr0): piloto 0.000 [0.000, 0.210], equipo 0.000, stint 0.189, residual 0.811, R² fijos 0.003.
- Canadian Grand Prix slow__trail_brake_frac (estilo, sin_iqr0): piloto 0.000 [0.000, 0.234], equipo 0.157, stint 0.005, residual 0.837, R² fijos 0.005.
- Canadian Grand Prix medium__trail_brake_frac (estilo, sin_iqr0): piloto 0.324 [0.000, 0.569], equipo 0.000, stint 0.000, residual 0.676, R² fijos 0.011.
- Canadian Grand Prix fast__apex_speed_rel (auto, con_iqr0): piloto 0.000 [0.000, 0.514], equipo 0.000, stint 0.123, residual 0.877, R² fijos 0.021.
- Canadian Grand Prix medium__apex_speed_rel (auto, con_iqr0): piloto 0.200 [0.082, 0.491], equipo 0.000, stint 0.057, residual 0.743, R² fijos 0.008.
- Canadian Grand Prix fast__coast_frac (estilo, con_iqr0): piloto 0.057 [0.000, 0.117], equipo 0.107, stint 0.000, residual 0.837, R² fijos 0.125.
- Canadian Grand Prix slow__brake_point_rel (auto, con_iqr0): piloto 0.000 [0.000, 0.516], equipo 0.181, stint 0.172, residual 0.646, R² fijos 0.009.
- Canadian Grand Prix medium__brake_point_rel (auto, con_iqr0): piloto 0.235 [0.025, 0.461], equipo 0.000, stint 0.061, residual 0.704, R² fijos 0.006.
- Canadian Grand Prix medium__trail_brake_frac (estilo, con_iqr0): piloto 0.324 [0.015, 0.627], equipo 0.000, stint 0.000, residual 0.676, R² fijos 0.011.
- Canadian Grand Prix slow__throttle_attack (estilo, con_iqr0): piloto 0.000 [0.000, 0.330], equipo 0.000, stint 0.330, residual 0.670, R² fijos 0.001.
- Canadian Grand Prix fast__trail_brake_frac (estilo, con_iqr0): piloto 0.044 [0.000, 0.065], equipo 0.189, stint 0.000, residual 0.767, R² fijos 0.034.
- Canadian Grand Prix slow__full_throttle_frac (auto, con_iqr0): piloto 0.000 [0.000, 0.292], equipo 0.077, stint 0.024, residual 0.899, R² fijos 0.007.
- Canadian Grand Prix slow__trail_brake_frac (estilo, con_iqr0): piloto 0.000 [0.000, 0.218], equipo 0.157, stint 0.005, residual 0.837, R² fijos 0.005.
- Canadian Grand Prix medium__throttle_attack (estilo, con_iqr0): piloto 0.000 [0.000, 0.487], equipo 0.140, stint 0.252, residual 0.608, R² fijos 0.000.
- Canadian Grand Prix fast__full_throttle_frac (auto, con_iqr0): piloto 0.000 [0.000, 0.745], equipo 0.171, stint 0.496, residual 0.333, R² fijos 0.074.
- Canadian Grand Prix medium__full_throttle_frac (auto, con_iqr0): piloto 0.000 [0.000, 0.130], equipo 0.000, stint 0.189, residual 0.811, R² fijos 0.003.

Media no ponderada de esas proporciones, por familia. No es un modelo conjunto.

- Canadian Grand Prix auto (con_iqr0): piloto 0.054, equipo 0.068, features 8.
- Canadian Grand Prix auto (sin_iqr0): piloto 0.054, equipo 0.068, features 8.
- Canadian Grand Prix estilo (con_iqr0): piloto 0.054, equipo 0.142, features 8.
- Canadian Grand Prix estilo (sin_iqr0): piloto 0.055, equipo 0.140, features 6.
- Chinese Grand Prix auto (con_iqr0): piloto 0.102, equipo 0.097, features 8.
- Chinese Grand Prix auto (sin_iqr0): piloto 0.102, equipo 0.097, features 8.
- Chinese Grand Prix estilo (con_iqr0): piloto 0.135, equipo 0.142, features 8.
- Chinese Grand Prix estilo (sin_iqr0): piloto 0.166, equipo 0.147, features 6.
- Saudi Arabian Grand Prix auto (con_iqr0): piloto 0.046, equipo 0.116, features 8.
- Saudi Arabian Grand Prix auto (sin_iqr0): piloto 0.052, equipo 0.133, features 7.
- Saudi Arabian Grand Prix estilo (con_iqr0): piloto 0.041, equipo 0.212, features 7.
- Saudi Arabian Grand Prix estilo (sin_iqr0): piloto 0.048, equipo 0.247, features 6.
- Canadian Grand Prix auto (con_iqr0): piloto 0.054, equipo 0.068, features 8.
- Canadian Grand Prix auto (sin_iqr0): piloto 0.054, equipo 0.068, features 8.
- Canadian Grand Prix estilo (con_iqr0): piloto 0.054, equipo 0.142, features 8.
- Canadian Grand Prix estilo (sin_iqr0): piloto 0.055, equipo 0.140, features 6.
- Chinese Grand Prix auto (con_iqr0): piloto 0.102, equipo 0.097, features 8.
- Chinese Grand Prix auto (sin_iqr0): piloto 0.102, equipo 0.097, features 8.
- Chinese Grand Prix estilo (con_iqr0): piloto 0.135, equipo 0.142, features 8.
- Chinese Grand Prix estilo (sin_iqr0): piloto 0.166, equipo 0.147, features 6.
- Saudi Arabian Grand Prix auto (con_iqr0): piloto 0.046, equipo 0.116, features 8.
- Saudi Arabian Grand Prix auto (sin_iqr0): piloto 0.052, equipo 0.133, features 7.
- Saudi Arabian Grand Prix estilo (con_iqr0): piloto 0.041, equipo 0.212, features 7.
- Saudi Arabian Grand Prix estilo (sin_iqr0): piloto 0.048, equipo 0.247, features 6.

Ritmo. η² del tiempo de vuelta sobre la clase, y de la posición de grilla sobre la clase modal.

- Chinese Grand Prix lap_time_s vuelta: 0.048 (n 909).
- Chinese Grand Prix lap_time_s mediana_clase_2: 97.110 (n 218).
- Chinese Grand Prix lap_time_s mediana_clase_1: 97.837 (n 327).
- Chinese Grand Prix lap_time_s mediana_clase_0: 97.823 (n 161).
- Chinese Grand Prix lap_time_s mediana_clase_3: 97.755 (n 203).
- Saudi Arabian Grand Prix lap_time_s mediana_clase_1: 94.591 (n 652).
- Saudi Arabian Grand Prix lap_time_s mediana_clase_0: 161.065 (n 4).
- Saudi Arabian Grand Prix lap_time_s vuelta: 0.944 (n 656).
- Canadian Grand Prix lap_time_s mediana_clase_0: 77.815 (n 10).
- Canadian Grand Prix lap_time_s vuelta: 0.002 (n 76).
- Canadian Grand Prix lap_time_s mediana_clase_1: 77.689 (n 66).

Calibración, 10 emparejamientos falsos. Media del percentil: 50.4.

Control del residuo de equipo. La simetría en datos permutados es el artefacto. La tasa del intervalo es el método de este módulo.

- Chinese Grand Prix Ferrari HAM-LEC: simetría 0.1611, separa residuos True, tasa separa permutada 0.150, tasa IC excluye 0 en la permutación 0.000.
- Chinese Grand Prix Haas F1 Team BEA-OCO: simetría 0.0612, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación 0.000.
- Chinese Grand Prix McLaren NOR-PIA: simetría 0.1550, separa residuos True, tasa separa permutada 0.500, tasa IC excluye 0 en la permutación 0.000.
- Chinese Grand Prix Kick Sauber BOR-HUL: simetría 0.0700, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación 0.100.
- Chinese Grand Prix Alpine DOO-GAS: simetría 0.2713, separa residuos True, tasa separa permutada 0.200, tasa IC excluye 0 en la permutación 0.425.
- Chinese Grand Prix Aston Martin ALO-STR: simetría —, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación —.
- Chinese Grand Prix Racing Bulls HAD-TSU: simetría 0.0886, separa residuos False, tasa separa permutada 0.100, tasa IC excluye 0 en la permutación 0.125.
- Chinese Grand Prix Mercedes ANT-RUS: simetría 0.0000, separa residuos True, tasa separa permutada 0.025, tasa IC excluye 0 en la permutación 0.000.
- Chinese Grand Prix Williams ALB-SAI: simetría 0.0902, separa residuos False, tasa separa permutada 0.200, tasa IC excluye 0 en la permutación 0.200.
- Chinese Grand Prix Red Bull Racing LAW-VER: simetría 0.2472, separa residuos True, tasa separa permutada 0.050, tasa IC excluye 0 en la permutación 0.025.
- Saudi Arabian Grand Prix Aston Martin ALO-STR: simetría 1.0999, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación 0.000.
- Saudi Arabian Grand Prix Alpine DOO-GAS: simetría —, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación —.
- Saudi Arabian Grand Prix Haas F1 Team BEA-OCO: simetría 0.3170, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación 0.125.
- Saudi Arabian Grand Prix Ferrari HAM-LEC: simetría 1.1896, separa residuos True, tasa separa permutada 0.150, tasa IC excluye 0 en la permutación 0.225.
- Saudi Arabian Grand Prix McLaren NOR-PIA: simetría 0.3536, separa residuos True, tasa separa permutada 0.700, tasa IC excluye 0 en la permutación 0.525.
- Saudi Arabian Grand Prix Kick Sauber BOR-HUL: simetría 0.7080, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación 0.450.
- Saudi Arabian Grand Prix Red Bull Racing TSU-VER: simetría —, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación —.
- Saudi Arabian Grand Prix Williams ALB-SAI: simetría 0.1729, separa residuos True, tasa separa permutada 0.050, tasa IC excluye 0 en la permutación 0.475.
- Saudi Arabian Grand Prix Mercedes ANT-RUS: simetría 1.3781, separa residuos False, tasa separa permutada 0.075, tasa IC excluye 0 en la permutación 0.200.
- Saudi Arabian Grand Prix Racing Bulls HAD-LAW: simetría 0.6183, separa residuos True, tasa separa permutada 0.200, tasa IC excluye 0 en la permutación 0.350.
- Canadian Grand Prix Williams ALB-SAI: simetría —, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación —.
- Canadian Grand Prix Red Bull Racing TSU-VER: simetría —, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación —.
- Canadian Grand Prix Mercedes nan-nan: simetría —, separa residuos nan, tasa separa permutada —, tasa IC excluye 0 en la permutación —.
- Canadian Grand Prix Racing Bulls HAD-LAW: simetría —, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación —.
- Canadian Grand Prix Aston Martin ALO-STR: simetría 0.0000, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación 0.350.
- Canadian Grand Prix Alpine COL-GAS: simetría —, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación —.
- Canadian Grand Prix Ferrari HAM-LEC: simetría —, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación —.
- Canadian Grand Prix Haas F1 Team BEA-OCO: simetría —, separa residuos False, tasa separa permutada 0.000, tasa IC excluye 0 en la permutación —.
- Canadian Grand Prix Kick Sauber BOR-HUL: simetría 5.3770, separa residuos True, tasa separa permutada 0.700, tasa IC excluye 0 en la permutación 0.400.
- Canadian Grand Prix McLaren nan-nan: simetría —, separa residuos nan, tasa separa permutada —, tasa IC excluye 0 en la permutación —.

Lawson y Tsunoda. Si la muestra no cruza el cambio de equipo, la función queda en no aplica.

- piloto=LAW, aplica=True, motivo=, race=Chinese Grand Prix, fase=antes, equipo=Red Bull Racing, companero=VER, distancia=2.437646492365618
- piloto=LAW, aplica=True, motivo=, race=Saudi Arabian Grand Prix, fase=despues, equipo=Racing Bulls, companero=HAD, distancia=1.8019461748406207
- piloto=LAW, aplica=True, motivo=, race=Canadian Grand Prix, fase=despues, equipo=Racing Bulls, companero=HAD
- piloto=LAW, aplica=True, motivo=, fase=resumen, distancia_antes=2.437646492365618, distancia_despues=1.8019461748406207, se_acerca_al_companero_nuevo=True
- piloto=TSU, aplica=True, motivo=, race=Chinese Grand Prix, fase=antes, equipo=Racing Bulls, companero=HAD, distancia=4.200404964921252
- piloto=TSU, aplica=True, motivo=, race=Saudi Arabian Grand Prix, fase=despues, equipo=Red Bull Racing, companero=VER
- piloto=TSU, aplica=True, motivo=, race=Canadian Grand Prix, fase=despues, equipo=Red Bull Racing, companero=VER
- piloto=TSU, aplica=True, motivo=, fase=resumen, distancia_antes=4.200404964921252, se_acerca_al_companero_nuevo=False

Las cifras de esta sección salen de los CSV de este directorio, escritos por la misma corrida.
