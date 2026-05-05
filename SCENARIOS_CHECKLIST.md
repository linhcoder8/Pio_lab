# 🎬 Scenarios Verification Checklist (cho Sếp Linh)

> Checklist NGẮN GỌN để Sếp Linh verify mỗi PR/milestone đã thực sự work — KHÔNG cần đọc code chi tiết.
>
> Khi agent báo "M{N} done", chạy nhanh checklist tương ứng.

---

## ✅ Pre-flight Check (mọi PR)

5 phút check trước khi review code:

```bash
# 1. Pull branch về local
git checkout <agent-branch>

# 2. Tests pass?
pytest tests/unit/ -v
# Expect: All green

# 3. Lint clean?
ruff check pio_lab/
# Expect: No errors

# 4. PROGRESS.md updated?
cat PROGRESS.md | head -50
# Expect: Milestone marked done với note

# 5. No secrets committed?
git diff main..HEAD | grep -iE "api[_-]?key|password|secret|token" | grep -v "API_KEY=mock\|API_KEY=changeme\|env_key:"
# Expect: Empty (no real keys)
```

Nếu fail bất kỳ bước nào → **không merge**, comment trên PR yêu cầu fix.

---

## 📋 Milestone-specific Verification

### M0 — Foundation ✓ Done khi:

```bash
# 1. Config loader work
python -c "
from pio_lab.utils.config_loader import load_pio_lab_config
config = load_pio_lab_config()
print('App name:', config['app']['name'])
"
# Expect: "App name: Pio_lab"

# 2. Logger work
python -c "
from pio_lab.utils.logging import setup_logging, logger
setup_logging('INFO', 'text')
logger.info('Test message')
"
# Expect: Log output with timestamp + message

# 3. Env validation work
python -c "
from pio_lab.utils.env import Settings
s = Settings()
print('Settings loaded')
"
# Expect: No error (hoặc clear error nếu missing required env)
```

### M1 — Postgres ✓ Done khi:

```bash
# 1. Postgres up
docker ps | grep pio_lab_postgres
# Expect: Running

# 2. Init DB work
python scripts/init_db.py
# Expect: "Database ready" + tables created

# 3. Tables exist
docker exec pio_lab_postgres psql -U pio_lab -d pio_lab -c "\dt"
# Expect: tasks, traces, conversations, provider_accounts

# 4. Insert + query work
pytest tests/unit/test_postgres_models.py -v
# Expect: All green
```

### M2 — Obsidian ✓ Done khi:

```bash
# 1. Vault read/write work
python -c "
from pathlib import Path
from pio_lab.memory.obsidian.vault import ObsidianVault
v = ObsidianVault(Path('./vault'))
v.write('test.md', 'hello')
print(v.read('test.md'))
"
# Expect: "hello"

# 2. SOUL.md / USER.md / AGENTS.md handlers work
pytest tests/unit/test_obsidian_vault.py -v
# Expect: All green

# Cleanup
rm vault/test.md
```

### M3 — Provider Router (Claude) ✓ Done khi:

```bash
# 1. Router load config
python -c "
from pio_lab.providers.router import ProviderRouter
r = ProviderRouter()
r.load()
print('Loaded routing rules:', len(r.config['routing_rules']))
"
# Expect: > 0

# 2. Smoke test 1 LLM call
python scripts/smoke_provider.py
# Expect: ✓ chief_of_staff → "Pio_lab works!" (hoặc message tương tự)
# Cần ANTHROPIC_API_KEY thật trong .env

# 3. Trace logged
docker exec pio_lab_postgres psql -U pio_lab -d pio_lab -c "SELECT count(*) FROM traces"
# Expect: count > 0
```

### M4 — Provider 4 còn lại ✓ Done khi:

```bash
# Smoke test all providers
python scripts/smoke_provider.py
# Expect: At least 3/5 providers work
# (Ollama có thể fail nếu Tailscale chưa setup — OK)

# Fallback chain work
# Manual test: tạm rename ANTHROPIC_API_KEY trong .env → run smoke
# Expect: fallback sang Codex/Gemini, vẫn return response
```

### M5 — Security ✓ Done khi:

```python
# Run trong python REPL hoặc test
from pathlib import Path
from pio_lab.security.policy_loader import PolicyLoader
from pio_lab.security.enforcer import SecurityEnforcer

loader = PolicyLoader()
loader.load()
enforcer = SecurityEnforcer(loader)

# 1. File access reject
assert not enforcer.check_file_access(Path("C:/Users/Admin/Desktop/secret.txt"))
print("✓ File access guard work")

# 2. Mask secrets
masked = enforcer.mask_secrets_in_output("My key is sk-abcdefghijklmnopqrstuv")
assert "[REDACTED]" in masked
print("✓ Mask work")

# 3. Approval flag
assert enforcer.requires_approval("send_email")
print("✓ Approval gate work")

# 4. Crypto block
assert not enforcer.check_crypto_keywords("My seed phrase is...")
print("✓ Crypto block work")
```

### M6 — Web Channel ✓ Done khi:

```bash
# 1. Server start
bash scripts/start_dev.sh &
sleep 5

# 2. Health check
curl http://localhost:8000/health
# Expect: {"status": "ok"}

# 3. Open browser
# http://localhost:8000/
# Expect: Chat page (basic HTML OK)
# Login với WEB_UI_ADMIN_PASSWORD từ .env
# Gõ message → echo response (M7 chưa wire CoS)

# Stop server
pkill -f "uvicorn pio_lab"
```

### M7 — Chief of Staff ✓ Done khi:

```python
# Run trong test
import asyncio
from pio_lab.layer3_chief_of_staff.chief_of_staff import ChiefOfStaff

async def test():
    cos = ChiefOfStaff(...)
    cos.build_graph()
    result = await cos.run({"input": "hello"}, {"channel": "test", "user_id": "1"})
    print(result)

asyncio.run(test())
# Expect: result["final_output"] không None
# Expect: result["traces"] có entries
```

```bash
# Replan loop test
pytest tests/unit/test_chief_of_staff.py::test_replan_on_qa_fail -v
# Expect: Pass
```

### M8 — Dept + Worker base ✓ Done khi:

```python
import asyncio
from pio_lab.core.registry import DepartmentRegistry
from pathlib import Path

reg = DepartmentRegistry(Path("./config/departments"))
reg.load_all()
print("Departments:", reg.list_departments())
# Expect: ['report', 'coder', 'research', 'media', 'qa']

# Run 1 worker
async def test():
    coder = reg.get("coder")
    result = await coder.run({"input": "Print 'hello' in Python"}, {})
    print(result["output"][:200])

asyncio.run(test())
# Expect: Output có code Python in "hello"
```

### M9 — 5 Departments cụ thể ✓ Done khi:

Run **scenarios 1-6** từ `docs/EXAMPLES.md`:

```bash
# Scenario 2: Code generation
python scripts/run_scenario.py 2
# Expect: file users.py tạo, syntax valid, QA pass

# Scenario 3: Research
python scripts/run_scenario.py 3
# Expect: 3 papers với DOI valid

# Scenario 4: Content
python scripts/run_scenario.py 4
# Expect: blog 800-1000 từ

# Scenario 5: Image
python scripts/run_scenario.py 5
# Expect: PNG 1280x720 trong output/

# Scenario 6: PowerPoint
python scripts/run_scenario.py 6
# Expect: .pptx 10 slides
```

### M10 — Knowledge Librarian ✓ Done khi:

```bash
# Run scenario 7 (cross-dept)
python scripts/run_scenario.py 7
# Sau khi done:

# 1. Task archived in Postgres
docker exec pio_lab_postgres psql -U pio_lab -d pio_lab -c \
  "SELECT id, status, completed_at FROM tasks ORDER BY completed_at DESC LIMIT 1"
# Expect: 1 row, status=done

# 2. Note created in vault
ls vault/tasks/$(date +%Y-%m-%d)/
# Expect: <task_id>.md exists

# 3. Search work
python -c "
import asyncio
from pio_lab.layer5_librarian.librarian import KnowledgeLibrarian
async def test():
    lib = KnowledgeLibrarian(...)
    results = await lib.search('adaptive optics', top_k=5)
    print(f'Found {len(results)} results')
asyncio.run(test())
"
# Expect: > 0
```

### M11 — Channels + UI ✓ Done khi:

**M11.1 — Telegram:**
1. Start bot, gõ message vào Telegram
2. Bot reply trong < 60s
3. Reply có format markdown đúng

**M11.2 — Discord:**
1. /chat slash command work
2. DM bot → reply

**M11.3 — Zalo:**
1. Webhook nhận message
2. Bot reply qua Zalo OA API

**M11.4 — Console UI:**
```
http://localhost:8000/admin

Pages cần work:
- /admin/             Dashboard với recent tasks
- /admin/bot          Edit USER.md, SOUL.md
- /admin/providers    Account/Model/Status table
- /admin/skills       Toggle on/off
- /admin/org          ORG diagram + Add Department
- /admin/tasks        Task history viewer
```

**Final acceptance — All 10 scenarios:**
```bash
python scripts/run_all_scenarios.py
# Expect: 10/10 pass
```

---

## 🎯 Phase 1 MVP Done ✓

Khi tất cả checklist sau pass:

- [ ] M0-M11 done (xem PROGRESS.md)
- [ ] All 10 scenarios pass
- [ ] CI green (tests + lint + arch check)
- [ ] Coverage ≥ 60% overall
- [ ] No `# TODO Phase 1` markers còn lại trong code
- [ ] README.md updated với screenshot demo
- [ ] Telegram bot demo work end-to-end
- [ ] Web UI demo work
- [ ] Add 1 department mới qua UI work
- [ ] Provider rotation work (test bằng cách remove key)

🎉 **Pio_lab MVP Phase 1 SHIPPED!**

---

## 📞 Khi scenario fail

1. **Đọc error message kỹ** — thường có hint
2. **Check `.env`** — API keys, DB connection
3. **Check Postgres up** — `docker ps`
4. **Check logs** — `tail -f traces/*.log`
5. **Reproduce trong Cursor** với prompt:
   ```
   @prompts/debug.md
   Scenario {N} fail. Output: {paste}.
   Debug và fix.
   ```
6. **Last resort:** rollback PR, request agent re-implement với feedback

---

*File này viết cho Sếp Linh — không phải Codex/Cursor.*
