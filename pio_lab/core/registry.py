"""Department registry for dynamic Layer 4 loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from pio_lab.layer4_departments.base.department_base import DepartmentConfig, GenericDepartment
from pio_lab.layer4_departments.base.worker_base import GenericWorker, ToolExecutor, WorkerConfig
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
    ) -> None:
        self.registry_path = Path(registry_path or DEPARTMENTS_ROOT / "_registry.yaml")
        self.router = router or get_router()
        self.tool_executor = tool_executor
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
            worker_config.id: GenericWorker(
                worker_config,
                router=self.router,
                tool_executor=self.tool_executor,
            )
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
        return GenericWorker(
            WorkerConfig.from_mapping(worker_config),
            router=self.router,
            tool_executor=self.tool_executor,
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


__all__ = ["DEPARTMENTS_ROOT", "DepartmentRegistry", "PROJECT_ROOT"]
