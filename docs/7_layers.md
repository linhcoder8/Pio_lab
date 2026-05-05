# 7 Layers Reference

## Layer 0 — Management Console
**Path:** `pio_lab/layer0_console/`
**Tech:** FastAPI + React/Vite + Tailwind
**Phase 1 features:**
- Bot Configuration (SOUL.md, USER.md)
- Provider Management (account/model/quota)
- Skills Toggle (RAG, Browser, Code…)
- ORG Diagram + Add Department/Worker
- Task History viewer

## Layer 1 — Input (Channel Adapters)
**Path:** `pio_lab/layer1_input/`
**Pattern:** Channel Adapter (mỗi channel implement `ChannelAdapter` interface)
**Phase 1 channels:** Telegram, Web, Discord, Zalo

## Layer 2 — OpenClaw Runtime
**Path:** `pio_lab/layer2_runtime/`
**Components:**
- `openclaw.py` — bootstrap & lifecycle
- `channel_router.py` — inbound/outbound routing
- `skill_engine.py` — skill registry + tool resolution
- `cron.py` — scheduled tasks
- `auth.py` — user authorization
- `heartbeat.py` — health checks

## Layer 3 — Chief of Staff (Orchestrator)
**Path:** `pio_lab/layer3_chief_of_staff/`
**Pattern:** LangGraph StateGraph
**Nodes:** plan → dispatch → report (+ replan loop, + human approval)

## Layer 4 — Departments (Dynamic Registry)
**Path:** `pio_lab/layer4_departments/` + config: `config/departments/`
**Pattern:** GenericDepartment + GenericWorker (config-driven)
**Phase 1 departments:** REPORT, CODER, RESEARCH, MEDIA, QA

## Layer 5 — Knowledge Librarian
**Path:** `pio_lab/layer5_librarian/`
**Storage:** PostgreSQL (structured) + Obsidian Vault (second brain)

## Layer 6 — Communicator (Output Adapter)
**Path:** `pio_lab/layer6_communicator/`
**Function:** Format kết quả theo channel + gửi qua channel router

## Cross-cutting Modules

### Provider Router (`pio_lab/providers/`)
5 providers + account pool + status tracker + token tracker.

### Memory (`pio_lab/memory/`)
- `postgres/` — SQLAlchemy models + migrations + trace logger
- `obsidian/` — Vault interface + USER.md / AGENTS.md / SOUL.md

### Security (`pio_lab/security/`)
Phase 1: default rules cứng từ `config/security_policy.yaml`.

### Distillation (`pio_lab/distillation/`)
Phase 1: trace logger only. Phase 2+: trainer.

### Export (`pio_lab/export/`)
Phase 1: workaround `scripts/backup.sh`. Phase 2+: `.piopkg` exporter.
