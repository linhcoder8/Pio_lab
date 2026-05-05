"""Anthropic Claude provider adapter."""

from __future__ import annotations

import os
from typing import Any

from pio_lab.providers.account_pool import ProviderAccount
from pio_lab.providers.adapters.base_provider import BaseProvider, NormalizedResponse
from pio_lab.providers.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderError,
    QuotaExceededError,
)


class ClaudeProvider(BaseProvider):
    """Claude adapter using the Anthropic async SDK."""

    name = "claude"

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
        """Call Claude and normalize the response."""
        if account.env_key is None:
            raise ProviderConfigurationError(
                "Claude account requires an env_key",
                provider=self.name,
                account_id=account.account_id,
            )
        api_key = os.environ.get(account.env_key)
        if not api_key:
            raise ProviderConfigurationError(
                f"Missing environment variable {account.env_key}",
                provider=self.name,
                account_id=account.account_id,
            )

        try:
            import anthropic
            from anthropic import AsyncAnthropic
        except ImportError as error:
            raise ProviderConfigurationError("anthropic package is not installed") from error

        client = AsyncAnthropic(api_key=api_key, timeout=kwargs.get("timeout", 60.0))
        request: dict[str, Any] = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": [message for message in messages if message.get("role") != "system"],
        }
        resolved_system = system or _extract_system_message(messages)
        if resolved_system:
            request["system"] = resolved_system
        if tools:
            request["tools"] = tools

        try:
            response = await client.messages.create(**request)
        except anthropic.RateLimitError as error:
            raise QuotaExceededError(
                "Claude quota or rate limit exceeded",
                provider=self.name,
                account_id=account.account_id,
            ) from error
        except anthropic.AuthenticationError as error:
            raise ProviderAuthenticationError(
                "Claude authentication failed",
                provider=self.name,
                account_id=account.account_id,
            ) from error
        except anthropic.APIError as error:
            raise ProviderError(
                f"Claude API error: {error}",
                provider=self.name,
                account_id=account.account_id,
            ) from error

        usage = getattr(response, "usage", None)
        return {
            "content": [_normalize_block(block) for block in response.content],
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
                "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
            },
            "model": model,
            "provider": self.name,
            "raw": response,
        }


def _extract_system_message(messages: list[dict[str, Any]]) -> str | None:
    for message in messages:
        if message.get("role") == "system":
            content = message.get("content")
            if isinstance(content, str):
                return content
    return None


def _normalize_block(block: Any) -> dict[str, Any]:
    block_type = getattr(block, "type", None)
    if block_type == "text":
        return {"type": "text", "text": getattr(block, "text", "")}
    if block_type == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(block, "id", ""),
            "name": getattr(block, "name", ""),
            "input": getattr(block, "input", {}),
        }
    return {"type": str(block_type or "unknown"), "raw": repr(block)}


__all__ = ["ClaudeProvider"]
