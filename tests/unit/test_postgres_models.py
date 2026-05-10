"""Tests for M1 Postgres memory models and trace logging."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pio_lab.memory.postgres.models import Base, Conversation, Provider, ProviderAccount, Task, Trace
from pio_lab.memory.postgres.traces import TraceLogger


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


def test_schema_contains_required_m1_tables() -> None:
    assert {"tasks", "traces", "conversations", "provider_accounts"}.issubset(
        Base.metadata.tables.keys()
    )


@pytest.mark.asyncio
async def test_async_session_can_insert_and_query_required_models(
    db_session: AsyncSession,
) -> None:
    provider = Provider(name="claude", provider_type="cloud", sdk="anthropic")
    account = ProviderAccount(provider="claude", account_id="claude_main")
    task = Task(
        user_id="user_1",
        channel="web",
        request={"input": "Adaptive optics la gi?"},
        plan={"fast_path": True},
        final_output={"text": "Adaptive optics adjusts optical systems in real time."},
        status="done",
    )
    conversation = Conversation(
        task=task,
        user_id="user_1",
        channel="web",
        role="user",
        content="Adaptive optics la gi?",
    )
    trace = Trace(
        task=task,
        agent_id="chief_of_staff",
        routing_key="chief_of_staff",
        provider="claude",
        model="claude-opus-4-6",
        messages_in=[{"role": "user", "content": "hi"}],
        messages_out={"content": "hello"},
        tokens_in=4,
        tokens_out=8,
        latency_ms=120,
    )

    db_session.add_all([provider, account, task, conversation, trace])
    await db_session.commit()

    task_result = await db_session.execute(select(Task).where(Task.user_id == "user_1"))
    trace_result = await db_session.execute(select(Trace).where(Trace.routing_key == "chief_of_staff"))
    account_result = await db_session.execute(select(ProviderAccount))
    conversation_result = await db_session.execute(select(Conversation))

    assert task_result.scalar_one().status == "done"
    assert trace_result.scalar_one().tokens_out == 8
    assert account_result.scalar_one().account_id == "claude_main"
    assert conversation_result.scalar_one().role == "user"


@pytest.mark.asyncio
async def test_trace_logger_log_inserts_one_row(db_session: AsyncSession) -> None:
    task = Task(
        user_id="user_2",
        channel="web",
        request={"input": "Say Pio_lab works"},
        status="running",
    )
    db_session.add(task)
    await db_session.flush()

    trace = await TraceLogger().log(
        task_id=task.id,
        agent_id="chief_of_staff",
        routing_key="chief_of_staff",
        provider="claude",
        model="claude-opus-4-6",
        messages_in=[{"role": "user", "content": "Say Pio_lab works"}],
        messages_out={"content": "Pio_lab works!"},
        tokens_in=6,
        tokens_out=5,
        latency_ms=42,
        session=db_session,
    )

    result = await db_session.execute(select(Trace).where(Trace.id == trace.id))
    inserted = result.scalar_one()

    assert inserted.task_id == task.id
    assert inserted.provider == "claude"
    assert inserted.messages_out["content"] == "Pio_lab works!"
