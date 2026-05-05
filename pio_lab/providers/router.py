"""Provider router for all LLM calls."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from pio_lab.memory.postgres.traces import TraceLogger
from pio_lab.providers.account_pool import AccountPool, ProviderAccount
from pio_lab.providers.adapters.base_provider import BaseProvider, NormalizedResponse
from pio_lab.providers.adapters.claude_adapter import ClaudeProvider
from pio_lab.providers.errors import ProviderError, ProviderUnavailableError, QuotaExceededError
from pio_lab.providers.status_tracker import StatusTracker
from pio_lab.providers.token_tracker import TokenTracker
from pio_lab.utils.config_loader import load_providers_config
from pio_lab.utils.logging import logger


@dataclass(frozen=True, slots=True)
class RoutingTarget:
    """One provider/model pair in a routing chain."""

    provider: str
    model: str


class ProviderRouter:
    """Resolve routing keys, call provider adapters, and log traces."""

    def __init__(
        self,
        *,
        config: dict[str, Any] | None = None,
        account_pool: AccountPool | None = None,
        status_tracker: StatusTracker | None = None,
        token_tracker: TokenTracker | None = None,
        trace_logger: TraceLogger | None = None,
        trace_session: AsyncSession | None = None,
        adapters: dict[str, BaseProvider] | None = None,
    ) -> None:
        self.config = config
        self.account_pool = account_pool or AccountPool()
        self.status_tracker = status_tracker or StatusTracker()
        self.token_tracker = token_tracker or TokenTracker()
        self.trace_logger = trace_logger or TraceLogger()
        self.trace_session = trace_session
        self.adapters = adapters or {}
        self.loaded = False

    def load(self) -> None:
        """Load provider config, account pool, and M3 adapters."""
        if self.config is None:
            self.config = load_providers_config()

        for provider, provider_config in self.config.get("providers", {}).items():
            self.account_pool.register_provider(provider, provider_config)

        self._init_adapters()
        self.loaded = True

    async def call(
        self,
        routing_key: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        **kwargs: Any,
    ) -> NormalizedResponse:
        """Call the first available provider in the routing chain."""
        if not self.loaded:
            self.load()

        errors: list[str] = []
        for target in self._resolve_chain(routing_key):
            adapter = self.adapters.get(target.provider)
            if adapter is None:
                self.status_tracker.set(
                    routing_key,
                    target.provider,
                    target.model,
                    "skipped",
                    error="provider adapter is not implemented in M3",
                )
                errors.append(f"{target.provider}/{target.model}: adapter not implemented")
                continue

            account = self.account_pool.next_available(target.provider, target.model)
            if account is None:
                self.status_tracker.set(
                    routing_key,
                    target.provider,
                    target.model,
                    "waiting",
                    error="no available account",
                )
                errors.append(f"{target.provider}/{target.model}: no available account")
                continue

            try:
                return await self._call_target(
                    target=target,
                    account=account,
                    routing_key=routing_key,
                    messages=messages,
                    tools=tools,
                    system=system,
                    task_id=task_id,
                    agent_id=agent_id or routing_key,
                    kwargs=kwargs,
                )
            except QuotaExceededError as error:
                cooldown = self._cooldown_minutes()
                self.account_pool.mark_quota_exhausted(account, cooldown)
                self.status_tracker.set(
                    routing_key,
                    target.provider,
                    target.model,
                    "failed",
                    error=str(error),
                )
                errors.append(f"{target.provider}/{target.model}: {error}")
            except ProviderError as error:
                self.status_tracker.set(
                    routing_key,
                    target.provider,
                    target.model,
                    "failed",
                    error=str(error),
                )
                errors.append(f"{target.provider}/{target.model}: {error}")
            except Exception as error:
                self.status_tracker.set(
                    routing_key,
                    target.provider,
                    target.model,
                    "failed",
                    error=str(error),
                )
                errors.append(f"{target.provider}/{target.model}: unexpected error: {error}")

        raise ProviderUnavailableError(routing_key, errors)

    def _resolve_chain(self, routing_key: str) -> list[RoutingTarget]:
        if self.config is None:
            self.load()
        assert self.config is not None

        raw_chain = self.config.get("routing_rules", {}).get(
            routing_key,
            self.config.get("default_chain", []),
        )
        return [
            RoutingTarget(provider=item["provider"], model=item["model"])
            for item in raw_chain
        ]

    def _init_adapters(self) -> None:
        """Initialize only the Claude adapter for M3."""
        self.adapters.setdefault("claude", ClaudeProvider())

    async def _call_target(
        self,
        *,
        target: RoutingTarget,
        account: ProviderAccount,
        routing_key: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        system: str | None,
        task_id: str | None,
        agent_id: str,
        kwargs: dict[str, Any],
    ) -> NormalizedResponse:
        adapter = self.adapters[target.provider]
        self.status_tracker.set(routing_key, target.provider, target.model, "running")
        started_at = time.perf_counter()

        response = await adapter.complete(
            account,
            target.model,
            messages,
            tools=tools,
            system=system,
            **kwargs,
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        response["provider"] = target.provider
        response["model"] = target.model
        usage = response.get("usage", {})
        tokens_in = int(usage.get("input_tokens", 0) or 0)
        tokens_out = int(usage.get("output_tokens", 0) or 0)
        self.token_tracker.record(
            provider=target.provider,
            routing_key=routing_key,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
        )
        self.account_pool.mark_used(account)
        self.status_tracker.set(routing_key, target.provider, target.model, "end")

        await self._log_trace(
            task_id=task_id,
            agent_id=agent_id,
            routing_key=routing_key,
            target=target,
            messages_in=messages,
            messages_out=_trace_safe_response(response),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            account=account,
        )
        return response

    async def _log_trace(
        self,
        *,
        task_id: str | None,
        agent_id: str,
        routing_key: str,
        target: RoutingTarget,
        messages_in: list[dict[str, Any]],
        messages_out: dict[str, Any],
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        account: ProviderAccount,
    ) -> None:
        try:
            await self.trace_logger.log(
                task_id=task_id,
                agent_id=agent_id,
                routing_key=routing_key,
                provider=target.provider,
                model=target.model,
                messages_in=messages_in,
                messages_out=messages_out,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=latency_ms,
                metadata={"account_id": account.account_id},
                session=self.trace_session,
            )
        except Exception as error:
            logger.warning("Provider trace logging failed: {error}", error=error)

    def _cooldown_minutes(self) -> int:
        if self.config is None:
            return 60
        return int(
            self.config.get("quota_management", {}).get("cooldown_minutes_after_quota_hit", 60)
        )


def _trace_safe_response(response: NormalizedResponse) -> dict[str, Any]:
    return {
        key: value
        for key, value in response.items()
        if key != "raw"
    }


_router: ProviderRouter | None = None


def get_router() -> ProviderRouter:
    """Return the process-wide provider router singleton."""
    global _router

    if _router is None:
        _router = ProviderRouter()
    return _router


def reset_router() -> None:
    """Reset singleton router, mainly for tests."""
    global _router

    _router = None


__all__ = ["ProviderRouter", "RoutingTarget", "get_router", "reset_router"]
