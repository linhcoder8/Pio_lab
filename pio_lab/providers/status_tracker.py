"""Provider call status tracker."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pio_lab.utils.helpers import utc_now

ProviderCallState = Literal["waiting", "running", "end", "failed", "skipped"]


@dataclass(slots=True)
class ProviderCallStatus:
    """Current state for one routing key/provider/model call."""

    routing_key: str
    provider: str
    model: str
    state: ProviderCallState
    error: str | None = None
    updated_at: object = None


class StatusTracker:
    """Track provider call status for observability."""

    def __init__(self) -> None:
        self._statuses: dict[tuple[str, str, str], ProviderCallStatus] = {}

    def set(
        self,
        routing_key: str,
        provider: str,
        model: str,
        state: ProviderCallState,
        *,
        error: str | None = None,
    ) -> ProviderCallStatus:
        """Set and return provider call status."""
        status = ProviderCallStatus(
            routing_key=routing_key,
            provider=provider,
            model=model,
            state=state,
            error=error,
            updated_at=utc_now(),
        )
        self._statuses[(routing_key, provider, model)] = status
        return status

    def get(self, routing_key: str, provider: str, model: str) -> ProviderCallStatus | None:
        """Return status for one provider call."""
        return self._statuses.get((routing_key, provider, model))


__all__ = ["ProviderCallState", "ProviderCallStatus", "StatusTracker"]
