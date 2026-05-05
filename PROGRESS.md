# 📊 Pio_lab — Progress Tracker

> Codex tự cập nhật file này sau mỗi milestone. Sếp Linh đọc để biết tiến độ.

**Phase hiện tại:** MVP Phase 1
**Bắt đầu:** 2026-05-04
**Last update:** 2026-05-05 (M5 Security Enforcer unit verified)

---

## ✅ Milestones

| # | Milestone | Status | Note |
|---|---|---|---|
| M0 | Foundation | ✅ Done | Completed as prerequisite for M1 |
| M1 | Memory · Postgres | ✅ Done | Unit verified; Docker daemon unavailable for live smoke |
| M2 | Memory · Obsidian | ✅ Done | Unit verified |
| M3 | Provider Router (Claude) | ✅ Done | Real provider smoke deferred by owner |
| M4 | Provider Router · 4 còn lại | ✅ Done | Adapter infrastructure unit verified; real providers deferred |
| M5 | Security Enforcer | ✅ Done | Unit verified |
| M6 | Channel · Web (test bed) | ⏸️ Pending | Next |
| M7 | Chief of Staff (LangGraph) | ⏸️ Pending | |
| M8 | Department + Worker base | ⏸️ Pending | |
| M9 | 5 Departments cụ thể | ⏸️ Pending | |
| M10 | Knowledge Librarian | ⏸️ Pending | |
| M11 | Channels còn lại + Console UI | ⏸️ Pending | |

**Status legend:** ⏸️ Pending · 🚧 In progress · ✅ Done · ⚠️ Blocked

---

## 📝 Detailed log

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

**Đang ở:** M6 — next

### Acceptance criteria — M6
- [ ] `bash scripts/start_dev.sh` start server
- [ ] `http://localhost:8000/` thấy chat page
- [ ] Gõ message → echo response (M7 sẽ wire CoS)
- [ ] Auth với `WEB_UI_ADMIN_PASSWORD`

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

**B1 (2026-05-05):** Docker daemon unavailable for live Postgres smoke.
  - Tại milestone: M1
  - Mô tả: `docker-compose up -d postgres` cannot connect to `npipe:////./pipe/docker_engine`.
  - Cần gì để unblock: Start Docker Desktop / Docker daemon, then rerun `docker-compose up -d postgres` and `python scripts/init_db.py`.

---

## 📈 Metrics

- **Tổng số commits:** 5 milestone commits after M5 commit
- **Test coverage hiện tại:** Not measured yet; focused unit suite passing
- **Lines of code (impl):** M0-M5 implementation added
- **API keys configured:** TBD (Sếp Linh điền `.env`)

---

*Cập nhật cuối: 2026-05-05 bởi Codex.*
