"""Tests for M0 foundation utilities."""

from __future__ import annotations

import pytest

from pio_lab.utils.config_loader import (
    clear_config_cache,
    load_pio_lab_config,
    load_providers_config,
    load_security_policy,
)
from pio_lab.utils.env import Settings
from pio_lab.utils.logging import setup_logging


def test_load_pio_lab_config_returns_main_config() -> None:
    clear_config_cache()

    config = load_pio_lab_config()

    assert config["app"]["name"] == "Pio_lab"
    assert "channels" in config


def test_load_providers_config_is_cached() -> None:
    clear_config_cache()

    first = load_providers_config()
    second = load_providers_config()

    assert first is second
    assert "routing_rules" in first


def test_load_security_policy_returns_mapping() -> None:
    clear_config_cache()

    policy = load_security_policy()

    assert isinstance(policy, dict)
    assert policy


def test_settings_builds_async_postgres_dsn() -> None:
    settings = Settings(
        postgres_host="db.local",
        postgres_port=5544,
        postgres_db="pio_lab_test",
        postgres_user="pio",
        postgres_password="secret value",
    )

    assert settings.postgres_dsn == (
        "postgresql+asyncpg://pio:secret+value@db.local:5544/pio_lab_test"
    )


def test_settings_rejects_invalid_port() -> None:
    with pytest.raises(ValueError):
        Settings(postgres_port=70000)


def test_setup_logging_supports_text_and_json_modes() -> None:
    text_logger = setup_logging("INFO", json=False)
    json_logger = setup_logging("DEBUG", json=True)

    assert text_logger is json_logger
