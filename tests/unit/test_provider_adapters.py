"""Adapter-level smoke tests for M4 providers with mocked SDK clients."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
import warnings

import pytest

from pio_lab.providers.account_pool import ProviderAccount
from pio_lab.providers.adapters.codex_adapter import CodexProvider, _resolve_codex_command
from pio_lab.providers.adapters.deepseek_adapter import DeepSeekProvider
from pio_lab.providers.adapters.gemini_adapter import GeminiProvider
from pio_lab.providers.adapters.ollama_adapter import OllamaProvider


class FakeOpenAICompletions:
    async def create(self, **kwargs: Any) -> Any:
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="OpenAI-compatible works", tool_calls=None),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=4),
        )


class FakeOpenAIClient:
    instances: list["FakeOpenAIClient"] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.chat = SimpleNamespace(completions=FakeOpenAICompletions())
        self.instances.append(self)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "account"),
    [
        (
            CodexProvider(),
            ProviderAccount(
                provider="codex",
                account_id="codex_main",
                env_key="OPENAI_API_KEY",
                models=["gpt-4o"],
            ),
        ),
        (
            DeepSeekProvider(),
            ProviderAccount(
                provider="deepseek",
                account_id="deepseek_main",
                env_key="DEEPSEEK_API_KEY",
                models=["deepseek-coder"],
            ),
        ),
    ],
)
async def test_openai_compatible_adapters_smoke(
    monkeypatch: pytest.MonkeyPatch,
    provider: CodexProvider | DeepSeekProvider,
    account: ProviderAccount,
) -> None:
    import openai

    monkeypatch.setenv(account.env_key or "", "test-key")
    monkeypatch.setattr(openai, "AsyncOpenAI", FakeOpenAIClient)

    response = await provider.complete(
        account,
        account.models[0],
        [{"role": "user", "content": "Say Pio_lab works"}],
    )

    assert response["provider"] == provider.name
    assert response["content"][0]["text"] == "OpenAI-compatible works"
    assert response["usage"] == {"input_tokens": 3, "output_tokens": 4}


@pytest.mark.asyncio
async def test_codex_adapter_can_use_codex_oauth_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir()
    (codex_home / "auth.json").write_text(
        """
        {
          "auth_mode": "chatgpt",
          "OPENAI_API_KEY": null,
          "tokens": {
            "access_token": "oauth-access-token",
            "refresh_token": "oauth-refresh-token",
            "account_id": "acct_test"
          }
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    async def fake_run(self: CodexProvider, prompt: str, *, timeout: float) -> str:
        assert "Say Pio_lab works" in prompt
        assert timeout == 180.0
        return "Codex OAuth works"

    monkeypatch.setattr(CodexProvider, "_run_codex_cli", fake_run)

    account = ProviderAccount(
        provider="codex",
        account_id="codex_oauth",
        models=["gpt-4o"],
        metadata={"credential_mode": "codex_oauth"},
    )

    response = await CodexProvider().complete(
        account,
        "gpt-4o",
        [{"role": "user", "content": "Say Pio_lab works"}],
    )

    assert response["provider"] == "codex"
    assert response["content"][0]["text"] == "Codex OAuth works"
    assert response["raw"]["transport"] == "codex_cli"


def test_codex_command_resolution_prefers_windows_cmd_wrapper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    wrapper = tmp_path / "codex.cmd"
    wrapper.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.delenv("CODEX_COMMAND", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))

    assert _resolve_codex_command().lower().endswith("codex.cmd")


def test_codex_prompt_does_not_expose_provider_adapter_language() -> None:
    from pio_lab.providers.adapters.codex_adapter import _codex_prompt

    prompt = _codex_prompt(
        [{"role": "user", "content": "Research lens design"}],
        system="You are Optics Researcher.",
        tools=None,
    )

    forbidden_terms = [
        "provider adapter",
        "Codex CLI",
        "workspace agent",
        "operate in a workspace",
    ]
    for term in forbidden_terms:
        assert term not in prompt
    assert "Answer this directly for a Telegram user: Research lens design" in prompt
    assert "Full user request:" in prompt
    assert "Research lens design" in prompt


@pytest.mark.asyncio
async def test_gemini_adapter_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as genai

    class FakeGeminiModel:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        async def generate_content_async(self, prompt: str) -> Any:
            return SimpleNamespace(
                text="Gemini works",
                usage_metadata=SimpleNamespace(prompt_token_count=5, candidates_token_count=6),
            )

    account = ProviderAccount(
        provider="gemini",
        account_id="gemini_main",
        env_key="GEMINI_API_KEY",
        models=["gemini-2.0-pro"],
    )
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(genai, "configure", lambda **kwargs: None)
    monkeypatch.setattr(genai, "GenerativeModel", FakeGeminiModel)

    response = await GeminiProvider().complete(
        account,
        "gemini-2.0-pro",
        [{"role": "user", "content": "Say Pio_lab works"}],
    )

    assert response["provider"] == "gemini"
    assert response["content"][0]["text"] == "Gemini works"
    assert response["usage"] == {"input_tokens": 5, "output_tokens": 6}


@pytest.mark.asyncio
async def test_ollama_adapter_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    import ollama

    class FakeOllamaClient:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        async def chat(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "message": {"content": "Ollama works"},
                "prompt_eval_count": 7,
                "eval_count": 8,
            }

    account = ProviderAccount(
        provider="ollama",
        account_id="ollama_local",
        models=["gpt-oss-20b"],
    )
    monkeypatch.setattr(ollama, "AsyncClient", FakeOllamaClient)

    response = await OllamaProvider().complete(
        account,
        "gpt-oss-20b",
        [{"role": "user", "content": "Say Pio_lab works"}],
    )

    assert response["provider"] == "ollama"
    assert response["content"][0]["text"] == "Ollama works"
    assert response["usage"] == {"input_tokens": 7, "output_tokens": 8}
