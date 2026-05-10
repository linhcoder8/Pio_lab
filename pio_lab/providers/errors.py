"""Provider router errors."""

from __future__ import annotations


class ProviderError(Exception):
    """Base error for provider calls."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        account_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.account_id = account_id


class ProviderConfigurationError(ProviderError):
    """Provider is misconfigured or missing required runtime state."""


class ProviderAuthenticationError(ProviderError):
    """Provider rejected credentials."""


class QuotaExceededError(ProviderError):
    """Provider account hit quota or rate limits."""


class ProviderUnavailableError(ProviderError):
    """All eligible providers in a routing chain failed."""

    def __init__(self, routing_key: str, errors: list[str]) -> None:
        joined_errors = "; ".join(errors) if errors else "no eligible provider"
        super().__init__(
            f"All providers failed for routing key '{routing_key}': {joined_errors}"
        )
        self.routing_key = routing_key
        self.errors = errors


__all__ = [
    "ProviderAuthenticationError",
    "ProviderConfigurationError",
    "ProviderError",
    "ProviderUnavailableError",
    "QuotaExceededError",
]
