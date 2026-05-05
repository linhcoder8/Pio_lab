"""Tests for M6 Web channel."""

from __future__ import annotations

from fastapi.testclient import TestClient

from pio_lab.layer2_runtime.openclaw import create_app
from pio_lab.utils.env import Settings


def _client() -> TestClient:
    settings = Settings(web_ui_admin_password="test-password", web_ui_secret="test-secret")
    return TestClient(create_app(settings))


def test_root_requires_authentication() -> None:
    client = _client()

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_with_admin_password_sets_session_cookie() -> None:
    client = _client()

    response = client.post(
        "/login",
        content="password=test-password",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "pio_session" in response.headers["set-cookie"]


def test_chat_page_loads_after_login() -> None:
    client = _client()
    client.post(
        "/login",
        content="password=test-password",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "Pio_lab Web" in response.text
    assert "/api/chat" in response.text


def test_api_chat_echoes_authenticated_message_and_masks_secret() -> None:
    client = _client()
    client.post(
        "/login",
        content="password=test-password",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    response = client.post(
        "/api/chat",
        json={"message": "Say hi with sk-abcdefghijklmnopqrstuvwxyz123456"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reply"].startswith("Echo: Say hi")
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in data["reply"]
    assert "sk-...3456" in data["reply"]


def test_api_chat_rejects_unauthenticated_message() -> None:
    client = _client()

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 401


def test_websocket_echoes_authenticated_message() -> None:
    client = _client()
    client.post(
        "/login",
        content="password=test-password",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"message": "hello"})
        data = websocket.receive_json()

    assert data["reply"] == "Echo: hello"
