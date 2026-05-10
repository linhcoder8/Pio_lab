"""Web channel adapter for the M6 test bed."""

from __future__ import annotations

import hmac
from hashlib import sha256
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from pio_lab.layer0_console.admin import ConsoleAdmin, DepartmentAdminService
from pio_lab.layer3_chief_of_staff.chief_of_staff import ChiefOfStaff, get_chief_of_staff
from pio_lab.security.enforcer import SecurityEnforcer, SecurityError, enforcer
from pio_lab.utils.env import Settings, get_settings
from pio_lab.utils.helpers import gen_request_id, utc_now

SESSION_COOKIE = "pio_session"
SESSION_VALUE = "authenticated"


class ChatRequest(BaseModel):
    """HTTP chat request payload."""

    message: str = Field(min_length=1, max_length=4096)
    channel: str = "web"
    user_id: str = "web_admin"


class ChatResponse(BaseModel):
    """HTTP chat response payload."""

    message_id: str
    reply: str
    channel: str
    created_at: str


class WebAdapter:
    """FastAPI router for the browser chat test bed."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        security: SecurityEnforcer | None = None,
        chief_of_staff: ChiefOfStaff | None = None,
        department_admin: DepartmentAdminService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.security = security or enforcer
        self.chief_of_staff = chief_of_staff or get_chief_of_staff()
        self.router = APIRouter()
        self.admin_console = ConsoleAdmin(
            is_authenticated=self.is_authenticated,
            department_admin=department_admin,
        )
        self._register_routes()
        self.router.include_router(self.admin_console.router)

    def is_authenticated(self, request: Request) -> bool:
        """Return whether an HTTP request has a valid session cookie."""
        return _verify_session_cookie(
            request.cookies.get(SESSION_COOKIE),
            self.settings.web_ui_secret,
        )

    async def authenticate_form(self, request: Request) -> bool:
        """Authenticate a URL-encoded login form."""
        body = (await request.body()).decode("utf-8")
        fields = parse_qs(body)
        password = fields.get("password", [""])[0]
        return hmac.compare_digest(password, self.settings.web_ui_admin_password)

    def create_session_response(self, redirect_to: str = "/") -> RedirectResponse:
        """Create a redirect response that sets the signed session cookie."""
        response = RedirectResponse(redirect_to, status_code=303)
        response.set_cookie(
            SESSION_COOKIE,
            _sign_session_cookie(self.settings.web_ui_secret),
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 12,
        )
        return response

    def clear_session_response(self) -> RedirectResponse:
        """Create a redirect response that clears the session cookie."""
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE)
        return response

    async def handle_chat(self, payload: ChatRequest) -> ChatResponse:
        """Route a web chat message through the Chief of Staff."""
        try:
            self.security.require_crypto_safe_text(payload.message)
        except SecurityError as error:
            reply = f"Blocked by security policy: {error}"
        else:
            result = await self.chief_of_staff.run(
                {
                    "input": payload.message,
                    "channel": payload.channel,
                    "user_id": payload.user_id,
                }
            )
            reply = self._format_chief_response(result)
            reply = self.security.mask_secrets_in_output(reply)

        return ChatResponse(
            message_id=gen_request_id("webmsg"),
            reply=reply,
            channel=payload.channel,
            created_at=utc_now().isoformat(),
        )

    def _format_chief_response(self, result: dict[str, Any]) -> str:
        if result.get("status") == "waiting_approval":
            approval = result.get("approval") or {}
            return str(approval.get("prompt") or "Yêu cầu cần phê duyệt của Sếp Linh.")
        final_output = result.get("final_output") or {}
        if isinstance(final_output, dict) and final_output.get("text"):
            return str(final_output["text"])
        return str(result.get("reply") or result.get("status") or "Pio_lab handled the request.")

    def _register_routes(self) -> None:
        @self.router.get("/", response_class=HTMLResponse)
        async def index(request: Request) -> Response:
            if not self.is_authenticated(request):
                return RedirectResponse("/login", status_code=303)
            return HTMLResponse(_chat_page_html())

        @self.router.get("/login", response_class=HTMLResponse)
        async def login_page(request: Request) -> Response:
            if self.is_authenticated(request):
                return RedirectResponse("/", status_code=303)
            return HTMLResponse(_login_page_html())

        @self.router.post("/login")
        async def login(request: Request) -> Response:
            if await self.authenticate_form(request):
                return self.create_session_response()
            return HTMLResponse(_login_page_html(error="Invalid password"), status_code=401)

        @self.router.post("/logout")
        async def logout() -> Response:
            return self.clear_session_response()

        @self.router.post("/api/chat", response_model=ChatResponse)
        async def chat(request: Request, payload: ChatRequest) -> Response:
            if not self.is_authenticated(request):
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            response = await self.handle_chat(payload)
            return JSONResponse(response.model_dump())

        @self.router.websocket("/ws/chat")
        async def websocket_chat(websocket: WebSocket) -> None:
            if not _verify_session_cookie(
                websocket.cookies.get(SESSION_COOKIE),
                self.settings.web_ui_secret,
            ):
                await websocket.close(code=1008)
                return

            await websocket.accept()
            try:
                while True:
                    data: dict[str, Any] = await websocket.receive_json()
                    response = await self.handle_chat(ChatRequest(**data))
                    await websocket.send_json(response.model_dump())
            except WebSocketDisconnect:
                return


def _sign_session_cookie(secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), SESSION_VALUE.encode("utf-8"), sha256).hexdigest()
    return f"{SESSION_VALUE}.{signature}"


def _verify_session_cookie(cookie: str | None, secret: str) -> bool:
    if not cookie or "." not in cookie:
        return False
    value, signature = cookie.rsplit(".", 1)
    if value != SESSION_VALUE:
        return False
    expected = _sign_session_cookie(secret).rsplit(".", 1)[1]
    return hmac.compare_digest(signature, expected)


def _login_page_html(error: str | None = None) -> str:
    error_html = f"<p class=\"error\">{error}</p>" if error else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pio_lab Login</title>
  <style>
    body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #f4f7fb; color: #16202a; }}
    main {{ min-height: 100vh; display: grid; place-items: center; padding: 24px; }}
    form {{ width: min(360px, 100%); background: #ffffff; border: 1px solid #d7dde5; border-radius: 8px; padding: 20px; }}
    h1 {{ font-size: 20px; margin: 0 0 16px; }}
    label {{ display: block; font-size: 13px; font-weight: 700; margin-bottom: 8px; }}
    input {{ box-sizing: border-box; width: 100%; padding: 11px 12px; border: 1px solid #bcc6d2; border-radius: 6px; }}
    button {{ width: 100%; margin-top: 14px; padding: 11px 12px; border: 0; border-radius: 6px; background: #1f6feb; color: white; font-weight: 700; }}
    .error {{ color: #b42318; font-size: 13px; margin: 0 0 12px; }}
  </style>
</head>
<body>
  <main>
    <form method="post" action="/login">
      <h1>Pio_lab</h1>
      {error_html}
      <label for="password">Admin password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" autofocus>
      <button type="submit">Sign in</button>
    </form>
  </main>
</body>
</html>"""


def _chat_page_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pio_lab Web Chat</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Inter, Arial, sans-serif; background: #eef3f8; color: #17212b; }
    header { height: 56px; display: flex; align-items: center; justify-content: space-between; padding: 0 18px; background: #ffffff; border-bottom: 1px solid #d7dde5; }
    h1 { font-size: 18px; margin: 0; }
    main { display: grid; grid-template-rows: 1fr auto; min-height: calc(100vh - 56px); max-width: 920px; margin: 0 auto; padding: 16px; gap: 12px; }
    #messages { overflow: auto; background: #ffffff; border: 1px solid #d7dde5; border-radius: 8px; padding: 14px; min-height: 420px; }
    .msg { max-width: 760px; white-space: pre-wrap; margin: 0 0 10px; padding: 10px 12px; border-radius: 8px; line-height: 1.45; }
    .user { margin-left: auto; background: #dbeafe; }
    .bot { background: #f4f6f8; }
    form.chat { display: grid; grid-template-columns: 1fr auto; gap: 8px; }
    textarea { resize: vertical; min-height: 48px; max-height: 180px; padding: 11px 12px; border: 1px solid #bcc6d2; border-radius: 8px; font: inherit; }
    button { border: 0; border-radius: 8px; background: #1f6feb; color: white; padding: 0 18px; font-weight: 700; }
    .logout { background: transparent; color: #455466; padding: 8px 0; }
  </style>
</head>
<body>
  <header>
    <h1>Pio_lab Web</h1>
    <nav><a href="/admin">Admin</a></nav>
    <form method="post" action="/logout"><button class="logout" type="submit">Logout</button></form>
  </header>
  <main>
    <section id="messages" aria-live="polite"></section>
    <form class="chat" id="chat-form">
      <textarea id="message" name="message" placeholder="Message Pio_lab" required></textarea>
      <button type="submit">Send</button>
    </form>
  </main>
  <script>
    const form = document.getElementById("chat-form");
    const input = document.getElementById("message");
    const messages = document.getElementById("messages");
    function addMessage(text, cls) {
      const node = document.createElement("div");
      node.className = `msg ${cls}`;
      node.textContent = text;
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      addMessage(text, "user");
      input.value = "";
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: text})
      });
      const data = await response.json();
      addMessage(data.reply || data.detail || "Request failed", "bot");
    });
  </script>
</body>
</html>"""


__all__ = ["ChatRequest", "ChatResponse", "WebAdapter"]
