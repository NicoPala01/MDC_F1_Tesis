# Método medible con FastF1

El perfil de un piloto en un Gran Premio no es la mediana de su telemetría. Es la tendencia de sus vueltas ya clasificadas.

1. Curvas clave de `config/circuits.yaml` (no cada número FastF1; eso queda para ampliar las zonas). Cada zona se parte en frenado, vértice y salida.
2. Cada vuelta canónica se mide en esas zonas. Las features quedan relativas a la mediana de la sesión por tipología (`slow`, `medium`, `fast`).
3. Una vuelta es un vector: un bloque de features por tipología. Si le falta una tipología de la sesión, no entra.
4. K-means clasifica las vueltas. Una clase tiene que cubrir al menos el 5 % de las vueltas de la sesión (mínimo 3).
5. El reporte del piloto es el conteo y la fracción de vueltas en cada clase. El arquetipo del GP es la clase modal.

Salidas por GP: `lap_classifications.csv`, `driver_lap_distribution.csv`, `driver_profiles.csv`.

Temporada: la tendencia es el arquetipo modal más repetido entre los GP. `stability.csv` es la fracción de carreras que coinciden. No se vuelve a clusterizar un vector mediano.

El tablero `app/dashboard.py` elige circuito y piloto y muestra nombre, equipo, perfil del GP, la distribución de vueltas y las medianas de las métricas.
