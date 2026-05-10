"""Department registry for dynamic Layer 4 loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from pio_lab.layer4_departments.base.department_base import DepartmentConfig, GenericDepartment
from pio_lab.layer4_departments.base.worker_base import GenericWorker, ToolExecutor, WorkerConfig
from pio_lab.memory.postgres.traces import TraceLogger
from pio_lab.providers.router import ProviderRouter, get_router
from pio_lab.utils.config_loader import CONFIG_ROOT

PROJECT_ROOT = CONFIG_ROOT.parent
DEPARTMENTS_ROOT = CONFIG_ROOT / "departments"


class DepartmentRegistry:
    """Load and manage active departments from YAML config."""

    def __init__(
        self,
        *,
        registry_path: str | Path | None = None,
        router: ProviderRouter | None = None,
        tool_executor: ToolExecutor | None = None,
        trace_logger: TraceLogger | None = None,
        trace_session: AsyncSession | None = None,
    ) -> None:
        self.registry_path = Path(registry_path or DEPARTMENTS_ROOT / "_registry.yaml")
        self.router = router or get_router()
        self.tool_executor = tool_executor
        self.trace_logger = trace_logger or TraceLogger()
        self.trace_session = trace_session
        self.departments: dict[str, GenericDepartment] = {}

    def load_all(self) -> DepartmentRegistry:
        """Load all enabled departments from the registry YAML."""
        registry = _load_yaml(self.registry_path)
        self.departments.clear()
        for entry in registry.get("departments", []):
            if entry.get("enabled", True):
                department = self._load_department(entry)
                self.departments[department.config.id] = department
        return self

    def list_departments(self) -> list[GenericDepartment]:
        """Return active departments in registry order."""
        return list(self.departments.values())

    def get_department(self, department_id: str) -> GenericDepartment:
        """Return one active department by id."""
        try:
            return self.departments[department_id]
        except KeyError as error:
            raise KeyError(f"Department not found: {department_id}") from error

    def add_department(
        self,
        department_config: dict[str, Any],
        worker_configs: list[dict[str, Any]] | None = None,
    ) -> GenericDepartment:
        """Add or replace a department at runtime without writing YAML."""
        config = DepartmentConfig.from_mapping(department_config)
        workers = {
            worker_config["id"]: self._build_worker(worker_config)
            for worker_config in (worker_configs or [])
        }
        department = GenericDepartment(config, workers=workers)
        self.departments[config.id] = department
        return department

    def _load_department(self, registry_entry: dict[str, Any]) -> GenericDepartment:
        config_path = _resolve_project_path(registry_entry["config_path"], self.registry_path.parent)
        department_data = _load_yaml(config_path)
        department_config = DepartmentConfig.from_mapping(department_data)
        worker_configs = self._load_worker_configs(department_data, config_path)
        workers = {
            worker_config.id: self._build_worker_from_config(worker_config)
            for worker_config in worker_configs
        }
        return GenericDepartment(department_config, workers=workers)

    def _load_worker_configs(
        self,
        department_data: dict[str, Any],
        department_config_path: Path,
    ) -> list[WorkerConfig]:
        workers_path = _resolve_relative_to_file(
            department_data.get("workers_path", "./workers"),
            department_config_path,
        )
        worker_configs = []
        for worker_id in department_data.get("workers", []):
            worker_data = _load_yaml(workers_path / f"{worker_id}.yaml")
            worker_configs.append(WorkerConfig.from_mapping(worker_data))
        return worker_configs

    def _build_worker(self, worker_config: dict[str, Any]) -> GenericWorker:
        return self._build_worker_from_config(WorkerConfig.from_mapping(worker_config))

    def _build_worker_from_config(self, worker_config: WorkerConfig) -> GenericWorker:
        worker_class = _worker_class(worker_config.department, worker_config.id)
        return worker_class(
            worker_config,
            router=self.router,
            tool_executor=self.tool_executor,
            trace_logger=self.trace_logger,
            trace_session=self.trace_session,
        )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {path}")
    return data


def _resolve_project_path(path: str | Path, base_dir: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    if str(path).startswith("./config/") or str(path).startswith("config/"):
        return (PROJECT_ROOT / str(path).lstrip("./")).resolve()
    return (base_dir / candidate).resolve()


def _resolve_relative_to_file(path: str | Path, file_path: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (file_path.parent / candidate).resolve()


def _worker_class(department_id: str, worker_id: str) -> type[GenericWorker]:
    key = (department_id, worker_id)
    if key == ("coder", "backend"):
        from pio_lab.layer4_departments.coder.workers.backend import BackendWorker

        return BackendWorker
    if key == ("research", "optics"):
        from pio_lab.layer4_departments.research.workers.optics import OpticsWorker

        return OpticsWorker
    if key == ("media", "content"):
        from pio_lab.layer4_departments.media.workers.content import ContentWorker

        return ContentWorker
    if key == ("report", "slide_word_web"):
        from pio_lab.layer4_departments.report.workers.slide_word_web import SlideWordWebWorker

        return SlideWordWebWorker
    if key == ("qa", "qa_reviewer"):
        from pio_lab.layer4_departments.qa.workers.qa_reviewer import QaReviewerWorker

        return QaReviewerWorker
    return GenericWorker


__all__ = ["DEPARTMENTS_ROOT", "DepartmentRegistry", "PROJECT_ROOT"]
