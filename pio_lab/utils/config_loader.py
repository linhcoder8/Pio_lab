"""Cached YAML config loaders."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_ROOT = Path(__file__).resolve().parents[2] / "config"


@lru_cache(maxsize=16)
def _load_yaml(filename: str) -> dict[str, Any]:
    path = CONFIG_ROOT / filename
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {path}")

    return data


def load_pio_lab_config() -> dict[str, Any]:
    """Load the main application config."""
    return _load_yaml("pio_lab.yaml")


def load_providers_config() -> dict[str, Any]:
    """Load provider routing config."""
    return _load_yaml("providers.yaml")


def load_security_policy() -> dict[str, Any]:
    """Load default security policy config."""
    return _load_yaml("security_policy.yaml")


def load_department_config(relative_path: str) -> dict[str, Any]:
    """Load a department config below config/departments."""
    return _load_yaml(f"departments/{relative_path}")


def clear_config_cache() -> None:
    """Clear cached YAML configs, useful in tests and hot reload paths."""
    _load_yaml.cache_clear()


__all__ = [
    "CONFIG_ROOT",
    "clear_config_cache",
    "load_department_config",
    "load_pio_lab_config",
    "load_providers_config",
    "load_security_policy",
]
