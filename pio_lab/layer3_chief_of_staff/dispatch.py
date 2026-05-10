"""DISPATCH node for Chief of Staff orchestration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from inspect import isawaitable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pio_lab.core.registry import DepartmentRegistry
from pio_lab.layer3_chief_of_staff.state import ChiefOfStaffState
from pio_lab.memory.postgres.traces import TraceLogger
from pio_lab.providers.errors import ProviderUnavailableError
from pio_lab.providers.router import ProviderRouter, get_router
from pio_lab.utils.logging import logger

DispatchHandler = Callable[[ChiefOfStaffState], dict[str, Any] | Awaitable[dict[str, Any]]]


class DispatchNode:
    """Execute the planned work.

    M8 will replace the fallback execution path with real Department/Worker dispatch.
    """

    def __init__(
        self,
        *,
        router: ProviderRouter | None = None,
        dispatch_handler: DispatchHandler | None = None,
        registry: DepartmentRegistry | None = None,
        trace_logger: TraceLogger | None = None,
        trace_session: AsyncSession | None = None,
    ) -> None:
        self.router = router or get_router()
        self.dispatch_handler = dispatch_handler
        self.registry = registry
        self.trace_logger = trace_logger
        self.trace_session = trace_session

    async def __call__(self, state: ChiefOfStaffState) -> dict[str, Any]:
        """Run the plan through an injected handler or ProviderRouter-backed fast path."""
        if state.get("status") == "rejected":
            return {}
        if self.dispatch_handler is not None:
            result = self.dispatch_handler(state)
            resolved = await result if isawaitable(result) else result
            return {
                **resolved,
                "trace_events": state.get("trace_events", [])
                + [{"node": "dispatch", "mode": "injected"}],
            }

        department_steps = _department_steps(state.get("plan", {}))
        if department_steps:
            return await self._dispatch_departments(state, department_steps)

        response_text, provider_meta = await self._call_router_or_fallback(state)
        result = {
            "step_id": "fast_path" if state.get("plan", {}).get("fast_path") else "execute",
            "routing_key": "chief_of_staff",
            "output": response_text,
            "provider": provider_meta,
        }
        return {
            "dispatch_results": [result],
            "status": "dispatched",
            "trace_events": state.get("trace_events", [])
            + [{"node": "dispatch", "mode": "provider_router", "provider": provider_meta}],
        }

    async def _dispatch_departments(
        self,
        state: ChiefOfStaffState,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        registry = self.registry or DepartmentRegistry(
            router=self.router,
            trace_logger=self.trace_logger,
            trace_session=self.trace_session,
        ).load_all()
        results: list[dict[str, Any]] = []
        for step in steps:
            department_id = str(step.get("department") or "")
            department = registry.get_department(department_id)
            context = {
                "state": dict(state),
                "previous_results": results,
                "output": _last_output(results),
            }
            worker_task = _worker_task_from_step(step, state, context)
            department_result = await department.run(worker_task, context)
            results.append({"step_id": step.get("id") or department_id, **department_result})

        return {
            "dispatch_results": results,
            "status": "dispatched",
            "trace_events": state.get("trace_events", [])
            + [
                {
                    "node": "dispatch",
                    "mode": "department_registry",
                    "steps": [step.get("id") for step in steps],
                }
            ],
        }

    async def _call_router_or_fallback(
        self,
        state: ChiefOfStaffState,
    ) -> tuple[str, dict[str, Any]]:
        messages = state.get("messages") or [{"role": "user", "content": state.get("input", "")}]
        system = (
            "You are Pio_lab Chief of Staff. Answer concisely in Vietnamese unless the user "
            "asks otherwise. For M7, do not claim that downstream departments have completed "
            "real file/tool work."
        )
        try:
            response = await self.router.call(
                "chief_of_staff",
                messages,
                system=system,
                task_id=state.get("trace_task_id"),
                agent_id="chief_of_staff",
                max_tokens=800,
            )
        except ProviderUnavailableError as error:
            logger.warning("Chief of Staff provider unavailable: {error}", error=error)
            return self._fallback_response(state), {
                "provider": "local_fallback",
                "model": "deterministic",
                "error": str(error),
            }

        return extract_response_text(response), {
            "provider": response.get("provider"),
            "model": response.get("model"),
        }

    def _fallback_response(self, state: ChiefOfStaffState) -> str:
        user_input = state.get("input", "").strip()
        if state.get("plan", {}).get("fast_path"):
            if user_input.lower() in {"hello", "hi", "xin chào", "chào"}:
                return "Xin chào Sếp Linh. Pio_lab đã sẵn sàng nhận việc."
            return (
                "Pio_lab đã nhận câu hỏi của Sếp Linh. Provider thật đang được deferred, "
                f"nên M7 trả lời bằng fallback cục bộ cho yêu cầu: {user_input}"
            )
        return (
            "Pio_lab đã lập kế hoạch điều phối. Phần Department/Worker thật sẽ được nối ở M8, "
            f"yêu cầu hiện tại: {user_input}"
        )


def extract_response_text(response: dict[str, Any]) -> str:
    """Extract text from normalized provider responses."""
    content = response.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text", "")))
            elif isinstance(item, str):
                chunks.append(item)
        text = "\n".join(chunk for chunk in chunks if chunk).strip()
        if text:
            return text
    return str(response.get("text") or response.get("output") or "")


def _department_steps(plan: dict[str, Any]) -> list[dict[str, Any]]:
    steps = [step for step in plan.get("steps", []) if isinstance(step, dict)]
    executable = [
        step
        for step in steps
        if step.get("department") and step.get("department") not in {"chief_of_staff", "qa"}
    ]
    if not executable:
        return []
    return [
        step
        for step in steps
        if step.get("department") and step.get("department") != "chief_of_staff"
    ]


def _worker_task_from_step(
    step: dict[str, Any],
    state: ChiefOfStaffState,
    context: dict[str, Any],
) -> dict[str, Any]:
    task_text = str(step.get("task") or state.get("input") or "")
    payload = {
        "input": task_text,
        "task": task_text,
        "worker": step.get("worker"),
        "worker_id": step.get("worker"),
        "trace_task_id": state.get("trace_task_id"),
        "original_input": state.get("input", ""),
    }
    if step.get("department") == "qa":
        payload["output"] = context.get("output", "")
    if "output_dir" in state:
        payload["output_dir"] = state["output_dir"]
    return payload


def _last_output(results: list[dict[str, Any]]) -> str:
    for result in reversed(results):
        if result.get("department_id") != "qa":
            return str(result.get("output") or "")
    return ""


__all__ = ["DispatchHandler", "DispatchNode", "extract_response_text"]
