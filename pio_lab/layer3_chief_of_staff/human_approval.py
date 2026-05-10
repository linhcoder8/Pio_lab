"""Human approval node for sensitive Chief of Staff actions."""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from pio_lab.layer3_chief_of_staff.state import ChiefOfStaffState
from pio_lab.security.enforcer import SecurityEnforcer, enforcer

ACTION_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("upload_to_youtube", ("youtube",)),
    ("upload_to_tiktok", ("tiktok",)),
    ("upload_to_social", ("instagram", "facebook", "social media")),
    ("send_email", ("email", "e-mail")),
    ("send_message_external_user", ("external user", "người ngoài")),
    ("delete_file", ("delete file", "remove file", "xóa file")),
    ("spend_money", ("spend money", "payment", "pay money")),
    ("install_package", ("install package", "pip install", "npm install")),
    ("run_shell_with_sudo", ("sudo", "administrator", "run as admin")),
    ("modify_system_config", ("system config", "registry", "windows config")),
)


def detect_sensitive_action(
    text: str,
    security: SecurityEnforcer | None = None,
) -> dict[str, Any] | None:
    """Return an approval request when text implies a sensitive action."""
    resolved_security = security or enforcer
    lowered = text.lower()

    for action_name, keywords in ACTION_KEYWORDS:
        if resolved_security.requires_approval(action_name) and any(
            keyword in lowered for keyword in keywords
        ):
            return {
                "action": action_name,
                "input": text,
                "prompt": _approval_prompt(action_name, text),
            }
    return None


async def approval_node(state: ChiefOfStaffState) -> dict[str, Any]:
    """Pause graph execution until the owner approves or rejects the action."""
    request = state.get("approval_request") or {}
    action = str(request.get("action") or "")
    if not state.get("requires_approval") or not action:
        return {}
    if action in set(state.get("approved_actions", [])):
        return {"requires_approval": False}

    answer = interrupt(
        {
            "type": "human_approval",
            "action": action,
            "prompt": request.get("prompt") or _approval_prompt(action, state.get("input", "")),
        }
    )
    approved, reason = parse_approval(answer)
    if not approved:
        text = f"Hủy hành động `{action}` theo yêu cầu phê duyệt của Sếp Linh."
        return {
            "status": "rejected",
            "requires_approval": False,
            "rejected_reason": reason,
            "final_output": {"text": text, "approval": {"approved": False, "reason": reason}},
            "trace_events": _append_event(
                state,
                {"node": "approval", "action": action, "approved": False, "reason": reason},
            ),
        }

    return {
        "status": "approved",
        "requires_approval": False,
        "approved_actions": sorted(set(state.get("approved_actions", [])) | {action}),
        "trace_events": _append_event(
            state,
            {"node": "approval", "action": action, "approved": True, "reason": reason},
        ),
    }


def parse_approval(answer: Any) -> tuple[bool, str]:
    """Normalize resume payloads into an approval decision."""
    if isinstance(answer, dict):
        approved = bool(answer.get("approved") or answer.get("approve"))
        reason = str(answer.get("reason") or answer.get("message") or "")
        return approved, reason

    if isinstance(answer, bool):
        return answer, ""

    normalized = str(answer).strip().lower()
    approved_values = {"yes", "y", "true", "approve", "approved", "ok", "dong y", "đồng ý"}
    rejected_values = {"no", "n", "false", "reject", "rejected", "cancel", "huy", "hủy"}
    if normalized in approved_values:
        return True, normalized
    if normalized in rejected_values:
        return False, normalized
    return False, f"Unclear approval response: {answer}"


def route_after_approval(state: ChiefOfStaffState) -> str:
    """Choose whether to continue or stop after approval."""
    if state.get("status") == "rejected":
        return "end"
    return "dispatch"


def _approval_prompt(action: str, text: str) -> str:
    return (
        "Hành động nhạy cảm cần phê duyệt.\n"
        f"Action: {action}\n"
        f"Request: {text}\n"
        "Trả lời YES để duyệt hoặc NO để hủy."
    )


def _append_event(state: ChiefOfStaffState, event: dict[str, Any]) -> list[dict[str, Any]]:
    return state.get("trace_events", []) + [event]


__all__ = [
    "approval_node",
    "detect_sensitive_action",
    "parse_approval",
    "route_after_approval",
]
