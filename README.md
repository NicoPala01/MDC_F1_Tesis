# Los datos al volante

Tesis de Maestría en Ciencia de Datos — Universidad Austral  
Autor: Nicolás Palavecino  
Tutor: Ezequiel Nuske

Clustering no supervisado de **perfiles observables** de telemetría FastF1. Los clústeres describen patrones de una sesión; no aíslan estilo causal (FastF1 no trae carga de combustible ni setup). Team / Compound / TyreLife se residualizan cuando existen.

## Qué calcula

1. **Por carrera:** vueltas canónicas → ventanas ZOI en las curvas clave (frenado | vértice | salida) → features por fragmento, relativas a la mediana de la sesión por tipología → **un vector por vuelta** → K-means++ de las vueltas. El perfil del piloto es la **clase modal**: la que concentra más vueltas suyas. `driver_lap_distribution.csv` es el reparto.
2. **Temporada:** el mismo análisis en cada GP. La tendencia de temporada es el arquetipo modal más frecuente entre las carreras. `stability.csv` mide en cuántas el piloto coincide con esa tendencia. No hay un segundo clustering de vectores medianos.

Circuito de prueba: **Monza** (`Italian Grand Prix`). El resto de la temporada usa `key_corners` si el evento está en `config/circuits.yaml`; si no, fallback por curva FastF1 y colapso a slow/medium/fast.

## Instalación

Desde la raíz del repo (no desde `scripts/`). El paquete vive en `src/`; hay que instalarlo en el entorno activo:

```bash
python -m pip install -e ".[dev]"
```

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Corrida

```bash
# Monza 2025, una sesión
python scripts/run_pipeline.py --smoke

# Todas las carreras 2025 + clustering global
python scripts/run_pipeline.py --season 2025
```

Salida: `results/2025/italian_grand_prix/` (`lap_classifications.csv`, `driver_lap_distribution.csv`, `driver_profiles.csv`) y `results/2025/season/`.

Un GP suelto: `python scripts/run_pipeline.py --circuit "British Grand Prix"`.

Tablero (circuito y piloto, distribución y perfil del GP):

```bash
python -m pip install -e ".[dashboard]"
streamlit run app/dashboard.py
```

Tests (sintéticos, sin red): `python -m pytest -v`.

## Notebooks

Ejecutar en orden con cache FastF1 local. El 04 solo lee resultados del CLI de temporada.

- `01_monza_laps_and_zoi.ipynb` — filtro, mapa ZOI, telemetría partida
- `02_monza_lap_profiles.ipynb` — tabla larga de features por zona
- `03_monza_clustering.ipynb` — exploración de k, PCA y radar
- `04_season_results.ipynb` — tendencia modal por GP y heatmap piloto × GP
