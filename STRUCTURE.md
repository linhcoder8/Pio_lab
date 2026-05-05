# 📁 Pio_lab — Project Structure

> Cấu trúc thư mục đã được duyệt và xây dựng. Snapshot: 162 files, 60 folders, 113 Python files, 18 YAML configs, 17 Markdown docs.

## 🌲 Tree Overview

```
Pio_lab_cla/
│
├── 📄 README.md                      # Project overview
├── 📄 STRUCTURE.md                   # File này
├── 📄 Pio_lab_Architecture.html      # Sơ đồ kiến trúc (đã duyệt)
├── 📄 Whitebook Pio_lab.docx         # Tài liệu yêu cầu gốc
├── 📄 .env.example                   # Env template
├── 📄 .gitignore
├── 📄 pyproject.toml                 # Python deps
├── 📄 docker-compose.yml             # Postgres + pgAdmin
│
├── 📁 docs/                          # Documentation
│   ├── architecture.md               # Tóm tắt kiến trúc
│   ├── 7_layers.md                   # Chi tiết 7 lớp
│   └── adding_departments.md         # Hướng dẫn mở rộng
│
├── 📁 config/                        # ⭐ Configuration layer
│   ├── pio_lab.yaml                  # Main app config
│   ├── providers.yaml                # Multi-provider routing
│   ├── security_policy.yaml          # Default security rules (Phase 1)
│   └── departments/                  # ⭐ Dynamic Registry (Layer 4)
│       ├── _registry.yaml            # 5 phòng ban active
│       ├── report/
│       │   ├── department.yaml
│       │   └── workers/
│       │       ├── slide_word_web.yaml
│       │       └── video_report.yaml
│       ├── coder/
│       │   ├── department.yaml
│       │   └── workers/{frontend, backend}.yaml
│       ├── research/
│       │   └── workers/optics.yaml
│       ├── media/
│       │   └── workers/{content, image_maker, video_maker}.yaml
│       └── qa/
│           └── workers/qa_reviewer.yaml
│
├── 📁 pio_lab/                       # ⭐ Main Python package
│   ├── __init__.py
│   ├── main.py                       # Entry point: `pio` command
│   │
│   ├── core/                         # Abstractions
│   │   ├── agent.py                  # BaseAgent + AgentConfig
│   │   ├── department.py             # Department class
│   │   ├── worker.py                 # Worker class
│   │   ├── registry.py               # DepartmentRegistry (hot reload)
│   │   ├── state.py                  # PioLabState (LangGraph state)
│   │   └── events.py                 # EventBus pub/sub
│   │
│   ├── layer0_console/               # 🖥️ Layer 0 — Web UI
│   │   ├── api/                      # FastAPI endpoints
│   │   │   ├── bot_config.py
│   │   │   ├── providers.py
│   │   │   ├── skills.py
│   │   │   └── org.py
│   │   └── web/                      # React + Vite frontend
│   │
│   ├── layer1_input/                 # 👤 Layer 1 — Channels (4)
│   │   ├── base_adapter.py           # ChannelAdapter interface
│   │   ├── telegram_adapter.py
│   │   ├── web_adapter.py
│   │   ├── discord_adapter.py
│   │   └── zalo_adapter.py
│   │
│   ├── layer2_runtime/               # 🌐 Layer 2 — OpenClaw
│   │   ├── openclaw.py               # Bootstrap & lifecycle
│   │   ├── channel_router.py
│   │   ├── skill_engine.py
│   │   ├── cron.py
│   │   ├── auth.py
│   │   └── heartbeat.py
│   │
│   ├── layer3_chief_of_staff/        # 👔 Layer 3 — Orchestrator
│   │   ├── chief_of_staff.py         # Main agent (LangGraph)
│   │   ├── plan.py                   # PLAN node
│   │   ├── dispatch.py               # DISPATCH node
│   │   ├── report.py                 # REPORT node
│   │   ├── replan.py                 # Replan loop
│   │   └── human_approval.py         # Human-in-the-loop
│   │
│   ├── layer4_departments/           # 🏢 Layer 4 — 5 Phòng ban
│   │   ├── base/                     # GenericDepartment + GenericWorker
│   │   ├── report/    + 2 workers
│   │   ├── coder/     + 2 workers
│   │   ├── research/  + 1 worker
│   │   ├── media/     + 3 workers
│   │   └── qa/        + 1 worker
│   │
│   ├── layer5_librarian/             # 📚 Layer 5 — Knowledge Librarian
│   │   ├── librarian.py              # Main agent
│   │   ├── postgres_store.py
│   │   ├── obsidian_store.py
│   │   └── indexer.py
│   │
│   ├── layer6_communicator/          # 💬 Layer 6 — Output adapter
│   │   ├── communicator.py
│   │   └── formatters/
│   │       ├── telegram_format.py
│   │       ├── web_format.py
│   │       ├── discord_format.py
│   │       └── zalo_format.py
│   │
│   ├── providers/                    # 🔌 Cross-cutting: Provider Router
│   │   ├── router.py                 # Main router
│   │   ├── account_pool.py           # Multi-account rotation
│   │   ├── status_tracker.py         # Running/End/Waiting
│   │   ├── token_tracker.py          # Quota & cost tracking
│   │   └── adapters/                 # 5 providers
│   │       ├── claude_adapter.py
│   │       ├── codex_adapter.py
│   │       ├── gemini_adapter.py
│   │       ├── deepseek_adapter.py
│   │       └── ollama_adapter.py     # via Tailscale
│   │
│   ├── memory/                       # 💾 Cross-cutting: Memory
│   │   ├── postgres/
│   │   │   ├── models.py             # SQLAlchemy: Task, Trace, Conversation
│   │   │   ├── traces.py             # Trace logger
│   │   │   └── migrations/           # Alembic
│   │   └── obsidian/
│   │       ├── vault.py              # Vault interface
│   │       ├── soul_md.py            # SOUL.md
│   │       ├── user_md.py            # USER.md
│   │       └── agents_md.py          # AGENTS.md auto-gen
│   │
│   ├── security/                     # 🛡️ Cross-cutting: Security
│   │   ├── policy_loader.py          # Đọc security_policy.yaml
│   │   └── enforcer.py               # Apply rules runtime
│   │
│   ├── distillation/                 # 🎓 Cross-cutting (Phase 1: trace only)
│   │   └── trace_logger.py           # Active in Phase 1
│   │
│   ├── export/                       # 📦 Cross-cutting (Phase 2+)
│   │   └── (placeholder, dùng scripts/backup.sh)
│   │
│   └── utils/
│       ├── logging.py                # loguru setup
│       └── helpers.py
│
├── 📁 vault/                         # 🧠 Obsidian Vault — Second Brain
│   ├── README.md
│   ├── USER.md                       # Profile của Sếp Linh
│   ├── AGENTS.md                     # Auto-gen registry
│   ├── SOUL.md                       # Bot personality
│   ├── tasks/                        # Task history
│   ├── knowledge/                    # Wiki notes
│   ├── skills/                       # Skill specs
│   └── .obsidian/                    # Obsidian config
│
├── 📁 scripts/                       # Helper scripts
│   ├── setup.py                      # First-time setup
│   ├── init_db.py                    # Init Postgres schema
│   ├── start_dev.sh                  # Dev mode
│   ├── start_prod.sh                 # Production
│   ├── backup.sh                     # Phase 1 export workaround
│   └── add_department.py             # CLI thêm phòng ban
│
├── 📁 tests/
│   ├── unit/test_registry.py
│   ├── integration/test_full_flow.py
│   └── fixtures/
│
└── 📁 infra/
    ├── docker/app.Dockerfile
    └── tailscale/README.md           # Setup Local AI qua Tailscale
```

## 🎯 Bản đồ kiến trúc → Code

| Layer | Nơi triển khai | Config |
|---|---|---|
| 0 — Console | `pio_lab/layer0_console/` | — |
| 1 — Input | `pio_lab/layer1_input/` | `config/pio_lab.yaml::channels` |
| 2 — Runtime | `pio_lab/layer2_runtime/` | `config/pio_lab.yaml::openclaw` |
| 3 — Chief of Staff | `pio_lab/layer3_chief_of_staff/` | `config/pio_lab.yaml::chief_of_staff` |
| 4 — Departments | `pio_lab/layer4_departments/` | `config/departments/*.yaml` ⭐ |
| 5 — Librarian | `pio_lab/layer5_librarian/` | `config/pio_lab.yaml::librarian` |
| 6 — Communicator | `pio_lab/layer6_communicator/` | — |
| **Provider Router** | `pio_lab/providers/` | `config/providers.yaml` ⭐ |
| **Memory** | `pio_lab/memory/` | `.env::POSTGRES_*` |
| **Security** | `pio_lab/security/` | `config/security_policy.yaml` ⭐ |

## ✅ MVP Phase 1 Coverage

- ✅ 7 lớp với skeleton classes + interfaces
- ✅ 5 phòng ban + tất cả workers (config + code stubs)
- ✅ 4 channels (Telegram, Web, Discord, Zalo)
- ✅ 5 providers (Claude, Codex, Gemini, DeepSeek, Ollama)
- ✅ Provider Router + account pool + tracker
- ✅ Memory (Postgres models + Obsidian vault interface)
- ✅ Security (default rules + enforcer)
- ✅ Trace logger (sẵn sàng cho Distillation Phase 2+)
- ✅ Vault (USER.md, AGENTS.md, SOUL.md)
- ✅ Helper scripts (setup, init_db, backup, add_department)
- ✅ Tests skeleton
- ✅ Docker + Tailscale setup docs

## ⏳ Sẵn sàng cho Phase tiếp theo

Tất cả file Python hiện chứa skeleton class + interface + docstring + `# TODO Phase 1` markers. Implementation sẽ là Phase 1 sau khi user duyệt cấu trúc này.
