"""Tests for M8 GenericWorker."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pio_lab.layer4_departments.base.worker_base import GenericWorker, WorkerConfig
from pio_lab.memory.postgres.models import Base, Trace
from pio_lab.memory.postgres.traces import TraceLogger
from pio_lab.providers.adapters.base_provider import BaseProvider
from pio_lab.providers.router import ProviderRouter


class SequencedProvider(BaseProvider):
    name = "fake"

    def __init__(self, responses: list[dict[str, Any]] | None = None) -> None:
        self.responses = responses or [_text_response("Worker final output")]
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self,
        account,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(
            {"model": model, "messages": messages, "tools": tools, "system": system, "kwargs": kwargs}
        )
        response = dict(self.responses.pop(0))
        response["model"] = model
        response["provider"] = "fake"
        return response


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_worker_runs_provider_call_and_tool_loop() -> None:
    provider = SequencedProvider(
        [
            {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "file_read",
                        "input": {"path": "README.md"},
                    }
                ],
                "usage": {"input_tokens": 3, "output_tokens": 4},
                "raw": None,
            },
            _text_response("Final answer after tool"),
        ]
    )
    router = _fake_router(provider)
    tool_calls: list[tuple[str, Any]] = []

    async def tool_executor(
        tool_name: str,
        tool_input: Any,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        tool_calls.append((tool_name, tool_input))
        return {"content": "README content"}

    worker = GenericWorker(
        WorkerConfig(
            id="backend",
            name="Backend Worker",
            department="coder",
            provider_routing_key="coder.backend",
            system_prompt="You are a backend worker.",
            tools_enabled=["file_read"],
            max_iterations=3,
        ),
        router=router,
        tool_executor=tool_executor,
    )

    result = await worker.run({"input": "Read README then answer"})

    assert result["output"] == "Final answer after tool"
    assert result["worker_id"] == "backend"
    assert len(provider.calls) == 2
    assert provider.calls[0]["tools"][0]["function"]["name"] == "file_read"
    assert tool_calls == [("file_read", {"path": "README.md"})]
    assert "Tool results" in provider.calls[1]["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_worker_trace_logged_via_provider_router(db_session: AsyncSession) -> None:
    router = _fake_router(
        SequencedProvider([_text_response("Traceable output")]),
        trace_logger=TraceLogger(),
        trace_session=db_session,
    )
    worker = GenericWorker(
        WorkerConfig(
            id="backend",
            name="Backend Worker",
            department="coder",
            provider_routing_key="coder.backend",
            max_iterations=1,
        ),
        router=router,
    )

    await worker.run({"input": "Write an API"})

    result = await db_session.execute(select(Trace).where(Trace.agent_id == "coder.backend"))
    trace = result.scalar_one()
    assert trace.routing_key == "coder.backend"
    assert trace.provider == "fake"
    assert trace.messages_out["content"][0]["text"] == "Traceable output"


def _fake_router(
    provider: SequencedProvider,
    *,
    trace_logger: TraceLogger | None = None,
    trace_session: AsyncSession | None = None,
) -> ProviderRouter:
    return ProviderRouter(
        config={
            "providers": {
                "fake": {
                    "accounts": [{"id": "fake_main", "models": ["fake-model"], "priority": 1}]
                }
            },
            "routing_rules": {"coder.backend": [{"provider": "fake", "model": "fake-model"}]},
            "default_chain": [{"provider": "fake", "model": "fake-model"}],
        },
        adapters={"fake": provider},
        trace_logger=trace_logger,
        trace_session=trace_session,
    )


def _text_response(text: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 1, "output_tokens": 2},
        "raw": None,
    }
