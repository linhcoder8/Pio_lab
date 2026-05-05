"""Initialize the PostgreSQL schema.

Usage:
    python scripts/init_db.py
"""

from __future__ import annotations

import asyncio

from pio_lab.memory.postgres.database import create_all, dispose_engine, init_engine
from pio_lab.utils.env import get_settings
from pio_lab.utils.logging import logger, setup_logging


async def main() -> None:
    """Create all Postgres tables from SQLAlchemy metadata."""
    settings = get_settings()
    setup_logging(settings.log_level, json=False)

    logger.info(
        "Initializing database schema at {host}:{port}",
        host=settings.postgres_host,
        port=settings.postgres_port,
    )
    try:
        init_engine(settings.postgres_dsn)
        await create_all()
    finally:
        await dispose_engine()
    logger.info("Database schema ready")


if __name__ == "__main__":
    asyncio.run(main())
