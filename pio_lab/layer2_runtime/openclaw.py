"""OpenClaw runtime bootstrap for M6."""

from __future__ import annotations

from fastapi import FastAPI

from pio_lab.layer0_console.admin import DepartmentAdminService
from pio_lab.layer1_input.web_adapter import WebAdapter
from pio_lab.layer3_chief_of_staff.chief_of_staff import ChiefOfStaff
from pio_lab.utils.env import Settings, get_settings
from pio_lab.utils.logging import setup_logging


def create_app(
    settings: Settings | None = None,
    *,
    chief_of_staff: ChiefOfStaff | None = None,
    department_admin: DepartmentAdminService | None = None,
) -> FastAPI:
    """Create the FastAPI app with the Web channel adapter mounted."""
    resolved_settings = settings or get_settings()
    setup_logging(resolved_settings.log_level, json=False)

    app = FastAPI(title=resolved_settings.app_name, version="0.1.0")
    web_adapter = WebAdapter(
        settings=resolved_settings,
        chief_of_staff=chief_of_staff,
        department_admin=department_admin,
    )
    app.include_router(web_adapter.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": resolved_settings.app_name}

    return app


__all__ = ["create_app"]
