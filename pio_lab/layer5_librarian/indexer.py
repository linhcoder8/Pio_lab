"""Small search index helpers for archived tasks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from pio_lab.memory.postgres.models import Task

TOKEN_RE = re.compile(r"[a-zA-Z0-9_À-ỹ]+")


@dataclass(frozen=True, slots=True)
class TaskSearchHit:
    """One search result from archived task memory."""

    task_id: str
    score: int
    status: str
    user_id: str
    channel: str
    text: str
    final_output: dict[str, Any] | None


class TaskSearchIndexer:
    """Build simple lexical documents for MVP task retrieval."""

    def document_for_task(self, task: Task) -> str:
        """Return searchable text for one task row."""
        payload = {
            "request": task.request,
            "plan": task.plan,
            "final_output": task.final_output,
            "status": task.status,
        }
        return json.dumps(payload, ensure_ascii=False, default=str)

    def score(self, query: str, document: str) -> int:
        """Score a document by counting query token occurrences."""
        tokens = self._tokens(query)
        if not tokens:
            return 0
        normalized_document = document.lower()
        return sum(normalized_document.count(token) for token in tokens)

    def hit_for_task(self, task: Task, query: str) -> TaskSearchHit | None:
        """Return a hit when the task matches the query."""
        document = self.document_for_task(task)
        score = self.score(query, document)
        if score <= 0:
            return None
        return TaskSearchHit(
            task_id=task.id,
            score=score,
            status=task.status,
            user_id=task.user_id,
            channel=task.channel,
            text=_preview(document),
            final_output=task.final_output,
        )

    def _tokens(self, text: str) -> list[str]:
        return [match.group(0).lower() for match in TOKEN_RE.finditer(text)]


def _preview(text: str, limit: int = 280) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


__all__ = ["TaskSearchHit", "TaskSearchIndexer"]
