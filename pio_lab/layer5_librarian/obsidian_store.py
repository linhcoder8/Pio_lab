"""Obsidian task-note archive store for the Knowledge Librarian."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pio_lab.memory.obsidian.vault import Vault
from pio_lab.utils.helpers import utc_now

SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


class ObsidianTaskStore:
    """Write archived tasks as markdown notes inside the vault."""

    def __init__(
        self,
        *,
        vault: Vault | None = None,
        vault_root: str | Path | None = None,
    ) -> None:
        self.vault = vault or Vault(vault_root)

    def write_task_note(
        self,
        *,
        task_id: str,
        user_id: str,
        channel: str,
        request: dict[str, Any],
        plan: dict[str, Any] | None,
        final_output: dict[str, Any] | None,
        status: str,
        dispatch_results: list[dict[str, Any]] | None = None,
        created_at: datetime | None = None,
    ) -> dict[str, str]:
        """Create the canonical task note under tasks/YYYY-MM-DD."""
        timestamp = created_at or utc_now()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        date_part = timestamp.astimezone(UTC).date().isoformat()
        safe_task_id = SAFE_FILENAME_RE.sub("_", task_id).strip("_") or "task"
        relative_path = f"tasks/{date_part}/{safe_task_id}.md"
        note_path = self.vault.write(
            relative_path,
            _render_task_note(
                task_id=task_id,
                user_id=user_id,
                channel=channel,
                request=request,
                plan=plan,
                final_output=final_output,
                status=status,
                dispatch_results=dispatch_results or [],
                created_at=timestamp,
            ),
        )
        return {"relative_path": relative_path, "path": str(note_path)}


def _render_task_note(
    *,
    task_id: str,
    user_id: str,
    channel: str,
    request: dict[str, Any],
    plan: dict[str, Any] | None,
    final_output: dict[str, Any] | None,
    status: str,
    dispatch_results: list[dict[str, Any]],
    created_at: datetime,
) -> str:
    request_text = str(request.get("input") or request.get("message") or request)
    output_text = _output_text(final_output)
    return "\n".join(
        [
            "---",
            f"task_id: {_yaml_scalar(task_id)}",
            f"user_id: {_yaml_scalar(user_id)}",
            f"channel: {_yaml_scalar(channel)}",
            f"created_at: {_yaml_scalar(created_at.isoformat())}",
            f"status: {_yaml_scalar(status)}",
            "---",
            "",
            "# Request",
            request_text,
            "",
            "# Plan",
            _format_plan(plan),
            "",
            "# Output",
            output_text,
            "",
            "# Trace",
            _format_trace(dispatch_results),
            "",
        ]
    )


def _format_plan(plan: dict[str, Any] | None) -> str:
    if not plan:
        return "_No plan captured._"
    steps = plan.get("steps")
    if isinstance(steps, list) and steps:
        return "\n".join(
            f"- {step.get('id', 'step')}: {step.get('routing_key') or step.get('department')}"
            for step in steps
            if isinstance(step, dict)
        )
    return f"```json\n{json.dumps(plan, ensure_ascii=False, indent=2, default=str)}\n```"


def _output_text(final_output: dict[str, Any] | None) -> str:
    if not final_output:
        return "_No final output captured._"
    text = final_output.get("text")
    if text:
        return str(text)
    return f"```json\n{json.dumps(final_output, ensure_ascii=False, indent=2, default=str)}\n```"


def _format_trace(dispatch_results: list[dict[str, Any]]) -> str:
    if not dispatch_results:
        return "_No dispatch trace captured._"
    lines = []
    for result in dispatch_results:
        step = result.get("step_id") or "step"
        department = result.get("department_id") or "unknown"
        worker = result.get("worker_id") or "unknown"
        routing_key = result.get("routing_key") or ""
        lines.append(f"- {step}: {department}.{worker} ({routing_key})")
    return "\n".join(lines)


def _yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


__all__ = ["ObsidianTaskStore"]
