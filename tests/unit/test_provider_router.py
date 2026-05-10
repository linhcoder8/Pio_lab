"""Tests for M3-M4 Provider Router."""

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


class FakeProvider(BaseProvider):
    name = "fake"

    def __init__(
        self,
        *,
        provider: str,
        text: str = "Pio_lab works!",
        response: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.name = provider
        self.response = response or {
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 6, "output_tokens": 5},
            "model": "unused",
            "provider": provider,
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


def test_router_loads_provider_config_and_accounts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CODEX_AUTH_FILE", raising=False)
    router = ProviderRouter()

    router.load()

    assert router.config is not None
    assert {"claude", "codex", "gemini", "deepseek", "ollama"}.issubset(router.adapters)
    assert len(router.account_pool.accounts_for("claude")) >= 1
    account = router.account_pool.next_available("claude", "claude-opus-4-6")
    assert account is not None
    assert account.account_id == "claude_main"


def test_router_registers_codex_oauth_account_when_codex_auth_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    (codex_home / "auth.json").write_text(
        """
        {
          "auth_mode": "chatgpt",
          "tokens": {
            "access_token": "oauth-access-token",
            "refresh_token": "oauth-refresh-token",
            "account_id": "acct_test"
          }
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY_2", raising=False)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    router = ProviderRouter()

    router.load()

    account = router.account_pool.next_available("codex", "o1-preview")
    assert account is not None
    assert account.account_id == "codex_oauth"


def test_resolve_chain_uses_routing_rule_and_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("PROVIDER_ROUTING_PROFILE", "")
    router = ProviderRouter()
    router.load()

    research_chain = router._resolve_chain("research.optics")
    default_chain = router._resolve_chain("unknown.route")

    assert research_chain[0].provider == "claude"
    assert research_chain[0].model == "claude-opus-4-6"
    assert default_chain[0].provider == "claude"
    assert default_chain[0].model == "claude-sonnet-4-6"


def test_codex_oauth_routing_profile_promotes_text_departments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROVIDER_ROUTING_PROFILE", "codex_oauth")
    router = ProviderRouter()
    router.load()

    research_chain = router._resolve_chain("research.optics")

    assert research_chain[0].provider == "codex"
    assert research_chain[0].model == "gpt-4o"


@pytest.mark.asyncio
async def test_router_call_uses_claude_adapter_and_logs_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("PROVIDER_ROUTING_PROFILE", "")
    adapter = FakeProvider(provider="claude")
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
        adapters={"claude": FakeProvider(provider="claude")},
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
async def test_router_falls_back_from_claude_to_codex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    claude = FakeProvider(
        provider="claude",
        error=QuotaExceededError(
            "quota exhausted",
            provider="claude",
            account_id="claude_main",
        ),
    )
    codex = FakeProvider(provider="codex", text="Codex fallback works")
    router = ProviderRouter(adapters={"claude": claude, "codex": codex})

    response = await router.call("chief_of_staff", [{"role": "user", "content": "hi"}])

    assert response["provider"] == "codex"
    assert response["content"][0]["text"] == "Codex fallback works"
    assert router.status_tracker.get("chief_of_staff", "claude", "claude-opus-4-6").state == "failed"
    assert router.status_tracker.get("chief_of_staff", "codex", "o1-preview").state == "end"
    assert codex.calls[0]["account"].account_id == "codex_main"


@pytest.mark.asyncio
async def test_router_marks_quota_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("PROVIDER_ROUTING_PROFILE", "")
    adapter = FakeProvider(
        provider="claude",
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
