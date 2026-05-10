"""Access wrapper and generator for vault/AGENTS.md."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pio_lab.memory.obsidian.vault import Vault


class AgentsMd:
    """Read, update, and regenerate the agent registry note."""

    filename = "AGENTS.md"

    def __init__(self, vault: Vault | None = None) -> None:
        self.vault = vault or Vault()

    def get(self) -> str:
        """Return AGENTS.md content."""
        return self.vault.read(self.filename)

    def set(self, content: str) -> Path:
        """Replace AGENTS.md content."""
        return self.vault.write(self.filename, content)

    def regenerate(self, registry: Any) -> str:
        """Regenerate AGENTS.md from a department registry object or mapping."""
        departments = _extract_departments(registry)
        lines = [
            "# Agents Registry",
            "",
            "> Auto-generated from the department registry.",
            "",
        ]

        for department in departments:
            department_id = _get_value(department, "id", "unknown")
            name = _get_value(department, "name", department_id)
            name_vi = _get_value(department, "name_vi", "")
            enabled = _get_value(department, "enabled", True)
            workers = _format_workers(_get_value(department, "workers", []))

            lines.extend(
                [
                    f"## {name} (`{department_id}`)",
                    f"- Status: {'enabled' if enabled else 'disabled'}",
                    f"- Vietnamese name: {name_vi}" if name_vi else "- Vietnamese name: n/a",
                    f"- Workers: {workers}",
                    "",
                ]
            )

        content = "\n".join(lines).rstrip() + "\n"
        self.set(content)
        return content


def _extract_departments(registry: Any) -> list[Any]:
    if isinstance(registry, dict):
        departments = registry.get("departments", [])
    else:
        departments = getattr(registry, "departments", [])
        if callable(departments):
            departments = departments()

    if isinstance(departments, dict):
        departments = departments.values()

    if not isinstance(departments, Iterable) or isinstance(departments, (str, bytes)):
        raise TypeError("registry departments must be an iterable")

    return list(departments)


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _format_workers(workers: Any) -> str:
    if not workers:
        return "none"
    if isinstance(workers, (str, bytes)):
        return str(workers)
    if isinstance(workers, dict):
        workers = workers.values()
    if not isinstance(workers, Iterable):
        return str(workers)

    names = [str(_get_value(worker, "id", worker)) for worker in workers]
    return ", ".join(names) if names else "none"


__all__ = ["AgentsMd"]
