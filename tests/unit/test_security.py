"""Tests for M5 security enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest

from pio_lab.security.enforcer import SecurityEnforcer, SecurityError
from pio_lab.security.policy_loader import load_policy


@pytest.fixture
def security_enforcer() -> SecurityEnforcer:
    return SecurityEnforcer(load_policy())


def test_file_outside_project_is_rejected(
    security_enforcer: SecurityEnforcer,
    tmp_path: Path,
) -> None:
    outside_file = tmp_path / "outside.txt"

    assert security_enforcer.check_file_access(outside_file) is False
    with pytest.raises(SecurityError):
        security_enforcer.require_file_access(outside_file)


def test_file_inside_project_is_allowed(security_enforcer: SecurityEnforcer) -> None:
    inside_file = Path("config/pio_lab.yaml")

    assert security_enforcer.check_file_access(inside_file) is True


def test_forbidden_extension_is_rejected(security_enforcer: SecurityEnforcer) -> None:
    secret_file = Path("tmp/private.pem")

    assert security_enforcer.check_file_access(secret_file) is False


def test_api_key_output_is_masked(security_enforcer: SecurityEnforcer) -> None:
    text = "Here's my key sk-abcdefghijklmnopqrstuvwxyz123456"

    masked = security_enforcer.mask_secrets_in_output(text)

    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in masked
    assert "sk-...3456" in masked


def test_sensitive_action_requires_approval(security_enforcer: SecurityEnforcer) -> None:
    assert security_enforcer.requires_approval("send_email") is True
    assert security_enforcer.requires_approval("read_note") is False


def test_crypto_seed_phrase_is_blocked(security_enforcer: SecurityEnforcer) -> None:
    text = "Please store this seed phrase in memory"

    assert security_enforcer.check_crypto_keywords(text) is False
    with pytest.raises(SecurityError):
        security_enforcer.require_crypto_safe_text(text)
