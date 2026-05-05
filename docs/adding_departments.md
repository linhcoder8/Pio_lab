# Thêm Phòng ban / Worker mới

## Cách 1: UI Console (sau khi Phase 1 implement xong)

`/org` page → click "+ Phòng ban" hoặc "+ Worker" → fill form → save.

## Cách 2: CLI

```bash
# Thêm phòng ban
python scripts/add_department.py \
    --id sales \
    --name SALES \
    --vi "Bán hàng" \
    --icon 💰 \
    --color "#3fb950"

# Thêm worker (sẽ làm trong Phase 1)
python scripts/add_worker.py \
    --dept sales \
    --id outreach \
    --name "Outreach Worker"
```

## Cách 3: Edit YAML thủ công

1. Tạo folder `config/departments/<dept_id>/`
2. Tạo `config/departments/<dept_id>/department.yaml` (xem template ở 5 phòng ban có sẵn)
3. Tạo `config/departments/<dept_id>/workers/<worker_id>.yaml`
4. Update `config/departments/_registry.yaml` thêm entry mới
5. Reload: hot-reload (nếu enabled) hoặc restart `pio`

## Worker config schema

```yaml
id: <worker_id>
name: <Display Name>
department: <dept_id>
description: |
  Mô tả worker này làm gì
system_prompt: |
  Prompt định nghĩa role/skill của worker
provider_routing_key: <dept_id>.<worker_id>   # phải khớp providers.yaml
tools_enabled:
  - tool_a
  - tool_b
max_iterations: 10
timeout_seconds: 300
require_human_approval:    # optional
  - sensitive_action_1
```

## Đừng quên

Sau khi thêm worker, nhớ thêm routing rule trong `config/providers.yaml`:

```yaml
routing_rules:
  sales.outreach:
    - { provider: claude, model: claude-sonnet-4-6 }
    - { provider: gemini, model: gemini-2.0-pro }
```
