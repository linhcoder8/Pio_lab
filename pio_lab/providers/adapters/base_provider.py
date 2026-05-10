"""Base provider adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pio_lab.providers.account_pool import ProviderAccount

NormalizedResponse = dict[str, Any]


class BaseProvider(ABC):
    """Provider adapter interface returning normalized responses."""

    name: str

    @abstractmethod
    async def complete(
        self,
        account: ProviderAccount,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> NormalizedResponse:
        """Complete one LLM request."""


__all__ = ["BaseProvider", "NormalizedResponse"]
