# 🎯 Hướng dẫn dùng Cursor + Codex để build Pio_lab

> Step-by-step cho **phương án B** (hands-off) với **Cursor IDE + Codex/GPT-5 model + Background Agents**.

---

## 📋 Mục lục

1. [Cài đặt Cursor](#1-cài-đặt-cursor)
2. [Đăng ký + chọn plan](#2-đăng-ký--chọn-plan)
3. [Configure model = Codex/GPT-5](#3-configure-model)
4. [Mở project Pio_lab](#4-mở-project)
5. [4 cách dùng AI trong Cursor](#5-4-cách-dùng-ai)
6. [Workflow chuẩn cho mỗi milestone](#6-workflow-mỗi-milestone)
7. [Background Agents (Automations) — autonomous mode](#7-background-agents)
8. [Tips hands-off cho Sếp Linh](#8-tips-hands-off)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Cài đặt Cursor

### Download & Install

**Windows:**
1. Vào https://cursor.com → Download for Windows
2. Chạy installer `Cursor Setup.exe`
3. Cài đặt mặc định (~5 phút)
4. Mở Cursor

**macOS / Linux:** tương tự, download phiên bản phù hợp.

### Lần đầu mở:
- Chọn theme (Dark / Light)
- **Quan trọng:** chọn **"Import VS Code Settings"** nếu bạn đã dùng VSCode (kế thừa extensions, keybindings)
- Login bằng Google / GitHub

---

## 2. Đăng ký + chọn plan

Cursor có 4 plans:

| Plan | Giá (~2026) | Phù hợp |
|---|---|---|
| **Hobby (Free)** | $0 | 2000 completions, 50 slow chat → đủ để test thử |
| **Pro** | $20/tháng | 500 fast chat (Codex/GPT-5), unlimited slow → **recommended cho dự án này** |
| **Business** | $40/tháng | Pro + privacy mode, team admin |
| **Ultra** | $200/tháng | 1000 fast chat + Background Agents unlimited |

**Khuyến nghị cho Pio_lab:**
- **Pro $20/tháng** đủ cho Phase 1 (12 milestones). Nếu chạy nhiều Background Agents song song → Ultra.

Đăng ký:
1. Trong Cursor: `Settings (Cmd/Ctrl + ,) → Account → Upgrade`
2. Hoặc vào https://cursor.com/settings → Subscription

---

## 3. Configure model = Codex/GPT-5

### Bật model Codex/GPT-5

1. Mở Cursor → `Settings → Models`
2. Bật toggle các model bạn muốn dùng:
   - ✅ **gpt-5-codex** (hoặc `gpt-5` / `o4` — model coding-tuned mới nhất của OpenAI)
   - ✅ **claude-sonnet-4-6** (backup, đôi khi tốt hơn cho refactor)
   - ✅ **claude-opus-4-6** (cho task khó)
3. Set **Default model** = `gpt-5-codex`

### Add API key (optional — dùng key riêng)

Nếu bạn có **OpenAI API key riêng** và muốn dùng key đó (không tốn quota Cursor):
- `Settings → Models → API Keys → OpenAI` → paste key
- Toggle "Use custom API key"

> **Lưu ý:** Dùng custom key sẽ tốn tiền OpenAI riêng (~$3-5/1M tokens). Dùng quota Cursor Pro thường rẻ hơn.

### Verify

Mở chat (Ctrl/Cmd + L) → check góc dưới hiển thị `gpt-5-codex` → done.

---

## 4. Mở project Pio_lab

### Mở folder

1. Cursor → `File → Open Folder...`
2. Chọn `E:\Pio_lab_cla\Pio_lab_cla`
3. Cursor hỏi "Trust this workspace?" → **Yes**

### Cursor sẽ tự động:

- **Index toàn bộ codebase** (162 files) — mất 1-2 phút lần đầu
- Đọc file `.cursorrules` (đã tạo sẵn) → hiểu project rules
- Phát hiện Python project → suggest install Python extension

### Verify indexing done

- Góc dưới phải Cursor → có chấm xanh "Indexed: 162 files"
- Hoặc: Settings → Codebase Indexing → "Up to date"

### Setup môi trường lần đầu

Mở Terminal trong Cursor (Ctrl/Cmd + `) :

```bash
# 1. Setup .env
python scripts/setup.py
# → Sửa .env: điền ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.

# 2. Start Postgres
docker-compose up -d

# 3. Install Python deps
pip install -e ".[dev]"
```

> **Note:** `init_db.py` chưa chạy được vì M1 chưa implement. Đợi Cursor làm M1 xong rồi chạy.

---

## 5. 4 cách dùng AI trong Cursor

Học 4 shortcut này trước khi bắt đầu:

### A. **Cmd/Ctrl + L** — Chat Panel (sidebar)

- Hỏi đáp về codebase, không edit file
- Dùng `@` để reference: `@CODEX_HANDOFF.md`, `@pio_lab/core/agent.py`, `@codebase` (toàn repo)
- Ví dụ: *"Đọc @CODEX_HANDOFF.md section M0 và giải thích cho tôi"*

### B. **Cmd/Ctrl + K** — Inline Edit

- Đặt cursor vào dòng code → `Cmd+K`
- Gõ instruction → AI sửa **TẠI CHỖ**
- Ví dụ: chọn function `fetch_data`, gõ "Convert to async with httpx"
- Reject/Accept với `Cmd+Backspace` / `Cmd+Enter`

### C. **Cmd/Ctrl + I** — Composer (Multi-file)

- **Quan trọng nhất cho dự án này.**
- Tạo edit nhiều file cùng lúc
- Reference nhiều file qua `@`
- Show diff tất cả files trước khi accept

**Ví dụ cho Pio_lab:**
```
@CODEX_HANDOFF.md (section M0)
@pio_lab/utils/

Implement M0 — Foundation theo acceptance criteria trong CODEX_HANDOFF.md.
Tạo các file cần thiết, write tests.
```

→ Composer sẽ propose tạo/sửa nhiều file → review diff → Apply All.

### D. **Cmd/Ctrl + Shift + L** — Quick Chat (popup)

- Chat ngắn, no panel
- Phù hợp hỏi nhanh

### Cheatsheet `@` references

| `@` | Ý nghĩa |
|---|---|
| `@filename.md` | Đính file vào context |
| `@folder/` | Đính folder (Cursor pick relevant files) |
| `@codebase` | Search semantic toàn repo |
| `@web` | Web search trong chat |
| `@docs` | Tham chiếu docs of libraries (e.g. `@docs LangGraph`) |
| `@git` | Git history/diff |
| `@terminal` | Output terminal hiện tại |
| `@cursor` | Cursor selection |

---

## 6. Workflow mỗi milestone

> **Lặp đi lặp lại pattern này 12 lần (M0 → M11).**

### Bước 1: Khởi động session

```
Cursor mở project → Ctrl+L (chat) → gõ:

"Đọc @PROGRESS.md để biết milestone hiện tại và tiếp tục."
```

Cursor sẽ:
- Đọc `.cursorrules` (tự động)
- Đọc `PROGRESS.md` (do prompt)
- Báo cáo: "Đang ở M{N}, các criteria còn lại: ..."

### Bước 2: Plan implementation

```
Ctrl+I (Composer) → gõ:

"@CODEX_HANDOFF.md section M{N}
Plan implementation cho milestone này.
Liệt kê file cần tạo/sửa, không code yet."
```

Review plan → confirm hoặc điều chỉnh.

### Bước 3: Implement

```
Trong Composer (vẫn cùng session):

"OK, implement plan trên. Bắt đầu.
Quan trọng: follow code conventions trong .cursorrules.
Mọi LLM call phải qua ProviderRouter."
```

Cursor proposes diff → review từng file → Accept All (hoặc per-file).

### Bước 4: Test

Mở terminal:
```bash
pytest tests/unit/test_<milestone>.py -v
```

Nếu fail → quay lại Composer:
```
"@terminal có failures. Fix các test fail, không phá implementation hiện có."
```

### Bước 5: Run scenario

```bash
# Vd cho M3 done: scenario 1 (Q&A)
python scripts/smoke_provider.py
```

Hoặc trong chat:
```
"Run scenario 1 từ @docs/EXAMPLES.md.
Verify acceptance criteria. Report kết quả."
```

### Bước 6: Update PROGRESS + commit

```
Composer:

"M{N} all criteria pass. Update @PROGRESS.md theo template:
- Mark M{N} done
- Note decisions made
- Set next milestone

Sau đó git commit message 'M{N}: {short description}'."
```

Cursor sẽ edit `PROGRESS.md` + chạy git commit cho bạn (cần allow terminal).

### Bước 7: Báo cáo + Confirm next

Cursor báo cáo. Bạn:
- Review code (đặc biệt files quan trọng)
- "OK, sang M{N+1}" → quay lại Bước 1

---

## 7. Background Agents (Automations)

> **Đây là tính năng autonomous chính của Cursor — phù hợp phương án B.**

### Background Agent là gì

- Cloud agent chạy **độc lập** trong VM riêng của Cursor
- Bạn give task → agent tự code → tự test → tự commit → tạo PR
- Bạn review PR → merge
- **Có thể chạy 10 agent song song** (Pro plan)

### Setup lần đầu

1. Trong Cursor → click icon **🌌 Agents** ở sidebar (hoặc `Ctrl+E`)
2. Lần đầu: connect GitHub repo
   - Push project lên GitHub trước (private repo OK)
   - Authorize Cursor app
3. Click "New Agent"

### Tạo Background Agent cho 1 milestone

**Form:**
- **Name:** `M3 - Provider Router (Claude)`
- **Repo:** `<your-github>/Pio_lab`
- **Branch:** `m3-provider-router`
- **Model:** `gpt-5-codex` (hoặc `claude-sonnet-4-6`)
- **Task:**
  ```
  Read @CLAUDE.md (.cursorrules), @PROGRESS.md, @CODEX_HANDOFF.md section M3,
  @docs/PROVIDER_API_REFERENCE.md (Claude section).

  Implement M3 — Provider Router (Claude only first):
  - All acceptance criteria trong section M3
  - Write tests
  - Update PROGRESS.md
  - Commit với message "M3: Provider Router with Claude adapter"

  KHÔNG implement M4 hay sau. Stop khi M3 done.
  ```
- **Auto-merge:** ❌ tắt (review trước)

Click **Launch**.

### Theo dõi Agent

- Agent panel hiển thị real-time logs
- Bạn thấy agent: read files → write code → run tests → commit → push
- Sau ~10-30 phút (tùy milestone): agent báo "Done" + tạo PR

### Review + Merge

1. Vào GitHub → tab Pull Requests → review diff
2. Hoặc trong Cursor → click PR link → diff hiển thị inline
3. **Quan trọng:** review thật sự, không auto-merge mù
4. OK → merge → next milestone

### Chạy parallel nhiều milestones

Với những milestone **độc lập** (không phụ thuộc nhau), launch song song:

| Có thể song song | Phải tuần tự |
|---|---|
| M1 (Postgres) ∥ M2 (Obsidian) ∥ M5 (Security) | M3 → M4 (cùng provider router) |
| M9 (5 dept implementation) per dept | M7 (CoS) → M8 (workers) |
| M11 channel adapters mỗi channel 1 agent | M10 cần M9 done |

→ Có thể chạy 5-6 agent song song → giảm thời gian từ tuần xuống ngày.

### Cost estimate

- 1 milestone medium ~ 50K-200K tokens → ~$0.5-2 với Codex
- 12 milestones ~ $10-30 cho cả Phase 1
- Nếu chạy parallel + retry → cho buffer 2x → **$50-100 cho cả Phase 1**

---

## 8. Tips hands-off cho Sếp Linh

### 8.1 Daily routine

```
Sáng (10 phút):
- Mở Cursor → Background Agents panel
- Check PR overnight có gì
- Review + merge nếu OK
- Launch agent cho milestone tiếp theo
- Đóng Cursor → đi làm việc khác

Chiều (10 phút):
- Check progress
- Review PR
- Merge / feedback

Tối (15 phút):
- Cuối ngày: launch overnight agent (milestone dài)
- Sáng mai: review + merge
```

### 8.2 Khi review PR

Đừng đọc TỪNG dòng — quá tốn thời gian. Thay vào đó:

**Quick review checklist (5 phút):**
1. **File structure đúng?** Không có file lạ ngoài plan
2. **PROGRESS.md updated?** Có note decisions không
3. **Tests pass?** CI green?
4. **Imports đúng?** Không phá architecture
5. **Random spot check 2-3 files** — đọc kỹ

Nếu OK 5/5 → merge. Nếu doubt → comment trên PR, agent revise.

### 8.3 Khi agent đi sai hướng

Symptom:
- PR có 50+ files thay đổi cho 1 milestone (quá nhiều)
- Agent tự tạo module không có trong handoff
- Tests skip nhiều

Action:
1. **Đừng merge.** Close PR.
2. Mở Composer → paste link PR đó:
   ```
   "@<PR url>
   Agent này đi sai hướng vì lý do X. Re-launch với constraint:
   - Chỉ thay đổi file trong list cụ thể: ...
   - Không tạo module mới
   - Strictly follow @CODEX_HANDOFF.md M{N}"
   ```
3. Launch lại với prompt chặt hơn

### 8.4 Khi cần help review code

Mở Cursor → Composer →
```
"@<file changed in PR>
Review code này. Check:
- Có bug logic không
- Performance issues
- Security risks
- Có khớp acceptance criteria @CODEX_HANDOFF.md M{N} không"
```

→ Cursor sẽ review giùm — như có 2nd opinion.

### 8.5 Cấu hình Cursor cho hands-off mode

`Settings → Cursor Settings`:
- ✅ **Auto-apply edits** (with confirmation)
- ✅ **Allow terminal commands** (cẩn thận với rm)
- ❌ **Auto-run tests** (manual control)
- ✅ **Codebase indexing**
- ✅ **Allow web search** (cho `@web` reference)

`Settings → Beta`:
- ✅ Background Agents
- ✅ Bug Bot (auto code review on PR)

### 8.6 Notify khi agent done

Background Agents → Settings:
- ✅ Email notifications
- ✅ Slack webhook (nếu có team)

→ Bạn không cần mở Cursor liên tục. Email báo "M3 done" → mở review.

---

## 9. Troubleshooting

### "Codebase indexing failed"

```bash
# Trong terminal Cursor:
rm -rf .cursor/
# Cursor → Cmd+Shift+P → "Reindex codebase"
```

### Agent timeout

- Pro plan: agent timeout 30 phút
- Solution: chia milestone thành sub-tasks, mỗi sub-task 1 agent

### Agent không đọc file context

Verify `.cursorrules` ở root (đã có).
Trong prompt, **explicit reference** files:
```
@CODEX_HANDOFF.md @PROGRESS.md @docs/EXAMPLES.md
```
KHÔNG dựa hoàn toàn vào auto-load.

### Code generated không follow conventions

- Edit `.cursorrules` thêm rule cụ thể
- Hoặc thêm vào prompt: *"Follow @.cursorrules strictly"*

### API key Cursor hết quota

- `Settings → Account → Usage` → check
- Pro: $20/tháng = 500 fast chat. Hết → fallback slow (vẫn work)
- Hoặc add custom OpenAI key (`Settings → Models → API Keys`)

### Conflict khi nhiều agent push parallel

- Mỗi agent dùng **branch riêng** (đã set trong launch form)
- Merge tuần tự, resolve conflict thủ công nếu có
- Không launch 2 agent cùng modify 1 milestone

---

## 🎯 Checklist trước khi bắt đầu M0

- [ ] Cursor installed + signed in
- [ ] Pro plan active (hoặc Free để test)
- [ ] Default model = `gpt-5-codex` (hoặc Claude Sonnet)
- [ ] Project folder opened: `E:\Pio_lab_cla\Pio_lab_cla`
- [ ] Codebase indexed (xanh)
- [ ] `.cursorrules` exists (đã tạo sẵn)
- [ ] `.env` copied + filled tối thiểu `ANTHROPIC_API_KEY` (hoặc `OPENAI_API_KEY`)
- [ ] Docker Postgres running: `docker ps` thấy `pio_lab_postgres`
- [ ] Python deps installed: `pip list | grep langgraph`
- [ ] Push lên GitHub (cho Background Agents): `git remote -v`
- [ ] Background Agents enabled (Settings → Beta)

---

## 🚀 Câu lệnh đầu tiên trong Cursor

Sau khi setup xong, mở Cursor → Ctrl+L → paste:

```
Đọc @.cursorrules @CODEX_HANDOFF.md @PROGRESS.md @STRUCTURE.md.

Sau khi hiểu, bắt đầu M0 — Foundation:
1. Plan briefly
2. Implement theo acceptance criteria
3. Write tests
4. Run pytest
5. Update @PROGRESS.md
6. Git commit "M0: Foundation"
7. Báo cáo

Tiếng Việt khi báo cáo.
```

Cursor sẽ tự chạy. Bạn ngồi xem, review từng change, accept khi OK.

Sau khi M0 done → gõ `"Tiếp tục M1"` → repeat.

---

## 📚 Reference

- Cursor docs: https://docs.cursor.com
- Background Agents: https://cursor.com/automations
- Cursor Pro features: https://cursor.com/pricing
- Community Discord: https://discord.gg/cursor

---

*File này companion với `CODEX_HANDOFF.md`. Đọc cả 2 trước khi bắt đầu.*
