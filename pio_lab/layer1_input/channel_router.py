"""Shared inbound channel routing helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pio_lab.layer3_chief_of_staff.chief_of_staff import ChiefOfStaff, get_chief_of_staff
from pio_lab.security.enforcer import SecurityEnforcer, SecurityError, enforcer
from pio_lab.utils.helpers import gen_request_id, utc_now
from pio_lab.utils.logging import logger


@dataclass(frozen=True, slots=True)
class ChannelReply:
    """Normalized outbound reply for any channel."""

    message_id: str
    channel: str
    user_id: str
    text: str
    chunks: list[str]
    created_at: str
    raw_result: dict[str, Any] = field(default_factory=dict)


class ChannelRouter:
    """Route text from external channels through Chief of Staff."""

    def __init__(
        self,
        *,
        chief_of_staff: ChiefOfStaff | None = None,
        security: SecurityEnforcer | None = None,
    ) -> None:
        self.chief_of_staff = chief_of_staff or get_chief_of_staff()
        self.security = security or enforcer

    async def handle_text(
        self,
        *,
        channel: str,
        user_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> ChannelReply:
        """Run a channel text message through the full Pio_lab flow."""
        try:
            self.security.require_crypto_safe_text(text)
        except SecurityError as error:
            reply_text = f"Blocked by security policy: {error}"
            raw_result: dict[str, Any] = {"status": "blocked", "error": str(error)}
        else:
            try:
                raw_result = await self.chief_of_staff.run(
                    {
                        "input": text,
                        "channel": channel,
                        "user_id": user_id,
                        "metadata": metadata or {},
                    }
                )
                reply_text = self._format_result(raw_result)
            except Exception as error:
                logger.exception(
                    "Channel routing failed for {channel}/{user_id}: {error}",
                    channel=channel,
                    user_id=user_id,
                    error=error,
                )
                raw_result = {
                    "status": "error",
                    "error_type": error.__class__.__name__,
                }
                reply_text = (
                    "Pio_lab gặp lỗi khi xử lý yêu cầu. Lỗi đã được ghi ở terminal/log; "
                    "hãy thử lại sau ít phút."
                )

        reply_text = self.security.mask_secrets_in_output(reply_text)
        return ChannelReply(
            message_id=gen_request_id(f"{channel}msg"),
            channel=channel,
            user_id=user_id,
            text=reply_text,
            chunks=chunk_text(reply_text, channel=channel),
            created_at=utc_now().isoformat(),
            raw_result=raw_result,
        )

    def _format_result(self, result: dict[str, Any]) -> str:
        if result.get("status") == "waiting_approval":
            approval = result.get("approval") or {}
            return str(approval.get("prompt") or "Yêu cầu cần phê duyệt của Sếp Linh.")
        final_output = result.get("final_output") or {}
        if isinstance(final_output, dict) and final_output.get("text"):
            return str(final_output["text"])
        return str(result.get("reply") or result.get("status") or "Pio_lab handled the request.")


def chunk_text(text: str, *, channel: str, limit: int | None = None) -> list[str]:
    """Chunk long messages for channel limits, especially Telegram."""
    selected_limit = limit or (4000 if channel == "telegram" else 1900 if channel == "discord" else 4096)
    if len(text) <= selected_limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > selected_limit:
        split_at = remaining.rfind("\n\n", 0, selected_limit)
        if split_at < selected_limit // 2:
            split_at = remaining.rfind("\n", 0, selected_limit)
        if split_at < selected_limit // 2:
            split_at = selected_limit
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


__all__ = ["ChannelReply", "ChannelRouter", "chunk_text"]
