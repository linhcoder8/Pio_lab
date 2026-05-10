"""Shared helpers for concrete Layer 4 workers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pio_lab.security.enforcer import SecurityEnforcer, enforcer
from pio_lab.security.policy_loader import PROJECT_ROOT
from pio_lab.utils.env import get_settings


def resolve_output_dir(
    task: dict[str, Any],
    context: dict[str, Any] | None,
    *default_parts: str,
    security: SecurityEnforcer | None = None,
) -> Path:
    """Resolve and create an output directory inside the approved workspace."""
    policy = security or enforcer
    context = context or {}
    requested = task.get("output_dir") or context.get("output_dir")
    candidate = Path(str(requested)) if requested else PROJECT_ROOT.joinpath(*default_parts)
    resolved = policy.require_file_access(candidate)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def count_words(text: str) -> int:
    """Count whitespace-separated words in generated prose."""
    return len([word for word in text.split() if word.strip()])


def should_use_provider_worker(
    task: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> bool:
    """Return whether a concrete worker should delegate text generation to ProviderRouter."""
    context = context or {}
    explicit = task.get("worker_mode") or context.get("worker_mode")
    if explicit:
        return str(explicit).strip().lower() in {"provider", "live", "llm"}
    mode = (
        os.environ["DEPARTMENT_WORKER_MODE"]
        if "DEPARTMENT_WORKER_MODE" in os.environ
        else get_settings().department_worker_mode
    )
    return mode.strip().lower() in {
        "provider",
        "live",
        "llm",
    }


def provider_task(
    task: dict[str, Any],
    *,
    instruction: str,
) -> dict[str, Any]:
    """Append provider-mode instructions without mutating the caller's task."""
    user_input = str(task.get("input") or task.get("task") or "")
    return {
        **task,
        "input": f"{user_input}\n\nTask instructions:\n{instruction}".strip(),
    }


__all__ = ["count_words", "provider_task", "resolve_output_dir", "should_use_provider_worker"]
