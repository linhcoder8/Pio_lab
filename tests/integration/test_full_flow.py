"""End-to-end tests for the local MVP flow."""

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
from pio_lab.memory.postgres.models import Base, Task, Trace
from pio_lab.memory.postgres.traces import TraceLogger

pytestmark = pytest.mark.integration


class FakeRouter:
    """Router fallback used only when the graph takes a chief_of_staff fast path."""

    async def call(
        self,
        routing_key: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": "Local fallback response"}],
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


@pytest.mark.asyncio
async def test_simple_research_flow_archives_task_and_note(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """User hỏi research → Optics worker → QA → librarian archive."""
    librarian = KnowledgeLibrarian(session=db_session, vault_root=tmp_path / "vault")
    chief = ChiefOfStaff(
        router=FakeRouter(),  # type: ignore[arg-type]
        trace_logger=TraceLogger(),
        trace_session=db_session,
        librarian=librarian,
    )

    result = await chief.run(
        {
            "input": "Research lens design and summarize with citations",
            "user_id": "integration_user",
            "channel": "web",
        }
    )

    assert result["status"] == "done"
    assert result["plan"]["intent"] == "research"
    assert result["dispatch_results"][0]["department_id"] == "research"
    assert result["dispatch_results"][1]["department_id"] == "qa"
    assert result["qa_verdict"] == "PASS"
    assert "[1]" in result["final_output"]["text"]
    assert result["archive"]["archived"] is True

    task_result = await db_session.execute(select(Task).where(Task.id == result["archive"]["task_id"]))
    task = task_result.scalar_one()
    assert task.request["input"] == "Research lens design and summarize with citations"
    assert task.final_output["text"] == result["final_output"]["text"]

    note_path = Path(result["archive"]["obsidian"]["path"])
    assert note_path.exists()
    note = note_path.read_text(encoding="utf-8")
    assert "# Request" in note
    assert "research.optics" in note

    search_hits = await librarian.search("optics lens")
    assert search_hits[0]["task_id"] == task.id

    trace_result = await db_session.execute(
        select(Trace).where(Trace.routing_key == "chief_of_staff")
    )
    assert trace_result.scalar_one().task_id == task.id


@pytest.mark.asyncio
async def test_qa_replan_loop_archives_only_final_pass(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Output fail QA → replan → retry → pass → one archived task."""
    calls: list[int] = []

    async def dispatch_handler(state: dict[str, Any]) -> dict[str, Any]:
        replan_count = int(state.get("replan_count", 0) or 0)
        calls.append(replan_count)
        return {
            "dispatch_results": [
                {
                    "step_id": "execute",
                    "department_id": "coder",
                    "worker_id": "backend",
                    "routing_key": "coder.backend",
                    "output": f"draft {replan_count}",
                }
            ],
            "status": "dispatched",
        }

    async def qa_reviewer(state: dict[str, Any]) -> dict[str, Any]:
        if int(state.get("replan_count", 0) or 0) == 0:
            return {"verdict": "NEEDS_FIX", "feedback": "Missing tests."}
        return {"verdict": "PASS", "feedback": ""}

    librarian = KnowledgeLibrarian(session=db_session, vault_root=tmp_path / "vault")
    chief = ChiefOfStaff(
        router=FakeRouter(),  # type: ignore[arg-type]
        trace_logger=TraceLogger(),
        trace_session=db_session,
        dispatch_handler=dispatch_handler,  # type: ignore[arg-type]
        qa_reviewer=qa_reviewer,  # type: ignore[arg-type]
        librarian=librarian,
    )

    result = await chief.run({"input": "Write tested Python code", "max_replans": 2})

    assert result["status"] == "done"
    assert result["replan_count"] == 1
    assert result["final_output"]["text"] == "draft 1"
    assert calls == [0, 1]
    assert result["archive"]["archived"] is True

    task_result = await db_session.execute(select(Task))
    tasks = list(task_result.scalars().all())
    assert len(tasks) == 1
    assert tasks[0].final_output["text"] == "draft 1"
