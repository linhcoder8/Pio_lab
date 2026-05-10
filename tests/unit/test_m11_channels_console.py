"""Tests for M11 channels and admin console."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from pio_lab.core.registry import DepartmentRegistry
from pio_lab.layer0_console.admin import DepartmentAdminService
from pio_lab.layer1_input.channel_router import ChannelRouter, chunk_text
from pio_lab.layer1_input.discord_adapter import DiscordAdapter
from pio_lab.layer1_input.telegram_adapter import TelegramAdapter
from pio_lab.layer1_input.zalo_adapter import ZaloAdapter
from pio_lab.layer2_runtime.openclaw import create_app
from pio_lab.providers.adapters.base_provider import BaseProvider
from pio_lab.providers.router import ProviderRouter
from pio_lab.utils.env import Settings


class FakeChiefOfStaff:
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "done",
            "final_output": {"text": f"{payload['channel']} reply: {payload['input']}"},
        }


class FakeProvider(BaseProvider):
    name = "fake"

    async def complete(
        self,
        account,
        model: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": "custom department dispatched"}],
            "usage": {"input_tokens": 1, "output_tokens": 1},
            "provider": "fake",
            "model": model,
            "raw": None,
        }


@pytest.mark.asyncio
async def test_telegram_message_routes_full_flow_and_chunks_long_output() -> None:
    router = ChannelRouter(chief_of_staff=FakeChiefOfStaff())  # type: ignore[arg-type]
    adapter = TelegramAdapter(
        settings=Settings(telegram_allowed_users="42"),
        channel_router=router,
    )

    reply = await adapter.handle_text(user_id=42, chat_id=100, text="Research lens design")

    assert reply.channel == "telegram"
    assert reply.text == "telegram reply: Research lens design"
    assert chunk_text("a" * 4100, channel="telegram")[1]


@pytest.mark.asyncio
async def test_telegram_rejects_user_outside_whitelist() -> None:
    adapter = TelegramAdapter(settings=Settings(telegram_allowed_users="42"))

    reply = await adapter.handle_text(user_id=7, text="hello")

    assert reply.raw_result["status"] == "forbidden"
    assert "Your Telegram user id: 7" in reply.text


@pytest.mark.asyncio
async def test_telegram_whoami_works_even_outside_whitelist() -> None:
    adapter = TelegramAdapter(settings=Settings(telegram_allowed_users="42"))

    reply = await adapter.handle_text(user_id=7, text="/whoami")

    assert reply.raw_result["status"] == "command"
    assert reply.text == "Your Telegram user id: 7"


@pytest.mark.asyncio
async def test_discord_message_and_zalo_webhook_route_to_channel_router() -> None:
    router = ChannelRouter(chief_of_staff=FakeChiefOfStaff())  # type: ignore[arg-type]
    discord = DiscordAdapter(channel_router=router, allowed_user_ids={"9"})
    zalo = ZaloAdapter(channel_router=router)

    discord_reply = await discord.handle_message(user_id=9, text="Write code")
    zalo_reply = await zalo.handle_webhook(
        {"event_name": "user_send_text", "sender": {"id": "zalo_user"}, "message": {"text": "Xin chào"}}
    )

    assert discord_reply.text == "discord reply: Write code"
    assert zalo_reply.text == "zalo reply: Xin chào"


def test_admin_console_pages_require_login_and_show_dashboard(tmp_path: Path) -> None:
    client = _admin_client(tmp_path)

    unauthenticated = client.get("/admin", follow_redirects=False)
    assert unauthenticated.status_code == 303

    _login(client)
    response = client.get("/admin")

    assert response.status_code == 200
    assert "Pio_lab Admin" in response.text
    assert "/admin/org" in response.text


def test_admin_api_add_department_updates_registry_and_dispatches(tmp_path: Path) -> None:
    service = _department_admin(tmp_path)
    client = _admin_client(tmp_path, department_admin=service)
    _login(client)

    response = client.post(
        "/api/admin/departments",
        json={
            "id": "sales",
            "name": "SALES",
            "name_vi": "Bán hàng",
            "worker_id": "pitch",
            "worker_name": "Pitch Worker",
        },
    )

    assert response.status_code == 201
    departments = client.get("/api/admin/departments").json()["departments"]
    assert any(department["id"] == "sales" for department in departments)

    registry = DepartmentRegistry(registry_path=tmp_path / "_registry.yaml", router=_fake_router())
    sales = registry.load_all().get_department("sales")
    assert sales.config.name == "SALES"


@pytest.mark.asyncio
async def test_department_admin_dispatches_new_department_with_injected_router(
    tmp_path: Path,
) -> None:
    service = _department_admin(tmp_path)
    service.create_department(
        service_payload("sales", "SALES", worker_id="pitch", worker_name="Pitch Worker")
    )

    result = await service.dispatch_department("sales", {"input": "Create a sales pitch"})

    assert result["department_id"] == "sales"
    assert result["worker_id"] == "pitch"
    assert result["output"] == "custom department dispatched"


def _admin_client(
    tmp_path: Path,
    *,
    department_admin: DepartmentAdminService | None = None,
) -> TestClient:
    settings = Settings(web_ui_admin_password="test-password", web_ui_secret="test-secret")
    app = create_app(
        settings,
        chief_of_staff=FakeChiefOfStaff(),  # type: ignore[arg-type]
        department_admin=department_admin or _department_admin(tmp_path),
    )
    return TestClient(app)


def _login(client: TestClient) -> None:
    client.post(
        "/login",
        content="password=test-password",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def _department_admin(tmp_path: Path) -> DepartmentAdminService:
    _write_empty_registry(tmp_path / "_registry.yaml")
    return DepartmentAdminService(registry_path=tmp_path / "_registry.yaml", router=_fake_router())


def _write_empty_registry(path: Path) -> None:
    path.write_text(yaml.safe_dump({"version": 1, "departments": []}), encoding="utf-8")


def _fake_router() -> ProviderRouter:
    return ProviderRouter(
        config={
            "providers": {
                "fake": {
                    "accounts": [{"id": "fake_main", "models": ["fake-model"], "priority": 1}]
                }
            },
            "routing_rules": {"sales.pitch": [{"provider": "fake", "model": "fake-model"}]},
            "default_chain": [{"provider": "fake", "model": "fake-model"}],
        },
        adapters={"fake": FakeProvider()},
    )


def service_payload(
    department_id: str,
    name: str,
    *,
    worker_id: str,
    worker_name: str,
):
    from pio_lab.layer0_console.admin import CreateDepartmentRequest

    return CreateDepartmentRequest(
        id=department_id,
        name=name,
        worker_id=worker_id,
        worker_name=worker_name,
    )
