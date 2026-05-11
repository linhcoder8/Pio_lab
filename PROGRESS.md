# 📊 Pio_lab — Progress Tracker

> Codex tự cập nhật file này sau mỗi milestone. Sếp Linh đọc để biết tiến độ.

**Phase hiện tại:** MVP Phase 1
**Bắt đầu:** 2026-05-04
**Last update:** 2026-05-11 (Command Center UI)

---

## ✅ Milestones

| # | Milestone | Status | Note |
|---|---|---|---|
| M0 | Foundation | ✅ Done | Completed as prerequisite for M1 |
| M1 | Memory · Postgres | ✅ Done | Unit + live Postgres smoke verified |
| M2 | Memory · Obsidian | ✅ Done | Unit verified |
| M3 | Provider Router (Claude) | ✅ Done | Real provider smoke deferred by owner |
| M4 | Provider Router · 4 còn lại | ✅ Done | Adapter infrastructure unit verified; real providers deferred |
| M5 | Security Enforcer | ✅ Done | Unit verified |
| M6 | Channel · Web (test bed) | ✅ Done | Verified via FastAPI server; bash unavailable in current Windows shell |
| M7 | Chief of Staff (LangGraph) | ✅ Done | LangGraph run/replan/approval verified |
| M8 | Department + Worker base | ✅ Done | Registry + GenericDepartment/Worker verified |
| M9 | 5 Departments cụ thể | ✅ Done | Concrete workers + CoS dispatch verified |
| M10 | Knowledge Librarian | ✅ Done | Postgres + Obsidian archive/search verified |
| M11 | Channels còn lại + Console UI | ✅ Done | Telegram/Discord/Zalo adapters + admin UI verified |

**Status legend:** ⏸️ Pending · 🚧 In progress · ✅ Done · ⚠️ Blocked

---

## 📝 Detailed log

### 2026-05-11 — Command Center UI from Whitebook
- ✅ Read `E:\PIO_lab\Whitebook Pio_lab.md`, architecture reference, ORG diagram, and request-flow diagram.
- ✅ Rebuilt `/` as Pio_lab Command Center with tabs: Command, ORG, Architecture, Request Flow, Providers, and Memory.
- ✅ Command tab keeps direct chat through `/api/chat` and quick prompts for research/content/report flows.
- ✅ ORG tab renders live DepartmentRegistry data and displays `ORG_pio_lab_final.png`.
- ✅ Architecture and Request Flow tabs serve the provided reference assets from `E:\PIO_lab`.
- ✅ Providers tab lists configured providers/accounts/models/routing rules and can run direct provider tests via `/api/providers/test`.
- ✅ Memory tab shows recent archived tasks and provider traces when Postgres is available.
- 🧪 Tests: full `python -m pytest -q` = 74 pass, 3 skipped; full `python -m ruff check .` pass.
- 🧪 Local server verified on `http://127.0.0.1:8001`: `/health`, `/login`, and reference image route load successfully.
- ⏭️ Next: extend provider management from read/test UI to editable account/model/routing forms.

### 2026-05-10 — Telegram live smoke prepared
- ✅ `.env` has `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USERS` configured.
- ✅ `python scripts/smoke_telegram.py` validates Telegram `getMe` successfully for `@Chief_pio_bot` without printing the token.
- ✅ Added `scripts/smoke_telegram.py` for repeatable token/send smoke and `scripts/start_telegram_bot.py` for local polling mode.
- ✅ Telegram whitelist rejection now returns the sender's numeric user id; `/whoami` is registered as a real Telegram command and works before whitelist approval.
- ✅ Telegram live full-flow works from allowed account: inbound Telegram → Chief of Staff → department/QA → reply.
- ✅ Live archive verified in Postgres `tasks`: 4 rows with `channel=telegram`, `status=done`, latest IDs include `c2801cb1-9470-477b-b069-9fa5741eafda`.
- ✅ Live archive verified in Obsidian vault under `vault/tasks/2026-05-10/*.md`.
- ✅ PR #2 merged to `main`; local `main` is up to date at merge commit `eb081d2`.
- ✅ Real provider smoke through Codex OAuth passes: `RUN_REAL_PROVIDER_TESTS=1 python -m pytest tests/integration/test_codex_oauth_provider.py -v`.
- ✅ Added opt-in live department mode: `DEPARTMENT_WORKER_MODE=provider` makes text workers call ProviderRouter; `PROVIDER_ROUTING_PROFILE=codex_oauth` promotes selected text paths to Codex OAuth.
- ✅ Live provider-backed department smoke passes: `RUN_REAL_PROVIDER_TESTS=1 python -m pytest tests/integration/test_live_provider_departments.py -v` verifies `RESEARCH.optics` output comes from Codex OAuth.
- ✅ Fixed Windows Codex CLI resolution: Codex OAuth adapter now resolves `codex.cmd`/`codex.exe` instead of assuming bare `codex` is executable from Python subprocess.
- ✅ Fixed Codex OAuth prompt leakage: provider-backed Telegram/department responses now answer the user directly instead of exposing adapter/runtime wording.
- ✅ Live prompt smoke verified: `Research lens design and summarize with citations` returns a lens-design answer with source hints and no `provider adapter`/`codex cli`/`workspace` terms.
- ✅ Fixed Telegram no-reply path when Codex CLI fails during web search: Codex OAuth adapter now disables CLI web search for this bridge, uses the output file when available, and passes `stdin=DEVNULL`.
- ✅ ChannelRouter now catches backend exceptions and sends a controlled Telegram-visible error instead of letting `python-telegram-bot` drop the reply.
- ✅ Research/content provider mode now falls back to deterministic workers if all provider targets fail.
- ✅ Live research/optics provider path verified again: `provider=codex` returns a lens-design summary without web-search failure.
- ✅ `.env.example` keeps Telegram values blank and includes `TELEGRAM_TEST_CHAT_ID` placeholder; real secrets stay in `.env` only.
- 🧪 Tests: full `python -m pytest -q` = 73 pass, 3 skipped; full `python -m ruff check .` pass.
- ⏭️ Next: restart Telegram bot with `.env` live mode, then resend the research/content task and confirm the Telegram reply is user-facing.

### 2026-05-10 — MVP hardening: full-flow integration tests
- ✅ Replaced placeholder `tests/integration/test_full_flow.py` with real end-to-end coverage.
- ✅ Research flow now verifies Chief of Staff → RESEARCH.optics → QA → Knowledge Librarian archive → Obsidian note → librarian search → lifecycle trace linked to archived task.
- ✅ QA replan flow now verifies first QA `NEEDS_FIX`, second run `PASS`, and only the final passing output is archived.
- ✅ Verified there are no remaining `TODO Phase 1` markers in `pio_lab`, `tests`, or `scripts`.
- 🧪 Tests: `python -m pytest tests/integration/test_full_flow.py -v` = 2 pass; full `python -m pytest -q` = 66 pass, 2 skipped; full `python -m ruff check .` pass.
- ⏭️ Next: live external-channel smoke when Telegram/Discord/Zalo credentials and webhook URLs are configured.

### 2026-05-10 — Milestone M11 done
- ✅ Added shared `ChannelRouter` for external channel text → security → Chief of Staff → formatted/masked reply.
- ✅ `TelegramAdapter` supports whitelist, `/start`, `/help`, `/status`, chunked replies, and full CoS routing.
- ✅ `DiscordAdapter` supports DM/slash-style prompts, optional whitelist, and full CoS routing.
- ✅ `ZaloAdapter` supports OA webhook payload parsing and outbound OA message sending.
- ✅ `/admin`, `/admin/tasks`, and `/admin/org` are available behind the existing web login session.
- ✅ Admin API can add a department backed by YAML config and reload/dispatch it through `DepartmentRegistry`.
- 📝 Decisions: M11 verifies channel adapters with unit-level fake CoS/router because live Telegram/Discord/Zalo smoke requires real bot tokens, public webhook URLs, and owner account IDs.
- 🧪 Tests: focused `tests/unit/test_m11_channels_console.py` = 6 pass; full `python -m pytest -q` = 66 pass, 2 skipped; full `python -m ruff check .` pass.
- ⏭️ Next: MVP hardening / live external-channel smoke

### 2026-05-10 — Milestone M10 done
- ✅ `KnowledgeLibrarian.run(state)` archives only completed QA-passed tasks.
- ✅ `PostgresTaskStore` inserts full task request, plan, output, and status into the existing `tasks` table.
- ✅ `ObsidianTaskStore` writes canonical notes under `vault/tasks/YYYY-MM-DD/<task_id>.md`.
- ✅ `KnowledgeLibrarian.search("optics lens")` returns relevant archived task rows.
- ✅ Runtime `get_chief_of_staff()` now wires the librarian so completed QA-passed web/runtime tasks archive automatically.
- 📝 Decisions: direct `ChiefOfStaff(...)` remains librarian opt-in for tests/custom runs; the runtime singleton enables it by default to avoid accidental DB/vault writes in isolated unit tests.
- 🧪 Tests: focused `tests/unit/test_librarian.py` = 4 pass; full `python -m pytest -q` = 60 pass, 2 skipped; full `python -m ruff check .` pass.
- ⏭️ Next: M11

### 2026-05-10 — Milestone M9 done
- ✅ `CODER.backend` writes one Python file plus a pytest file, then verifies the artifact with pytest.
- ✅ `RESEARCH.optics` returns a lens-design summary with stable citations.
- ✅ `MEDIA.content` generates a blog article with at least 500 words.
- ✅ `REPORT.slide_word_web` creates a real `.pptx` artifact.
- ✅ `QA.qa_reviewer` returns PASS/NEEDS_FIX as JSON and surfaces issues.
- ✅ Chief of Staff dispatch now routes planned department work through `DepartmentRegistry`, then runs QA and reports the non-QA output.
- 📝 Decisions: M9 concrete workers are deterministic/offline so M3/M4 real provider credentials can remain deferred; provider-backed workers can replace or extend these classes later.
- 🧪 Tests: focused M9/registry suite = 9 pass; full `python -m pytest -q` = 56 pass, 2 skipped; full `python -m ruff check .` pass.
- ⏭️ Next: M10

### 2026-05-10 — Milestone M8 done
- ✅ `DepartmentRegistry.load_all()` loads 5 active departments and 9 workers from `config/departments/_registry.yaml`.
- ✅ `DepartmentRegistry.add_department(...)` supports runtime in-memory department registration.
- ✅ `GenericDepartment.run(task)` selects the expected worker, including CODER backend for API/backend tasks.
- ✅ `GenericWorker.run(task)` completes ProviderRouter calls and a minimal tool-use loop via injected tool executor.
- ✅ Worker provider calls log traces through ProviderRouter/TraceLogger.
- 📝 Decisions: M8 uses deterministic worker-selection heuristics and a pluggable tool executor; M9 will replace this with concrete department behavior and real skills.
- 🧪 Tests: focused M8 suite = 5 pass; full `python -m pytest -v` = 50 pass, 2 skipped; full `ruff check pio_lab tests` pass.
- ⏭️ Next: M9

### 2026-05-10 — Codex OAuth provider option added
- ✅ M3/M4 provider credentials now support `credential_mode: codex_oauth`.
- ✅ `config/providers.yaml` includes `codex_oauth`, so Codex can be selected when `OPENAI_API_KEY` is absent but `codex login` exists.
- ✅ Codex OAuth uses local Codex CLI transport instead of OpenAI SDK because the cached OAuth token does not expose standard OpenAI API scopes.
- ✅ Current machine verified: `codex login status` is logged in with ChatGPT; router selects `codex_oauth` for `codex/o1-preview`.
- ✅ Real smoke: `RUN_REAL_PROVIDER_TESTS=1 python -m pytest tests/integration/test_codex_oauth_provider.py -v` pass.
- ✅ M7 smoke with `ChiefOfStaff().run({"input": "hello"})` completed through ProviderRouter with `provider=codex`, `model=o1-preview`.
- 🧪 Tests: full `python -m pytest -v` = 47 pass, 2 skipped; full `ruff check pio_lab tests` pass.

### 2026-05-10 — Milestone M7 done
- ✅ `ChiefOfStaff.run({"input": "hello"})` completes a LangGraph execution.
- ✅ Chief of Staff lifecycle trace is logged into Postgres `traces`.
- ✅ Replan loop triggers on mocked QA `NEEDS_FIX`, then retries and completes after QA `PASS`.
- ✅ Human approval pauses the graph with LangGraph interrupt and resumes after approval.
- ✅ Web chat now routes through Chief of Staff instead of M6 echo.
- 📝 Decisions: M7 uses a deterministic local fallback when no provider account is available, so the graph and Web test bed remain usable while real provider keys are deferred.
- 🧪 Tests: 10 pass for focused M7/Web suite; full `tests/unit/` = 43 pass at M7 commit; full `ruff check pio_lab tests` pass.
- 🧪 Smoke: default `ChiefOfStaff().run({"input": "hello"})` returned `done`; Postgres trace query verified `chief_of_staff/internal/langgraph`.
- ⏭️ Next: M8

### 2026-05-10 — M1 live Postgres smoke unblocked
- ✅ Docker Desktop daemon is running.
- ✅ `docker compose up -d postgres` starts `pio_lab_postgres` and container health is `healthy`.
- ✅ `python scripts/init_db.py` initializes the Postgres schema successfully.
- ✅ Verified tables in Postgres: `conversations`, `provider_accounts`, `providers`, `tasks`, `traces`.
- 📝 Decisions: `scripts/init_db.py` now inserts the repo root into `sys.path` so the documented command imports this checkout even if another editable `pio_lab` install exists on the machine.
- ⚠️ Non-blocking note: Docker Compose warns that the top-level `version` field is obsolete.

### 2026-05-05 — Milestone M6 done
- ✅ FastAPI app boots from `pio_lab.main:app`.
- ✅ `/` serves authenticated web chat and `/login` handles password auth with signed cookie session.
- ✅ `POST /api/chat` returns dummy echo response and masks secrets before response.
- ✅ `WS /ws/chat` returns dummy echo response for authenticated sessions.
- 📝 Decisions: M6 uses a minimal server-rendered HTML chat page; M7 will replace echo with Chief of Staff routing.
- 🧪 Tests: 6 pass for `tests/unit/test_web_channel.py`; full `pytest -v` = 41 pass, 1 skip; full `ruff check pio_lab tests` pass.
- ⚠️ Environment note: `bash scripts/start_dev.sh` could not be executed because Windows `bash.exe` fails with `The system cannot find the file specified`; server was verified with `python -m uvicorn pio_lab.main:app --host 127.0.0.1 --port 8000`.
- ⏭️ Next: M7

### 2026-05-05 — Milestone M5 done
- ✅ File access outside project root is rejected.
- ✅ API key-like output is masked before user/log exposure.
- ✅ Sensitive action `send_email` triggers approval.
- ✅ Crypto-wallet phrase `seed phrase` is blocked.
- 📝 Decisions: Security enforcer returns booleans for check methods and provides `require_*` helpers that raise `SecurityError`.
- 🧪 Tests: 6 pass for `tests/unit/test_security.py`; full `pytest -v` = 35 pass, 1 skip; full `ruff check pio_lab tests` pass.
- ⏭️ Next: M6

### 2026-05-05 — Milestone M4 done
- ✅ Codex/OpenAI, Gemini, DeepSeek, and Ollama adapter infrastructure implemented.
- ✅ Each M4 adapter has a mocked SDK smoke test with normalized response output.
- ✅ Fallback chain verified: Claude quota failure → Codex response.
- ✅ Status tracker reflects failed/end states in fallback tests.
- 📝 Decisions: Real provider/API smoke is deferred until after the app is complete per owner direction.
- 🧪 Tests: 10 pass for provider router/adapters; full provider-related ruff pass.
- ⏭️ Next: M5

### 2026-05-05 — Milestone M3 done
- ✅ Router loads `config/providers.yaml` and resolves routing chains.
- ✅ Account pool registers Claude accounts and selects env-backed `claude_main` in tests.
- ✅ `router.call("research.optics", ...)` returns normalized Claude response with mocked adapter.
- ✅ Trace logging path verified with real `TraceLogger` and SQLAlchemy session.
- 📝 Decisions: Real provider/API smoke is deferred until after the app is complete per owner direction.
- 🧪 Tests: 6 pass for `tests/unit/test_provider_router.py`; 23 pass for `tests/unit/`; full `pytest -v` = 25 pass, 1 skip; ruff pass.
- ⏭️ Next: M4

### 2026-05-05 — Milestone M2 done
- ✅ `Vault.write/read/list_notes` implemented with safe relative paths under the vault root.
- ✅ `SoulMd`, `UserMd`, and `AgentsMd` get/set wrappers implemented.
- ✅ `AgentsMd.regenerate(registry)` writes `AGENTS.md` from mapping or object registry state.
- 📝 Decisions: Vault API is synchronous to match the milestone acceptance interface and keep local markdown operations simple.
- 🧪 Tests: 6 pass for `tests/unit/test_obsidian_vault.py`; 17 pass for current `tests/unit/`; ruff pass.
- ⏭️ Next: M3

### 2026-05-05 — Milestone M1 done
- ✅ `pio_lab/memory/postgres/models.py` has tasks, traces, conversations, providers, provider_accounts.
- ✅ `pio_lab/memory/postgres/database.py` provides async engine/session helpers.
- ✅ `TraceLogger.log()` inserts trace rows through an async session.
- ✅ `scripts/init_db.py` creates tables from SQLAlchemy metadata when Postgres is reachable.
- 📝 Decisions: Completed missing M0 utility foundation first because `pio_lab/` package was absent and M1 depends on M0.
- 🧪 Tests: 9 pass for focused M0/M1 suite; 11 pass for current `tests/unit/`; ruff pass.
- ⚠️ Live DB smoke: `docker-compose up -d postgres` failed because Docker daemon is not running.
- ⏭️ Next: M2

### 2026-05-05 — Milestone M0 done
- ✅ `pio_lab/utils/config_loader.py` implemented with cached YAML loading.
- ✅ `pio_lab/utils/env.py` implemented with Pydantic Settings and async Postgres DSN.
- ✅ `pio_lab/utils/logging.py` implemented for text and JSON loguru setup.
- 🧪 Tests: covered by `tests/unit/test_config_loader.py`.
- ⏭️ Next: M1

### 2026-05-04 — Folder Structure Complete
- ✅ 162 files, 60 folders đã tạo
- ✅ Skeleton classes + interfaces cho tất cả 7 layers
- ✅ Configs đầy đủ (5 phòng ban, 9 workers, 5 providers, security policy)
- ✅ Vault với USER.md, AGENTS.md, SOUL.md
- ✅ Helper scripts (setup, init_db, backup, add_department)
- ✅ CODEX_HANDOFF.md tạo xong → ready for Codex
- ⏭️ Next: Codex bắt đầu **M0 — Foundation**

---

## 🚀 Current milestone

**Đang ở:** MVP hardening / live smoke

### Acceptance criteria — M11
- [x] **M11.1 Telegram:** user gõ → reply (full flow via adapter test)
- [x] **M11.2 Discord:** slash/DM-style prompt → reply
- [x] **M11.3 Zalo:** OA webhook payload → reply + outbound sender implemented
- [x] **M11.4 UI:** `/admin/*` pages work, add dept qua UI/API, registry reload verified

---

## ❓ Questions for Sếp Linh

> Codex note câu hỏi cần sếp giải đáp vào đây. Format:
>
> **Q1 (timestamp):** Câu hỏi rõ ràng
>   - Context: ...
>   - Options:
>     - A: ...
>     - B: ...
>   - Recommendation: ...

(Hiện tại chưa có câu hỏi nào)

---

## 🔧 Decisions made (Codex tự note khi quyết định)

> Khi Codex tự quyết định implementation detail không có trong handoff, ghi vào đây.
> Format:
>
> **D1 (timestamp):** Quyết định gì
>   - Lý do: ...
>   - Trade-off: ...
>   - Có thể revisit?: yes/no

**D1 (2026-05-05):** Complete minimal M0 utility foundation before M1.
  - Lý do: `pio_lab/` package was absent on disk, while M1 depends on M0 utilities.
  - Trade-off: M1 commit includes M0 prerequisite files instead of being purely Postgres-only.
  - Có thể revisit?: no

**D2 (2026-05-05):** Use a synchronous API for Obsidian vault operations.
  - Lý do: M2 acceptance criteria call `vault.write/read/list_notes` directly, and local markdown operations are small.
  - Trade-off: No async file abstraction yet; can be revisited if vault writes become high-volume.
  - Có thể revisit?: yes

**D3 (2026-05-05):** M3 implements only Claude adapter and skips other configured providers.
  - Lý do: Handoff explicitly says Codex/Gemini/DeepSeek/Ollama are M4 scope.
  - Trade-off: Routing keys without Claude raise `ProviderUnavailableError` until M4.
  - Có thể revisit?: no

**D4 (2026-05-05):** Defer real provider/API smoke until after core app completion.
  - Lý do: Sếp Linh confirmed providers will be added after the app is complete.
  - Trade-off: M3/M4 acceptance is unit/mock verified now; real provider validation remains a later integration task.
  - Có thể revisit?: yes

**D5 (2026-05-05):** Security checks expose both boolean and raising APIs.
  - Lý do: Boolean checks fit hooks, while `require_*` helpers make hard-block paths explicit.
  - Trade-off: Callers must choose the appropriate style for their control flow.
  - Có thể revisit?: yes

**D6 (2026-05-05):** M6 uses signed cookie auth without server-side session storage.
  - Lý do: Single-user web test bed only needs lightweight auth before M7 wires runtime state.
  - Trade-off: No session revocation list yet; `/logout` clears the browser cookie.
  - Có thể revisit?: yes

**D7 (2026-05-10):** M7 keeps a deterministic local fallback when provider accounts are unavailable.
  - Lý do: Sếp Linh đã defer provider thật đến sau khi app hoàn thành, nhưng M7/Web cần chạy được graph end-to-end ngay.
  - Trade-off: Fast-path answer can be placeholder until API keys are configured; all real LLM calls still go through ProviderRouter when credentials exist.
  - Có thể revisit?: yes

**D8 (2026-05-10):** Add Codex OAuth credential mode for M3/M4 provider routing.
  - Lý do: Sếp Linh muốn có option dùng `codex login`/ChatGPT OAuth thay vì chỉ nhập `OPENAI_API_KEY`.
  - Trade-off: API key vẫn là default khuyến nghị cho automation; OAuth cache chạy qua Codex CLI local, chậm hơn SDK và chưa có structured tool loop.
  - Có thể revisit?: yes

**D9 (2026-05-10):** M8 uses deterministic worker-selection heuristics and injected tool execution.
  - Lý do: M8 cần base Department/Worker chạy được trước khi M9 nối từng phòng ban và skill thật.
  - Trade-off: Worker selection chưa LLM-based; concrete departments can override or extend in M9.
  - Có thể revisit?: yes

**D10 (2026-05-10):** M9 concrete workers run deterministic/offline implementations first.
  - Lý do: Sếp Linh đã defer provider thật đến sau khi app hoàn thành, nhưng M9 cần chứng minh dispatch → artifact → QA end-to-end ngay.
  - Trade-off: Research/content/report output là baseline local; có thể nâng cấp từng worker sang provider/tool-backed flow sau khi M3/M4 credentials ổn định.
  - Có thể revisit?: yes

**D11 (2026-05-10):** Runtime singleton enables Knowledge Librarian, direct `ChiefOfStaff(...)` remains opt-in.
  - Lý do: Web/runtime path cần auto archive sau QA pass, nhưng unit/custom constructor không nên tự ghi DB/vault nếu caller chưa inject session/vault.
  - Trade-off: Code dùng `ChiefOfStaff(...)` trực tiếp phải truyền `librarian=KnowledgeLibrarian(...)` nếu muốn archive.
  - Có thể revisit?: yes

**D12 (2026-05-10):** Verify M11 external channels with fake CoS/router instead of live bot networks.
  - Lý do: Live Telegram/Discord/Zalo smoke cần token thật, public webhook URL/ngrok, và owner account IDs; unit adapter tests vẫn chứng minh inbound → CoS → outbound formatting.
  - Trade-off: Cần một lượt live smoke riêng sau khi Sếp Linh cấu hình token/webhook thật.
  - Có thể revisit?: yes

**D13 (2026-05-10):** Keep Codex OAuth prompts user-facing and hide local runtime details.
  - Lý do: Telegram live response exposed adapter/runtime wording instead of answering the user's research task.
  - Trade-off: Codex OAuth remains a CLI-backed bridge and cannot use the structured tool loop yet, so source/tool limitations may still be mentioned when relevant.
  - Có thể revisit?: yes

**D14 (2026-05-10):** Disable Codex CLI web search inside the OAuth provider bridge.
  - Lý do: Telegram live run failed while Codex CLI was performing web search, causing no reply to be sent.
  - Trade-off: Provider-backed department answers use model knowledge/source hints unless a later structured tool loop is implemented.
  - Có thể revisit?: yes

---

## ⚠️ Blockers

> Khi gặp blocker nghiêm trọng (cần Sếp Linh can thiệp).
>
> Format:
>
> **B1 (timestamp):** Tên blocker
>   - Tại milestone: ...
>   - Mô tả: ...
>   - Cần gì để unblock: ...

**B1 (2026-05-05, resolved 2026-05-10):** Docker daemon unavailable for live Postgres smoke.
  - Tại milestone: M1
  - Mô tả: `docker-compose up -d postgres` cannot connect to `npipe:////./pipe/docker_engine`.
  - Resolution: Docker Desktop started, `pio_lab_postgres` is healthy, `python scripts/init_db.py` completed, and Postgres tables were verified.

---

## 📈 Metrics

- **Tổng số commits:** 12 implementation commits after M11 commit
- **Test coverage hiện tại:** Not measured yet; unit + local integration suite passing
- **Lines of code (impl):** M0-M11 implementation added
- **API keys configured:** Telegram bot token configured in `.env`; Codex OAuth logged in and selected by `.env` live routing profile; provider API keys TBD
- **TODO Phase 1 markers:** 0 in `pio_lab`, `tests`, `scripts`

---

*Cập nhật cuối: 2026-05-10 bởi Codex.*
