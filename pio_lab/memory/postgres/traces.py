"""Trace logging for provider calls."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pio_lab.memory.postgres.database import get_session
from pio_lab.memory.postgres.models import Trace
from pio_lab.utils.logging import logger


class TraceLogger:
    """Persist provider call traces to the memory database."""

    async def log(
        self,
        *,
        agent_id: str,
        routing_key: str,
        provider: str,
        model: str,
        messages_in: list[dict[str, Any]],
        messages_out: dict[str, Any] | list[dict[str, Any]],
        task_id: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: int = 0,
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> Trace:
        """Insert one trace row and return it."""
        trace = Trace(
            task_id=task_id,
            agent_id=agent_id,
            routing_key=routing_key,
            provider=provider,
            model=model,
            messages_in=messages_in,
            messages_out=messages_out,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            status=status,
            error=error,
            extra=metadata,
        )

        if session is not None:
            return await self._insert(session, trace)

        async with get_session() as managed_session:
            return await self._insert(managed_session, trace)

    async def _insert(self, session: AsyncSession, trace: Trace) -> Trace:
        session.add(trace)
        await session.commit()
        await session.refresh(trace)
        logger.debug("Logged provider trace {trace_id}", trace_id=trace.id)
        return trace


__all__ = ["TraceLogger"]
