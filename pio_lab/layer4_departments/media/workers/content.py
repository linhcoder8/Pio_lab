"""Deterministic content writer for M9 department dispatch."""

from __future__ import annotations

from typing import Any

from pio_lab.layer4_departments.base.worker_base import GenericWorker
from pio_lab.layer4_departments.worker_utils import count_words


class ContentWorker(GenericWorker):
    """Write long-form prose without requiring an external provider."""

    async def run(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a blog article of at least 500 words."""
        topic = str(task.get("topic") or task.get("input") or task.get("task") or "AI operations")
        article = _build_blog(topic)
        word_count = count_words(article)
        result = {
            "worker_id": self.config.id,
            "department_id": self.config.department,
            "routing_key": self.config.provider_routing_key,
            "output": article,
            "word_count": word_count,
        }
        await self.log_internal_trace(
            task=task,
            output=result,
            metadata={"topic": topic, "word_count": word_count},
        )
        return result


def _build_blog(topic: str) -> str:
    paragraphs = [
        (
            f"# {topic}\n\n"
            f"{topic} matters because modern teams need practical systems, not scattered "
            "experiments. A good workflow turns a vague request into a concrete plan, sends "
            "specialized work to the right department, checks the result, and returns something "
            "that a human can use immediately. The important shift is treating automation as an "
            "operating model instead of a single chatbot window."
        ),
        (
            "The first principle is clear ownership. When a request arrives, the system should "
            "decide whether it is a coding task, a research task, a content task, a reporting "
            "task, or a quality review task. That decision does not need to be dramatic. It only "
            "needs to be reliable enough that each worker receives the right context, tools, and "
            "output expectations. This keeps the work understandable and makes failures easier "
            "to debug."
        ),
        (
            "The second principle is useful memory. Short-term state helps an agent finish the "
            "current job, while long-term notes preserve decisions, assumptions, and reusable "
            "facts. For a personal AI company, memory should stay close to normal work habits: "
            "project files, markdown notes, trace logs, and structured records. That blend gives "
            "the owner visibility without forcing every detail into a database table."
        ),
        (
            "The third principle is verification. A worker that writes code should run tests. A "
            "research worker should cite sources. A content worker should meet length and tone "
            "requirements. A reporting worker should create a real artifact, not only promise "
            "one. Quality assurance should inspect the produced output and give a machine-readable "
            "verdict, because orchestration can only improve work it can measure."
        ),
        (
            "This style of system also changes how people delegate. Instead of writing a perfect "
            "prompt for every specialist, the user can state the outcome and let the Chief of "
            "Staff break it into steps. The plan may be simple for small tasks and more cautious "
            "for sensitive actions such as uploads, deletes, purchases, or external messages. "
            "That distinction matters because autonomy is useful only when it respects risk."
        ),
        (
            "A strong implementation remains boring in the right places. File access is limited "
            "to approved paths. Secrets are masked. Provider calls go through a router. Workers "
            "return consistent dictionaries. Trace logging records what happened without turning "
            "every feature into an external dependency. These conventions make the system easier "
            "to extend when real providers, OAuth, and richer tools are added later."
        ),
        (
            f"For {topic}, the practical takeaway is to build the smallest end-to-end path that "
            "proves the loop: plan, dispatch, produce, review, and report. Once that path is "
            "stable, individual departments can become more capable without changing the user's "
            "mental model. The product starts to feel less like a demo and more like a dependable "
            "workspace."
        ),
    ]
    article = "\n\n".join(paragraphs)
    while count_words(article) < 500:
        article += (
            "\n\nOperational maturity comes from repeating the same disciplined loop: define the "
            "expected artifact, record the assumptions, run the available checks, and keep the "
            "result easy to inspect. That rhythm gives every milestone a visible outcome."
        )
    return article


__all__ = ["ContentWorker"]
