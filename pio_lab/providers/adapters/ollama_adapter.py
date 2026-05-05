"""Ollama local provider adapter."""

from __future__ import annotations

import os
from typing import Any

from pio_lab.providers.account_pool import ProviderAccount
from pio_lab.providers.adapters.base_provider import BaseProvider, NormalizedResponse
from pio_lab.providers.errors import ProviderConfigurationError, ProviderError


class OllamaProvider(BaseProvider):
    """Ollama adapter for local/Tailscale-hosted models."""

    name = "ollama"

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
        """Call Ollama chat and normalize the response."""
        try:
            import ollama
        except ImportError as error:
            raise ProviderConfigurationError("ollama package is not installed") from error

        host = os.environ.get("OLLAMA_HOST")
        client = ollama.AsyncClient(host=host) if host else ollama.AsyncClient()
        request_messages = _with_system(messages, system)

        try:
            response = await client.chat(
                model=model,
                messages=request_messages,
                tools=tools,
                options={"num_predict": kwargs.get("max_tokens", 4096)},
            )
        except Exception as error:
            raise ProviderError(
                f"Ollama API error: {error}",
                provider=self.name,
                account_id=account.account_id,
            ) from error

        content = response.get("message", {}).get("content", "")
        return {
            "content": [{"type": "text", "text": content}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": int(response.get("prompt_eval_count", 0) or 0),
                "output_tokens": int(response.get("eval_count", 0) or 0),
            },
            "model": model,
            "provider": self.name,
            "raw": response,
        }


def _with_system(messages: list[dict[str, Any]], system: str | None) -> list[dict[str, Any]]:
    if not system:
        return messages
    if messages and messages[0].get("role") == "system":
        return messages
    return [{"role": "system", "content": system}, *messages]


__all__ = ["OllamaProvider"]
