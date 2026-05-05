"""DeepSeek OpenAI-compatible provider adapter."""

from __future__ import annotations

from pio_lab.providers.adapters.openai_chat_adapter import OpenAIChatProvider


class DeepSeekProvider(OpenAIChatProvider):
    """DeepSeek adapter using the OpenAI-compatible API."""

    name = "deepseek"
    base_url = "https://api.deepseek.com"


__all__ = ["DeepSeekProvider"]
