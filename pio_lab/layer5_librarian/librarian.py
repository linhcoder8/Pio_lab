"""Knowledge Librarian: archive completed work into durable memory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pio_lab.layer5_librarian.obsidian_store import ObsidianTaskStore
from pio_lab.layer5_librarian.postgres_store import PostgresTaskStore


class KnowledgeLibrarian:
    """Archive QA-passed tasks to Postgres and Obsidian, then retrieve them."""

    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        vault_root: str | Path | None = None,
        postgres_store: PostgresTaskStore | None = None,
        obsidian_store: ObsidianTaskStore | None = None,
        postgres_enabled: bool = True,
        obsidian_enabled: bool = True,
    ) -> None:
        self.postgres_enabled = postgres_enabled
        self.obsidian_enabled = obsidian_enabled
        self.postgres_store = postgres_store or (
            PostgresTaskStore(session=session) if postgres_enabled else None
        )
        self.obsidian_store = obsidian_store or (
            ObsidianTaskStore(vault_root=vault_root) if obsidian_enabled else None
        )

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Archive one Chief of Staff completed state when QA passes."""
        if not self.should_archive(state):
            return {"archived": False, "reason": "QA did not pass or task is incomplete"}

        request = _request_payload(state)
        final_output = _final_output(state)
        archive: dict[str, Any] = {"archived": True}
        task_id: str | None = None
        created_at = None

        if self.postgres_enabled:
            if self.postgres_store is None:
                raise RuntimeError("Postgres archive store is not configured")
            task = await self.postgres_store.archive_task(
                user_id=str(state.get("user_id") or "local_user"),
                channel=str(state.get("channel") or "local"),
                request=request,
                plan=state.get("plan"),
                final_output=final_output,
                status=str(state.get("status") or "done"),
            )
            task_id = task.id
            created_at = task.created_at
            archive["postgres"] = {"task_id": task.id}

        if self.obsidian_enabled:
            if self.obsidian_store is None:
                raise RuntimeError("Obsidian archive store is not configured")
            note_task_id = task_id or str(state.get("task_id") or "task")
            note = self.obsidian_store.write_task_note(
                task_id=note_task_id,
                user_id=str(state.get("user_id") or "local_user"),
                channel=str(state.get("channel") or "local"),
                request=request,
                plan=state.get("plan"),
                final_output=final_output,
                status=str(state.get("status") or "done"),
                dispatch_results=state.get("dispatch_results", []),
                created_at=created_at,
            )
            archive["obsidian"] = note

        if task_id is not None:
            archive["task_id"] = task_id
        return archive

    async def search(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve relevant archived tasks."""
        if not self.postgres_enabled:
            return []
        if self.postgres_store is None:
            return []
        return await self.postgres_store.search(query, limit=limit)

    def should_archive(self, state: dict[str, Any]) -> bool:
        """Return whether the state is a completed QA-passed task."""
        status = str(state.get("status") or "").lower()
        verdict = _qa_verdict(state)
        return status in {"done", "done_with_warnings"} and verdict == "PASS"


def _request_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": state.get("task_id"),
        "thread_id": state.get("thread_id"),
        "input": state.get("input", ""),
        "messages": state.get("messages", []),
        "channel": state.get("channel"),
        "user_id": state.get("user_id"),
    }


def _final_output(state: dict[str, Any]) -> dict[str, Any] | None:
    final_output = state.get("final_output")
    if isinstance(final_output, dict):
        return final_output
    if final_output:
        return {"text": str(final_output)}
    return None


def _qa_verdict(state: dict[str, Any]) -> str:
    if state.get("qa_verdict"):
        return str(state["qa_verdict"]).upper()
    final_output = state.get("final_output") or {}
    if isinstance(final_output, dict):
        qa = final_output.get("qa") or {}
        if isinstance(qa, dict) and qa.get("verdict"):
            return str(qa["verdict"]).upper()
    return ""


__all__ = ["KnowledgeLibrarian"]
