"""REPLAN node for QA retry loops."""

from __future__ import annotations

from pio_lab.layer3_chief_of_staff.state import ChiefOfStaffState


async def replan_node(state: ChiefOfStaffState) -> dict[str, object]:
    """Increment replan count and route back to PLAN."""
    next_count = int(state.get("replan_count", 0) or 0) + 1
    return {
        "replan_count": next_count,
        "status": "replanning",
        "trace_events": state.get("trace_events", [])
        + [
            {
                "node": "replan",
                "replan_count": next_count,
                "qa_feedback": state.get("qa_feedback"),
            }
        ],
    }


__all__ = ["replan_node"]
