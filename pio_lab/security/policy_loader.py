"""Load and normalize Phase 1 security policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pio_lab.utils.config_loader import load_security_policy

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class SecurityPolicy:
    """Normalized security policy values used by the enforcer."""

    project_root: Path
    raw: dict[str, Any]
    allowed_paths: tuple[Path, ...]
    forbidden_paths: tuple[str, ...]
    forbidden_extensions: tuple[str, ...]
    api_key_patterns: tuple[str, ...]
    crypto_keywords: tuple[str, ...]
    approval_actions: tuple[str, ...]


def load_policy(project_root: Path | None = None) -> SecurityPolicy:
    """Load security policy from config/security_policy.yaml."""
    root = (project_root or PROJECT_ROOT).resolve()
    raw = load_security_policy()
    file_system = raw.get("file_system", {})
    api_keys = raw.get("api_keys", {})
    crypto_wallet = raw.get("crypto_wallet", {})

    allowed_paths = tuple(
        _resolve_policy_path(path, root)
        for path in file_system.get("allowed_paths", [])
    )
    forbidden_extensions = tuple(
        extension.lower()
        for extension in file_system.get("forbidden_extensions", [])
    )

    return SecurityPolicy(
        project_root=root,
        raw=raw,
        allowed_paths=allowed_paths,
        forbidden_paths=tuple(file_system.get("forbidden_paths", [])),
        forbidden_extensions=forbidden_extensions,
        api_key_patterns=tuple(api_keys.get("detect_patterns", [])),
        crypto_keywords=tuple(crypto_wallet.get("forbidden_keywords", [])),
        approval_actions=tuple(raw.get("require_human_approval", [])),
    )


def _resolve_policy_path(path: str, project_root: Path) -> Path:
    replaced = path.replace("{PROJECT_ROOT}", str(project_root))
    return Path(replaced).expanduser().resolve()


__all__ = ["PROJECT_ROOT", "SecurityPolicy", "load_policy"]
