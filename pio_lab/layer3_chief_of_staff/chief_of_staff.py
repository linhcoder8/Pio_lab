"""Chief of Staff LangGraph orchestrator."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from pio_lab.layer3_chief_of_staff.dispatch import DispatchHandler, DispatchNode
from pio_lab.layer3_chief_of_staff.human_approval import approval_node, route_after_approval
from pio_lab.layer3_chief_of_staff.plan import PlanNode, route_after_plan
from pio_lab.layer3_chief_of_staff.report import QAReviewer, ReportNode, route_after_report
from pio_lab.layer3_chief_of_staff.replan import replan_node
from pio_lab.layer3_chief_of_staff.state import ChiefOfStaffState
from pio_lab.layer5_librarian import KnowledgeLibrarian
from pio_lab.memory.postgres.traces import TraceLogger
from pio_lab.providers.router import ProviderRouter, get_router
from pio_lab.security.enforcer import SecurityEnforcer, enforcer
from pio_lab.utils.config_loader import load_pio_lab_config
from pio_lab.utils.helpers import gen_request_id
from pio_lab.utils.logging import logger


class ChiefOfStaff:
    """Layer 3 orchestrator: plan → approval → dispatch → report → replan."""

    def __init__(
        self,
        *,
        router: ProviderRouter | None = None,
        security: SecurityEnforcer | None = None,
        trace_logger: TraceLogger | None = None,
        trace_session: AsyncSession | None = None,
        dispatch_handler: DispatchHandler | None = None,
        qa_reviewer: QAReviewer | None = None,
        librarian: KnowledgeLibrarian | None = None,
        app_config: dict[str, Any] | None = None,
    ) -> None:
        self.router = router or get_router()
        self.security = security or enforcer
        self.trace_logger = trace_logger or TraceLogger()
        self.trace_session = trace_session
        self.librarian = librarian
        self.app_config = app_config or load_pio_lab_config()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph(dispatch_handler, qa_reviewer)

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run a new Chief of Staff graph execution."""
        initial_state = self._initial_state(payload)
        thread_id = initial_state["thread_id"]
        result = await self.graph.ainvoke(
            initial_state,
            config=_thread_config(thread_id),
        )
        return await self._finalize_result(result, thread_id)

    async def resume(self, thread_id: str, approval: Any) -> dict[str, Any]:
        """Resume a paused approval graph with the owner's decision."""
        result = await self.graph.ainvoke(
            Command(resume=approval),
            config=_thread_config(thread_id),
        )
        return await self._finalize_result(result, thread_id)

    def _build_graph(
        self,
        dispatch_handler: DispatchHandler | None,
        qa_reviewer: QAReviewer | None,
    ) -> Any:
        builder = StateGraph(ChiefOfStaffState)
        builder.add_node(
            "plan",
            PlanNode(security=self.security, app_config=self.app_config),
        )
        builder.add_node(
            "dispatch",
            DispatchNode(
                router=self.router,
                dispatch_handler=dispatch_handler,
                trace_logger=self.trace_logger,
                trace_session=self.trace_session,
            ),
        )
        builder.add_node("report", ReportNode(qa_reviewer=qa_reviewer))
        builder.add_node("replan", replan_node)
        builder.add_node("approval", approval_node)

        builder.add_edge(START, "plan")
        builder.add_conditional_edges(
            "plan",
            route_after_plan,
            {"approval": "approval", "dispatch": "dispatch"},
        )
        builder.add_conditional_edges(
            "approval",
            route_after_approval,
            {"dispatch": "dispatch", "end": END},
        )
        builder.add_edge("dispatch", "report")
        builder.add_conditional_edges(
            "report",
            route_after_report,
            {"replan": "replan", "end": END},
        )
        builder.add_edge("replan", "plan")
        return builder.compile(checkpointer=self.checkpointer)

    def _initial_state(self, payload: dict[str, Any]) -> ChiefOfStaffState:
        user_input = str(payload.get("input") or payload.get("message") or "").strip()
        task_id = str(payload.get("task_id") or gen_request_id("task"))
        thread_id = str(payload.get("thread_id") or task_id)
        max_replans = int(
            payload.get("max_replans")
            or self.app_config.get("chief_of_staff", {}).get("replan_max_attempts", 3)
        )
        return {
            **payload,
            "input": user_input,
            "task_id": task_id,
            "trace_task_id": payload.get("trace_task_id"),
            "thread_id": thread_id,
            "user_id": str(payload.get("user_id") or "local_user"),
            "channel": str(payload.get("channel") or "local"),
            "messages": payload.get("messages")
            or [{"role": "user", "content": user_input}],
            "status": "received",
            "replan_count": int(payload.get("replan_count", 0) or 0),
            "max_replans": max_replans,
            "trace_events": list(payload.get("trace_events", [])),
        }

    async def _finalize_result(self, result: dict[str, Any], thread_id: str) -> dict[str, Any]:
        if "__interrupt__" in result:
            interrupt_value = result["__interrupt__"][0].value
            paused = {
                **{key: value for key, value in result.items() if key != "__interrupt__"},
                "thread_id": thread_id,
                "status": "waiting_approval",
                "approval": interrupt_value,
            }
            await self._log_lifecycle(paused)
            return paused

        completed = {**result, "thread_id": thread_id}
        completed = await self._archive_result(completed)
        await self._log_lifecycle(completed)
        return completed

    async def _archive_result(self, state: dict[str, Any]) -> dict[str, Any]:
        if self.librarian is None:
            return state
        try:
            archive = await self.librarian.run(state)
        except Exception as error:
            logger.warning("Knowledge Librarian archive failed: {error}", error=error)
            return {
                **state,
                "archive": {"archived": False, "error": str(error)},
            }

        updated = {**state, "archive": archive}
        if archive.get("task_id") and not updated.get("trace_task_id"):
            updated["trace_task_id"] = archive["task_id"]
        return updated

    async def _log_lifecycle(self, state: dict[str, Any]) -> None:
        try:
            await self.trace_logger.log(
                task_id=state.get("trace_task_id"),
                agent_id="chief_of_staff",
                routing_key="chief_of_staff",
                provider="internal",
                model="langgraph",
                messages_in=[{"role": "user", "content": state.get("input", "")}],
                messages_out={
                    "status": state.get("status"),
                    "plan": state.get("plan"),
                    "qa_verdict": state.get("qa_verdict"),
                    "final_output": state.get("final_output"),
                    "approval": state.get("approval"),
                },
                tokens_in=0,
                tokens_out=0,
                latency_ms=0,
                metadata={
                    "thread_id": state.get("thread_id"),
                    "events": state.get("trace_events", []),
                },
                session=self.trace_session,
            )
        except Exception as error:
            logger.warning("Chief of Staff trace logging failed: {error}", error=error)


def _thread_config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}


_chief_of_staff: ChiefOfStaff | None = None


def get_chief_of_staff() -> ChiefOfStaff:
    """Return the process-wide Chief of Staff singleton."""
    global _chief_of_staff

    if _chief_of_staff is None:
        _chief_of_staff = ChiefOfStaff(librarian=KnowledgeLibrarian())
    return _chief_of_staff


def reset_chief_of_staff() -> None:
    """Reset the singleton, mainly for tests."""
    global _chief_of_staff

    _chief_of_staff = None


__all__ = ["ChiefOfStaff", "get_chief_of_staff", "reset_chief_of_staff"]
