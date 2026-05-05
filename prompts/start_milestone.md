# Start Milestone Template

## Prompt

```
Đọc các file sau:
- @.cursorrules
- @CODEX_HANDOFF.md (focus section M{N})
- @PROGRESS.md
- @MILESTONES_QUICK_REF.md
- @docs/PROVIDER_API_REFERENCE.md (nếu M3-M4)
- @docs/EXAMPLES.md scenario tương ứng

Implement Milestone M{N} — {NAME}:

1. **Plan briefly** (5-10 dòng):
   - File nào tạo mới
   - File nào sửa
   - Test nào sẽ viết
   - Risks lường trước

2. **Implement**:
   - Strictly follow @.cursor/rules/architecture-lock.mdc — KHÔNG sửa structure
   - Mọi LLM call qua ProviderRouter (xem @.cursor/rules/provider-routing.mdc)
   - Type hints, async, no print() (xem @.cursor/rules/python-conventions.mdc)
   - Code conventions trong `.cursorrules`

3. **Tests**:
   - Mỗi acceptance criterion → ít nhất 1 test
   - Edge case + error path
   - Mock LLM cho unit test, real cho integration test
   - Run: `pytest tests/unit/test_<milestone>.py -v`

4. **Verify scenario** (nếu applicable):
   - Run scenario {SCENARIO_NUMBER} từ @docs/EXAMPLES.md
   - Document result trong PROGRESS.md

5. **Update @PROGRESS.md** theo template:
```
### YYYY-MM-DD — Milestone M{N} done
- ✅ {acceptance criterion 1}
- ✅ {acceptance criterion 2}
- 📝 Decisions: {decisions made}
- 🧪 Tests: {X pass, Y fail}
- ⏭️ Next: M{N+1}
```

6. **Git commit**: `M{N}: {short description}`

7. **Báo cáo** (tiếng Việt):
   - Tóm tắt 5-10 dòng
   - File path đã tạo/sửa
   - Test results
   - Issues hoặc decisions cần Sếp Linh review
```

## Ví dụ thực tế cho M3

```
Đọc các file sau:
- @.cursorrules
- @CODEX_HANDOFF.md (focus section M3)
- @PROGRESS.md
- @MILESTONES_QUICK_REF.md
- @docs/PROVIDER_API_REFERENCE.md (Claude section đặc biệt quan trọng)
- @docs/EXAMPLES.md scenario 1

Implement Milestone M3 — Provider Router (Claude only):

[... template above ...]

Important M3-specific:
- Bắt đầu với CHỈ Claude adapter, KHÔNG implement Codex/Gemini/DeepSeek/Ollama (đó là M4)
- Test với 1 message simple: "Say 'Pio_lab works!'"
- Verify trace logged vào Postgres `traces` table
- Account pool tối thiểu 1 Claude account (test với env var ANTHROPIC_API_KEY)
```
