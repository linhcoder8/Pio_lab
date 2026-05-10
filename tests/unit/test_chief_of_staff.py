"""Tests for M7 Chief of Staff orchestration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pio_lab.layer3_chief_of_staff.chief_of_staff import ChiefOfStaff
from pio_lab.memory.postgres.models import Base, Trace
from pio_lab.memory.postgres.traces import TraceLogger


class FakeRouter:
    def __init__(self, text: str = "Xin chào từ Chief of Staff") -> None:
        self.text = text
        self.calls: list[dict[str, Any]] = []

    async def call(
        self,
        routing_key: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append({"routing_key": routing_key, "messages": messages, "kwargs": kwargs})
        return {
            "content": [{"type": "text", "text": self.text}],
            "usage": {"input_tokens": 4, "output_tokens": 7},
            "provider": "fake",
            "model": "fake-model",
            "raw": None,
        }


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


@pytest.mark.asyncio
async def test_chief_of_staff_run_completes_graph_execution() -> None:
    router = FakeRouter("Pio_lab đã sẵn sàng.")
    traces = FakeTraceLogger()
    chief = ChiefOfStaff(router=router, trace_logger=traces)  # type: ignore[arg-type]

    result = await chief.run({"input": "hello", "user_id": "sếp", "channel": "web"})

    assert result["status"] == "done"
    assert result["plan"]["fast_path"] is True
    assert result["final_output"]["text"] == "Pio_lab đã sẵn sàng."
    assert router.calls[0]["routing_key"] == "chief_of_staff"
    assert traces.entries[0]["routing_key"] == "chief_of_staff"


@pytest.mark.asyncio
async def test_chief_of_staff_logs_trace_row(db_session: AsyncSession) -> None:
    chief = ChiefOfStaff(
        router=FakeRouter("Trace được ghi."),
        trace_logger=TraceLogger(),
        trace_session=db_session,
    )  # type: ignore[arg-type]

    await chief.run({"input": "hello"})

    result = await db_session.execute(
        select(Trace).where(
            Trace.routing_key == "chief_of_staff",
            Trace.provider == "internal",
            Trace.model == "langgraph",
        )
    )
    trace = result.scalar_one()
    assert trace.messages_out["status"] == "done"
    assert trace.messages_out["final_output"]["text"] == "Trace được ghi."


@pytest.mark.asyncio
async def test_chief_of_staff_replans_when_qa_fails_once() -> None:
    calls: list[str] = []

    async def dispatch_handler(state: dict[str, Any]) -> dict[str, Any]:
        calls.append(f"dispatch-{state.get('replan_count', 0)}")
        return {
            "dispatch_results": [
                {
                    "step_id": "execute",
                    "routing_key": "coder.backend",
                    "output": f"draft {state.get('replan_count', 0)}",
                }
            ],
            "status": "dispatched",
        }

    async def qa_reviewer(state: dict[str, Any]) -> dict[str, Any]:
        if int(state.get("replan_count", 0) or 0) == 0:
            return {"verdict": "NEEDS_FIX", "feedback": "Missing test."}
        return {"verdict": "PASS", "feedback": ""}

    chief = ChiefOfStaff(
        router=FakeRouter(),
        trace_logger=FakeTraceLogger(),
        dispatch_handler=dispatch_handler,  # type: ignore[arg-type]
        qa_reviewer=qa_reviewer,  # type: ignore[arg-type]
    )  # type: ignore[arg-type]

    result = await chief.run({"input": "Viết function Python", "max_replans": 2})

    assert result["status"] == "done"
    assert result["replan_count"] == 1
    assert result["qa_verdict"] == "PASS"
    assert calls == ["dispatch-0", "dispatch-1"]
    assert result["final_output"]["text"] == "draft 1"


@pytest.mark.asyncio
async def test_chief_of_staff_pauses_for_human_approval_and_resumes() -> None:
    chief = ChiefOfStaff(
        router=FakeRouter("Upload đã được duyệt."),
        trace_logger=FakeTraceLogger(),
    )  # type: ignore[arg-type]

    paused = await chief.run({"input": "Upload video optics_intro.mp4 lên YouTube"})

    assert paused["status"] == "waiting_approval"
    assert paused["approval"]["action"] == "upload_to_youtube"

    resumed = await chief.resume(paused["thread_id"], {"approved": True, "reason": "OK"})

    assert resumed["status"] == "done"
    assert "upload_to_youtube" in resumed["approved_actions"]
    assert resumed["final_output"]["text"] == "Upload đã được duyệt."
