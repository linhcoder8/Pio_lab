# 🦞 Pio_lab — Personal AI Company

> Hệ thống đa AI Agent vận hành 24/7, hybrid AI (Cloud + Local), với trí nhớ dài hạn và khả năng mở rộng động.

**Owner / CEO:** Sếp Linh
**Codename Runtime:** OpenClaw (Lobster)
**Status:** MVP Phase 1 — Architecture & Folder Structure ✓ Approved

---

## Tổng quan

Pio_lab là một "công ty AI cá nhân" với cấu trúc tổ chức 7 lớp, có khả năng:
- Nhận yêu cầu qua nhiều kênh chat (Telegram, Web, Discord, Zalo)
- Tự động lập kế hoạch và phân công cho các phòng ban chuyên môn
- Sử dụng đa nhà cung cấp AI (Codex, Claude, Gemini, DeepSeek, Ollama local)
- Tích lũy kiến thức vào "second brain" (Obsidian + PostgreSQL)
- Mở rộng động: thêm phòng ban / worker / skill / plugin runtime

## Kiến trúc 7 lớp

```
Layer 0: 🖥️ Management Console (Web UI)
Layer 1: 👤 Input (4 channels: Telegram, Web, Discord, Zalo)
Layer 2: 🌐 OpenClaw Runtime (Skill Engine, Cron, Channel Router)
Layer 3: 👔 Chief of Staff (Orchestrator) — Plan → Dispatch → Report
Layer 4: 🏢 5 Phòng ban (REPORT, CODER, RESEARCH, MEDIA, QA) — Dynamic Registry
Layer 5: 📚 Knowledge Librarian (Postgres + Obsidian)
Layer 6: 💬 Communicator (Output Adapter)
```

**Cross-cutting:** Provider Router · Persistent Memory · Security Policy · Distillation (Phase 2+) · Portable Export (Phase 2+)

Xem sơ đồ chi tiết: [Pio_lab_Architecture.html](./Pio_lab_Architecture.html)

## Cấu trúc thư mục

```
Pio_lab_cla/
├── pio_lab/                # Python package — code chính
│   ├── core/               # Abstractions (Agent, Department, Worker, Registry)
│   ├── layer0_console/     # Management Console (Web UI + API)
│   ├── layer1_input/       # Channel Adapters
│   ├── layer2_runtime/     # OpenClaw Runtime
│   ├── layer3_chief_of_staff/  # Orchestrator
│   ├── layer4_departments/ # 5 phòng ban
│   ├── layer5_librarian/   # Knowledge Librarian
│   ├── layer6_communicator/# Output Adapter
│   ├── providers/          # Multi-provider router
│   ├── memory/             # Postgres + Obsidian
│   ├── security/           # Policy enforcer
│   ├── distillation/       # Trace logger (Phase 1) / Trainer (Phase 2+)
│   └── export/             # Portable export (Phase 2+)
│
├── config/                 # YAML configs (dynamic registry)
│   └── departments/        # Phòng ban + Worker configs
│
├── vault/                  # Obsidian Vault — second brain
│   ├── USER.md
│   ├── AGENTS.md
│   ├── SOUL.md
│   └── ...
│
├── infra/                  # Docker + Tailscale setup
├── scripts/                # Helper scripts
├── tests/                  # Unit + Integration tests
└── docs/                   # Documentation
```

## Cài đặt nhanh

```bash
# 1. Clone & setup
cp .env.example .env  # điền API keys

# 2. Chạy Postgres + Ollama
docker-compose up -d

# 3. Cài Python deps
pip install -e .

# 4. Init DB
python scripts/init_db.py

# 5. Start dev
bash scripts/start_dev.sh
```

## Roadmap

- **Phase 1 (MVP)** — đang triển khai
  - 7 lớp đầy đủ, 4 channels, 5 phòng ban, 5 providers, Memory full
  - SKIP: Distillation training, Portable Export, Security Engine UI
- **Phase 2** — Distillation + Security Engine UI
- **Phase 3** — Portable Export + WhatsApp channel
- **Phase 4** — iMessage + advanced features

## License

Personal project — internal use.
