"""Logging setup."""

from __future__ import annotations

import sys
from typing import Any

from loguru import logger


def setup_logging(level: str = "INFO", json: bool = False) -> Any:
    """Configure loguru for console logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=level.upper(),
        serialize=json,
        backtrace=False,
        diagnose=False,
    )
    return logger


__all__ = ["logger", "setup_logging"]
