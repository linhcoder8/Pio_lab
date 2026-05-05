"""OpenClaw runtime bootstrap for M6."""

from __future__ import annotations

from fastapi import FastAPI

from pio_lab.layer1_input.web_adapter import WebAdapter
from pio_lab.utils.env import Settings, get_settings
from pio_lab.utils.logging import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI app with the Web channel adapter mounted."""
    resolved_settings = settings or get_settings()
    setup_logging(resolved_settings.log_level, json=False)

    app = FastAPI(title=resolved_settings.app_name, version="0.1.0")
    web_adapter = WebAdapter(settings=resolved_settings)
    app.include_router(web_adapter.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": resolved_settings.app_name}

    return app


__all__ = ["create_app"]
