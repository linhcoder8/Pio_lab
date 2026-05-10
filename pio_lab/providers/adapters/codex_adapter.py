"""OpenAI/Codex provider adapter."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

from pio_lab.providers.account_pool import ProviderAccount
from pio_lab.providers.adapters.openai_chat_adapter import OpenAIChatProvider
from pio_lab.providers.credentials import resolve_provider_credential
from pio_lab.providers.errors import ProviderConfigurationError, ProviderError
from pio_lab.utils.config_loader import CONFIG_ROOT


class CodexProvider(OpenAIChatProvider):
    """OpenAI adapter used by the Codex routing target."""

    name = "codex"

    async def complete(
        self,
        account: ProviderAccount,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Complete via OpenAI API key or local Codex OAuth CLI."""
        if account.metadata.get("credential_mode") == "codex_oauth":
            return await self._complete_with_codex_cli(
                account,
                model,
                messages,
                tools=tools,
                system=system,
                **kwargs,
            )
        return await super().complete(
            account,
            model,
            messages,
            tools=tools,
            system=system,
            **kwargs,
        )

    async def _complete_with_codex_cli(
        self,
        account: ProviderAccount,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        resolve_provider_credential(
            provider=self.name,
            account_id=account.account_id,
            env_key=account.env_key,
            metadata=account.metadata,
        )
        prompt = _codex_prompt(messages, system, tools)
        timeout = float(kwargs.get("timeout", 180.0))
        text = await self._run_codex_cli(prompt, timeout=timeout)
        return {
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "model": model,
            "provider": self.name,
            "raw": {"transport": "codex_cli"},
        }

    async def _run_codex_cli(self, prompt: str, *, timeout: float) -> str:
        command = os.environ.get("CODEX_COMMAND", "codex")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".txt") as file:
            output_path = Path(file.name)

        args = [
            command,
            "exec",
            "--sandbox",
            "read-only",
            "--cd",
            str(CONFIG_ROOT.parent),
            "--skip-git-repo-check",
            "--ephemeral",
            "--output-last-message",
            str(output_path),
            prompt,
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            if process.returncode != 0:
                detail = (stderr or stdout).decode("utf-8", errors="replace").strip()
                raise ProviderError(
                    f"Codex CLI failed: {detail[:500]}",
                    provider=self.name,
                )
            text = output_path.read_text(encoding="utf-8").strip()
            if text:
                return text
            return stdout.decode("utf-8", errors="replace").strip()
        except TimeoutError as error:
            raise ProviderError("Codex CLI timed out", provider=self.name) from error
        except OSError as error:
            raise ProviderConfigurationError(
                f"Codex CLI is not available: {error}",
                provider=self.name,
            ) from error
        finally:
            output_path.unlink(missing_ok=True)


def _codex_prompt(
    messages: list[dict[str, Any]],
    system: str | None,
    tools: list[dict[str, Any]] | None,
) -> str:
    parts = [
        "You are the Codex provider adapter inside Pio_lab.",
        "Return only the assistant response for the user. Do not modify files.",
    ]
    if system:
        parts.extend(["", "System instructions:", system])
    if tools:
        parts.extend(
            [
                "",
                "Tool schemas were requested by the caller, but this OAuth transport exposes no "
                "structured tool loop yet. Answer with the best text response.",
            ]
        )
    parts.append("")
    parts.append("Conversation:")
    for message in messages:
        role = str(message.get("role", "user"))
        content = message.get("content", "")
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


__all__ = ["CodexProvider"]
