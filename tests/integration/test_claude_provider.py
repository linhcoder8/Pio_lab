"""Real Claude provider smoke test.

Set RUN_REAL_PROVIDER_TESTS=1 and ANTHROPIC_API_KEY to run.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from pio_lab.providers.router import ProviderRouter


class NullTraceLogger:
    async def log(self, **kwargs: Any) -> None:
        return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_claude_provider_simple_message() -> None:
    if os.environ.get("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 to call the real provider")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY is required for real Claude smoke test")

    router = ProviderRouter(trace_logger=NullTraceLogger())  # type: ignore[arg-type]
    response = await router.call(
        "research.optics",
        [{"role": "user", "content": "Say 'Pio_lab works!'"}],
        max_tokens=64,
    )

    assert response["provider"] == "claude"
    assert response["content"]
