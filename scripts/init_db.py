"""
Init PostgreSQL schema.

Usage:
    python scripts/init_db.py
"""
import asyncio
import os

# TODO Phase 1: import models + create tables via SQLAlchemy / Alembic


async def main() -> None:
    print("Initializing database...")
    # TODO: connect to POSTGRES_* from .env, run migrations
    print("✓ Database ready")


if __name__ == "__main__":
    asyncio.run(main())
