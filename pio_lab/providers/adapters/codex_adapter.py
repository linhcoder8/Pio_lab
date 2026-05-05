"""OpenAI/Codex provider adapter."""

from __future__ import annotations

from pio_lab.providers.adapters.openai_chat_adapter import OpenAIChatProvider


class CodexProvider(OpenAIChatProvider):
    """OpenAI adapter used by the Codex routing target."""

    name = "codex"


__all__ = ["CodexProvider"]
