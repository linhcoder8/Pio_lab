# 📝 Prompt Templates — Pio_lab Workflow

> Reusable prompts để paste vào Cursor (Composer/Chat) hoặc Background Agents.

## Files

| File | Khi dùng |
|---|---|
| `start_milestone.md` | Bắt đầu milestone mới |
| `review_milestone.md` | Review code sau khi agent finish |
| `debug.md` | Khi test fail, code không work |
| `fix_test.md` | Khi cần sửa test mà không phá implementation |
| `refactor.md` | Refactor an toàn 1 module |
| `add_department.md` | Thêm phòng ban mới (Phase 2+ hoặc khi extend) |
| `agent_launch.md` | Template Background Agent task field |

## Cách dùng

1. Mở file template
2. Replace `{PLACEHOLDER}` với value cụ thể
3. Copy → paste vào Cursor

Hoặc dùng Cursor `@` reference:
```
@prompts/start_milestone.md
M3, focus on Claude adapter only.
```
Cursor sẽ đọc template + customize theo context.
