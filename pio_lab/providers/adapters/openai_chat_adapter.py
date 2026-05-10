"""Shared OpenAI chat-completions adapter base."""

from __future__ import annotations

from typing import Any

from pio_lab.providers.account_pool import ProviderAccount
from pio_lab.providers.adapters.base_provider import BaseProvider, NormalizedResponse
from pio_lab.providers.credentials import resolve_provider_credential
from pio_lab.providers.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderError,
    QuotaExceededError,
)


class OpenAIChatProvider(BaseProvider):
    """Base adapter for OpenAI-compatible chat completion providers."""

    name = "openai_compatible"
    base_url: str | None = None

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
        """Call an OpenAI-compatible provider and normalize the response."""
        api_key = self._api_key(account)
        try:
            import openai
            from openai import AsyncOpenAI
        except ImportError as error:
            raise ProviderConfigurationError("openai package is not installed") from error

        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        client = AsyncOpenAI(**client_kwargs)

        request_messages = _with_system(messages, system)
        request: dict[str, Any] = {
            "model": model,
            "messages": request_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        if tools:
            request["tools"] = tools

        try:
            response = await client.chat.completions.create(**request)
        except openai.RateLimitError as error:
            raise QuotaExceededError(
                f"{self.name} quota or rate limit exceeded",
                provider=self.name,
                account_id=account.account_id,
            ) from error
        except openai.AuthenticationError as error:
            raise ProviderAuthenticationError(
                f"{self.name} authentication failed",
                provider=self.name,
                account_id=account.account_id,
            ) from error
        except openai.APIError as error:
            raise ProviderError(
                f"{self.name} API error: {error}",
                provider=self.name,
                account_id=account.account_id,
            ) from error

        choice = response.choices[0]
        message = choice.message
        content = _normalize_openai_content(getattr(message, "content", None))
        for tool_call in getattr(message, "tool_calls", None) or []:
            content.append(
                {
                    "type": "tool_use",
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "input": tool_call.function.arguments,
                }
            )

        usage = getattr(response, "usage", None)
        return {
            "content": content,
            "stop_reason": getattr(choice, "finish_reason", None) or "end_turn",
            "usage": {
                "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
            },
            "model": model,
            "provider": self.name,
            "raw": response,
        }

    def _api_key(self, account: ProviderAccount) -> str:
        try:
            return resolve_provider_credential(
                provider=self.name,
                account_id=account.account_id,
                env_key=account.env_key,
                metadata=account.metadata,
            )
        except ProviderConfigurationError as error:
            raise ProviderConfigurationError(
                str(error),
                provider=self.name,
                account_id=account.account_id,
            ) from error


def _with_system(messages: list[dict[str, Any]], system: str | None) -> list[dict[str, Any]]:
    if not system:
        return messages
    if messages and messages[0].get("role") == "system":
        return messages
    return [{"role": "system", "content": system}, *messages]


def _normalize_openai_content(content: Any) -> list[dict[str, Any]]:
    if content is None:
        return []
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        normalized = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                normalized.append({"type": "text", "text": item.get("text", "")})
        return normalized
    return [{"type": "text", "text": str(content)}]


__all__ = ["OpenAIChatProvider"]
