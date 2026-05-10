"""Tests for M8 DepartmentRegistry and GenericDepartment."""

from __future__ import annotations

from typing import Any

import pytest

from pio_lab.core.registry import DepartmentRegistry
from pio_lab.providers.adapters.base_provider import BaseProvider
from pio_lab.providers.router import ProviderRouter


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
async def test_department_run_selects_backend_worker() -> None:
    """Coder department chọn backend worker cho task API/backend."""
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
    registry = DepartmentRegistry(router=router).load_all()
    coder = registry.get_department("coder")

    result = await coder.run({"input": "Viết FastAPI backend endpoint POST /users"})

    assert result["department_id"] == "coder"
    assert result["worker_id"] == "backend"
    assert result["routing_key"] == "coder.backend"
    assert result["output"] == "Worker completed"
