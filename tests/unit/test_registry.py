"""Tests for M8 DepartmentRegistry and GenericDepartment."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from pio_lab.core.registry import DepartmentRegistry
from pio_lab.providers.adapters.base_provider import BaseProvider
from pio_lab.providers.router import ProviderRouter
from pio_lab.security.policy_loader import PROJECT_ROOT


class FakeProvider(BaseProvider):
    name = "fake"

    async def complete(
        self,
        account,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": "Worker completed"}],
            "usage": {"input_tokens": 1, "output_tokens": 2},
            "provider": "fake",
            "model": model,
            "raw": None,
        }


class FakeTraceLogger:
    async def log(self, **kwargs: Any) -> None:
        return None


@pytest.fixture
def output_root() -> Iterator[Path]:
    root = PROJECT_ROOT / "tmp" / "tests" / f"registry_{uuid4().hex}"
    yield root
    if root.exists():
        shutil.rmtree(root)


def test_registry_loads_5_departments() -> None:
    """Registry phải load đủ 5 phòng ban từ config/departments/_registry.yaml."""
    registry = DepartmentRegistry().load_all()

    assert set(registry.departments) == {"report", "coder", "research", "media", "qa"}
    assert sum(len(department.workers) for department in registry.list_departments()) == 9
    assert registry.get_department("coder").workers["backend"].config.provider_routing_key == (
        "coder.backend"
    )


def test_add_department_at_runtime() -> None:
    """Hot reload: thêm phòng ban in-memory không cần restart."""
    registry = DepartmentRegistry()

    department = registry.add_department(
        {
            "id": "sales",
            "name": "SALES",
            "workers": ["pitch"],
            "system_prompt": "Route sales tasks.",
        },
        [
            {
                "id": "pitch",
                "name": "Pitch Worker",
                "department": "sales",
                "provider_routing_key": "sales.pitch",
            }
        ],
    )

    assert registry.get_department("sales") is department
    assert department.select_worker({"input": "Write a pitch"}).config.id == "pitch"


@pytest.mark.asyncio
async def test_department_run_selects_backend_worker(output_root: Path) -> None:
    """Coder department chọn backend worker và chạy artifact M9."""
    router = ProviderRouter(
        config={
            "providers": {
                "fake": {
                    "accounts": [{"id": "fake_main", "models": ["fake-model"], "priority": 1}]
                }
            },
            "routing_rules": {"coder.backend": [{"provider": "fake", "model": "fake-model"}]},
            "default_chain": [{"provider": "fake", "model": "fake-model"}],
        },
        adapters={"fake": FakeProvider()},
    )
    registry = DepartmentRegistry(
        router=router,
        trace_logger=FakeTraceLogger(),  # type: ignore[arg-type]
    ).load_all()
    coder = registry.get_department("coder")

    result = await coder.run(
        {
            "input": "Viết Python function có test",
            "output_dir": str(output_root / "coder"),
        }
    )

    assert result["department_id"] == "coder"
    assert result["worker_id"] == "backend"
    assert result["routing_key"] == "coder.backend"
    assert result["pytest"]["passed"] is True
