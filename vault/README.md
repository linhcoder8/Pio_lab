# Pio_lab Vault — Second Brain

Đây là **Obsidian Vault** chứa toàn bộ knowledge của Pio_lab.

## Cấu trúc

```
vault/
├── USER.md          ← Profile của bạn (Sếp Linh)
├── AGENTS.md        ← Auto-generated registry of agents
├── SOUL.md          ← Bot personality / behavioral rules
├── tasks/           ← Task history (mỗi task 1 file md)
│   └── YYYY-MM-DD/
│       └── <request_id>.md
├── knowledge/       ← Wiki notes (Pio_lab tự tích lũy)
└── skills/          ← Skill library (markdown specs)
```

## Mở bằng Obsidian

1. Cài Obsidian: https://obsidian.md
2. Open as Vault → chọn folder này
3. Plugin recommended:
   - Dataview (query notes như database)
   - Templater (templates)
   - Local REST API (để Pio_lab integrate sau)

## Backup

```bash
tar czf vault_backup_$(date +%Y%m%d).tar.gz vault/
```
