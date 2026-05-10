"""Shared helpers for concrete Layer 4 workers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pio_lab.security.enforcer import SecurityEnforcer, enforcer
from pio_lab.security.policy_loader import PROJECT_ROOT


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


__all__ = ["count_words", "resolve_output_dir"]
