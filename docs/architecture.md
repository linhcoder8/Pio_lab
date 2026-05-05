# Pio_lab Architecture (v3)

Xem sơ đồ trực quan: [Pio_lab_Architecture.html](../Pio_lab_Architecture.html)

## 7 lớp + 5 cross-cutting modules

(Tóm tắt — chi tiết xem `docs/7_layers.md`)

| # | Layer | Vai trò | MVP Phase 1 |
|---|---|---|---|
| 0 | Management Console | Web UI quản trị | ✓ Full |
| 1 | Input | 4 channels: Telegram/Web/Discord/Zalo | ✓ Full |
| 2 | OpenClaw Runtime | OS, Skill Engine, Cron | ✓ Full |
| 3 | Chief of Staff | Orchestrator (Plan-Dispatch-Report) | ✓ Full |
| 4 | Departments | 5 phòng ban dynamic registry | ✓ Full |
| 5 | Knowledge Librarian | Postgres + Obsidian | ✓ Full |
| 6 | Communicator | Output adapter | ✓ Full |

| Cross-cutting | MVP |
|---|---|
| Provider Router | ✓ Full (5 providers) |
| Persistent Memory | ✓ Full |
| Security Policy | ⊘ Default rules cứng |
| Distillation | ⊘ Trace logger only |
| Portable Export | ⊘ Workaround scripts/backup.sh |
