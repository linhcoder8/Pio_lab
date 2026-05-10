"""Generic department implementation for Layer 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pio_lab.layer4_departments.base.worker_base import GenericWorker, WorkerConfig


@dataclass(frozen=True, slots=True)
class DepartmentConfig:
    """Runtime config for one department."""

    id: str
    name: str
    name_vi: str = ""
    description: str = ""
    system_prompt: str = ""
    workers: list[str] = field(default_factory=list)
    default_tools: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> DepartmentConfig:
        """Build department config from YAML data."""
        return cls(
            id=str(data["id"]),
            name=str(data.get("name") or data["id"]),
            name_vi=str(data.get("name_vi") or ""),
            description=str(data.get("description") or ""),
            system_prompt=str(data.get("system_prompt") or ""),
            workers=list(data.get("workers") or []),
            default_tools=list(data.get("default_tools") or []),
            raw=dict(data),
        )


class GenericDepartment:
    """Config-driven department that selects and runs one worker."""

    def __init__(
        self,
        config: DepartmentConfig,
        *,
        workers: dict[str, GenericWorker] | None = None,
    ) -> None:
        self.config = config
        self.workers = workers or {}

    def select_worker(self, task: dict[str, Any]) -> GenericWorker:
        """Select the best worker using explicit task hints and simple heuristics."""
        requested = task.get("worker") or task.get("worker_id")
        if requested and str(requested) in self.workers:
            return self.workers[str(requested)]

        user_input = str(task.get("input") or task.get("task") or "").lower()
        preferred = self._heuristic_worker_id(user_input)
        if preferred in self.workers:
            return self.workers[preferred]

        for worker_id in self.config.workers:
            if worker_id in self.workers:
                return self.workers[worker_id]

        if self.workers:
            return next(iter(self.workers.values()))
        raise ValueError(f"Department {self.config.id} has no workers")

    async def run(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Select a worker, run it, and return an aggregated department result."""
        worker = self.select_worker(task)
        worker_result = await worker.run(task, context or {})
        return {
            "department_id": self.config.id,
            "worker_id": worker.config.id,
            "routing_key": worker.config.provider_routing_key,
            "output": worker_result.get("output", ""),
            "worker_result": worker_result,
        }

    def _heuristic_worker_id(self, user_input: str) -> str:
        if self.config.id == "coder":
            if any(marker in user_input for marker in ("ui", "frontend", "react", "css", "html")):
                return "frontend"
            return "backend"
        if self.config.id == "research":
            return "optics"
        if self.config.id == "media":
            if any(marker in user_input for marker in ("image", "thumbnail", "ảnh", "hình")):
                return "image_maker"
            if any(marker in user_input for marker in ("video", "youtube", "tiktok")):
                return "video_maker"
            return "content"
        if self.config.id == "report":
            if "video" in user_input:
                return "video_report"
            return "slide_word_web"
        if self.config.id == "qa":
            return "qa_reviewer"
        return ""


def build_worker(config: dict[str, Any], **kwargs: Any) -> GenericWorker:
    """Build a GenericWorker from a config mapping."""
    return GenericWorker(WorkerConfig.from_mapping(config), **kwargs)


__all__ = ["DepartmentConfig", "GenericDepartment", "build_worker"]
