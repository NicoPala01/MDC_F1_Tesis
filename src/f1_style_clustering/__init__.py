"""
f1_style_clustering: Formula 1 Driving Style Classification through Telemetry Clustering.

Master's Thesis Project - Universidad Austral
Author: Nicolás Palavecino
"""

__version__ = "0.1.0"
__author__ = "Nicolás Palavecino"

from .config import load_config, load_circuit_config
from .pipeline import run_pipeline_b

__all__ = [
    "load_config",
    "load_circuit_config",
    "run_pipeline_b",
]

