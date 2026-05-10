"""Real Codex OAuth provider smoke test.

Set RUN_REAL_PROVIDER_TESTS=1 and run `codex login` first.
"""

from __future__ import annotations

from typing import Any

import pytest

from pio_lab.providers.router import ProviderRouter


class NullTraceLogger:
    async def log(self, **kwargs: Any) -> None:
        return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_codex_oauth_provider_simple_message() -> None:
    import os

    if os.environ.get("RUN_REAL_PROVIDER_TESTS") != "1":
        pytest.skip("Set RUN_REAL_PROVIDER_TESTS=1 to call the real provider")

    router = ProviderRouter(
        config={
            "providers": {
                "codex": {
                    "accounts": [
                        {
                            "id": "codex_oauth",
                            "credential_mode": "codex_oauth",
                            "models": ["gpt-4o-mini"],
                            "priority": 1,
                        }
                    ]
                }
            },
            "routing_rules": {
                "chief_of_staff": [{"provider": "codex", "model": "gpt-4o-mini"}]
            },
            "default_chain": [{"provider": "codex", "model": "gpt-4o-mini"}],
        },
        trace_logger=NullTraceLogger(),  # type: ignore[arg-type]
    )
    router.load()
    account = router.account_pool.next_available("codex", "gpt-4o-mini")
    if account is None:
        pytest.skip("Codex OAuth credentials are not available; run `codex login`")

    response = await router.call(
        "chief_of_staff",
        [{"role": "user", "content": "Say 'Pio_lab works!'"}],
        timeout=240,
    )

    assert response["provider"] == "codex"
    assert response["content"]
