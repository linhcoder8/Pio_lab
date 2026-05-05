# 📋 Milestones Quick Reference

> Cheatsheet 1 trang cho 12 milestones. Đọc nhanh khi cần. Chi tiết đầy đủ: `CODEX_HANDOFF.md` section 6.

---

## 🗺️ Dependency Graph

```
M0 (Foundation)
 ├─→ M1 (Postgres)  ─┐
 ├─→ M2 (Obsidian)  ─┤
 ├─→ M5 (Security)  ─┤
 └─→ M3 (Provider Claude)
       └─→ M4 (Provider 4 còn lại)
              ↓
M6 (Web Channel) ←────┤
              ↓
       M7 (Chief of Staff) ★ critical path
              ↓
       M8 (Dept + Worker base)
              ↓
       M9 (5 Departments) ←─┐
              ↓             │
       M10 (Librarian) ←────┘
              ↓
       M11 (Channels + Console UI)
              ↓
            DONE 🎉
```

**Có thể parallel:** M1 ∥ M2 ∥ M5 ∥ (M3→M4) ∥ M6
**Phải tuần tự:** M3→M4, M7→M8→M9→M10, M11.x sau M9

---

## 📊 Bảng tổng hợp 12 Milestones

| # | Tên | Effort | Files chính | Depends |
|---|---|---|---|---|
| **M0** | Foundation | XS | `pio_lab/utils/{config_loader,env,logging}.py` | - |
| **M1** | Memory · Postgres | S | `pio_lab/memory/postgres/{models,traces,database}.py` + Alembic | M0 |
| **M2** | Memory · Obsidian | XS | `pio_lab/memory/obsidian/{vault,soul_md,user_md,agents_md}.py` | M0 |
| **M3** | Provider Router (Claude) | M | `pio_lab/providers/{router,account_pool,status_tracker,token_tracker,adapters/claude_adapter}.py` | M0 |
| **M4** | Provider · 4 còn lại | M | `pio_lab/providers/adapters/{codex,gemini,deepseek,ollama}_adapter.py` | M3 |
| **M5** | Security Enforcer | S | `pio_lab/security/{policy_loader,enforcer}.py` | M0 |
| **M6** | Channel · Web | S | `pio_lab/layer1_input/web_adapter.py`, `pio_lab/layer2_runtime/openclaw.py` | M0 |
| **M7** | Chief of Staff (LangGraph) | L | `pio_lab/layer3_chief_of_staff/{chief_of_staff,plan,dispatch,report,replan,human_approval}.py` | M3, M6 |
| **M8** | Dept + Worker base | M | `pio_lab/layer4_departments/base/{department_base,worker_base}.py`, `pio_lab/core/registry.py` | M3, M7 |
| **M9** | 5 Departments cụ thể | M | `pio_lab/layer4_departments/{report,coder,research,media,qa}/**` | M8 |
| **M10** | Knowledge Librarian | S | `pio_lab/layer5_librarian/*.py` | M1, M2, M9 |
| **M11** | Channels + Console UI | L | `pio_lab/layer1_input/{telegram,discord,zalo}_adapter.py`, `pio_lab/layer0_console/web/**` | M9 |

**Effort scale:** XS = 1-2h · S = 2-4h · M = 4-8h · L = 8-16h

---

## 🎯 Acceptance Criteria — Cô đọng

### M0 — Foundation
- [ ] `config_loader.load_pio_lab_config()` work + cache
- [ ] `env.Settings` validate POSTGRES_*, API keys
- [ ] `setup_logging()` work với JSON + text mode
- [ ] `pytest tests/unit/test_config_loader.py` pass

### M1 — Postgres
- [ ] `docker-compose up -d` start Postgres
- [ ] `python scripts/init_db.py` create tables
- [ ] `TraceLogger.log()` insert row
- [ ] Schema có: tasks, traces, conversations, provider_accounts

### M2 — Obsidian
- [ ] `vault.write/read/list_notes` work
- [ ] `SoulMd/UserMd/AgentsMd` get/set work
- [ ] `AgentsMd.regenerate(registry)` build từ registry

### M3 — Provider Router (Claude)
- [ ] Router load `config/providers.yaml` thành công
- [ ] Account pool có ít nhất 1 Claude account
- [ ] `await router.call("research.optics", [{"role":"user","content":"hi"}])` → response
- [ ] Trace logged vào Postgres

### M4 — 4 providers còn lại
- [ ] Mỗi adapter pass smoke test (1 message simple)
- [ ] Fallback chain: Claude fail → Codex
- [ ] Status tracker đúng (Running/End/Waiting)

### M5 — Security
- [ ] Open file ngoài project → reject
- [ ] Text "sk-abc..." → masked
- [ ] Action "send_email" → trigger approval flag
- [ ] Text "seed phrase" → blocked

### M6 — Web Channel
- [ ] `bash scripts/start_dev.sh` start server
- [ ] `http://localhost:8000/` thấy chat page
- [ ] Gõ message → echo response (M7 sẽ wire CoS)
- [ ] Auth với `WEB_UI_ADMIN_PASSWORD`

### M7 — Chief of Staff
- [ ] `chief_of_staff.run({"input":"hello"})` complete graph
- [ ] Trace logged
- [ ] Replan loop trigger được khi QA fail (mocked)
- [ ] Human approval pause + resume

### M8 — Dept + Worker base
- [ ] Registry load 5 phòng ban
- [ ] `dept.run(task)` chọn worker đúng
- [ ] `worker.run(task)` complete với LLM + tool use
- [ ] Trace logged

### M9 — 5 Departments cụ thể
- [ ] CODER.backend: write Python file, pytest pass
- [ ] RESEARCH.optics: search → summary với citation
- [ ] MEDIA.content: blog 500 từ
- [ ] REPORT.slide_word_web: tạo .pptx
- [ ] QA.qa_reviewer: trả PASS/NEEDS_FIX JSON
- [ ] End-to-end: user → CoS → 1 dept → QA → output

### M10 — Librarian
- [ ] Sau QA pass → librarian called
- [ ] `tasks` row inserted full plan + output
- [ ] Markdown note created `vault/tasks/`
- [ ] `librarian.search()` returns relevant past

### M11 — Channels + UI
- [ ] **M11.1 Telegram:** user gõ → reply (full flow)
- [ ] **M11.2 Discord:** slash + DM
- [ ] **M11.3 Zalo:** OA webhook + send
- [ ] **M11.4 UI:** `/admin/*` pages work, add dept qua UI

---

## 🔗 Provider Routing Keys (cheat)

```
chief_of_staff              → claude-opus-4-6 / o1-preview / gemini-2.0-pro
report.slide_word_web       → claude-sonnet-4-6 / gpt-4o
report.video_report         → claude-sonnet-4-6
coder.frontend              → gemini-2.0-pro / gpt-4o
coder.backend               → gpt-4o / deepseek-coder / qwen2.5-coder:32b
research.optics             → claude-opus-4-6 / gemini-2.0-pro
media.content               → claude-sonnet-4-6 / gemini-2.0-flash
media.image_maker           → gemini-2.0-pro (Imagen)
media.video_maker           → claude-sonnet-4-6
qa.qa_reviewer              → claude-opus-4-6 / gemini-2.0-pro
```

Full chain trong `config/providers.yaml::routing_rules`.

---

## 🧪 Quick test commands

```bash
# Test 1 milestone
pytest tests/unit/test_<milestone>.py -v

# Test all unit
pytest tests/unit/ -v

# Coverage
pytest --cov=pio_lab --cov-report=html

# Lint
ruff check pio_lab/
mypy pio_lab/

# Run smoke
python scripts/smoke_provider.py    # M3-M4 done
python scripts/smoke_e2e.py         # M7+ done

# Run server
bash scripts/start_dev.sh           # M6 done
```

---

## 🚦 Progress check command

```bash
# Last 10 commits
git log --oneline -10

# What's pending
grep -r "# TODO Phase 1" pio_lab/ | wc -l    # số TODO còn lại
```

---

## 🎬 10 Test Scenarios — sau mỗi milestone

| Sau milestone | Run scenarios | File |
|---|---|---|
| M3 | 1 | `docs/EXAMPLES.md` |
| M4 | 1 | |
| M6 | 1 (qua Web UI) | |
| M7 | 1 (qua CoS) | |
| M9 | 1, 2, 3, 4, 5, 6 | |
| M10 | 1-7 | |
| M11 | **All 10** (Definition of Done) | |

---

## 🆘 Stuck cheatsheet

| Symptom | Quick fix |
|---|---|
| Test fail timeout | Tăng timeout trong test, check Tailscale Ollama |
| Provider 401 | Verify `.env` API key, restart Cursor |
| Postgres connection refused | `docker-compose up -d`, check port 5432 free |
| Import circular | Refactor: move shared code to `pio_lab/core/` |
| LangGraph state not persisted | Add `checkpointer=MemorySaver()` |
| Tool use not parsed | Provider SDK version cũ → upgrade `pip install -U anthropic openai` |
| Cursor không đọc context | Explicit `@filename` thay vì auto |

---

## 📌 Critical reminder

- **M7 là critical path** — đừng song song M7 với gì khác
- **M3 phải pass smoke test thật** trước khi sang M4 (nếu Provider Router broken, mọi thứ về sau broken)
- **M9 — implement 1 department done hoàn toàn** trước khi sang department tiếp theo (đừng làm half-half)
- **Sau M9** phải end-to-end work với 1 dept + QA → mới sang M10

---

*Đọc full chi tiết: `@CODEX_HANDOFF.md`. File này chỉ là cheatsheet.*
