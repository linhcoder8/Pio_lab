"""Web channel adapter for the M6 test bed."""

from __future__ import annotations

import hmac
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from pio_lab.core.registry import DepartmentRegistry
from pio_lab.layer0_console.admin import ConsoleAdmin, DepartmentAdminService
from pio_lab.layer3_chief_of_staff.chief_of_staff import ChiefOfStaff, get_chief_of_staff
from pio_lab.layer3_chief_of_staff.dispatch import extract_response_text
from pio_lab.memory.postgres.database import get_session
from pio_lab.memory.postgres.models import Task, Trace
from pio_lab.providers.router import get_router
from pio_lab.security.enforcer import SecurityEnforcer, SecurityError, enforcer
from pio_lab.utils.config_loader import load_providers_config
from pio_lab.utils.env import Settings, get_settings
from pio_lab.utils.helpers import gen_request_id, utc_now

SESSION_COOKIE = "pio_session"
SESSION_VALUE = "authenticated"
REFERENCE_ASSET_ROOT = Path("E:/PIO_lab")
REFERENCE_ASSETS = {
    "ORG_pio_lab_final.png",
    "Pio_lab_Architecture.png",
    "process_flow.png",
}


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


class ProviderTestRequest(BaseModel):
    """Admin provider test payload."""

    routing_key: str = Field(default="research.optics", min_length=1, max_length=128)
    prompt: str = Field(min_length=1, max_length=4096)
    system: str = Field(default="", max_length=2000)


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

        @self.router.get("/assets/reference/{filename}")
        async def reference_asset(filename: str) -> Response:
            if filename not in REFERENCE_ASSETS:
                raise HTTPException(status_code=404, detail="Asset not found")
            path = REFERENCE_ASSET_ROOT / filename
            if not path.exists():
                raise HTTPException(status_code=404, detail="Asset not found")
            return FileResponse(path)

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

        @self.router.get("/api/dashboard/state")
        async def dashboard_state(request: Request) -> Response:
            if not self.is_authenticated(request):
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            return JSONResponse(await _dashboard_state())

        @self.router.post("/api/providers/test")
        async def provider_test(request: Request, payload: ProviderTestRequest) -> Response:
            if not self.is_authenticated(request):
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            router = get_router()
            try:
                response = await router.call(
                    payload.routing_key,
                    [{"role": "user", "content": payload.prompt}],
                    system=payload.system or None,
                    agent_id="admin.provider_test",
                    timeout=180,
                )
            except Exception as error:
                return JSONResponse(
                    {
                        "status": "error",
                        "error_type": error.__class__.__name__,
                        "detail": str(error),
                    },
                    status_code=400,
                )
            return JSONResponse(
                {
                    "status": "ok",
                    "routing_key": payload.routing_key,
                    "provider": response.get("provider"),
                    "model": response.get("model"),
                    "text": extract_response_text(response),
                    "usage": response.get("usage") or {},
                }
            )

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


async def _dashboard_state() -> dict[str, Any]:
    router = get_router()
    if not router.loaded:
        router.load()

    return {
        "departments": _department_state(router),
        "providers": _provider_state(router),
        "routing": _routing_state(router),
        "statuses": _provider_status_state(router),
        "tasks": await _recent_task_state(),
        "traces": await _recent_trace_state(),
        "assets": {
            filename: (REFERENCE_ASSET_ROOT / filename).exists()
            for filename in sorted(REFERENCE_ASSETS)
        },
    }


def _department_state(router: Any) -> list[dict[str, Any]]:
    try:
        registry = DepartmentRegistry(router=router).load_all()
        return [
            {
                "id": department.config.id,
                "name": department.config.name,
                "name_vi": department.config.name_vi,
                "description": department.config.description,
                "workers": [
                    {
                        "id": worker.config.id,
                        "name": worker.config.name,
                        "routing_key": worker.config.provider_routing_key,
                    }
                    for worker in department.workers.values()
                ],
            }
            for department in registry.list_departments()
        ]
    except Exception as error:
        return [{"id": "unavailable", "name": "Registry unavailable", "error": str(error)}]


def _provider_state(router: Any) -> list[dict[str, Any]]:
    config = router.config or load_providers_config()
    providers = config.get("providers", {})
    rows: list[dict[str, Any]] = []
    for provider_id, provider_config in providers.items():
        accounts = []
        for account in router.account_pool.accounts_for(provider_id):
            accounts.append(
                {
                    "id": account.account_id,
                    "models": account.models,
                    "priority": account.priority,
                    "status": account.status,
                    "has_credentials": account.has_credentials(),
                    "credential_mode": account.metadata.get("credential_mode", ""),
                    "last_used": account.last_used.isoformat() if account.last_used else "",
                }
            )
        rows.append(
            {
                "id": provider_id,
                "type": provider_config.get("type", ""),
                "sdk": provider_config.get("sdk", ""),
                "accounts": accounts,
            }
        )
    return rows


def _routing_state(router: Any) -> list[dict[str, Any]]:
    config = router.config or load_providers_config()
    routing_rules = dict(config.get("routing_rules", {}))
    routing_rules["default_chain"] = config.get("default_chain", [])
    return [
        {
            "key": key,
            "chain": [
                {"provider": item.get("provider", ""), "model": item.get("model", "")}
                for item in chain
            ],
        }
        for key, chain in sorted(routing_rules.items())
    ]


def _provider_status_state(router: Any) -> list[dict[str, Any]]:
    list_statuses = getattr(router.status_tracker, "list_statuses", None)
    statuses = list_statuses() if callable(list_statuses) else []
    return [
        {
            "routing_key": status.routing_key,
            "provider": status.provider,
            "model": status.model,
            "state": status.state,
            "error": status.error,
            "updated_at": status.updated_at.isoformat() if status.updated_at else "",
        }
        for status in statuses[:20]
    ]


async def _recent_task_state(limit: int = 8) -> list[dict[str, Any]]:
    try:
        async with get_session() as session:
            result = await session.execute(select(Task).order_by(Task.created_at.desc()).limit(limit))
            tasks = list(result.scalars().all())
    except Exception:
        return []
    return [
        {
            "id": task.id,
            "status": task.status,
            "channel": task.channel,
            "user_id": task.user_id,
            "created_at": task.created_at.isoformat() if task.created_at else "",
            "output": _task_output_preview(task),
        }
        for task in tasks
    ]


async def _recent_trace_state(limit: int = 8) -> list[dict[str, Any]]:
    try:
        async with get_session() as session:
            result = await session.execute(select(Trace).order_by(Trace.created_at.desc()).limit(limit))
            traces = list(result.scalars().all())
    except Exception:
        return []
    return [
        {
            "agent_id": trace.agent_id,
            "routing_key": trace.routing_key,
            "provider": trace.provider,
            "model": trace.model,
            "status": trace.status,
            "latency_ms": trace.latency_ms,
            "created_at": trace.created_at.isoformat() if trace.created_at else "",
        }
        for trace in traces
    ]


def _task_output_preview(task: Task) -> str:
    final_output = task.final_output or {}
    text = str(final_output.get("text") or final_output)
    return text[:220]


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
  <title>Pio_lab Web Command Center</title>
  <style>
    * { box-sizing: border-box; }
    :root {
      color-scheme: light;
      --ink: #16213a;
      --muted: #667085;
      --line: #d7dde8;
      --panel: #ffffff;
      --blue: #1f5fbe;
      --green: #24824b;
      --amber: #c18411;
      --red: #cf3d45;
      --violet: #7b42c6;
      --orange: #c86f2a;
      --cyan: #0f7a98;
    }
    body {
      margin: 0;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      background:
        linear-gradient(135deg, rgba(31, 95, 190, .10), transparent 34%),
        linear-gradient(45deg, transparent 52%, rgba(200, 111, 42, .12)),
        #f5f7fb;
      color: var(--ink);
    }
    header {
      position: sticky;
      top: 0;
      z-index: 10;
      display: grid;
      grid-template-columns: minmax(220px, 1fr) auto auto auto;
      gap: 14px;
      align-items: center;
      min-height: 64px;
      padding: 10px 18px;
      background: rgba(255,255,255,.92);
      border-bottom: 1px solid var(--line);
      backdrop-filter: blur(14px);
    }
    h1 { font-size: 19px; margin: 0; letter-spacing: 0; }
    h2 { font-size: 17px; margin: 0 0 12px; letter-spacing: 0; }
    h3 { font-size: 14px; margin: 0 0 8px; letter-spacing: 0; }
    a { color: var(--blue); text-decoration: none; font-weight: 700; }
    button, select, input, textarea { font: inherit; }
    button {
      border: 0;
      border-radius: 7px;
      background: var(--blue);
      color: #fff;
      padding: 10px 13px;
      font-weight: 800;
      cursor: pointer;
    }
    button.secondary { background: #edf2f7; color: var(--ink); border: 1px solid var(--line); }
    .logout { background: transparent; color: #455466; padding: 8px 0; }
    .top-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: end; }
    .tabs { display: flex; gap: 7px; flex-wrap: wrap; justify-content: center; }
    .tab {
      background: #fff;
      color: #1d2b44;
      border: 1px solid var(--line);
      padding: 8px 10px;
      border-radius: 7px;
    }
    .tab.active { background: #0f2a4f; color: #fff; border-color: #0f2a4f; }
    main { max-width: 1440px; margin: 0 auto; padding: 18px; }
    .view { display: none; }
    .view.active { display: block; }
    .grid { display: grid; gap: 14px; }
    .hero-grid { grid-template-columns: minmax(0, 1.18fr) minmax(340px, .82fr); align-items: stretch; }
    .band {
      background: rgba(255,255,255,.86);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 8px 26px rgba(16, 24, 40, .06);
    }
    .command-panel {
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-height: 640px;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .command-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      background: #f8fbff;
    }
    .identity { display: flex; gap: 10px; align-items: center; }
    .avatar {
      width: 42px;
      height: 42px;
      display: grid;
      place-items: center;
      border-radius: 8px;
      background: #0f2a4f;
      color: #fff;
      font-weight: 900;
    }
    .sub { color: var(--muted); font-size: 13px; line-height: 1.4; }
    #messages {
      overflow: auto;
      padding: 16px;
      min-height: 420px;
      background:
        linear-gradient(90deg, rgba(36,130,75,.06), transparent 40%),
        linear-gradient(135deg, transparent 58%, rgba(123,66,198,.06));
    }
    .msg {
      max-width: 820px;
      white-space: pre-wrap;
      margin: 0 0 12px;
      padding: 11px 13px;
      border-radius: 8px;
      line-height: 1.48;
      border: 1px solid transparent;
    }
    .user { margin-left: auto; background: #dbeafe; border-color: #b9d4ff; }
    .bot { background: #ffffff; border-color: #dce4ef; }
    .quick-row { display: flex; gap: 8px; flex-wrap: wrap; padding: 0 16px 12px; }
    .quick { background: #eef6f1; color: #1f6f42; border: 1px solid #c9e7d2; padding: 7px 9px; border-radius: 7px; font-size: 13px; }
    form.chat {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      padding: 14px;
      border-top: 1px solid var(--line);
      background: #fff;
    }
    textarea, input, select {
      width: 100%;
      border: 1px solid #bac6d6;
      border-radius: 7px;
      padding: 10px 11px;
      color: var(--ink);
      background: #fff;
    }
    textarea { resize: vertical; min-height: 58px; max-height: 180px; }
    .ops-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; }
    .metric {
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      min-height: 82px;
    }
    .metric strong { display: block; font-size: 22px; color: #0f2a4f; }
    .metric span { color: var(--muted); font-size: 12px; }
    .org-stage {
      position: relative;
      overflow: hidden;
      min-height: 520px;
      background: linear-gradient(135deg, #f2f7ff, #fff7f1);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
    }
    .org-stage h2 { text-align: center; font-size: 24px; color: #0f2a4f; margin-bottom: 18px; }
    .org-top { display: grid; place-items: center; gap: 12px; margin-bottom: 18px; }
    .node {
      background: rgba(255,255,255,.92);
      border: 2px solid #244f91;
      border-radius: 8px;
      padding: 13px 18px;
      font-weight: 900;
      text-align: center;
      min-width: 260px;
      box-shadow: 0 8px 18px rgba(15, 42, 79, .12);
    }
    .chief { border-color: #0f2a4f; background: #edf5ff; }
    .dept-grid { display: grid; grid-template-columns: repeat(5, minmax(150px, 1fr)); gap: 12px; align-items: stretch; }
    .dept {
      background: #fff;
      border: 2px solid var(--green);
      border-radius: 8px;
      overflow: hidden;
      min-height: 210px;
      display: grid;
      grid-template-rows: auto 1fr;
    }
    .dept-head { padding: 11px 12px; color: #fff; font-weight: 900; display: flex; gap: 8px; align-items: center; }
    .dept-body { padding: 10px; display: grid; gap: 8px; align-content: start; }
    .worker { background: #f7fbff; border: 1px solid #d9e4f2; border-radius: 7px; padding: 9px; font-size: 13px; }
    .worker strong { display: block; color: #12284a; margin-bottom: 3px; }
    .report .dept-head { background: var(--orange); }
    .coder .dept-head { background: var(--green); }
    .research .dept-head { background: var(--red); }
    .media .dept-head { background: var(--violet); }
    .qa .dept-head { background: var(--amber); }
    .reference-grid { grid-template-columns: 1fr; }
    .reference-img {
      width: 100%;
      display: block;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    .flow-grid { grid-template-columns: minmax(0, 1fr) minmax(360px, .72fr); align-items: start; }
    .timeline { display: grid; gap: 10px; }
    .step {
      display: grid;
      grid-template-columns: 40px 1fr;
      gap: 10px;
      align-items: start;
      padding: 11px;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .step-num {
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      background: #0f2a4f;
      color: #fff;
      border-radius: 7px;
      font-weight: 900;
    }
    .provider-layout { grid-template-columns: minmax(0, .95fr) minmax(380px, 1.05fr); align-items: start; }
    .provider-list, .routing-list, .history-list { display: grid; gap: 10px; }
    .provider {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }
    .provider-title { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 8px; font-weight: 900; }
    .tag { display: inline-flex; align-items: center; border-radius: 6px; padding: 3px 7px; font-size: 12px; font-weight: 800; background: #eef2f7; color: #344054; }
    .ok { background: #e8f7ee; color: #1f6f42; }
    .warn { background: #fff4de; color: #9a6700; }
    .bad { background: #ffe8e8; color: #b42318; }
    .account { display: grid; gap: 4px; padding: 8px 0; border-top: 1px solid #eef2f7; font-size: 13px; }
    .models { color: var(--muted); font-size: 12px; word-break: break-word; }
    .provider-form { display: grid; gap: 10px; }
    .provider-result {
      min-height: 180px;
      white-space: pre-wrap;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 8px;
      padding: 13px;
      overflow: auto;
      line-height: 1.45;
    }
    .table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    .table th, .table td { text-align: left; padding: 9px; border-bottom: 1px solid #edf1f6; vertical-align: top; font-size: 13px; }
    .table th { color: #475467; background: #f8fafc; font-size: 12px; }
    .empty { color: var(--muted); padding: 10px; border: 1px dashed var(--line); border-radius: 8px; }
    @media (max-width: 1100px) {
      header { grid-template-columns: 1fr; }
      .tabs, .top-actions { justify-content: start; }
      .hero-grid, .flow-grid, .provider-layout, .ops-grid { grid-template-columns: 1fr; }
      .dept-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
      .metric-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
    }
    @media (max-width: 640px) {
      main { padding: 10px; }
      .dept-grid, .metric-grid { grid-template-columns: 1fr; }
      form.chat { grid-template-columns: 1fr; }
      .node { min-width: 0; width: 100%; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Pio_lab Web</h1>
      <div class="sub">Personal AI Company · Hybrid AI · Obsidian Memory</div>
    </div>
    <nav class="tabs" aria-label="Primary">
      <button class="tab active" data-view="command">Command</button>
      <button class="tab" data-view="org">ORG</button>
      <button class="tab" data-view="architecture">Architecture</button>
      <button class="tab" data-view="flow">Request Flow</button>
      <button class="tab" data-view="providers">Providers</button>
      <button class="tab" data-view="memory">Memory</button>
    </nav>
    <div class="top-actions">
      <a href="/admin">Admin</a>
      <a href="/admin/org">Add Agent</a>
    </div>
    <form method="post" action="/logout"><button class="logout" type="submit">Logout</button></form>
  </header>
  <main>
    <section class="view active" id="view-command">
      <div class="grid hero-grid">
        <div class="command-panel">
          <div class="command-head">
            <div class="identity">
              <div class="avatar">P</div>
              <div>
                <h2>Chief of Staff</h2>
                <div class="sub">Plan · Dispatch · QA · Archive</div>
              </div>
            </div>
            <span class="tag ok">Telegram + Web Ready</span>
          </div>
          <section id="messages" aria-live="polite"></section>
          <div class="quick-row">
            <button class="quick" data-prompt="Research lens design and summarize with citations">Research optics</button>
            <button class="quick" data-prompt="Write a 500-word blog about AI operations">Write content</button>
            <button class="quick" data-prompt="Create a one-slide report about Pio_lab architecture">Create report</button>
          </div>
          <form class="chat" id="chat-form">
            <textarea id="message" name="message" placeholder="Message Pio_lab" required></textarea>
            <button type="submit">Send</button>
          </form>
        </div>
        <aside class="grid">
          <section class="band">
            <h2>Runtime Snapshot</h2>
            <div class="metric-grid" id="metrics"></div>
          </section>
          <section class="band">
            <h2>Current Departments</h2>
            <div id="department-mini" class="provider-list"></div>
          </section>
        </aside>
      </div>
    </section>

    <section class="view" id="view-org">
      <div class="org-stage">
        <h2>Sơ đồ khối tổ chức Pio_lab</h2>
        <div class="org-top">
          <div class="node">CEO (Sếp Linh) · Ra yêu cầu</div>
          <div class="node chief">Chief of Staff · Điều phối & Báo cáo</div>
        </div>
        <div class="dept-grid" id="org-grid"></div>
      </div>
      <div class="band" style="margin-top:14px">
        <h2>Reference ORG</h2>
        <img class="reference-img" src="/assets/reference/ORG_pio_lab_final.png" alt="Pio_lab organization reference">
      </div>
    </section>

    <section class="view" id="view-architecture">
      <div class="grid reference-grid">
        <section class="band">
          <h2>Pio_lab Architecture v3</h2>
          <img class="reference-img" src="/assets/reference/Pio_lab_Architecture.png" alt="Pio_lab architecture">
        </section>
      </div>
    </section>

    <section class="view" id="view-flow">
      <div class="grid flow-grid">
        <section class="band">
          <h2>Request Flow</h2>
          <img class="reference-img" src="/assets/reference/process_flow.png" alt="Pio_lab request flow">
        </section>
        <section class="band">
          <h2>Processing Steps</h2>
          <div class="timeline">
            <div class="step"><div class="step-num">1</div><div><h3>Input</h3><div class="sub">Telegram, Web, Discord, Zalo nhận yêu cầu.</div></div></div>
            <div class="step"><div class="step-num">2</div><div><h3>Chief of Staff</h3><div class="sub">Phân loại, lập plan, chọn department/worker.</div></div></div>
            <div class="step"><div class="step-num">3</div><div><h3>Specialized Agent</h3><div class="sub">ProviderRouter gọi Codex, Claude, Gemini, DeepSeek hoặc Ollama.</div></div></div>
            <div class="step"><div class="step-num">4</div><div><h3>QA Gate</h3><div class="sub">Review kết quả, replan nếu cần.</div></div></div>
            <div class="step"><div class="step-num">5</div><div><h3>Archive</h3><div class="sub">Lưu task vào PostgreSQL và note vào Obsidian vault.</div></div></div>
          </div>
        </section>
      </div>
    </section>

    <section class="view" id="view-providers">
      <div class="grid provider-layout">
        <section class="band">
          <h2>Provider Management</h2>
          <div id="provider-list" class="provider-list"></div>
        </section>
        <section class="band">
          <h2>Test Provider</h2>
          <form class="provider-form" id="provider-form">
            <label>Routing key<select id="provider-routing"></select></label>
            <label>Prompt<textarea id="provider-prompt" required>Summarize lens design in two bullets with citations.</textarea></label>
            <button type="submit">Run Provider</button>
          </form>
          <div class="provider-result" id="provider-result">Provider output will appear here.</div>
        </section>
      </div>
      <section class="band" style="margin-top:14px">
        <h2>Routing Rules</h2>
        <div id="routing-list" class="routing-list"></div>
      </section>
    </section>

    <section class="view" id="view-memory">
      <div class="grid ops-grid">
        <section class="band">
          <h2>Archived Tasks</h2>
          <div id="task-history"></div>
        </section>
        <section class="band">
          <h2>Provider Traces</h2>
          <div id="trace-history"></div>
        </section>
      </div>
    </section>
  </main>
  <script>
    let dashboardState = {departments: [], providers: [], routing: [], tasks: [], traces: [], statuses: []};
    const form = document.getElementById("chat-form");
    const input = document.getElementById("message");
    const messages = document.getElementById("messages");
    const tabs = document.querySelectorAll(".tab");

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        tabs.forEach((node) => node.classList.remove("active"));
        document.querySelectorAll(".view").forEach((node) => node.classList.remove("active"));
        tab.classList.add("active");
        document.getElementById(`view-${tab.dataset.view}`).classList.add("active");
      });
    });

    function addMessage(text, cls) {
      const node = document.createElement("div");
      node.className = `msg ${cls}`;
      node.textContent = text;
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }

    document.querySelectorAll(".quick").forEach((button) => {
      button.addEventListener("click", () => {
        input.value = button.dataset.prompt;
        input.focus();
      });
    });

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
      loadDashboardState();
    });

    document.getElementById("provider-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const result = document.getElementById("provider-result");
      result.textContent = "Running provider...";
      const response = await fetch("/api/providers/test", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          routing_key: document.getElementById("provider-routing").value,
          prompt: document.getElementById("provider-prompt").value
        })
      });
      const data = await response.json();
      if (!response.ok) {
        result.textContent = `${data.error_type || "Error"}: ${data.detail || "Provider failed"}`;
      } else {
        result.textContent = `[${data.provider}/${data.model}]\n\n${data.text || ""}`;
      }
      loadDashboardState();
    });

    async function loadDashboardState() {
      const response = await fetch("/api/dashboard/state");
      dashboardState = await response.json();
      renderMetrics();
      renderDepartments();
      renderProviders();
      renderRouting();
      renderHistory();
    }

    function renderMetrics() {
      const metrics = document.getElementById("metrics");
      const providerReady = dashboardState.providers
        .flatMap((provider) => provider.accounts || [])
        .filter((account) => account.has_credentials).length;
      metrics.innerHTML = [
        metric("Departments", dashboardState.departments.length),
        metric("Providers ready", providerReady),
        metric("Recent tasks", dashboardState.tasks.length),
        metric("Recent traces", dashboardState.traces.length)
      ].join("");
    }

    function metric(label, value) {
      return `<div class="metric"><strong>${escapeHtml(String(value))}</strong><span>${escapeHtml(label)}</span></div>`;
    }

    function renderDepartments() {
      const mini = document.getElementById("department-mini");
      const org = document.getElementById("org-grid");
      mini.innerHTML = dashboardState.departments.map((department) => `
        <div class="provider">
          <div class="provider-title"><span>${escapeHtml(department.name || department.id)}</span><span class="tag">${escapeHtml(department.id)}</span></div>
          <div class="models">${(department.workers || []).map((worker) => escapeHtml(worker.name || worker.id)).join(" · ")}</div>
        </div>
      `).join("") || `<div class="empty">No departments loaded.</div>`;
      org.innerHTML = dashboardState.departments.map((department) => {
        const cls = ["report", "coder", "research", "media", "qa"].includes(department.id) ? department.id : "";
        return `<article class="dept ${cls}">
          <div class="dept-head">${deptIcon(department.id)} ${escapeHtml(department.name || department.id)}</div>
          <div class="dept-body">
            ${(department.workers || []).map((worker) => `
              <div class="worker"><strong>${escapeHtml(worker.name || worker.id)}</strong><span class="sub">${escapeHtml(worker.routing_key || "")}</span></div>
            `).join("")}
          </div>
        </article>`;
      }).join("");
    }

    function renderProviders() {
      const list = document.getElementById("provider-list");
      const select = document.getElementById("provider-routing");
      list.innerHTML = dashboardState.providers.map((provider) => `
        <article class="provider">
          <div class="provider-title">
            <span>${escapeHtml(provider.id)}</span>
            <span class="tag">${escapeHtml(provider.sdk || provider.type || "provider")}</span>
          </div>
          ${(provider.accounts || []).map((account) => `
            <div class="account">
              <div><strong>${escapeHtml(account.id)}</strong> <span class="tag ${account.has_credentials ? "ok" : "warn"}">${account.has_credentials ? "ready" : "missing credentials"}</span></div>
              <div class="models">${escapeHtml((account.models || []).join(" · "))}</div>
              <div class="sub">priority ${escapeHtml(String(account.priority))}${account.credential_mode ? " · " + escapeHtml(account.credential_mode) : ""}</div>
            </div>
          `).join("")}
        </article>
      `).join("");
      select.innerHTML = dashboardState.routing
        .filter((route) => route.key !== "default_chain")
        .map((route) => `<option value="${escapeAttr(route.key)}">${escapeHtml(route.key)}</option>`)
        .join("");
    }

    function renderRouting() {
      const list = document.getElementById("routing-list");
      list.innerHTML = dashboardState.routing.map((route) => `
        <div class="provider">
          <div class="provider-title"><span>${escapeHtml(route.key)}</span><span class="tag">${(route.chain || []).length} target</span></div>
          <div class="models">${(route.chain || []).map((target) => `${escapeHtml(target.provider)}/${escapeHtml(target.model)}`).join(" → ")}</div>
        </div>
      `).join("");
    }

    function renderHistory() {
      document.getElementById("task-history").innerHTML = table(
        ["Status", "Channel", "Output"],
        dashboardState.tasks.map((task) => [task.status, task.channel, task.output || task.id])
      );
      document.getElementById("trace-history").innerHTML = table(
        ["Route", "Provider", "Latency"],
        dashboardState.traces.map((trace) => [trace.routing_key, `${trace.provider}/${trace.model}`, `${trace.latency_ms || 0} ms`])
      );
    }

    function table(headers, rows) {
      if (!rows.length) return `<div class="empty">No rows yet.</div>`;
      return `<table class="table"><thead><tr>${headers.map((item) => `<th>${escapeHtml(item)}</th>`).join("")}</tr></thead><tbody>${
        rows.map((row) => `<tr>${row.map((item) => `<td>${escapeHtml(String(item || ""))}</td>`).join("")}</tr>`).join("")
      }</tbody></table>`;
    }

    function deptIcon(id) {
      return {report: "📊", coder: "💻", research: "🔍", media: "🎬", qa: "✅"}[id] || "🤖";
    }

    function escapeHtml(value) {
      return value.replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    function escapeAttr(value) {
      return escapeHtml(String(value));
    }

    addMessage("Pio_lab Command Center sẵn sàng.", "bot");
    loadDashboardState();
  </script>
</body>
</html>"""


__all__ = ["ChatRequest", "ChatResponse", "WebAdapter"]
