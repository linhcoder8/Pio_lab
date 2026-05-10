"""Smoke test Telegram bot credentials without printing secrets."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


async def main() -> int:
    """Run Telegram getMe and optionally send a test message."""
    from pio_lab.layer1_input.channel_router import ChannelReply
    from pio_lab.layer1_input.telegram_adapter import TelegramAdapter
    from pio_lab.utils.env import get_settings

    parser = argparse.ArgumentParser(description="Smoke test Telegram bot setup.")
    parser.add_argument(
        "--send-test",
        action="store_true",
        help="Send a test message to TELEGRAM_TEST_CHAT_ID or the provided --chat-id.",
    )
    parser.add_argument("--chat-id", help="Telegram chat id for --send-test.")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN configured: no")
        return 1

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
        )
        data: dict[str, Any] = response.json()

    if not data.get("ok"):
        print("Telegram getMe: failed")
        print(f"Description: {data.get('description', 'unknown error')}")
        return 1

    bot = data["result"]
    allowed_users = [
        item.strip()
        for item in (settings.telegram_allowed_users or "").split(",")
        if item.strip()
    ]
    print("Telegram getMe: ok")
    print(f"Bot username: @{bot.get('username')}")
    print(f"Bot id: {bot.get('id')}")
    print(f"Allowed users configured: {len(allowed_users)}")

    if not args.send_test:
        print("Send test: skipped")
        return 0

    chat_id = args.chat_id or settings.telegram_test_chat_id
    if not chat_id:
        print("Send test: skipped, TELEGRAM_TEST_CHAT_ID or --chat-id is required")
        return 1

    adapter = TelegramAdapter(settings=settings)
    await adapter.send_reply(
        chat_id=chat_id,
        reply=ChannelReply(
            message_id="telegram_smoke",
            channel="telegram",
            user_id=str(chat_id),
            text="Pio_lab Telegram smoke test: ok",
            chunks=["Pio_lab Telegram smoke test: ok"],
            created_at="",
            raw_result={"status": "smoke"},
        ),
    )
    print("Send test: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
