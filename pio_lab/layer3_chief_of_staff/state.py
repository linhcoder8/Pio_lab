"""State schema for the Chief of Staff LangGraph."""

from __future__ import annotations

from typing import Any, TypedDict


class ChiefOfStaffState(TypedDict, total=False):
    """Shared graph state for M7 orchestration."""

    task_id: str
    trace_task_id: str | None
    thread_id: str
    input: str
    user_id: str
    channel: str
    messages: list[dict[str, Any]]
    plan: dict[str, Any]
    dispatch_results: list[dict[str, Any]]
    qa_verdict: str
    qa_feedback: str | None
    replan_count: int
    max_replans: int
    final_output: dict[str, Any]
    archive: dict[str, Any]
    status: str
    requires_approval: bool
    approval_request: dict[str, Any]
    approved_actions: list[str]
    rejected_reason: str | None
    trace_events: list[dict[str, Any]]


__all__ = ["ChiefOfStaffState"]
