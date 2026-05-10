"""Deterministic QA reviewer for M9 department dispatch."""

from __future__ import annotations

import json
import re
from typing import Any

from pio_lab.layer4_departments.base.worker_base import GenericWorker


SECRET_PATTERNS = (
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"AIza[a-zA-Z0-9_-]{35}"),
    re.compile(r"xoxb-[a-zA-Z0-9-]+"),
)


class QaReviewerWorker(GenericWorker):
    """Return PASS/NEEDS_FIX JSON for downstream orchestration."""

    async def run(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Review output and return a structured JSON verdict."""
        output = _candidate_output(task, context or {})
        qa = _review(output)
        output_json = json.dumps(qa, ensure_ascii=False)
        result = {
            "worker_id": self.config.id,
            "department_id": self.config.department,
            "routing_key": self.config.provider_routing_key,
            "output": output_json,
            "qa": qa,
        }
        await self.log_internal_trace(
            task=task,
            output=result,
            status="success" if qa["verdict"] == "PASS" else "needs_fix",
            metadata={"reviewed_chars": len(output)},
        )
        return result


def _candidate_output(task: dict[str, Any], context: dict[str, Any]) -> str:
    explicit = task.get("output") or context.get("output")
    if explicit:
        return str(explicit)
    previous_results = context.get("previous_results") or []
    if isinstance(previous_results, list) and previous_results:
        return str(previous_results[-1].get("output") or "")
    return str(task.get("input") or task.get("task") or "")


def _review(output: str) -> dict[str, Any]:
    issues: list[str] = []
    if not output.strip():
        issues.append("Output is empty.")
    if "NEEDS_FIX_ME" in output:
        issues.append("Output contains explicit failure marker.")
    if any(pattern.search(output) for pattern in SECRET_PATTERNS):
        issues.append("Output appears to contain an API key or token.")

    verdict = "NEEDS_FIX" if issues else "PASS"
    return {
        "verdict": verdict,
        "score": 60 if issues else 95,
        "issues": issues,
        "suggestions": [] if not issues else ["Fix issues and rerun QA."],
    }


__all__ = ["QaReviewerWorker"]
