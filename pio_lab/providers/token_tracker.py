"""Token accounting for provider responses."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(slots=True)
class TokenUsage:
    """Aggregated token usage."""

    input_tokens: int = 0
    output_tokens: int = 0


class TokenTracker:
    """Track token usage by provider and routing key."""

    def __init__(self) -> None:
        self._usage: defaultdict[tuple[str, str], TokenUsage] = defaultdict(TokenUsage)

    def record(
        self,
        *,
        provider: str,
        routing_key: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Add one call's token usage."""
        usage = self._usage[(provider, routing_key)]
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens

    def get(self, provider: str, routing_key: str) -> TokenUsage:
        """Return aggregate usage for provider/routing key."""
        return self._usage[(provider, routing_key)]


__all__ = ["TokenTracker", "TokenUsage"]
