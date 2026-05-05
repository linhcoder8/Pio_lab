"""Google Gemini provider adapter."""

from __future__ import annotations

from typing import Any

from pio_lab.providers.account_pool import ProviderAccount
from pio_lab.providers.adapters.base_provider import BaseProvider, NormalizedResponse
from pio_lab.providers.errors import ProviderConfigurationError, ProviderError


class GeminiProvider(BaseProvider):
    """Gemini adapter using google-generativeai."""

    name = "gemini"

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
        """Call Gemini and normalize the response."""
        api_key = self._api_key(account)
        try:
            import google.generativeai as genai
        except ImportError as error:
            raise ProviderConfigurationError("google-generativeai package is not installed") from error

        genai.configure(api_key=api_key)
        generation_config = {"max_output_tokens": kwargs.get("max_tokens", 4096)}
        generative_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system,
            generation_config=generation_config,
            tools=tools,
        )
        prompt = _messages_to_gemini_prompt(messages)

        try:
            response = await generative_model.generate_content_async(prompt)
        except Exception as error:
            raise ProviderError(
                f"Gemini API error: {error}",
                provider=self.name,
                account_id=account.account_id,
            ) from error

        usage = getattr(response, "usage_metadata", None)
        return {
            "content": [{"type": "text", "text": getattr(response, "text", "")}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": getattr(usage, "prompt_token_count", 0) if usage else 0,
                "output_tokens": getattr(usage, "candidates_token_count", 0) if usage else 0,
            },
            "model": model,
            "provider": self.name,
            "raw": response,
        }

    def _api_key(self, account: ProviderAccount) -> str:
        if account.env_key is None:
            raise ProviderConfigurationError(
                "Gemini account requires an env_key",
                provider=self.name,
                account_id=account.account_id,
            )

        import os

        api_key = os.environ.get(account.env_key)
        if not api_key:
            raise ProviderConfigurationError(
                f"Missing environment variable {account.env_key}",
                provider=self.name,
                account_id=account.account_id,
            )
        return api_key


def _messages_to_gemini_prompt(messages: list[dict[str, Any]]) -> str:
    parts = []
    for message in messages:
        role = message.get("role", "user")
        if role == "system":
            continue
        content = message.get("content", "")
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


__all__ = ["GeminiProvider"]
