"""Shared pytest environment isolation."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_local_runtime_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep local .env live modes from changing deterministic tests."""
    monkeypatch.setenv("DEPARTMENT_WORKER_MODE", "deterministic")
    monkeypatch.setenv("PROVIDER_ROUTING_PROFILE", "")
