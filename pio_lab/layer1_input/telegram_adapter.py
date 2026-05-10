"""Telegram channel adapter."""

from __future__ import annotations

from typing import Any

from pio_lab.layer1_input.channel_router import ChannelReply, ChannelRouter
from pio_lab.utils.env import Settings, get_settings


class TelegramAdapter:
    """Handle Telegram messages and route them through Pio_lab."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        channel_router: ChannelRouter | None = None,
        bot: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.channel_router = channel_router or ChannelRouter()
        self.bot = bot
        self.allowed_user_ids = _parse_allowed_users(self.settings.telegram_allowed_users)

    def is_allowed_user(self, user_id: int | str | None) -> bool:
        """Return whether a Telegram user can use the bot."""
        if not self.allowed_user_ids:
            return True
        return str(user_id or "") in self.allowed_user_ids

    async def handle_text(
        self,
        *,
        user_id: int | str,
        text: str,
        chat_id: int | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChannelReply:
        """Process one Telegram text message."""
        if not self.is_allowed_user(user_id):
            return ChannelReply(
                message_id="telegram_forbidden",
                channel="telegram",
                user_id=str(user_id),
                text="Telegram user is not allowed.",
                chunks=["Telegram user is not allowed."],
                created_at="",
                raw_result={"status": "forbidden"},
            )

        normalized_text = _command_response(text) or text
        if normalized_text != text:
            return ChannelReply(
                message_id="telegram_command",
                channel="telegram",
                user_id=str(user_id),
                text=normalized_text,
                chunks=[normalized_text],
                created_at="",
                raw_result={"status": "command"},
            )

        reply = await self.channel_router.handle_text(
            channel="telegram",
            user_id=str(user_id),
            text=text,
            metadata={"chat_id": chat_id, **(metadata or {})},
        )
        if self.bot is not None and chat_id is not None:
            await self.send_reply(chat_id=chat_id, reply=reply)
        return reply

    async def send_reply(self, *, chat_id: int | str, reply: ChannelReply) -> None:
        """Send all Telegram chunks through an injected bot."""
        if self.bot is None:
            return
        for chunk in reply.chunks:
            await self.bot.send_message(chat_id=chat_id, text=chunk)

    def build_application(self) -> Any:
        """Build a python-telegram-bot application when the dependency is available."""
        if not self.settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

        from telegram.ext import Application, CommandHandler, MessageHandler, filters

        application = Application.builder().token(self.settings.telegram_bot_token).build()
        application.add_handler(CommandHandler("start", self._telegram_update_handler))
        application.add_handler(CommandHandler("help", self._telegram_update_handler))
        application.add_handler(CommandHandler("status", self._telegram_update_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._telegram_update_handler))
        return application

    async def _telegram_update_handler(self, update: Any, context: Any) -> None:
        message = update.effective_message
        user = update.effective_user
        if message is None or user is None:
            return
        reply = await self.handle_text(
            user_id=user.id,
            chat_id=message.chat_id,
            text=message.text or "",
            metadata={"telegram_update_id": update.update_id},
        )
        for chunk in reply.chunks:
            await message.reply_text(chunk)


def _parse_allowed_users(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def _command_response(text: str) -> str | None:
    command = text.strip().split(maxsplit=1)[0].lower()
    if command == "/start":
        return "Pio_lab Telegram đã sẵn sàng."
    if command == "/help":
        return "Gửi yêu cầu cho Pio_lab; hệ thống sẽ điều phối qua Chief of Staff."
    if command == "/status":
        return "Pio_lab online."
    return None


__all__ = ["TelegramAdapter"]
