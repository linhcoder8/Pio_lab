"""PLAN node for Chief of Staff orchestration."""

from __future__ import annotations

from typing import Any

from pio_lab.layer3_chief_of_staff.human_approval import detect_sensitive_action
from pio_lab.layer3_chief_of_staff.state import ChiefOfStaffState
from pio_lab.security.enforcer import SecurityEnforcer, enforcer
from pio_lab.utils.config_loader import load_pio_lab_config


class PlanNode:
    """Build a lightweight execution plan for M7."""

    def __init__(
        self,
        *,
        security: SecurityEnforcer | None = None,
        app_config: dict[str, Any] | None = None,
    ) -> None:
        self.security = security or enforcer
        self.app_config = app_config or load_pio_lab_config()

    async def __call__(self, state: ChiefOfStaffState) -> dict[str, Any]:
        """Plan a request with fast path, approval detection, and replan context."""
        user_input = state.get("input", "").strip()
        replan_count = int(state.get("replan_count", 0) or 0)
        max_replans = int(
            state.get("max_replans")
            or self.app_config.get("chief_of_staff", {}).get("replan_max_attempts", 3)
        )
        approval_request = detect_sensitive_action(user_input, self.security)
        approved_actions = set(state.get("approved_actions", []))
        requires_approval = bool(
            approval_request and approval_request["action"] not in approved_actions
        )
        fast_path = self._is_fast_path(user_input) and replan_count == 0
        steps = self._build_steps(user_input, fast_path, replan_count, state.get("qa_feedback"))
        plan = {
            "intent": "casual_qa" if fast_path else self._classify_intent(user_input),
            "fast_path": fast_path,
            "steps": steps,
            "replan_count": replan_count,
        }

        return {
            "plan": plan,
            "max_replans": max_replans,
            "requires_approval": requires_approval,
            "approval_request": approval_request or {},
            "status": "planned",
            "trace_events": state.get("trace_events", [])
            + [
                {
                    "node": "plan",
                    "intent": plan["intent"],
                    "fast_path": fast_path,
                    "requires_approval": requires_approval,
                    "replan_count": replan_count,
                }
            ],
        }

    def _is_fast_path(self, user_input: str) -> bool:
        lowered = user_input.lower()
        if len(user_input) > 240:
            return False
        heavy_markers = (
            "write",
            "viết",
            "create",
            "tạo",
            "research",
            "tìm",
            "paper",
            "upload",
            "delete",
            "install",
            "file",
            "code",
            "bug",
        )
        return not any(marker in lowered for marker in heavy_markers)

    def _classify_intent(self, user_input: str) -> str:
        lowered = user_input.lower()
        if any(marker in lowered for marker in ("research", "paper", "tìm", "doi")):
            return "research"
        if any(marker in lowered for marker in ("blog", "caption", "content")):
            return "content_creation"
        if any(marker in lowered for marker in ("code", "bug", "fastapi", "python", "function")):
            return "code_generation"
        if "upload" in lowered:
            return "external_action"
        return "general_task"

    def _build_steps(
        self,
        user_input: str,
        fast_path: bool,
        replan_count: int,
        qa_feedback: str | None,
    ) -> list[dict[str, Any]]:
        if fast_path:
            return [
                {
                    "id": "fast_path",
                    "department": None,
                    "worker": None,
                    "routing_key": "chief_of_staff",
                    "task": user_input,
                }
            ]

        intent = self._classify_intent(user_input)
        first_step = {
            "id": "execute",
            "department": "coder" if intent == "code_generation" else "chief_of_staff",
            "worker": "backend" if intent == "code_generation" else None,
            "routing_key": "coder.backend" if intent == "code_generation" else "chief_of_staff",
            "task": user_input,
        }
        if intent == "research":
            first_step.update(
                {"department": "research", "worker": "optics", "routing_key": "research.optics"}
            )
        if intent == "content_creation":
            first_step.update(
                {"department": "media", "worker": "content", "routing_key": "media.content"}
            )
        if replan_count > 0 and qa_feedback:
            first_step["task"] = f"{user_input}\n\nQA feedback to fix: {qa_feedback}"

        return [
            first_step,
            {
                "id": "qa",
                "department": "qa",
                "worker": "qa_reviewer",
                "routing_key": "qa.qa_reviewer",
                "task": "Review output quality and policy compliance",
                "deps": ["execute"],
            },
        ]


def route_after_plan(state: ChiefOfStaffState) -> str:
    """Route to approval or dispatch after planning."""
    if state.get("requires_approval"):
        return "approval"
    return "dispatch"


__all__ = ["PlanNode", "route_after_plan"]
