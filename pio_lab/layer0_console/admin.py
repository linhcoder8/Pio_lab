"""Minimal Layer 0 admin console for M11."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import yaml
from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from pio_lab.core.registry import DEPARTMENTS_ROOT, DepartmentRegistry
from pio_lab.memory.postgres.database import get_session
from pio_lab.memory.postgres.models import Task
from pio_lab.providers.router import ProviderRouter, get_router

DEPARTMENT_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")


class CreateDepartmentRequest(BaseModel):
    """Payload for creating a department from the admin console."""

    id: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=2, max_length=64)
    name_vi: str = ""
    description: str = ""
    worker_id: str = Field(default="generalist", min_length=2, max_length=32)
    worker_name: str = "Generalist Worker"


class DepartmentAdminService:
    """Create/list runtime departments backed by YAML config."""

    def __init__(
        self,
        *,
        registry_path: str | Path | None = None,
        router: ProviderRouter | None = None,
    ) -> None:
        self.registry_path = Path(registry_path or DEPARTMENTS_ROOT / "_registry.yaml")
        self.departments_root = self.registry_path.parent
        self.router = router or get_router()

    def list_departments(self) -> list[dict[str, Any]]:
        """Return departments currently visible to the registry."""
        registry = DepartmentRegistry(registry_path=self.registry_path, router=self.router).load_all()
        return [
            {
                "id": department.config.id,
                "name": department.config.name,
                "name_vi": department.config.name_vi,
                "workers": sorted(department.workers.keys()),
            }
            for department in registry.list_departments()
        ]

    def create_department(self, payload: CreateDepartmentRequest) -> dict[str, Any]:
        """Create department YAML files and update the registry."""
        department_id = payload.id.strip().lower()
        worker_id = payload.worker_id.strip().lower()
        _validate_identifier(department_id, "department id")
        _validate_identifier(worker_id, "worker id")

        registry = self._load_registry()
        if any(entry.get("id") == department_id for entry in registry.get("departments", [])):
            raise ValueError(f"Department already exists: {department_id}")

        department_dir = self.departments_root / department_id
        workers_dir = department_dir / "workers"
        workers_dir.mkdir(parents=True, exist_ok=False)

        department_config = {
            "id": department_id,
            "name": payload.name,
            "name_vi": payload.name_vi,
            "description": payload.description or f"Custom department {payload.name}",
            "system_prompt": f"You are manager of {payload.name}. Route work carefully.",
            "workers_path": "./workers",
            "workers": [worker_id],
            "default_tools": [],
        }
        worker_config = {
            "id": worker_id,
            "name": payload.worker_name,
            "department": department_id,
            "description": f"Default worker for {payload.name}",
            "system_prompt": f"You are {payload.worker_name}. Complete the user's task.",
            "provider_routing_key": f"{department_id}.{worker_id}",
            "tools_enabled": [],
            "max_iterations": 3,
            "timeout_seconds": 120,
        }

        _write_yaml(department_dir / "department.yaml", department_config)
        _write_yaml(workers_dir / f"{worker_id}.yaml", worker_config)

        registry.setdefault("version", 1)
        registry.setdefault("departments", []).append(
            {
                "id": department_id,
                "name": payload.name,
                "name_vi": payload.name_vi,
                "enabled": True,
                "config_path": f"./{department_id}/department.yaml",
            }
        )
        _write_yaml(self.registry_path, registry)
        return {
            "id": department_id,
            "name": payload.name,
            "worker_id": worker_id,
            "config_path": str(department_dir / "department.yaml"),
        }

    async def dispatch_department(
        self,
        department_id: str,
        task: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatch a task directly to one department for admin validation."""
        registry = DepartmentRegistry(registry_path=self.registry_path, router=self.router).load_all()
        department = registry.get_department(department_id)
        return await department.run(task)

    def _load_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            return {"version": 1, "departments": []}
        with self.registry_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        if not isinstance(data, dict):
            raise ValueError("Department registry YAML must be a mapping")
        data.setdefault("departments", [])
        return data


class ConsoleAdmin:
    """FastAPI routes for the admin console."""

    def __init__(
        self,
        *,
        is_authenticated: Callable[[Request], bool],
        department_admin: DepartmentAdminService | None = None,
    ) -> None:
        self.is_authenticated = is_authenticated
        self.department_admin = department_admin or DepartmentAdminService()
        self.router = APIRouter()
        self._register_routes()

    def _register_routes(self) -> None:
        @self.router.get("/admin", response_class=HTMLResponse)
        async def dashboard(request: Request) -> Response:
            if not self.is_authenticated(request):
                return RedirectResponse("/login", status_code=303)
            return HTMLResponse(_admin_shell("Dashboard", _dashboard_html()))

        @self.router.get("/admin/tasks", response_class=HTMLResponse)
        async def tasks_page(request: Request) -> Response:
            if not self.is_authenticated(request):
                return RedirectResponse("/login", status_code=303)
            return HTMLResponse(_admin_shell("Tasks", await _tasks_html()))

        @self.router.get("/admin/org", response_class=HTMLResponse)
        async def org_page(request: Request) -> Response:
            if not self.is_authenticated(request):
                return RedirectResponse("/login", status_code=303)
            return HTMLResponse(_admin_shell("Organization", self._org_html()))

        @self.router.post("/admin/org")
        async def create_department_form(request: Request) -> Response:
            if not self.is_authenticated(request):
                return RedirectResponse("/login", status_code=303)
            payload = _department_payload_from_form(await request.body())
            try:
                self.department_admin.create_department(payload)
            except Exception as error:
                return HTMLResponse(
                    _admin_shell("Organization", self._org_html(error=str(error))),
                    status_code=400,
                )
            return RedirectResponse("/admin/org", status_code=303)

        @self.router.get("/api/admin/status")
        async def api_status(request: Request) -> Response:
            if not self.is_authenticated(request):
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            return JSONResponse({"status": "ok", "departments": self.department_admin.list_departments()})

        @self.router.get("/api/admin/departments")
        async def api_departments(request: Request) -> Response:
            if not self.is_authenticated(request):
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            return JSONResponse({"departments": self.department_admin.list_departments()})

        @self.router.post("/api/admin/departments")
        async def api_create_department(request: Request, payload: CreateDepartmentRequest) -> Response:
            if not self.is_authenticated(request):
                return JSONResponse({"detail": "Not authenticated"}, status_code=401)
            try:
                created = self.department_admin.create_department(payload)
            except Exception as error:
                return JSONResponse({"detail": str(error)}, status_code=400)
            return JSONResponse(created, status_code=201)

    def _org_html(self, error: str | None = None) -> str:
        departments = self.department_admin.list_departments()
        rows = "\n".join(
            f"<tr><td>{dept['id']}</td><td>{dept['name']}</td><td>{', '.join(dept['workers'])}</td></tr>"
            for dept in departments
        )
        error_html = f"<p class=\"error\">{error}</p>" if error else ""
        return f"""
<section class="toolbar"><h2>Departments</h2></section>
{error_html}
<table><thead><tr><th>ID</th><th>Name</th><th>Workers</th></tr></thead><tbody>{rows}</tbody></table>
<section class="panel">
  <h2>Add Department</h2>
  <form method="post" action="/admin/org" class="grid-form">
    <label>ID<input name="id" required pattern="[a-z][a-z0-9_]{{1,31}}"></label>
    <label>Name<input name="name" required></label>
    <label>Vietnamese name<input name="name_vi"></label>
    <label>Worker ID<input name="worker_id" value="generalist" required></label>
    <label>Worker name<input name="worker_name" value="Generalist Worker" required></label>
    <label class="wide">Description<textarea name="description"></textarea></label>
    <button type="submit">Add Department</button>
  </form>
</section>
"""


async def _tasks_html(limit: int = 20) -> str:
    try:
        rows = await _recent_task_rows(limit=limit)
    except Exception as error:
        return f"<p class=\"error\">Task store unavailable: {error}</p>"
    if not rows:
        return "<p>No archived tasks yet.</p>"
    return (
        "<table><thead><tr><th>ID</th><th>Status</th><th>Channel</th><th>Output</th></tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


async def _recent_task_rows(limit: int) -> list[str]:
    async with get_session() as session:
        result = await session.execute(select(Task).order_by(Task.created_at.desc()).limit(limit))
        tasks = list(result.scalars().all())
    return [
        "<tr>"
        f"<td>{task.id}</td><td>{task.status}</td><td>{task.channel}</td>"
        f"<td>{_task_output_preview(task)}</td>"
        "</tr>"
        for task in tasks
    ]


def _dashboard_html() -> str:
    return """
<section class="stats">
  <a href="/admin/tasks">Task History</a>
  <a href="/admin/org">Organization</a>
  <a href="/">Web Chat</a>
</section>
"""


def _admin_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pio_lab Admin · {title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, Arial, sans-serif; background: #f5f7fa; color: #17212b; }}
    header {{ display: flex; justify-content: space-between; align-items: center; height: 56px; padding: 0 18px; background: #fff; border-bottom: 1px solid #d7dde5; }}
    nav a {{ margin-right: 14px; color: #1f6feb; text-decoration: none; font-weight: 700; }}
    main {{ max-width: 1040px; margin: 0 auto; padding: 20px; }}
    h1 {{ font-size: 18px; margin: 0; }}
    h2 {{ font-size: 16px; margin: 0 0 12px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d7dde5; }}
    th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #e6ebf1; vertical-align: top; }}
    th {{ background: #eef3f8; font-size: 13px; }}
    .panel {{ margin-top: 18px; background: #fff; border: 1px solid #d7dde5; padding: 16px; border-radius: 8px; }}
    .grid-form {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    label {{ display: grid; gap: 6px; font-size: 13px; font-weight: 700; }}
    input, textarea {{ width: 100%; padding: 10px; border: 1px solid #bcc6d2; border-radius: 6px; font: inherit; }}
    textarea {{ min-height: 88px; resize: vertical; }}
    button {{ border: 0; border-radius: 6px; background: #1f6feb; color: #fff; padding: 11px 14px; font-weight: 700; }}
    .wide {{ grid-column: 1 / -1; }}
    .error {{ color: #b42318; font-weight: 700; }}
    .stats {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .stats a {{ display: block; padding: 14px 16px; background: #fff; border: 1px solid #d7dde5; border-radius: 8px; color: #1f6feb; font-weight: 700; text-decoration: none; }}
  </style>
</head>
<body>
  <header>
    <h1>Pio_lab Admin</h1>
    <nav><a href="/admin">Dashboard</a><a href="/admin/tasks">Tasks</a><a href="/admin/org">Org</a></nav>
  </header>
  <main>{body}</main>
</body>
</html>"""


def _department_payload_from_form(raw_body: bytes) -> CreateDepartmentRequest:
    fields = parse_qs(raw_body.decode("utf-8"))
    return CreateDepartmentRequest(
        id=fields.get("id", [""])[0],
        name=fields.get("name", [""])[0],
        name_vi=fields.get("name_vi", [""])[0],
        description=fields.get("description", [""])[0],
        worker_id=fields.get("worker_id", ["generalist"])[0],
        worker_name=fields.get("worker_name", ["Generalist Worker"])[0],
    )


def _task_output_preview(task: Task) -> str:
    final_output = task.final_output or {}
    text = str(final_output.get("text") or final_output)
    return text[:180]


def _validate_identifier(value: str, label: str) -> None:
    if not DEPARTMENT_ID_RE.match(value):
        raise ValueError(f"Invalid {label}: {value}")


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(payload, file, allow_unicode=True, sort_keys=False)


__all__ = ["ConsoleAdmin", "CreateDepartmentRequest", "DepartmentAdminService"]
