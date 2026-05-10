"""Run the Telegram bot in polling mode for local live smoke."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    """Start Telegram polling."""
    from pio_lab.layer1_input.telegram_adapter import TelegramAdapter
    from pio_lab.utils.logging import setup_logging

    setup_logging("INFO", json=False)
    application = TelegramAdapter().build_application()
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
