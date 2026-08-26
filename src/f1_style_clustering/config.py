"""Configuration loader and utilities for f1_style_clustering."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Load and parse a YAML file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load the main pipeline configuration."""
    if config_path:
        path = Path(config_path)
    else:
        path = DEFAULT_CONFIG_DIR / "pipeline_config.yaml"
    return load_yaml(path)


def load_circuit_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load the circuit and corner typology configuration."""
    if config_path:
        path = Path(config_path)
    else:
        path = DEFAULT_CONFIG_DIR / "circuits.yaml"
    return load_yaml(path)

