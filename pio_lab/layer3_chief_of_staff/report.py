"""REPORT node and QA decision for Chief of Staff."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from inspect import isawaitable
from typing import Any

from pio_lab.layer3_chief_of_staff.state import ChiefOfStaffState

QAReviewer = Callable[[ChiefOfStaffState], dict[str, Any] | Awaitable[dict[str, Any]]]


class ReportNode:
    """Aggregate dispatch results and run a lightweight QA verdict."""

    def __init__(self, *, qa_reviewer: QAReviewer | None = None) -> None:
        self.qa_reviewer = qa_reviewer or default_qa_reviewer

    async def __call__(self, state: ChiefOfStaffState) -> dict[str, Any]:
        """Create final report or trigger the replan loop when QA fails."""
        if state.get("status") == "rejected":
            return {}

        qa_result = self.qa_reviewer(state)
        qa = await qa_result if isawaitable(qa_result) else qa_result
        verdict = str(qa.get("verdict", "PASS")).upper()
        feedback = str(qa.get("feedback") or "")
        max_replans = int(state.get("max_replans", 3) or 3)
        replan_count = int(state.get("replan_count", 0) or 0)

        if verdict == "NEEDS_FIX" and replan_count < max_replans:
            return {
                "qa_verdict": verdict,
                "qa_feedback": feedback,
                "status": "needs_replan",
                "trace_events": state.get("trace_events", [])
                + [{"node": "report", "qa_verdict": verdict, "feedback": feedback}],
            }

        output_text = _aggregate_outputs(state.get("dispatch_results", []))
        status = "done" if verdict == "PASS" else "done_with_warnings"
        if verdict != "PASS":
            output_text = f"{output_text}\n\nQA chưa pass sau {max_replans} lần replan: {feedback}"

        return {
            "qa_verdict": verdict,
            "qa_feedback": feedback,
            "status": status,
            "final_output": {
                "text": output_text,
                "qa": {"verdict": verdict, "feedback": feedback},
            },
            "trace_events": state.get("trace_events", [])
            + [{"node": "report", "qa_verdict": verdict, "status": status}],
        }


def default_qa_reviewer(state: ChiefOfStaffState) -> dict[str, Any]:
    """Use QA department output when available, with a conservative fallback."""
    dispatch_results = state.get("dispatch_results", [])
    if not dispatch_results:
        return {"verdict": "NEEDS_FIX", "feedback": "No dispatch result was produced."}
    qa = _latest_qa_result(dispatch_results)
    if qa:
        verdict = str(qa.get("verdict", "PASS")).upper()
        issues = qa.get("issues") or []
        feedback = "; ".join(str(issue) for issue in issues) if issues else ""
        return {"verdict": verdict, "feedback": feedback, "qa": qa}
    return {"verdict": "PASS", "feedback": ""}


def route_after_report(state: ChiefOfStaffState) -> str:
    """Route to replan while QA says the output needs fixes."""
    if state.get("status") == "needs_replan":
        return "replan"
    return "end"


def _aggregate_outputs(results: list[dict[str, Any]]) -> str:
    reportable = [result for result in results if result.get("department_id") != "qa"]
    chunks = [str(result.get("output", "")).strip() for result in reportable or results]
    text = "\n\n".join(chunk for chunk in chunks if chunk)
    return text or "Không có output từ bước dispatch."


def _latest_qa_result(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    for result in reversed(results):
        worker_result = result.get("worker_result") or {}
        qa = result.get("qa") or worker_result.get("qa")
        if isinstance(qa, dict):
            return qa
        output = result.get("output") or worker_result.get("output")
        if isinstance(output, str) and output.strip().startswith("{"):
            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and "verdict" in parsed:
                return parsed
    return None


__all__ = ["QAReviewer", "ReportNode", "default_qa_reviewer", "route_after_report"]
