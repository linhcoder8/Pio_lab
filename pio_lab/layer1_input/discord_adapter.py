"""Discord channel adapter."""

from __future__ import annotations

from typing import Any

from pio_lab.layer1_input.channel_router import ChannelReply, ChannelRouter
from pio_lab.utils.env import Settings, get_settings
from pio_lab.utils.helpers import utc_now


class DiscordAdapter:
    """Handle Discord DM/slash-style messages through Pio_lab."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        channel_router: ChannelRouter | None = None,
        allowed_user_ids: set[str] | None = None,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.channel_router = channel_router or ChannelRouter()
        self.allowed_user_ids = allowed_user_ids or set()
        self.client = client

    def is_allowed_user(self, user_id: int | str | None) -> bool:
        """Return whether a Discord user can use the adapter."""
        if not self.allowed_user_ids:
            return True
        return str(user_id or "") in self.allowed_user_ids

    async def handle_message(
        self,
        *,
        user_id: int | str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> ChannelReply:
        """Process one Discord message or slash command prompt."""
        if not self.is_allowed_user(user_id):
            return ChannelReply(
                message_id="discord_forbidden",
                channel="discord",
                user_id=str(user_id),
                text="Discord user is not allowed.",
                chunks=["Discord user is not allowed."],
                created_at=utc_now().isoformat(),
                raw_result={"status": "forbidden"},
            )
        if text.strip().lower() in {"/status", "status"}:
            return ChannelReply(
                message_id="discord_status",
                channel="discord",
                user_id=str(user_id),
                text="Pio_lab online.",
                chunks=["Pio_lab online."],
                created_at=utc_now().isoformat(),
                raw_result={"status": "command"},
            )
        return await self.channel_router.handle_text(
            channel="discord",
            user_id=str(user_id),
            text=text,
            metadata=metadata or {},
        )

    async def send_reply(self, target: Any, reply: ChannelReply) -> None:
        """Send reply chunks to a Discord target supporting `.send`."""
        for chunk in reply.chunks:
            await target.send(chunk)

    def build_client(self) -> Any:
        """Build a discord.py client when the dependency is available."""
        if not self.settings.discord_bot_token:
            raise RuntimeError("DISCORD_BOT_TOKEN is not configured")

        import discord

        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_message(message: Any) -> None:
            if message.author.bot:
                return
            reply = await self.handle_message(
                user_id=message.author.id,
                text=message.content,
                metadata={"channel_id": message.channel.id},
            )
            await self.send_reply(message.channel, reply)

        self.client = client
        return client


__all__ = ["DiscordAdapter"]
