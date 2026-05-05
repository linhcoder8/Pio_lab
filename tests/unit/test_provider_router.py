"""Tests for M3 Provider Router with Claude only."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pio_lab.memory.postgres.models import Base, Trace
from pio_lab.memory.postgres.traces import TraceLogger
from pio_lab.providers.adapters.base_provider import BaseProvider
from pio_lab.providers.errors import ProviderUnavailableError, QuotaExceededError
from pio_lab.providers.router import ProviderRouter


class FakeClaudeProvider(BaseProvider):
    name = "claude"

    def __init__(self, response: dict[str, Any] | None = None, error: Exception | None = None) -> None:
        self.response = response or {
            "content": [{"type": "text", "text": "Pio_lab works!"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 6, "output_tokens": 5},
            "model": "unused",
            "provider": "claude",
            "raw": {"fake": True},
        }
        self.error = error
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
            {
                "account": account,
                "model": model,
                "messages": messages,
                "tools": tools,
                "system": system,
                "kwargs": kwargs,
            }
        )
        if self.error is not None:
            raise self.error
        return dict(self.response)


class FakeTraceLogger:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    async def log(self, **kwargs: Any) -> None:
        self.entries.append(kwargs)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


def test_router_loads_provider_config_and_claude_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    router = ProviderRouter()

    router.load()

    assert router.config is not None
    assert "claude" in router.adapters
    assert "codex" not in router.adapters
    assert len(router.account_pool.accounts_for("claude")) >= 1
    account = router.account_pool.next_available("claude", "claude-opus-4-6")
    assert account is not None
    assert account.account_id == "claude_main"


def test_resolve_chain_uses_routing_rule_and_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    router = ProviderRouter()
    router.load()

    research_chain = router._resolve_chain("research.optics")
    default_chain = router._resolve_chain("unknown.route")

    assert research_chain[0].provider == "claude"
    assert research_chain[0].model == "claude-opus-4-6"
    assert default_chain[0].provider == "claude"
    assert default_chain[0].model == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_router_call_uses_claude_adapter_and_logs_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    adapter = FakeClaudeProvider()
    trace_logger = FakeTraceLogger()
    router = ProviderRouter(adapters={"claude": adapter}, trace_logger=trace_logger)  # type: ignore[arg-type]

    response = await router.call(
        "research.optics",
        [{"role": "user", "content": "Say 'Pio_lab works!'"}],
        task_id="task_1",
    )

    assert response["content"][0]["text"] == "Pio_lab works!"
    assert response["provider"] == "claude"
    assert response["model"] == "claude-opus-4-6"
    assert adapter.calls[0]["account"].account_id == "claude_main"
    assert len(trace_logger.entries) == 1
    assert trace_logger.entries[0]["routing_key"] == "research.optics"
    assert trace_logger.entries[0]["provider"] == "claude"
    assert "raw" not in trace_logger.entries[0]["messages_out"]


@pytest.mark.asyncio
async def test_router_logs_trace_row_with_real_trace_logger(
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    router = ProviderRouter(
        adapters={"claude": FakeClaudeProvider()},
        trace_logger=TraceLogger(),
        trace_session=db_session,
    )

    await router.call(
        "chief_of_staff",
        [{"role": "user", "content": "Adaptive optics la gi?"}],
    )

    result = await db_session.execute(select(Trace).where(Trace.routing_key == "chief_of_staff"))
    trace = result.scalar_one()
    assert trace.provider == "claude"
    assert trace.model == "claude-opus-4-6"
    assert trace.messages_out["content"][0]["text"] == "Pio_lab works!"


@pytest.mark.asyncio
async def test_router_skips_unimplemented_m4_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    router = ProviderRouter(adapters={"claude": FakeClaudeProvider()})

    with pytest.raises(ProviderUnavailableError) as error:
        await router.call("coder.backend", [{"role": "user", "content": "hi"}])

    assert "adapter not implemented" in str(error.value)
    assert router.status_tracker.get("coder.backend", "codex", "gpt-4o").state == "skipped"


@pytest.mark.asyncio
async def test_router_marks_quota_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    adapter = FakeClaudeProvider(
        error=QuotaExceededError(
            "quota exhausted",
            provider="claude",
            account_id="claude_main",
        )
    )
    router = ProviderRouter(adapters={"claude": adapter})
    router.load()
    account = router.account_pool.next_available("claude", "claude-opus-4-6")
    assert account is not None

    with pytest.raises(ProviderUnavailableError):
        await router.call("research.optics", [{"role": "user", "content": "hi"}])

    assert account.quota_exhausted_until is not None
    assert router.account_pool.next_available("claude", "claude-opus-4-6") is None
