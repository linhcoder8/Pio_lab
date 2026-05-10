"""OpenAI/Codex provider adapter."""

from __future__ import annotations

import asyncio
import os
import shutil
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
        command = _resolve_codex_command()
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


def _resolve_codex_command() -> str:
    """Resolve the Codex CLI command, including Windows npm wrappers."""
    configured = os.environ.get("CODEX_COMMAND")
    if configured:
        resolved = shutil.which(configured)
        return resolved or configured

    for candidate in ("codex", "codex.cmd", "codex.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return "codex"


def _codex_prompt(
    messages: list[dict[str, Any]],
    system: str | None,
    tools: list[dict[str, Any]] | None,
) -> str:
    latest_user = _latest_user_content(messages)
    parts = [
        f"Answer this directly for a Telegram user: {latest_user}",
        "Keep implementation details, runtime details, credentials, local paths, and tooling hidden.",
        "Do not describe where or how you are running. Do not modify files.",
    ]
    if system:
        parts.extend(["", "Specialist role:", system])
    if tools:
        parts.extend(
            [
                "",
                "Some requested capabilities may be unavailable in this response path. Answer from "
                "available knowledge and be transparent about source limitations when needed.",
            ]
        )
    parts.append("")
    if len(messages) > 1:
        parts.append("Conversation context:")
        for message in messages[:-1]:
            role = str(message.get("role", "user"))
            content = message.get("content", "")
            parts.append(f"{role}: {content}")
        parts.append("")
    parts.extend(["Full user request:", latest_user])
    parts.extend(
        [
            "",
            "Write the response now. Start with the answer.",
        ]
    )
    return "\n".join(parts)


def _latest_user_content(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role", "user") == "user":
            return str(message.get("content", ""))
    if not messages:
        return ""
    return str(messages[-1].get("content", ""))


__all__ = ["CodexProvider"]
