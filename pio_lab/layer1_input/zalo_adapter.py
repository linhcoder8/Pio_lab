"""Zalo OA channel adapter."""

from __future__ import annotations

from typing import Any

import httpx

from pio_lab.layer1_input.channel_router import ChannelReply, ChannelRouter
from pio_lab.utils.env import Settings, get_settings
from pio_lab.utils.helpers import utc_now

ZALO_SEND_MESSAGE_URL = "https://openapi.zalo.me/v3.0/oa/message/cs"


class ZaloAdapter:
    """Handle Zalo webhook messages and outbound OA replies."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        channel_router: ChannelRouter | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.channel_router = channel_router or ChannelRouter()
        self.http_client = http_client

    async def handle_webhook(self, payload: dict[str, Any]) -> ChannelReply:
        """Process a Zalo webhook event payload."""
        user_id = _extract_user_id(payload)
        text = _extract_text(payload)
        if not user_id or not text:
            return ChannelReply(
                message_id="zalo_ignored",
                channel="zalo",
                user_id=user_id or "",
                text="",
                chunks=[],
                created_at=utc_now().isoformat(),
                raw_result={"status": "ignored"},
            )
        return await self.channel_router.handle_text(
            channel="zalo",
            user_id=user_id,
            text=text,
            metadata={"event_name": payload.get("event_name")},
        )

    async def send_reply(self, *, user_id: str, reply: ChannelReply) -> list[dict[str, Any]]:
        """Send reply chunks to Zalo OA."""
        if not self.settings.zalo_access_token:
            raise RuntimeError("ZALO_ACCESS_TOKEN is not configured")

        responses: list[dict[str, Any]] = []
        client = self.http_client
        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=30)
            close_client = True
        try:
            for chunk in reply.chunks:
                response = await client.post(
                    ZALO_SEND_MESSAGE_URL,
                    headers={"access_token": self.settings.zalo_access_token},
                    json={
                        "recipient": {"user_id": user_id},
                        "message": {"text": chunk},
                    },
                )
                response.raise_for_status()
                responses.append(response.json())
        finally:
            if close_client:
                await client.aclose()
        return responses


def _extract_user_id(payload: dict[str, Any]) -> str:
    sender = payload.get("sender") or {}
    if isinstance(sender, dict) and sender.get("id"):
        return str(sender["id"])
    user_id = payload.get("user_id")
    return str(user_id or "")


def _extract_text(payload: dict[str, Any]) -> str:
    message = payload.get("message") or {}
    if isinstance(message, dict) and message.get("text"):
        return str(message["text"])
    return str(payload.get("text") or "")


__all__ = ["ZALO_SEND_MESSAGE_URL", "ZaloAdapter"]
