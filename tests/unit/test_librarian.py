"""Tests for M10 Knowledge Librarian."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pio_lab.layer3_chief_of_staff.chief_of_staff import ChiefOfStaff
from pio_lab.layer5_librarian import KnowledgeLibrarian
from pio_lab.memory.postgres.models import Base, Task
from pio_lab.memory.postgres.traces import TraceLogger


class FakeRouter:
    async def call(
        self,
        routing_key: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": "Archived response about optics lens design"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "provider": "fake",
            "model": "fake-model",
            "raw": None,
        }


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


def _passed_state() -> dict[str, Any]:
    return {
        "task_id": "task_for_librarian",
        "thread_id": "thread_for_librarian",
        "user_id": "user_1",
        "channel": "web",
        "input": "Research optics lens design",
        "messages": [{"role": "user", "content": "Research optics lens design"}],
        "plan": {
            "intent": "research",
            "steps": [
                {
                    "id": "execute",
                    "department": "research",
                    "worker": "optics",
                    "routing_key": "research.optics",
                }
            ],
        },
        "dispatch_results": [
            {
                "step_id": "execute",
                "department_id": "research",
                "worker_id": "optics",
                "routing_key": "research.optics",
                "output": "Lens design summary with citations",
            }
        ],
        "qa_verdict": "PASS",
        "final_output": {"text": "Lens design summary with citations"},
        "status": "done",
    }


@pytest.mark.asyncio
async def test_librarian_archives_passed_task_to_postgres_and_obsidian(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    librarian = KnowledgeLibrarian(session=db_session, vault_root=tmp_path / "vault")

    archive = await librarian.run(_passed_state())

    assert archive["archived"] is True
    assert archive["postgres"]["task_id"] == archive["task_id"]
    note_path = Path(archive["obsidian"]["path"])
    assert note_path.exists()
    note = note_path.read_text(encoding="utf-8")
    assert "# Request" in note
    assert "Research optics lens design" in note
    assert "research.optics" in note

    result = await db_session.execute(select(Task).where(Task.id == archive["task_id"]))
    task = result.scalar_one()
    assert task.status == "done"
    assert task.plan["intent"] == "research"
    assert task.final_output["text"] == "Lens design summary with citations"


@pytest.mark.asyncio
async def test_librarian_skips_when_qa_does_not_pass(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    librarian = KnowledgeLibrarian(session=db_session, vault_root=tmp_path / "vault")
    state = _passed_state() | {"qa_verdict": "NEEDS_FIX", "status": "needs_replan"}

    archive = await librarian.run(state)

    result = await db_session.execute(select(Task))
    assert archive["archived"] is False
    assert result.scalars().all() == []
    assert not (tmp_path / "vault" / "tasks").exists()


@pytest.mark.asyncio
async def test_librarian_search_returns_relevant_past_tasks(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    librarian = KnowledgeLibrarian(session=db_session, vault_root=tmp_path / "vault")
    await librarian.run(_passed_state())
    await librarian.run(
        _passed_state()
        | {
            "input": "Write a cooking note",
            "final_output": {"text": "A recipe note about soup"},
        }
    )

    hits = await librarian.search("optics lens")

    assert hits
    assert hits[0]["score"] > 0
    assert "Lens design" in hits[0]["final_output"]["text"]


@pytest.mark.asyncio
async def test_chief_of_staff_archives_after_report_passes_qa(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    librarian = KnowledgeLibrarian(session=db_session, vault_root=tmp_path / "vault")
    chief = ChiefOfStaff(
        router=FakeRouter(),  # type: ignore[arg-type]
        trace_logger=TraceLogger(),
        trace_session=db_session,
        librarian=librarian,
    )

    result = await chief.run({"input": "hello", "user_id": "user_1", "channel": "web"})

    assert result["status"] == "done"
    assert result["archive"]["archived"] is True
    assert Path(result["archive"]["obsidian"]["path"]).exists()

    task_result = await db_session.execute(select(Task).where(Task.id == result["archive"]["task_id"]))
    task = task_result.scalar_one()
    assert task.final_output["text"] == "Archived response about optics lens design"
