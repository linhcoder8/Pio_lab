"""Live provider smoke tests for provider-backed department workers."""

from __future__ import annotations

from typing import Any

import pytest

from pio_lab.core.registry import DepartmentRegistry
from pio_lab.providers.router import ProviderRouter


class NullTraceLogger:
    async def log(self, **kwargs: Any) -> None:
        return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_optics_can_use_codex_oauth_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    if os.environ.get("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 to call the real provider")
    monkeypatch.setenv("PROVIDER_ROUTING_PROFILE", "codex_oauth")

    router = ProviderRouter(trace_logger=NullTraceLogger())  # type: ignore[arg-type]
    router.load()
    account = router.account_pool.next_available("codex", "gpt-4o")
    if account is None:
        pytest.skip("Codex OAuth credentials are not available; run `codex login`")

    registry = DepartmentRegistry(
        router=router,
        trace_logger=NullTraceLogger(),  # type: ignore[arg-type]
    ).load_all()

    result = await registry.get_department("research").run(
        {
            "input": "Summarize lens design in two short bullets.",
            "worker": "optics",
            "worker_mode": "provider",
        }
    )

    assert result["department_id"] == "research"
    assert result["worker_id"] == "optics"
    assert result["routing_key"] == "research.optics"
    assert result["output"].strip()
    assert result["worker_result"]["raw_response"]["provider"] == "codex"
    assert result["worker_result"]["raw_response"]["model"] == "gpt-4o"
