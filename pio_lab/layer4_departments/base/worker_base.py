"""Generic worker implementation for Layer 4 departments."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from inspect import isawaitable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pio_lab.memory.postgres.traces import TraceLogger
from pio_lab.providers.router import ProviderRouter, get_router
from pio_lab.security.enforcer import SecurityEnforcer, SecurityError, enforcer
from pio_lab.utils.logging import logger

ToolExecutor = Callable[[str, Any, dict[str, Any], dict[str, Any]], Any | Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class WorkerConfig:
    """Runtime config for one worker."""

    id: str
    name: str
    department: str
    provider_routing_key: str
    description: str = ""
    system_prompt: str = ""
    tools_enabled: list[str] = field(default_factory=list)
    max_iterations: int = 10
    timeout_seconds: int = 300
    require_human_approval: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> WorkerConfig:
        """Build a worker config from YAML data."""
        return cls(
            id=str(data["id"]),
            name=str(data.get("name") or data["id"]),
            department=str(data.get("department") or ""),
            provider_routing_key=str(data.get("provider_routing_key") or ""),
            description=str(data.get("description") or ""),
            system_prompt=str(data.get("system_prompt") or ""),
            tools_enabled=list(data.get("tools_enabled") or []),
            max_iterations=int(data.get("max_iterations") or 10),
            timeout_seconds=int(data.get("timeout_seconds") or 300),
            require_human_approval=list(data.get("require_human_approval") or []),
            raw=dict(data),
        )


class GenericWorker:
    """Config-driven worker with a minimal ReAct loop."""

    def __init__(
        self,
        config: WorkerConfig,
        *,
        router: ProviderRouter | None = None,
        tool_executor: ToolExecutor | None = None,
        security: SecurityEnforcer | None = None,
        trace_logger: TraceLogger | None = None,
        trace_session: AsyncSession | None = None,
    ) -> None:
        self.config = config
        self.router = router or get_router()
        self.tool_executor = tool_executor or default_tool_executor
        self.security = security or enforcer
        self.trace_logger = trace_logger or TraceLogger()
        self.trace_session = trace_session

    async def run(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run one worker task through ProviderRouter and optional tool calls."""
        resolved_context = context or {}
        messages = self._initial_messages(task, resolved_context)
        iterations: list[dict[str, Any]] = []

        for iteration in range(self.config.max_iterations):
            response = await self.router.call(
                self.config.provider_routing_key,
                messages,
                tools=self._tool_schemas(),
                system=self.config.system_prompt,
                task_id=task.get("trace_task_id"),
                agent_id=self.agent_id,
                timeout=self.config.timeout_seconds,
            )
            content = _content_blocks(response)
            tool_calls = [block for block in content if block.get("type") == "tool_use"]
            iterations.append(
                {
                    "iteration": iteration,
                    "provider": response.get("provider"),
                    "model": response.get("model"),
                    "tool_calls": [call.get("name") for call in tool_calls],
                }
            )

            text = extract_text(response)
            if not tool_calls:
                return {
                    "worker_id": self.config.id,
                    "department_id": self.config.department,
                    "routing_key": self.config.provider_routing_key,
                    "output": text,
                    "iterations": iterations,
                    "raw_response": {key: value for key, value in response.items() if key != "raw"},
                }

            messages.append({"role": "assistant", "content": content})
            tool_result_text = await self._execute_tool_calls(tool_calls, task, resolved_context)
            messages.append({"role": "user", "content": tool_result_text})

        raise TimeoutError(f"Worker {self.agent_id} max iterations exceeded")

    @property
    def agent_id(self) -> str:
        """Stable worker agent id for traces."""
        return f"{self.config.department}.{self.config.id}"

    def _initial_messages(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        user_input = str(task.get("input") or task.get("task") or "")
        if context:
            user_input = f"{user_input}\n\nContext:\n{context}"
        return [{"role": "user", "content": user_input}]

    def _tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"Pio_lab tool: {tool_name}",
                    "parameters": {"type": "object", "additionalProperties": True},
                },
            }
            for tool_name in self.config.tools_enabled
        ]

    async def log_internal_trace(
        self,
        *,
        task: dict[str, Any],
        output: dict[str, Any],
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log deterministic worker execution without requiring a provider call."""
        try:
            await self.trace_logger.log(
                task_id=task.get("trace_task_id"),
                agent_id=self.agent_id,
                routing_key=self.config.provider_routing_key,
                provider="internal",
                model=f"{self.config.department}.{self.config.id}",
                messages_in=[{"role": "user", "content": str(task.get("input") or "")}],
                messages_out=output,
                tokens_in=0,
                tokens_out=0,
                latency_ms=0,
                status=status,
                error=error,
                metadata=metadata,
                session=self.trace_session,
            )
        except Exception as log_error:
            logger.warning(
                "Internal worker trace logging failed for {agent_id}: {error}",
                agent_id=self.agent_id,
                error=log_error,
            )

    async def _execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        results = []
        approval_actions = set(self.config.require_human_approval)
        for tool_call in tool_calls:
            tool_name = str(tool_call.get("name") or "")
            if tool_name in approval_actions or self.security.requires_approval(tool_name):
                raise SecurityError(f"Tool requires human approval: {tool_name}")

            result = self.tool_executor(tool_name, tool_call.get("input") or {}, task, context)
            resolved = await result if isawaitable(result) else result
            results.append(
                {
                    "tool_call_id": tool_call.get("id"),
                    "name": tool_name,
                    "result": resolved,
                }
            )
        return f"Tool results: {results}"


async def default_tool_executor(
    tool_name: str,
    tool_input: Any,
    task: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Default tool executor used until M9 wires real skills."""
    return {
        "ok": False,
        "tool": tool_name,
        "input": tool_input,
        "error": "Tool executor is not configured yet.",
    }


def extract_text(response: dict[str, Any]) -> str:
    """Extract text from a normalized provider response."""
    chunks = [
        str(block.get("text", ""))
        for block in _content_blocks(response)
        if block.get("type") == "text"
    ]
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _content_blocks(response: dict[str, Any]) -> list[dict[str, Any]]:
    content = response.get("content")
    if isinstance(content, list):
        return [item for item in content if isinstance(item, dict)]
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return []


__all__ = [
    "GenericWorker",
    "ToolExecutor",
    "WorkerConfig",
    "default_tool_executor",
    "extract_text",
]
