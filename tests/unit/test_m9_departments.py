"""Tests for M9 concrete department workers."""

from __future__ import annotations

import json
import shutil
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from pio_lab.core.registry import DepartmentRegistry
from pio_lab.layer3_chief_of_staff.chief_of_staff import ChiefOfStaff
from pio_lab.providers.errors import ProviderUnavailableError
from pio_lab.security.policy_loader import PROJECT_ROOT


class FakeRouter:
    async def call(
        self,
        routing_key: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": "fallback"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "provider": "fake",
            "model": "fake-model",
            "raw": None,
        }


class FailingRouter:
    async def call(
        self,
        routing_key: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise ProviderUnavailableError(routing_key, ["codex/gpt-4o: failed"])


class FakeTraceLogger:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    async def log(self, **kwargs: Any) -> None:
        self.entries.append(kwargs)


@pytest.fixture
def output_root() -> Iterator[Path]:
    root = PROJECT_ROOT / "tmp" / "tests" / f"m9_{uuid4().hex}"
    yield root
    if root.exists():
        shutil.rmtree(root)


@pytest.fixture
def registry() -> DepartmentRegistry:
    return DepartmentRegistry(
        router=FakeRouter(),  # type: ignore[arg-type]
        trace_logger=FakeTraceLogger(),  # type: ignore[arg-type]
    ).load_all()


@pytest.mark.asyncio
async def test_coder_backend_writes_python_file_and_runs_pytest(
    registry: DepartmentRegistry,
    output_root: Path,
) -> None:
    result = await registry.get_department("coder").run(
        {
            "input": "Write one Python function with tests",
            "worker": "backend",
            "output_dir": str(output_root / "coder"),
        }
    )

    assert result["worker_id"] == "backend"
    assert result["pytest"]["passed"] is True
    assert Path(result["artifacts"]["code_path"]).exists()
    assert "pytest passed" in result["output"]


@pytest.mark.asyncio
async def test_research_optics_returns_lens_design_summary_with_citation(
    registry: DepartmentRegistry,
) -> None:
    result = await registry.get_department("research").run(
        {"input": "Search lens design and summarize", "worker": "optics"}
    )

    assert result["worker_id"] == "optics"
    assert "Lens design" in result["output"] or "lens design" in result["output"]
    assert "[1]" in result["output"]
    assert result["citations"][0]["url"].startswith("https://doi.org/")


@pytest.mark.asyncio
async def test_research_provider_mode_falls_back_when_provider_unavailable() -> None:
    registry = DepartmentRegistry(
        router=FailingRouter(),  # type: ignore[arg-type]
        trace_logger=FakeTraceLogger(),  # type: ignore[arg-type]
    ).load_all()

    result = await registry.get_department("research").run(
        {
            "input": "Research lens design and summarize",
            "worker": "optics",
            "worker_mode": "provider",
        }
    )

    assert result["worker_id"] == "optics"
    assert "Lens design" in result["output"] or "lens design" in result["output"]
    assert result["citations"]


@pytest.mark.asyncio
async def test_media_content_writes_500_word_blog(registry: DepartmentRegistry) -> None:
    result = await registry.get_department("media").run(
        {"input": "Write a 500-word blog about AI operations", "worker": "content"}
    )

    assert result["worker_id"] == "content"
    assert result["word_count"] >= 500
    assert "# Write a 500-word blog" in result["output"]


@pytest.mark.asyncio
async def test_report_slide_word_web_creates_pptx(
    registry: DepartmentRegistry,
    output_root: Path,
) -> None:
    result = await registry.get_department("report").run(
        {
            "input": "Create a one-slide report for M9",
            "worker": "slide_word_web",
            "output_dir": str(output_root / "report"),
        }
    )
    pptx_path = Path(result["artifacts"]["pptx_path"])

    assert result["worker_id"] == "slide_word_web"
    assert pptx_path.suffix == ".pptx"
    assert zipfile.is_zipfile(pptx_path)
    with zipfile.ZipFile(pptx_path) as archive:
        assert "ppt/slides/slide1.xml" in archive.namelist()


@pytest.mark.asyncio
async def test_qa_reviewer_returns_pass_and_needs_fix_json(
    registry: DepartmentRegistry,
) -> None:
    qa = registry.get_department("qa")

    pass_result = await qa.run({"worker": "qa_reviewer", "output": "Complete output"})
    fail_result = await qa.run({"worker": "qa_reviewer", "output": "NEEDS_FIX_ME"})

    assert json.loads(pass_result["output"])["verdict"] == "PASS"
    assert json.loads(fail_result["output"])["verdict"] == "NEEDS_FIX"


@pytest.mark.asyncio
async def test_e2e_user_request_dispatches_department_then_qa(
    output_root: Path,
) -> None:
    traces = FakeTraceLogger()
    chief = ChiefOfStaff(
        router=FakeRouter(),  # type: ignore[arg-type]
        trace_logger=traces,  # type: ignore[arg-type]
    )

    result = await chief.run(
        {
            "input": "Write a Python function for circle area",
            "output_dir": str(output_root / "e2e"),
            "user_id": "local_user",
            "channel": "test",
        }
    )

    assert result["status"] == "done"
    assert result["dispatch_results"][0]["department_id"] == "coder"
    assert result["dispatch_results"][1]["department_id"] == "qa"
    assert result["qa_verdict"] == "PASS"
    assert "pytest passed" in result["final_output"]["text"]
    assert any(entry["routing_key"] == "coder.backend" for entry in traces.entries)
    assert any(entry["routing_key"] == "qa.qa_reviewer" for entry in traces.entries)
