"""Postgres task archive store for the Knowledge Librarian."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pio_lab.layer5_librarian.indexer import TaskSearchIndexer
from pio_lab.memory.postgres.database import get_session
from pio_lab.memory.postgres.models import Task


class PostgresTaskStore:
    """Persist and retrieve archived task rows."""

    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        indexer: TaskSearchIndexer | None = None,
    ) -> None:
        self.session = session
        self.indexer = indexer or TaskSearchIndexer()

    async def archive_task(
        self,
        *,
        user_id: str,
        channel: str,
        request: dict[str, Any],
        plan: dict[str, Any] | None,
        final_output: dict[str, Any] | None,
        status: str,
    ) -> Task:
        """Insert a completed task archive row."""
        task = Task(
            user_id=user_id,
            channel=channel,
            request=request,
            plan=plan,
            final_output=final_output,
            status=status,
        )
        async with self._session() as session:
            session.add(task)
            await session.commit()
            await session.refresh(task)
        return task

    async def search(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Return relevant archived tasks using MVP lexical search."""
        async with self._session() as session:
            result = await session.execute(select(Task))
            tasks = list(result.scalars().all())

        hits = [
            hit
            for task in tasks
            if (hit := self.indexer.hit_for_task(task, query)) is not None
        ]
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return [
            {
                "task_id": hit.task_id,
                "score": hit.score,
                "status": hit.status,
                "user_id": hit.user_id,
                "channel": hit.channel,
                "text": hit.text,
                "final_output": hit.final_output,
            }
            for hit in hits[:limit]
        ]

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncSession]:
        if self.session is not None:
            yield self.session
            return

        async with get_session() as session:
            yield session


__all__ = ["PostgresTaskStore"]
