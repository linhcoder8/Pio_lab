"""Small shared helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


def gen_request_id(prefix: str = "req") -> str:
    """Generate a compact request id with a readable prefix."""
    return f"{prefix}_{uuid4().hex}"


__all__ = ["gen_request_id", "utc_now"]
