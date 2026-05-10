"""Deterministic backend worker for M9 department dispatch."""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from pio_lab.layer4_departments.base.worker_base import GenericWorker
from pio_lab.layer4_departments.worker_utils import resolve_output_dir


class BackendWorker(GenericWorker):
    """Create and verify a small Python backend-style artifact."""

    async def run(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Write one Python file and prove it with pytest."""
        output_dir = resolve_output_dir(
            task,
            context,
            "tmp",
            "m9",
            "coder_backend",
            security=self.security,
        )
        code_path = self.security.require_file_access(output_dir / "circle_area.py")
        test_path = self.security.require_file_access(output_dir / "test_circle_area.py")

        code_path.write_text(_circle_area_source(), encoding="utf-8")
        test_path.write_text(_circle_area_tests(), encoding="utf-8")
        pytest_result = await _run_pytest(output_dir, test_path.name, self.config.timeout_seconds)
        passed = pytest_result["returncode"] == 0
        status = "success" if passed else "error"
        output = (
            f"Created {code_path.name} and {test_path.name}. "
            f"pytest {'passed' if passed else 'failed'}."
        )
        result = {
            "worker_id": self.config.id,
            "department_id": self.config.department,
            "routing_key": self.config.provider_routing_key,
            "output": output,
            "artifacts": {
                "code_path": str(code_path),
                "test_path": str(test_path),
            },
            "pytest": pytest_result | {"passed": passed},
        }
        await self.log_internal_trace(
            task=task,
            output=result,
            status=status,
            error=None if passed else pytest_result["stderr"],
            metadata={"artifact_type": "python_file"},
        )
        if not passed:
            raise RuntimeError(f"BackendWorker pytest failed: {pytest_result['stderr']}")
        return result


async def _run_pytest(output_dir, test_name: str, timeout_seconds: int) -> dict[str, Any]:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pytest",
        test_name,
        "-q",
        cwd=output_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(
        process.communicate(),
        timeout=min(timeout_seconds, 120),
    )
    return {
        "returncode": int(process.returncode or 0),
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
    }


def _circle_area_source() -> str:
    return '''"""Circle geometry helpers."""

from __future__ import annotations

import math


def circle_area(radius: float) -> float:
    """Return the area of a circle for a non-negative radius."""
    if radius < 0:
        raise ValueError("radius must be non-negative")
    return math.pi * radius ** 2
'''


def _circle_area_tests() -> str:
    return '''"""Tests for circle_area."""

from __future__ import annotations

import math

import pytest

from circle_area import circle_area


def test_circle_area_zero() -> None:
    assert circle_area(0) == 0


def test_circle_area_unit_radius() -> None:
    assert circle_area(1) == pytest.approx(math.pi)


def test_circle_area_rejects_negative_radius() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        circle_area(-1)
'''


__all__ = ["BackendWorker"]
