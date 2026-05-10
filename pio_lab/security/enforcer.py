"""Runtime security policy checks."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from pio_lab.security.policy_loader import SecurityPolicy, load_policy


class SecurityError(Exception):
    """Raised when security policy blocks an operation."""


class SecurityEnforcer:
    """Apply Phase 1 hardcoded security policy."""

    def __init__(self, policy: SecurityPolicy | None = None) -> None:
        self.policy = policy or load_policy()
        self._secret_patterns = [re.compile(pattern) for pattern in self.policy.api_key_patterns]

    def check_file_access(self, path: str | Path) -> bool:
        """Return whether a filesystem path is allowed by policy."""
        candidate = Path(path).expanduser()
        try:
            resolved = candidate.resolve(strict=False)
        except OSError:
            return False

        if resolved.suffix.lower() in self.policy.forbidden_extensions:
            return False
        if self._matches_forbidden_path(resolved):
            return False
        return any(_is_relative_to(resolved, allowed) for allowed in self.policy.allowed_paths)

    def require_file_access(self, path: str | Path) -> Path:
        """Return resolved path or raise when file access is denied."""
        candidate = Path(path).expanduser().resolve(strict=False)
        if not self.check_file_access(candidate):
            raise SecurityError(f"File access denied: {candidate}")
        return candidate

    def mask_secrets_in_output(self, text: str) -> str:
        """Mask configured API key patterns in output text."""
        masked = text
        for pattern in self._secret_patterns:
            masked = pattern.sub(_mask_match, masked)
        return masked

    def requires_approval(self, action_name: str) -> bool:
        """Return whether an action requires human approval."""
        normalized_action = action_name.strip().lower()
        return normalized_action in {
            action.lower()
            for action in self.policy.approval_actions
        }

    def check_crypto_keywords(self, text: str) -> bool:
        """Return False when text contains blocked crypto-wallet content."""
        lowered = text.lower()
        return not any(keyword.lower() in lowered for keyword in self.policy.crypto_keywords)

    def require_crypto_safe_text(self, text: str) -> str:
        """Return text or raise when it contains blocked crypto-wallet content."""
        if not self.check_crypto_keywords(text):
            raise SecurityError("Input contains forbidden crypto-wallet content")
        return text

    def _matches_forbidden_path(self, path: Path) -> bool:
        normalized = path.as_posix()
        lower_normalized = normalized.lower()
        for pattern in self.policy.forbidden_paths:
            resolved_pattern = pattern.replace("{PROJECT_ROOT}", str(self.policy.project_root))
            expanded_pattern = Path(resolved_pattern).expanduser().as_posix().lower()
            if fnmatch.fnmatch(lower_normalized, expanded_pattern):
                return True
        return False


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _mask_match(match: re.Match[str]) -> str:
    secret = match.group(0)
    if len(secret) <= 8:
        return "***"
    return f"{secret[:3]}...{secret[-4:]}"


enforcer = SecurityEnforcer()


__all__ = ["SecurityEnforcer", "SecurityError", "enforcer"]
