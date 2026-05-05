# 🤖 Pio_lab — Codex Handoff Document

> **Bạn (GPT Codex) đang tiếp quản dự án `Pio_lab` từ giai đoạn folder structure đã hoàn tất.**
> File này chứa toàn bộ context để bạn implement Phase 1 MVP từ skeleton hiện tại.
>
> **Đọc TOÀN BỘ file này trước khi viết bất kỳ dòng code nào.**

---

## 📚 Companion documents (BẮT BUỘC đọc cùng)

| File | Mục đích | Khi nào đọc |
|---|---|---|
| `STRUCTURE.md` | Bản đồ thư mục đầy đủ 162 files | Đầu mỗi session |
| `PROGRESS.md` | Tracker — Codex tự cập nhật | Đầu/cuối mỗi session |
| `Pio_lab_Architecture.png` | Visual diagram v3 (7 lớp + cross-cutting) | Khi cần hình dung kiến trúc |
| `docs/Pio_lab_Architecture.svg` | Source SVG (edit nếu cần update) | Khi update architecture |
| `docs/PROVIDER_API_REFERENCE.md` | **Sample request/response của 5 providers** với tool use, errors | M3-M4 (implement adapters) |
| `docs/EXAMPLES.md` | **10 task scenarios** end-to-end để test | Sau mỗi milestone |
| `docs/7_layers.md` | Chi tiết từng layer | Khi implement layer cụ thể |
| `docs/adding_departments.md` | Cách extend phòng ban runtime | Khi test dynamic registry |
| `Pio_lab_Architecture.html` | Sơ đồ HTML (mở browser xem interactive) | Optional |

---

## 📑 Mục lục

0. [Mission Brief — Đọc đầu tiên](#0-mission-brief)
1. [Project Overview](#1-project-overview)
2. [Architecture: 7 Layers + Cross-cutting](#2-architecture)
3. [Current State — Đã có gì](#3-current-state)
4. [Tech Stack & Dependencies](#4-tech-stack)
5. [Code Conventions](#5-code-conventions)
6. [Implementation Plan — 12 Milestones](#6-implementation-plan)
7. [Reference: Key Files](#7-reference-key-files)
8. [Provider Routing Logic](#8-provider-routing)
9. [Testing Strategy](#9-testing-strategy)
10. [Workflow Per Session](#10-workflow-per-session)
11. [Common Pitfalls](#11-common-pitfalls)
12. [Definition of Done — MVP Phase 1](#12-definition-of-done)

---

## 0. Mission Brief

**WHO YOU ARE:** GPT Codex agent.
**WHAT YOU DO:** Implement Pio_lab Phase 1 MVP from existing skeleton.
**WHO USES IT:** Sếp Linh (single user, owner).
**LANGUAGE FOR DOCSTRINGS/COMMENTS:** Tiếng Việt + English mix OK. Tiếng Việt cho user-facing strings.
**LANGUAGE FOR CODE:** English.

**OPERATING PRINCIPLES:**
1. **One milestone at a time.** Đừng nhảy cóc — finish M0 trước khi sang M1.
2. **Skeleton trước, implementation sau.** Tất cả file đã có skeleton + `# TODO Phase 1` markers — bạn fill in code, KHÔNG phá structure đã design.
3. **Tests first khi có thể.** Mỗi feature lớn phải có test ít nhất ở smoke level.
4. **Commit after each milestone** với message format: `M{number}: {short description}`.
5. **Update `PROGRESS.md`** sau mỗi milestone — đánh dấu done + ghi note nếu có thay đổi.
6. **Hỏi Sếp Linh** khi có ambiguity — KHÔNG tự ý đổi architecture.

**SUCCESS = Phase 1 MVP chạy được:**
- User gõ tin nhắn vào Telegram bot → Pio_lab xử lý → trả lời (qua phòng ban + provider router + memory).
- Web UI tối thiểu xem được task history.
- Logs tất cả LLM calls vào Postgres `traces` table.

---

## 1. Project Overview

### Tên: **Pio_lab** (Personal AI Company)
- **Owner / CEO:** Sếp Linh
- **Codename Runtime:** OpenClaw (Lobster)
- **Status hiện tại:** MVP Phase 1 — folder structure ✓ approved, ready for implementation

### Vision (1 dòng)
> Một "công ty AI cá nhân" chạy 24/7, có nhiều phòng ban chuyên môn (Coder/Research/Media/Report/QA) do Chief of Staff điều phối, dùng hybrid AI (Cloud + Local Ollama qua Tailscale), tích lũy knowledge vào second brain (Postgres + Obsidian).

### Use cases Phase 1
1. Sếp Linh gõ Telegram: *"Research X và viết blog post"* → Research dept tìm info → Media dept viết blog → QA verify → trả về Telegram.
2. Sếp Linh hỏi Web UI: *"Sửa bug ở file Y"* → Coder dept (Backend) làm → trả về kèm diff.
3. *"Tóm tắt 5 paper mới về quang học"* → Research/Optics → output markdown vào Obsidian Vault.
4. Cron 7am hàng ngày → tự động chạy "morning brief" → push notify.

### Non-goals Phase 1 (rõ ràng KHÔNG làm)
- Distillation training (chỉ collect traces)
- Portable export (manual scripts/backup.sh)
- Security Engine UI (dùng default rules cứng)
- WhatsApp / iMessage channels
- Solid Edge integration đầy đủ (placeholder thôi)
- YouTube/TikTok auto-upload đầy đủ (skeleton + Human Approval gate)

---

## 2. Architecture

### 7 Layers (đọc từ trên xuống = flow request)

```
┌─────────────────────────────────────────────────┐
│ L0 · 🖥️  Management Console (Web UI)            │  Admin/Config
└─────────────────────────────────────────────────┘
            ↕ (cấu hình + observe)
┌─────────────────────────────────────────────────┐
│ L1 · 👤 Input — Channels (Telegram·Web·DC·Zalo)│  Inbound
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ L2 · 🌐 OpenClaw Runtime                         │  Bootstrap, Skill Engine, Cron
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ L3 · 👔 Chief of Staff (Orchestrator)            │  PLAN→DISPATCH→REPORT
│      Internal: LangGraph StateGraph              │  + replan loop + human approval
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ L4 · 🏢 5 Departments (Dynamic Registry)        │  Specialists
│      REPORT · CODER · RESEARCH · MEDIA · QA     │
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ L5 · 📚 Knowledge Librarian                      │  Postgres + Obsidian
└─────────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────────┐
│ L6 · 💬 Communicator (Output Adapter)            │  Format theo channel
└─────────────────────────────────────────────────┘
            ↓
       User receives reply
```

### Cross-cutting modules (xuyên suốt)
- **Provider Router** — mọi LLM call đi qua đây (Codex/Claude/Gemini/DeepSeek/Ollama)
- **Persistent Memory** — Postgres (structured) + Obsidian Vault (markdown wiki)
- **Security Policy** — Phase 1 default rules cứng từ YAML
- **Distillation** — Phase 1 chỉ trace logger
- **Portable Export** — Phase 1 dùng `scripts/backup.sh`

### Reference sơ đồ trực quan
File `Pio_lab_Architecture.html` ở root — mở browser để xem.

---

## 3. Current State

### ✅ Đã có (skeleton + configs)
- 162 files, 60 folders đã tạo
- 113 Python files với class signatures + docstrings + `# TODO Phase 1` markers
- 18 YAML config files đầy đủ:
  - `config/pio_lab.yaml` — main app config
  - `config/providers.yaml` — multi-provider routing rules (5 providers)
  - `config/security_policy.yaml` — default security rules
  - `config/departments/_registry.yaml` + 5 phòng ban + 9 worker configs
- 17 Markdown docs (README, STRUCTURE, architecture, 7_layers, adding_departments…)
- `pyproject.toml` với deps đã chọn
- `docker-compose.yml` cho Postgres
- Vault skeleton (USER.md, AGENTS.md, SOUL.md)
- Helper scripts (setup.py, backup.sh, add_department.py)

### ❌ Chưa làm (việc của bạn — Codex)
- **Tất cả code logic** (mọi `# TODO Phase 1` markers)
- **DB schema migrations** (Alembic)
- **Tests** thực sự (mới có skeleton)
- **Frontend React** (mới có README.md placeholder)
- **Skill implementations** (file_read, web_search, image_gen…)
- **Integration** giữa các layer

### File tham chiếu BẮT BUỘC đọc
1. `STRUCTURE.md` — bản đồ thư mục đầy đủ
2. `README.md` — overview + quick start
3. `docs/7_layers.md` — chi tiết từng layer
4. `docs/adding_departments.md` — cách extend
5. `Pio_lab_Architecture.png` — **visual diagram v3** (xem trước khi code)
6. `docs/PROVIDER_API_REFERENCE.md` — **sample API responses** cho 5 providers
7. `docs/EXAMPLES.md` — **10 task scenarios** để test sau mỗi milestone

---

## 4. Tech Stack

### Core
- **Python 3.11+** (use type hints khắp nơi)
- **FastAPI** (Web channel + Layer 0 Console API)
- **LangGraph** + LangChain Core (Chief of Staff orchestration)
- **PostgreSQL 16** (chạy qua docker-compose)
- **SQLAlchemy 2.0 async** + **Alembic** (DB)
- **Pydantic v2** (validation)
- **Loguru** (logging)
- **PyYAML** (config)
- **httpx** (HTTP client)

### Frontend (Layer 0 Console)
- **React 18** + **Vite** + **TypeScript**
- **Tailwind CSS** + **shadcn/ui**
- **Zustand** (state)
- **TanStack Query** (API)

### LLM Providers (Phase 1 đầy đủ 5)
- `anthropic>=0.30` — Claude (Opus/Sonnet/Haiku)
- `openai>=1.30` — Codex/GPT (4o, 4o-mini, o1)
- `google-generativeai>=0.5` — Gemini (2.0 pro/flash)
- DeepSeek — qua OpenAI SDK với base_url custom
- `ollama>=0.2` — Local AI qua Tailscale

### Channel Libraries
- `python-telegram-bot>=21` — Telegram
- `discord.py>=2.3` — Discord
- Web: native FastAPI WebSocket
- Zalo: HTTP qua `httpx` (Zalo OA REST API)

### Tools
- `pytest` + `pytest-asyncio` + `pytest-cov`
- `ruff` (lint + format)
- `mypy` (type check)

### Infrastructure
- Docker (Postgres)
- Tailscale (kết nối Local Ollama)
- Obsidian (đọc vault thủ công)

---

## 5. Code Conventions

### Style
- **Line length:** 100 chars (ruff config)
- **Quotes:** double quotes preferred
- **Imports:** absolute paths (`from pio_lab.core.agent import BaseAgent`)
- **Type hints:** REQUIRED on public functions, return types annotated
- **Async:** preferred for I/O operations
- **Naming:**
  - `snake_case` cho functions/variables
  - `PascalCase` cho classes
  - `SCREAMING_SNAKE_CASE` cho constants

### Docstring format
```python
def my_function(arg1: str, arg2: int) -> dict[str, Any]:
    """
    Một câu mô tả ngắn (tiếng Việt OK).

    Chi tiết hơn nếu cần.

    Args:
        arg1: ...
        arg2: ...

    Returns:
        Dict containing ...

    Raises:
        ValueError: when ...
    """
```

### Async pattern
```python
# Prefer:
async def fetch_data() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return response.json()

# Avoid blocking calls in async:
# ❌ requests.get(...) trong async function
# ✅ await httpx.AsyncClient().get(...)
```

### Error handling pattern
```python
from pio_lab.utils.logging import logger

try:
    result = await provider.complete(...)
except QuotaExceededError as e:
    logger.warning(f"Quota exhausted for {provider.name}, rotating: {e}")
    # → fallback to next provider in chain
except Exception as e:
    logger.exception(f"Unexpected error in {context}")
    raise
```

### Logging
```python
# ❌ KHÔNG dùng print()
# ✅ Dùng loguru
from pio_lab.utils.logging import logger

logger.info("Loaded {count} departments", count=5)
logger.error("Failed to dispatch task {task_id}", task_id=tid)
```

### Config loading
```python
# Tất cả config đọc qua đúng 1 chỗ - utils/config_loader.py (cần tạo)
# KHÔNG hardcode path trong từng module
```

### Don't
- ❌ KHÔNG dùng `print()` — dùng `logger`
- ❌ KHÔNG hardcode API keys — dùng `.env` qua `os.environ`
- ❌ KHÔNG block event loop — dùng async I/O
- ❌ KHÔNG sửa architecture (7 layers, naming) — confirm với Sếp Linh trước
- ❌ KHÔNG commit `.env`, `vault/.obsidian/workspace*`, `traces/`
- ❌ KHÔNG xóa hoặc rename file đã có mà không cập nhật imports

---

## 6. Implementation Plan

### Tổng quan 12 milestones (làm tuần tự)

| # | Milestone | Mục tiêu | Effort | Phụ thuộc |
|---|---|---|---|---|
| M0 | Foundation | Config loader, logging, helpers, .env | XS | - |
| M1 | Memory · Postgres | Models, migrations, trace logger | S | M0 |
| M2 | Memory · Obsidian | Vault read/write, USER/AGENTS/SOUL.md | XS | M0 |
| M3 | Provider Router | Router + 1 adapter (Claude) hoạt động | M | M0 |
| M4 | Provider Router · 4 còn lại | Codex, Gemini, DeepSeek, Ollama | M | M3 |
| M5 | Security Enforcer | Policy loader + enforcer hooks | S | M0 |
| M6 | Channel · Web | FastAPI + WebSocket adapter (test bed) | S | M0 |
| M7 | Chief of Staff | LangGraph: plan→dispatch→report | L | M3, M6 |
| M8 | Department + Worker base | GenericDepartment + GenericWorker | M | M3, M7 |
| M9 | 5 Departments cụ thể | Wire 5 phòng ban + 9 workers | M | M8 |
| M10 | Knowledge Librarian | Archive after QA pass | S | M1, M2, M9 |
| M11 | Channels còn lại + Console | Telegram, Discord, Zalo + Layer 0 UI | L | M9 |

**Order rationale:** M0-M2 là foundation. M3-M4 cho phép gọi LLM. M5 đảm bảo an toàn. M6 cho test bed (Web UI dễ debug hơn Telegram). M7-M9 build core flow. M10 archive. M11 mở rộng.

---

### M0 — Foundation

**Goal:** Có nền tảng để mọi module khác dùng.

**Files to create/modify:**
- `pio_lab/utils/config_loader.py` (NEW) — load + cache YAML configs
- `pio_lab/utils/logging.py` (EXISTS — flesh out) — loguru setup
- `pio_lab/utils/helpers.py` (EXISTS) — đã có gen_request_id, utc_now
- `pio_lab/utils/env.py` (NEW) — Pydantic Settings để validate env vars
- `tests/unit/test_config_loader.py` (NEW)

**Acceptance criteria:**
- [ ] `config_loader.load_pio_lab_config()` trả về dict từ `config/pio_lab.yaml`
- [ ] `config_loader.load_providers_config()` cache result
- [ ] `env.Settings` validate POSTGRES_*, các API keys
- [ ] `setup_logging()` work với JSON + text mode
- [ ] Test pass: `pytest tests/unit/test_config_loader.py`

**Reference code template (config_loader):**
```python
from functools import lru_cache
from pathlib import Path
import yaml

CONFIG_ROOT = Path(__file__).resolve().parent.parent.parent / "config"

@lru_cache(maxsize=8)
def _load_yaml(filename: str) -> dict:
    path = CONFIG_ROOT / filename
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_pio_lab_config() -> dict:
    return _load_yaml("pio_lab.yaml")

def load_providers_config() -> dict:
    return _load_yaml("providers.yaml")

def load_security_policy() -> dict:
    return _load_yaml("security_policy.yaml")
```

---

### M1 — Memory · Postgres

**Goal:** DB schema + trace logger hoạt động.

**Files:**
- `pio_lab/memory/postgres/models.py` (EXISTS) — đã có Task/Trace/Conversation, **thêm Provider, Account models**
- `pio_lab/memory/postgres/database.py` (NEW) — async engine + session factory
- `pio_lab/memory/postgres/migrations/` — chạy `alembic init -t async migrations` + `alembic revision --autogenerate -m "init"`
- `pio_lab/memory/postgres/traces.py` (EXISTS) — implement `TraceLogger.log()`
- `scripts/init_db.py` (EXISTS — flesh out)
- `tests/unit/test_postgres_models.py`

**Acceptance criteria:**
- [ ] `docker-compose up -d` start Postgres
- [ ] `python scripts/init_db.py` creates tables successfully
- [ ] `TraceLogger.log(...)` insert được 1 row
- [ ] Test query: select tasks/traces work via async session

**Schema must include:**
- `tasks` (id, user_id, channel, request, plan, final_output, status, timestamps)
- `traces` (task_id FK, agent_id, routing_key, provider, model, messages_in/out, tokens_in/out, latency_ms)
- `conversations` (user_id, channel, role, content, created_at)
- `provider_accounts` (provider, account_id, status, last_used, quota_exhausted_until)

---

### M2 — Memory · Obsidian

**Goal:** Read/write markdown vào `vault/`.

**Files:**
- `pio_lab/memory/obsidian/vault.py` (EXISTS) — implement đầy đủ
- `pio_lab/memory/obsidian/soul_md.py` `user_md.py` `agents_md.py` (EXISTS) — implement get/set
- `tests/unit/test_obsidian_vault.py`

**Acceptance criteria:**
- [ ] `vault.write("tasks/2026-05-04/abc.md", content)` create file đúng path
- [ ] `vault.list_notes("tasks")` trả về list đầy đủ
- [ ] `SoulMd.get()` trả content của `vault/SOUL.md`
- [ ] `AgentsMd.regenerate(registry)` build lại file từ registry state

**Format chuẩn cho task note:**
```markdown
---
task_id: abc123
user_id: ...
channel: telegram
created_at: 2026-05-04T10:30:00+07:00
status: done
---

# Request
{user request original text}

# Plan
- Step 1: ...
- Step 2: ...

# Output
{final output}

# Trace
{summary of which dept/worker handled what}
```

---

### M3 — Provider Router (Claude only first)

> **📖 Đọc trước:** `docs/PROVIDER_API_REFERENCE.md` — section "Anthropic Claude"
> Chứa: request format, raw response shape, tool use multi-turn, errors, full adapter implementation hint.

**Goal:** `router.call("test", messages)` work với Claude provider.

**Files:**
- `pio_lab/providers/router.py` (EXISTS) — implement `_resolve_chain`, `_init_adapters`, `call`
- `pio_lab/providers/account_pool.py` (EXISTS) — implement `register`, `next_available`, `mark_quota_exhausted`
- `pio_lab/providers/status_tracker.py` (EXISTS) — implement
- `pio_lab/providers/token_tracker.py` (EXISTS) — implement
- `pio_lab/providers/adapters/base_provider.py` (EXISTS) — interface chốt
- `pio_lab/providers/adapters/claude_adapter.py` (EXISTS) — implement với anthropic SDK
- `tests/unit/test_provider_router.py`
- `tests/integration/test_claude_provider.py` (cần API key thật trong .env)

**Acceptance criteria:**
- [ ] Router load từ `config/providers.yaml` thành công
- [ ] Account pool có ít nhất 1 Claude account
- [ ] `await router.call("research.optics", [{"role":"user","content":"hi"}])` → response
- [ ] Trace được log vào Postgres

**Claude adapter template:**
```python
import os
from anthropic import AsyncAnthropic
from pio_lab.providers.adapters.base_provider import BaseProvider

class ClaudeProvider(BaseProvider):
    name = "claude"

    async def complete(self, account, model, messages, tools=None, **kwargs):
        api_key = os.environ[account.env_key]
        client = AsyncAnthropic(api_key=api_key)
        # Convert messages format if needed
        response = await client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 4096),
            messages=messages,
            tools=tools or [],
            system=kwargs.get("system"),
        )
        return {
            "content": response.content,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            "model": model,
            "raw": response,
        }
```

---

### M4 — Provider Router · 4 providers còn lại

> **📖 Đọc trước:** `docs/PROVIDER_API_REFERENCE.md` — sections "OpenAI Codex", "Google Gemini", "DeepSeek", "Ollama".
> Mỗi section có: SDK setup, request/response shape, tool format khác nhau, errors, adapter hints.
> Lưu ý đặc biệt: Ollama tool calling support phụ thuộc model — đọc kỹ.

**Goal:** All 5 providers gọi được, fallback chain hoạt động.

**Files:**
- `codex_adapter.py` — OpenAI SDK
- `gemini_adapter.py` — google-generativeai
- `deepseek_adapter.py` — OpenAI SDK với `base_url=https://api.deepseek.com`
- `ollama_adapter.py` — `ollama` Python client với `OLLAMA_HOST` qua Tailscale

**Acceptance criteria:**
- [ ] Mỗi adapter pass smoke test (gọi 1 message simple, có response)
- [ ] Fallback chain: nếu Claude fail → router auto try Codex
- [ ] Status tracker reflect đúng (Running/End/Waiting)

**Lưu ý đặc biệt:**
- Ollama tool calling support varies → check model trước (qwen2.5-coder:32b OK, gpt-oss-20b limited)
- Gemini message format khác (cần convert)
- DeepSeek dùng OpenAI-compatible API

---

### M5 — Security Enforcer

**Goal:** Default rules từ `security_policy.yaml` được apply runtime.

**Files:**
- `pio_lab/security/policy_loader.py` (EXISTS) — implement
- `pio_lab/security/enforcer.py` (EXISTS) — implement
- `tests/unit/test_security.py`

**Hooks cần wire:**
- File system tools: trước khi `open(path)`, check `enforcer.check_file_access(path)`
- LLM output: trước khi gửi user, `enforcer.mask_secrets_in_output(text)`
- Action dispatch: trước khi thực thi sensitive action, check `enforcer.requires_approval(action)`
- Crypto check: trước khi process text liên quan crypto, check `enforcer.check_crypto_keywords(text)`

**Acceptance criteria:**
- [ ] Test: cố gắng open file ngoài project root → bị reject
- [ ] Test: text "Here's my key sk-abc123..." được mask
- [ ] Test: action "send_email" trigger approval flag
- [ ] Test: text chứa "seed phrase" bị block

---

### M6 — Channel · Web (test bed)

**Goal:** Web UI chat đơn giản — gõ message → nhận reply.

**Files:**
- `pio_lab/layer1_input/web_adapter.py` (EXISTS) — FastAPI + WebSocket
- `pio_lab/layer2_runtime/openclaw.py` — bootstrap được FastAPI app + adapter
- Endpoint cần expose: `POST /api/chat` (sync), `WS /ws/chat` (realtime)
- Optional: minimal HTML chat page tại `/` để test (chưa cần React)

**Acceptance criteria:**
- [ ] `bash scripts/start_dev.sh` start được server
- [ ] Open `http://localhost:8000/` thấy chat page (basic HTML đủ)
- [ ] Gõ message → dummy echo response (M7 sẽ wire vào Chief of Staff)
- [ ] Auth: yêu cầu `WEB_UI_ADMIN_PASSWORD` đăng nhập (đơn giản: cookie session)

**Reasoning:** Web UI dễ debug hơn Telegram trong giai đoạn dev — không cần ngrok, không cần bot token.

---

### M7 — Chief of Staff (LangGraph)

**Goal:** `chief_of_staff.run(task)` work end-to-end (dummy departments OK).

**Files:**
- `pio_lab/layer3_chief_of_staff/chief_of_staff.py` — implement `build_graph()`, `run()`
- `pio_lab/layer3_chief_of_staff/plan.py` — `plan_node` thực sự gọi LLM (router) để build plan
- `pio_lab/layer3_chief_of_staff/dispatch.py` — `dispatch_node` parallel via `asyncio.gather`
- `pio_lab/layer3_chief_of_staff/report.py` — `report_node` aggregate + gọi QA dept
- `pio_lab/layer3_chief_of_staff/replan.py` — implement với max retry counter
- `pio_lab/layer3_chief_of_staff/human_approval.py` — LangGraph interrupt + wait

**LangGraph structure:**
```python
from langgraph.graph import StateGraph, START, END
from pio_lab.core.state import PioLabState

graph = StateGraph(PioLabState)
graph.add_node("plan", plan_node)
graph.add_node("dispatch", dispatch_node)
graph.add_node("report", report_node)
graph.add_node("replan", replan_node)
graph.add_node("approval", approval_node)

graph.add_edge(START, "plan")

graph.add_conditional_edges(
    "plan",
    lambda s: "approval" if needs_approval_in_plan(s) else "dispatch",
    {"approval": "approval", "dispatch": "dispatch"},
)
graph.add_edge("approval", "dispatch")  # after approval, continue
graph.add_edge("dispatch", "report")
graph.add_conditional_edges(
    "report",
    lambda s: "replan" if s["qa_verdict"] == "NEEDS_FIX" else END,
    {"replan": "replan", END: END},
)
graph.add_edge("replan", "plan")  # loop back

app = graph.compile(checkpointer=...)
```

**Acceptance criteria:**
- [ ] `chief_of_staff.run({"input": "hello"})` complete graph execution
- [ ] Trace logged vào Postgres
- [ ] Replan loop trigger được khi QA fail (test bằng mock)
- [ ] Human approval pause graph + resume sau approve

---

### M8 — Department + Worker base

**Goal:** GenericDepartment + GenericWorker chạy được task qua LLM.

**Files:**
- `pio_lab/layer4_departments/base/department_base.py` — implement `select_worker` (LLM-based) + `run` (dispatch + aggregate)
- `pio_lab/layer4_departments/base/worker_base.py` — implement ReAct loop
- `pio_lab/core/registry.py` — implement `load_all`, `_load_department`, `add_department`
- `tests/unit/test_generic_worker.py`

**ReAct loop pattern:**
```python
async def run(self, task, context):
    tools = skill_engine.get_tools_for(self.config.id, self.config.tools_enabled)
    system = self.config.system_prompt
    messages = [{"role": "user", "content": task["input"]}]

    for iteration in range(self.config.max_iterations):
        response = await router.call(
            self.config.provider_routing_key,
            messages,
            tools=tools,
            system=system,
        )
        # If LLM returns tool_use → execute tool → append result → continue
        # If LLM returns final answer → break
        if is_final(response):
            return {"output": extract_text(response), "trace": messages}
        tool_results = await execute_tools(response, tools)
        messages.append(response)
        messages.append({"role": "user", "content": tool_results})

    raise TimeoutError(f"Worker {self.config.id} max iterations exceeded")
```

**Acceptance criteria:**
- [ ] Registry load 5 phòng ban từ `config/departments/_registry.yaml`
- [ ] `dept.run(task)` chọn worker đúng
- [ ] `worker.run(task)` complete với LLM call + tool use
- [ ] Trace logged

---

### M9 — 5 Departments cụ thể

**Goal:** REPORT/CODER/RESEARCH/MEDIA/QA hoạt động end-to-end với real workloads.

**Files:** mỗi `pio_lab/layer4_departments/{dept}/department.py` + `workers/*.py` đã có alias `= GenericDepartment/Worker` — KHÔNG cần override trừ khi cần custom.

**Tools cần wire (skill engine):**
- `file_read`, `file_write` (with security check)
- `web_search` (Google Search API hoặc Tavily)
- `markdown_to_html`
- `office_skill_pptx` / `office_skill_docx` — gọi anthropic-skills:pptx / :docx
- `image_generation` — Gemini Imagen hoặc OpenAI DALL-E
- `tts_skill` — OpenAI TTS hoặc ElevenLabs
- `video_edit_ffmpeg` — subprocess wrapper
- `git`, `npm`, `pip`, `docker` — subprocess wrappers (with security check)

**Acceptance criteria:**
- [ ] CODER.backend: write 1 file Python, run pytest pass
- [ ] RESEARCH.optics: search "lens design" → return summary với citation
- [ ] MEDIA.content: viết blog 500 từ
- [ ] REPORT.slide_word_web: tạo file `.pptx` từ data
- [ ] QA.qa_reviewer: nhận output → trả PASS/NEEDS_FIX với JSON đúng format
- [ ] End-to-end test: user request → CoS → dispatch → 1 dept → QA → output

---

### M10 — Knowledge Librarian

**Goal:** Sau QA pass, archive task vào Postgres + Obsidian.

**Files:**
- `pio_lab/layer5_librarian/librarian.py` — implement `run` (archive) + `search` (retrieval)
- `pio_lab/layer5_librarian/postgres_store.py` — wrap `tasks` table
- `pio_lab/layer5_librarian/obsidian_store.py` — write `vault/tasks/YYYY-MM-DD/<id>.md`
- `pio_lab/layer5_librarian/indexer.py` — Postgres FTS index

**Acceptance criteria:**
- [ ] After CoS report node passes QA → librarian called automatically
- [ ] `tasks` row inserted với full plan + output
- [ ] Markdown note created in `vault/tasks/`
- [ ] `librarian.search("optics lens")` returns relevant past tasks

---

### M11 — Channels còn lại + Layer 0 Console

**Goal:** Telegram/Discord/Zalo work + minimal React UI cho admin.

**Sub-milestones:**

**M11.1 — Telegram adapter (1 day)**
- Implement `telegram_adapter.py` với python-telegram-bot
- Whitelist user IDs từ `TELEGRAM_ALLOWED_USERS`
- Basic commands: `/start`, `/help`, `/status`
- Wire vào ChannelRouter

**M11.2 — Discord adapter (1 day)**
- discord.py — slash commands + DM support
- Whitelist user IDs

**M11.3 — Zalo adapter (2-3 days, khó nhất)**
- Đăng ký Zalo OA, lấy webhook URL
- Implement webhook endpoint
- Send qua Zalo OA REST API

**M11.4 — Layer 0 Console UI (3-5 days)**
- Scaffold React + Vite + Tailwind + shadcn/ui
- Pages:
  - `/` Dashboard (status, recent tasks)
  - `/bot` Bot config editor (USER.md, SOUL.md inline editor)
  - `/providers` Account/Model table với add/remove
  - `/skills` Skills toggle
  - `/org` ORG diagram + Add Department/Worker forms
  - `/tasks` Task history viewer

**Acceptance criteria:**
- [ ] User gõ Telegram → trả lời (full flow)
- [ ] User mở `http://localhost:8000/admin` → login → thấy dashboard
- [ ] Add 1 department mới qua UI → reflected in registry → có thể dispatch task

---

## 7. Reference: Key Files

### File QUAN TRỌNG NHẤT khi bạn cần ngữ cảnh

| File | Khi cần đọc |
|---|---|
| `STRUCTURE.md` | Bản đồ tổng thể |
| `README.md` | Quick overview |
| `docs/7_layers.md` | Hiểu chi tiết từng layer |
| `docs/adding_departments.md` | Khi thêm/sửa phòng ban |
| `config/pio_lab.yaml` | Toggle features, channels enabled |
| `config/providers.yaml` | Routing rules per worker — phải khớp `provider_routing_key` |
| `config/departments/*/workers/*.yaml` | Spec của từng worker (system_prompt, tools, max_iter) |
| `config/security_policy.yaml` | Rules bảo mật default |
| `pio_lab/core/state.py` | Shared state schema (LangGraph) |
| `pio_lab/core/agent.py` | BaseAgent interface |
| `Pio_lab_Architecture.html` | Visual diagram |

### File AUTO-GENERATED (đừng edit thủ công)
- `vault/AGENTS.md` — gen từ registry
- `pio_lab/memory/postgres/migrations/versions/*.py` — Alembic gen

---

## 8. Provider Routing Logic

### Cách Provider Router chọn LLM

```
Worker calls router.call("coder.backend", messages, tools=...)
  ↓
Router lookup config/providers.yaml routing_rules.coder.backend
  ↓
Returns chain: [
    { provider: codex, model: gpt-4o },
    { provider: deepseek, model: deepseek-coder },
    { provider: ollama, model: qwen2.5-coder:32b }
]
  ↓
Try each in order:
  for entry in chain:
    account = account_pool.next_available(entry.provider)
    if account is None: continue
    try:
      response = await provider.complete(account, model, messages, tools)
      tracker.record(...)
      return response
    except QuotaExceeded:
      account_pool.mark_quota_exhausted(account.id)
      continue
    except OtherError:
      log + continue
  ↓
If ALL fail: raise RuntimeError
```

### Routing key naming convention
- Department-level: `{department_id}._manager` → for dept's own LLM call (selecting worker)
- Worker-level: `{department_id}.{worker_id}` → must match key in `config/providers.yaml`
- Special: `chief_of_staff` (top-level decisions)

### Test routing
```python
# pytest tests/integration/test_routing.py
async def test_chain_fallback():
    # mock claude to fail → assert codex called instead
    ...
```

---

## 9. Testing Strategy

### Cấu trúc tests
```
tests/
├── unit/                    # Fast, no external deps
│   ├── test_config_loader.py
│   ├── test_provider_router.py  (with mocks)
│   ├── test_security.py
│   └── ...
├── integration/             # Real services, có thể chậm
│   ├── test_postgres_models.py
│   ├── test_claude_provider.py  (cần ANTHROPIC_API_KEY)
│   ├── test_ollama_provider.py  (cần Tailscale)
│   └── test_full_flow.py
└── fixtures/
    └── sample_tasks.yaml
```

### Run tests
```bash
# Tất cả
pytest

# Chỉ unit (nhanh)
pytest tests/unit/

# Skip integration nếu không có API keys
pytest -m "not integration"

# Coverage
pytest --cov=pio_lab --cov-report=html
```

### Mock pattern cho LLM
```python
from unittest.mock import AsyncMock, patch

async def test_worker_with_mocked_llm():
    mock_response = {
        "content": [{"type": "text", "text": "Mocked answer"}],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    with patch("pio_lab.providers.router.ProviderRouter.call",
               new=AsyncMock(return_value=mock_response)):
        worker = GenericWorker(...)
        result = await worker.run({"input": "test"}, {})
        assert "Mocked answer" in result["output"]
```

### Smoke test khi finish 1 milestone
Tạo `scripts/smoke_test.py` chạy:
1. Connect Postgres
2. Call provider router với 1 simple prompt
3. Write 1 note vào vault
4. Check tất cả không error

---

## 10. Workflow Per Session

### Đầu mỗi session
1. **Đọc `PROGRESS.md`** — biết lần trước stop ở đâu
2. **Đọc `CODEX_HANDOFF.md`** (file này) — refresh context
3. **Check git log** — xem recent commits: `git log --oneline -10`
4. **Run tests** — verify không có regression: `pytest tests/unit/`
5. **Start tiếp milestone** đang dở hoặc next milestone

### Trong session
1. Pick **1 milestone**
2. Pick **1 acceptance criterion** trong milestone đó
3. **Code** — implement minimal để pass criterion
4. **Test** — viết test ngay (TDD when possible)
5. **Verify** — run test, manual smoke
6. **Repeat** cho các criteria khác trong milestone

### Cuối milestone
1. **All acceptance criteria pass**
2. **Update `PROGRESS.md`** — mark milestone done + ghi note
3. **Run full test suite** — `pytest`
4. **Commit:** `git commit -m "M{N}: {description}"`
5. **Đánh giá:** có cần đổi gì cho milestone tiếp không? — note vào PROGRESS.md

### Khi gặp ambiguity
- KHÔNG đoán mò
- Note vào `PROGRESS.md` mục "Questions for Sếp Linh"
- Implement cách bạn nghĩ là tốt nhất, mark `TODO: confirm with owner`
- Tiếp tục — đừng block

---

## 11. Common Pitfalls

### ⚠️ Pitfall 1: Quên `provider_routing_key` không khớp

Worker config:
```yaml
# config/departments/coder/workers/frontend.yaml
provider_routing_key: coder.frontend
```

PHẢI có entry tương ứng trong `config/providers.yaml`:
```yaml
routing_rules:
  coder.frontend:
    - { provider: gemini, model: gemini-2.0-pro }
```

Nếu không match → router fall back về `default_chain` (có thể không phù hợp).

### ⚠️ Pitfall 2: Đặt blocking call trong async function

```python
# ❌ BAD
async def fetch():
    response = requests.get(url)  # BLOCKS event loop!
    return response.json()

# ✅ GOOD
async def fetch():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return response.json()
```

### ⚠️ Pitfall 3: Ollama tool calling không support đầy đủ

`gpt-oss-20b` có thể không return tool_use đúng format.
→ Test trước, fallback `qwen2.5-coder:32b` cho tool-heavy task.
→ Hoặc strip tools khỏi messages khi gọi Ollama, parse output text manually.

### ⚠️ Pitfall 4: Telegram message > 4096 chars

Communicator cần chunk message:
```python
def chunk_telegram(text: str, limit: int = 4000) -> list[str]:
    # Split tại boundary tự nhiên (newline, paragraph)
    ...
```

### ⚠️ Pitfall 5: LangGraph state mutation

LangGraph state immutable! Mỗi node TRẢ VỀ dict mới, không mutate state in-place.

```python
# ❌ BAD
async def my_node(state):
    state["plan"].append(new_step)  # mutates!
    return state

# ✅ GOOD
async def my_node(state):
    return {"plan": state.get("plan", []) + [new_step]}
```

### ⚠️ Pitfall 6: Postgres async session leak

Always use context manager:
```python
async with async_session() as session:
    async with session.begin():
        # operations
        ...
# auto commit + close
```

### ⚠️ Pitfall 7: Đừng quên security_enforcer.mask_secrets_in_output()

Trước khi gửi LLM output về user qua Communicator, PHẢI mask secrets:
```python
formatted = self._format_for_channel(channel, text)
formatted = security.mask_secrets_in_output(formatted)
await router.route_outbound(channel, user_id, formatted)
```

### ⚠️ Pitfall 8: Tailscale Ollama connection timeout

Ollama qua Tailscale có thể slow first request.
- Set `httpx` timeout = 60s (không default 5s)
- Health check Ollama trong heartbeat — nếu down, mark provider unavailable

---

## 12. Definition of Done — MVP Phase 1

> **📖 Đọc trước:** `docs/EXAMPLES.md` — 10 scenarios end-to-end với expected plan, departments involved, tools, output, edge cases, acceptance criteria từng scenario.
> **MVP Done = 10 scenarios pass.**

### Demo end-to-end phải work:

**Scenario A — Telegram Research:**
1. Sếp Linh gõ Telegram bot: *"Tìm 3 paper mới về adaptive optics, tóm tắt"*
2. Hệ thống reply: *"Đã nhận, đang xử lý..."* (within 2s)
3. Chief of Staff plan: dispatch Research dept
4. Research/Optics worker: web search + paper fetch + summarize
5. QA worker: verify (factual + format)
6. Knowledge Librarian: archive vào Postgres + write `vault/tasks/.../note.md`
7. Communicator: format markdown cho Telegram, chunk if needed
8. Sếp Linh nhận reply (within 60s tổng cộng)
9. Mở Obsidian Vault: thấy note mới

**Scenario B — Web UI Code Task:**
1. Mở `http://localhost:8000/`
2. Login với `WEB_UI_ADMIN_PASSWORD`
3. Chat: *"Viết FastAPI endpoint POST /users với validation"*
4. CoS dispatch CODER/Backend
5. Backend worker: viết file → chạy test → trả file diff
6. Web UI hiển thị code block với syntax highlight
7. Mở `/admin/tasks` thấy task vừa rồi với status DONE

**Scenario C — Add Department from UI:**
1. Mở `/admin/org`
2. Click "+ Phòng ban" → fill form (id=sales, name=SALES, vi=Bán hàng)
3. Click Save
4. Backend: tạo `config/departments/sales/department.yaml` + reload registry
5. UI refresh → thấy phòng ban Sales mới
6. Test: gõ "Sales pitch cho sản phẩm X" → CoS dispatch Sales (sau khi add 1 worker)

### Tech checklist
- [ ] Tất cả 12 milestones hoàn thành
- [ ] Test coverage ≥ 60% cho `pio_lab/core` và `pio_lab/providers`
- [ ] No `# TODO Phase 1` markers còn lại trong code (chỉ TODO Phase 2+ OK)
- [ ] `pytest` xanh
- [ ] `ruff check pio_lab/` không error
- [ ] `mypy pio_lab/` không error nghiêm trọng (warnings OK)
- [ ] Docker compose up + setup.py + init_db.py + start_dev.sh chạy được clean
- [ ] README.md updated với screenshots (nếu có thể)

### Không phải Definition of Done
- KHÔNG cần Distillation training (Phase 2+)
- KHÔNG cần Portable Export module (workaround OK)
- KHÔNG cần WhatsApp / iMessage
- KHÔNG cần Solid Edge full integration
- KHÔNG cần Security Policy Engine UI

---

## 📞 Khi cần hỏi Sếp Linh

Trong `PROGRESS.md` có section **"Questions for Sếp Linh"**. Note câu hỏi vào đó. Sếp Linh sẽ check session sau và trả lời.

Câu hỏi phải kèm:
- Context: bạn đang làm gì
- Options: 2-3 cách bạn nghĩ ra
- Recommendation: bạn nghiêng về option nào, tại sao

---

## 🚀 Bắt đầu — Reading Order

### Session đầu tiên (1-2 giờ đọc, đầu tư xứng đáng):

1. **CODEX_HANDOFF.md** (file này) — toàn bộ context
2. **Pio_lab_Architecture.png** — visual diagram, hiểu 7 lớp + cross-cutting
3. **STRUCTURE.md** — bản đồ 162 files, biết file ở đâu
4. **README.md** — quick overview
5. **docs/7_layers.md** — chi tiết từng layer
6. **docs/PROVIDER_API_REFERENCE.md** — sample API cho 5 providers (sẽ cần ở M3-M4)
7. **docs/EXAMPLES.md** — 10 scenarios test (sẽ cần sau mỗi milestone)
8. **docs/adding_departments.md** — extensibility pattern
9. **PROGRESS.md** — biết progress hiện tại

### Setup môi trường (15 phút):

```bash
cd <project_root>
git status                       # check clean

python scripts/setup.py          # tạo .env nếu chưa
# Edit .env với API keys thật (ANTHROPIC_API_KEY tối thiểu cho M3)

docker-compose up -d             # start Postgres
# Note: init_db.py sẽ chạy được sau khi finish M1

pip install -e ".[dev]"          # install Python deps
```

### Bắt đầu code:

```bash
cat PROGRESS.md                  # xem milestone đang ở đâu

# Đọc section M{N} trong CODEX_HANDOFF.md → implement → test → commit
# Sau mỗi milestone: update PROGRESS.md, run smoke test (docs/EXAMPLES.md scenario tương ứng)
```

### Workflow lặp:

```
[Read PROGRESS.md] → [Pick milestone] → [Read milestone section in handoff]
       ↓
[Implement files] → [Write tests] → [Run pytest]
       ↓
[Run scenario from EXAMPLES.md] → [Pass? commit] → [Update PROGRESS.md]
       ↓
[Repeat]
```

---

**Chúc bạn (Codex) implement vui vẻ. Sếp Linh sẽ review từng milestone qua PROGRESS.md.**

---

## 📦 Handoff Package Manifest

Package bao gồm các tài liệu sau (Sếp Linh đảm bảo có sẵn):

| File | Size | Mục đích |
|---|---|---|
| `CODEX_HANDOFF.md` | This file | Master document |
| `STRUCTURE.md` | ~9KB | Folder structure map |
| `PROGRESS.md` | ~3KB | Progress tracker (Codex updates) |
| `Pio_lab_Architecture.png` | ~630KB | Architecture v3 visual |
| `Pio_lab_Architecture.html` | ~22KB | Interactive architecture diagram |
| `docs/Pio_lab_Architecture.svg` | ~20KB | Source SVG (editable) |
| `docs/PROVIDER_API_REFERENCE.md` | ~19KB | 5 providers API specs |
| `docs/EXAMPLES.md` | ~16KB | 10 test scenarios |
| `docs/7_layers.md` | ~3KB | Layer details |
| `docs/architecture.md` | ~1KB | Quick arch summary |
| `docs/adding_departments.md` | ~2KB | Extensibility guide |
| `README.md` | ~3KB | Project README |
| `Whitebook Pio_lab.docx` | ~7MB | Original requirements doc |
| `ORG_pio_lab_final.png` | ~6MB | User's ORG chart |
| `pyproject.toml` | ~2KB | Python deps |
| `docker-compose.yml` | ~1KB | Postgres setup |
| `.env.example` | ~2KB | Env vars template |
| `config/*.yaml` (4 files) | ~10KB | Main configs |
| `config/departments/**/*.yaml` (15 files) | ~14KB | Dynamic registry |
| `pio_lab/**/*.py` (113 files) | ~80KB | Skeleton code |
| `vault/{USER,AGENTS,SOUL}.md` | ~5KB | Bot personality |
| `scripts/*` (6 files) | ~5KB | Helper scripts |

**Total handoff package:** ~14MB (chủ yếu là 2 PNG lớn — có thể skip nếu cần gọn).

---

*Tài liệu này được tạo bởi Claude Sonnet 4.7 vào ngày 2026-05-04 để handoff cho GPT Codex tiếp tục phát triển dự án Pio_lab Phase 1 MVP.*
*Companion documents: PROVIDER_API_REFERENCE.md, EXAMPLES.md, Pio_lab_Architecture.png/svg.*
