"""Provider account pool and rotation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from pio_lab.providers.credentials import has_provider_credentials
from pio_lab.utils.helpers import utc_now


@dataclass(slots=True)
class ProviderAccount:
    """Runtime account config for one provider account."""

    provider: str
    account_id: str
    models: list[str]
    priority: int = 100
    env_key: str | None = None
    status: str = "available"
    last_used: datetime | None = None
    quota_exhausted_until: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Compatibility alias used by provider adapters."""
        return self.account_id

    def supports_model(self, model: str) -> bool:
        """Return whether this account can call a model."""
        return model in self.models

    def has_credentials(self) -> bool:
        """Return whether the account has required credentials available."""
        if (
            self.env_key is None
            and not self.metadata.get("credential_mode")
            and not self.metadata.get("credential_modes")
        ):
            return True
        return has_provider_credentials(
            provider=self.provider,
            account_id=self.account_id,
            env_key=self.env_key,
            metadata=self.metadata,
        )

    def is_available(self, model: str, now: datetime | None = None) -> bool:
        """Return whether the account can be selected for a call."""
        current_time = now or utc_now()
        if self.status != "available":
            return False
        if not self.supports_model(model):
            return False
        if not self.has_credentials():
            return False
        return self.quota_exhausted_until is None or self.quota_exhausted_until <= current_time


class AccountPool:
    """In-memory provider account pool."""

    def __init__(self) -> None:
        self._accounts: dict[str, list[ProviderAccount]] = {}

    def register_provider(self, provider: str, provider_config: dict[str, Any]) -> None:
        """Register all accounts for one provider from config."""
        for raw_account in provider_config.get("accounts", []):
            account = ProviderAccount(
                provider=provider,
                account_id=raw_account["id"],
                env_key=raw_account.get("env_key"),
                models=list(raw_account.get("models", [])),
                priority=int(raw_account.get("priority", 100)),
                metadata={
                    key: value
                    for key, value in raw_account.items()
                    if key not in {"id", "env_key", "models", "priority"}
                },
            )
            self.register(account)

    def register(self, account: ProviderAccount) -> None:
        """Register one account."""
        accounts = self._accounts.setdefault(account.provider, [])
        accounts[:] = [item for item in accounts if item.account_id != account.account_id]
        accounts.append(account)
        accounts.sort(key=lambda item: item.priority)

    def accounts_for(self, provider: str) -> list[ProviderAccount]:
        """Return accounts for a provider."""
        return list(self._accounts.get(provider, []))

    def next_available(self, provider: str, model: str) -> ProviderAccount | None:
        """Return the highest-priority available account for a provider/model."""
        eligible = [
            account
            for account in self._accounts.get(provider, [])
            if account.is_available(model)
        ]
        if not eligible:
            return None
        return sorted(
            eligible,
            key=lambda account: (
                account.priority,
                account.last_used is not None,
                account.last_used or datetime.min.replace(tzinfo=utc_now().tzinfo),
            ),
        )[0]

    def mark_used(self, account: ProviderAccount) -> None:
        """Update last-used timestamp after a successful call."""
        account.last_used = utc_now()

    def mark_quota_exhausted(self, account: ProviderAccount, cooldown_minutes: int) -> None:
        """Temporarily remove an account from rotation."""
        account.quota_exhausted_until = utc_now() + timedelta(minutes=cooldown_minutes)


__all__ = ["AccountPool", "ProviderAccount"]
