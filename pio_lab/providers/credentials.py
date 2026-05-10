"""Credential resolution for provider accounts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pio_lab.providers.errors import ProviderConfigurationError


def has_provider_credentials(
    *,
    provider: str,
    account_id: str,
    env_key: str | None,
    metadata: dict[str, Any],
) -> bool:
    """Return whether a provider account has a usable local credential."""
    try:
        resolve_provider_credential(
            provider=provider,
            account_id=account_id,
            env_key=env_key,
            metadata=metadata,
        )
    except ProviderConfigurationError:
        return False
    return True


def resolve_provider_credential(
    *,
    provider: str,
    account_id: str,
    env_key: str | None,
    metadata: dict[str, Any],
) -> str:
    """Resolve API-key or Codex OAuth credentials for one provider account."""
    errors: list[str] = []
    for mode in _credential_modes(env_key, metadata):
        if mode == "env":
            credential = _credential_from_env(env_key)
            if credential:
                return credential
            errors.append(f"missing environment variable {env_key}")
            continue

        if mode == "codex_oauth":
            credential = _credential_from_codex_auth()
            if credential:
                return credential
            errors.append("missing Codex OAuth access token")
            continue

        errors.append(f"unsupported credential mode {mode}")

    details = "; ".join(errors) if errors else "no credential mode configured"
    raise ProviderConfigurationError(
        f"Missing credentials for {provider}/{account_id}: {details}",
        provider=provider,
        account_id=account_id,
    )


def _credential_modes(env_key: str | None, metadata: dict[str, Any]) -> list[str]:
    raw_modes = metadata.get("credential_modes")
    if raw_modes is None:
        raw_mode = metadata.get("credential_mode")
        if raw_mode == "auto":
            return ["env", "codex_oauth"] if env_key else ["codex_oauth"]
        if raw_mode:
            return [str(raw_mode)]
        return ["env"] if env_key else ["none"]

    if isinstance(raw_modes, str):
        return [raw_modes]
    return [str(mode) for mode in raw_modes]


def _credential_from_env(env_key: str | None) -> str | None:
    if not env_key:
        return None
    return os.environ.get(env_key) or None


def _credential_from_codex_auth() -> str | None:
    auth_path = _codex_auth_path()
    try:
        raw = json.loads(auth_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if raw.get("auth_mode") not in {"chatgpt", "oauth"}:
        return None
    tokens = raw.get("tokens")
    if not isinstance(tokens, dict):
        return None
    token = tokens.get("access_token")
    return token if isinstance(token, str) and token else None


def _codex_auth_path() -> Path:
    explicit = os.environ.get("CODEX_AUTH_FILE")
    if explicit:
        return Path(explicit).expanduser()

    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "auth.json"

    return Path.home() / ".codex" / "auth.json"


__all__ = ["has_provider_credentials", "resolve_provider_credential"]
