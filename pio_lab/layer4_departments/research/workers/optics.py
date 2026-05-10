"""Deterministic optics researcher for M9 department dispatch."""

from __future__ import annotations

from typing import Any

from pio_lab.layer4_departments.base.worker_base import GenericWorker
from pio_lab.layer4_departments.worker_utils import provider_task, should_use_provider_worker


class OpticsWorker(GenericWorker):
    """Produce a cited local research summary for optics prompts."""

    async def run(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a lens design summary with stable citations."""
        if should_use_provider_worker(task, context):
            return await super().run(
                provider_task(
                    task,
                    instruction=(
                        "Return a concise optics research summary for the user's topic. "
                        "Include 2-3 citation-style references or source hints when possible. "
                        "Do not claim that files were written."
                    ),
                ),
                context,
            )

        query = str(task.get("query") or task.get("input") or task.get("task") or "lens design")
        citations = [
            {
                "id": "1",
                "title": "Rudolph Kingslake, Lens Design Fundamentals",
                "url": "https://doi.org/10.1016/B978-0-12-408654-1.X5000-2",
            },
            {
                "id": "2",
                "title": "Warren J. Smith, Modern Lens Design",
                "url": "https://doi.org/10.1117/3.528920",
            },
            {
                "id": "3",
                "title": "A. E. Siegman, Lasers",
                "url": "https://ui.adsabs.harvard.edu/abs/1986lasr.book.....S/abstract",
            },
        ]
        summary = (
            f"Search topic: {query}\n\n"
            "Lens design usually starts from first-order layout: focal length, aperture, "
            "field of view, working distance, wavelength band, and detector or eye geometry. "
            "After paraxial constraints are set, the designer balances aberrations such as "
            "spherical aberration, coma, astigmatism, field curvature, distortion, and chromatic "
            "error. Classical references describe this as an iterative trade between optical "
            "power distribution, glass choice, stop position, element bending, and manufacturable "
            "tolerances [1].\n\n"
            "For modern lens design, the practical workflow is merit-function driven: define "
            "image quality metrics such as RMS spot radius, MTF, wavefront error, chief-ray "
            "angle, distortion, packaging constraints, and cost limits; then optimize surfaces "
            "while checking sensitivity and tolerancing. Smith emphasizes that a design that "
            "optimizes perfectly on paper can still fail if alignment, thermal drift, coating "
            "choice, and assembly tolerances are not included early [2].\n\n"
            "For laser and photonics systems, Gaussian beam propagation and diffraction are "
            "central. Lens design must account for beam waist, Rayleigh range, numerical "
            "aperture, and damage threshold. Siegman's treatment of Gaussian optics is useful "
            "for choosing focusing lenses and relay systems where diffraction-limited behavior "
            "matters more than broad-field imaging performance [3].\n\n"
            "Recommendation: start with paraxial requirements, choose a feasible glass and "
            "surface family, optimize image quality, then validate with tolerance and stray-light "
            "checks before committing mechanical CAD."
        )
        result = {
            "worker_id": self.config.id,
            "department_id": self.config.department,
            "routing_key": self.config.provider_routing_key,
            "output": summary,
            "citations": citations,
        }
        await self.log_internal_trace(
            task=task,
            output=result,
            metadata={"query": query, "citation_count": len(citations)},
        )
        return result


__all__ = ["OpticsWorker"]
