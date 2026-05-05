# 🎯 Pio_lab — Task Scenarios for Testing

> 10 scenarios để Codex test end-to-end khi implement xong từng milestone.
> Sắp xếp từ đơn giản → phức tạp.

**Cách dùng:**
- M0-M3: chạy scenario 1 (Q&A đơn giản, no tools)
- M4-M6: chạy scenarios 1-2
- M7-M9: chạy scenarios 1-5
- M10-M11: chạy tất cả 10

Mỗi scenario có:
- **Input** (User gõ gì)
- **Expected Plan** (Chief of Staff phân tích thế nào)
- **Departments involved**
- **Tools used**
- **Provider routing**
- **Expected Output**
- **Edge cases / What can go wrong**

---

## Scenario 1: Simple Q&A (Fast Path)

> Test M0-M3: chỉ cần Provider Router work.

### Input
```
"Adaptive optics là gì?"
```

### Expected Plan
- Chief of Staff: classify intent = "casual_qa", set `fast_path=True`
- Skip dispatch → trả lời ngay

### Departments
- (none — fast path)

### Tools
- (none)

### Provider Routing
- Key: `chief_of_staff`
- Try: `claude-opus-4-6` → `gpt-4o` → `gemini-2.0-pro`

### Expected Output
- Telegram/Web reply: 1-2 đoạn giải thích về adaptive optics
- Length: ~150-300 từ
- Markdown formatting OK

### Edge cases
- Provider chính fail → router fallback (test bằng cách remove ANTHROPIC_API_KEY temporarily)
- Output dài hơn 4096 chars → Telegram chunk thành nhiều messages

### Acceptance criteria
- [ ] Reply trong < 5 giây
- [ ] Trace logged trong Postgres `traces` table với đúng provider used
- [ ] Conversation log trong `conversations` table với role=user và role=assistant

---

## Scenario 2: Single Department — Code Generation

> Test M3-M9: full path qua 1 phòng ban.

### Input (Web UI)
```
"Viết FastAPI endpoint POST /users với validation Pydantic.
Schema: name (str, 1-100), email (EmailStr), age (int, >=18).
Return user_id sau khi tạo."
```

### Expected Plan
```yaml
intent: code_generation
fast_path: false
plan:
  - department: coder
    worker: backend
    task: "Viết FastAPI endpoint POST /users với Pydantic validation"
    deps: []
  - department: qa
    worker: qa_reviewer
    task: "Review code: spec match, security, format"
    deps: [0]
```

### Departments
- CODER → backend worker
- QA → qa_reviewer

### Tools
- `file_write` (để tạo file users.py)
- `shell_exec` (chạy `python -c "import users"` để verify syntax)

### Provider Routing
- `coder.backend` → `gpt-4o` → `deepseek-coder` → `qwen2.5-coder:32b`
- `qa.qa_reviewer` → `claude-opus-4-6` → `gemini-2.0-pro`

### Expected Output
```python
# users.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

router = APIRouter()

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(..., ge=18)

@router.post("/users", response_model=dict)
async def create_user(user: UserCreate):
    # TODO: persist to DB
    user_id = ...
    return {"user_id": user_id}
```

QA verdict: PASS (or NEEDS_FIX với detailed feedback)

### Edge cases
- Backend worker quên import `EmailStr` → QA catch → trigger replan
- Tool `file_write` bị block bởi Security (path ngoài project) → Worker phải retry với path hợp lệ

### Acceptance criteria
- [ ] File `users.py` được tạo trong workspace
- [ ] Code có syntax valid (Python parser pass)
- [ ] QA verdict = PASS
- [ ] Task archived trong Postgres + `vault/tasks/YYYY-MM-DD/<id>.md`

---

## Scenario 3: Research with Web Search

> Test web_search skill + paper retrieval.

### Input (Telegram)
```
"Tìm 3 paper mới (2024-2025) về wavefront sensing trong adaptive optics.
Tóm tắt mỗi paper trong 100 từ. Có DOI link."
```

### Expected Plan
```yaml
intent: research
plan:
  - department: research
    worker: optics
    task: "Search recent papers on wavefront sensing 2024-2025, summarize 3 papers"
  - department: qa
    worker: qa_reviewer
    task: "Verify factual accuracy + DOI valid"
    deps: [0]
```

### Tools
- `web_search` (Tavily/Google) hoặc `arxiv_search`
- `paper_pdf_read` (download + extract abstract)
- `obsidian_write` (lưu vào `vault/knowledge/optics/`)

### Provider Routing
- `research.optics` → `claude-opus-4-6` → `gemini-2.0-pro`

### Expected Output
```markdown
## 3 paper về wavefront sensing (2024-2025)

### 1. [Paper Title 1]
**DOI:** 10.xxxx/xxxx
**Authors:** ...
**Tóm tắt (100 từ):** ...

### 2. ...
### 3. ...
```

Plus: 3 notes trong `vault/knowledge/optics/wavefront_*.md` với cross-link.

### Edge cases
- Web search return 0 results → worker phải báo lỗi rõ, KHÔNG fabricate paper
- Paper có paywall → ghi rõ "abstract only, full text behind paywall"
- DOI format sai → QA catch

### Acceptance criteria
- [ ] Output có ít nhất 3 papers thật (verify DOI work)
- [ ] Không hallucination (cross-check với arxiv.org thực sự)
- [ ] 3 notes mới trong vault với hashtag `#optics #wavefront-sensing`

---

## Scenario 4: Content Creation (Blog Post + SEO)

> Test Media department.

### Input (Web UI)
```
"Viết blog post 800-1000 từ về 'Top 5 lợi ích của adaptive optics trong y học'.
Tone thân thiện, SEO target keyword: 'adaptive optics y học'.
Format markdown có headings, bullet points."
```

### Expected Plan
```yaml
plan:
  - department: research
    worker: optics
    task: "Tóm tắt ứng dụng adaptive optics trong y học (5 use cases chính)"
  - department: media
    worker: content
    task: "Viết blog post 800-1000 từ dựa vào research, SEO keyword 'adaptive optics y học'"
    deps: [0]
  - department: qa
    worker: qa_reviewer
    task: "Verify factual + SEO check (keyword density, headings)"
    deps: [1]
```

### Tools
- `web_search` (research stage)
- `seo_keyword_research` (Phase 2 — Phase 1 dùng prompt-based check)
- `file_write`

### Provider Routing
- Research: `claude-opus-4-6`
- Media.content: `claude-sonnet-4-6` → `gemini-2.0-flash`
- QA: `claude-opus-4-6`

### Expected Output
```markdown
# Top 5 lợi ích của Adaptive Optics trong Y học

Trong y học hiện đại, adaptive optics y học đang trở thành...

## 1. Nâng cao chẩn đoán bệnh võng mạc
...
## 2. ...
```

### Edge cases
- Blog dài quá 1000 từ → media worker phải tự cắt
- Keyword stuffing (mật độ > 3%) → QA flag

### Acceptance criteria
- [ ] Output 800-1000 từ
- [ ] Keyword "adaptive optics y học" xuất hiện 5-10 lần (1-1.5% density)
- [ ] H1/H2 hierarchy đúng
- [ ] Cross-department flow work (research output feed vào media input)

---

## Scenario 5: Image Generation

> Test Media.image_maker với DALL-E / Imagen.

### Input
```
"Tạo thumbnail YouTube cho video 'Adaptive Optics 101'.
Style: tech/scientific, dark blue + neon green, có text 'Adaptive Optics 101'.
1280x720."
```

### Expected Plan
```yaml
plan:
  - department: media
    worker: image_maker
    task: "Generate YouTube thumbnail 1280x720 với spec..."
```

### Tools
- `image_generation` (Gemini Imagen hoặc OpenAI DALL-E 3)
- `image_edit` (resize, add text overlay if needed)
- `file_write` (save PNG)

### Provider Routing
- `media.image_maker` → `gemini-2.0-pro` (Imagen integration) → fallback `gpt-image-1`

### Expected Output
- File `output/thumbnail_<id>.png` đúng resolution 1280x720
- Reply tóm tắt + image preview (Telegram inline image)

### Edge cases
- DALL-E rate limit → fallback Imagen
- Output không đúng aspect ratio → image_edit resize/crop
- Generated image có watermark provider → QA flag (cần postprocess strip)

### Acceptance criteria
- [ ] PNG file 1280x720 exists
- [ ] Image content match prompt (visual inspection)
- [ ] Cost log < $0.04 per image (DALL-E 3 standard)

---

## Scenario 6: PowerPoint Slide Creation

> Test Report department + anthropic-skills:pptx integration.

### Input
```
"Tạo presentation 10 slides về 'Adaptive Optics in Astronomy'.
Mỗi slide có: title, 3 bullet points, optional image suggestion.
Theme: dark, professional. Save as .pptx."
```

### Expected Plan
```yaml
plan:
  - department: research
    worker: optics
    task: "Tóm tắt 10 chủ đề adaptive optics in astronomy (mỗi chủ đề thành 1 slide)"
  - department: report
    worker: slide_word_web
    task: "Create .pptx với 10 slides từ research output, dark theme"
    deps: [0]
  - department: qa
    worker: qa_reviewer
    task: "Verify slide count, format, no truncated text"
    deps: [1]
```

### Tools
- `office_skill_pptx` (gọi anthropic-skills:pptx)
- `file_write`

### Provider Routing
- Report.slide_word_web: `claude-sonnet-4-6` (skill compatible)

### Expected Output
- File `output/adaptive_optics_astronomy.pptx`
- 10 slides, mỗi slide đúng template
- Reply: "✓ Đã tạo presentation 10 slides. [pptx file]"

### Edge cases
- Bullet point dài quá 1 dòng → wrap hoặc split
- Image placeholder không có image thực → để text "[Image: description]" thay vì broken link

### Acceptance criteria
- [ ] File `.pptx` mở được trong PowerPoint
- [ ] Đúng 10 slides
- [ ] Layout consistent
- [ ] No empty slides

---

## Scenario 7: Cross-Department Pipeline (Research → Content → Image)

> Test plan với nhiều dependencies.

### Input
```
"Tôi muốn tạo 1 bài đăng Instagram về 'Adaptive Optics':
- Caption 200-300 từ (dễ hiểu, có hashtag)
- 1 ảnh minh họa style flat illustration"
```

### Expected Plan
```yaml
plan:
  - department: research
    worker: optics
    task: "Tóm tắt adaptive optics đơn giản, 5 ý chính cho người không chuyên"
  - department: media
    worker: content
    task: "Viết caption Instagram 200-300 từ + 8-12 hashtag"
    deps: [0]
  - department: media
    worker: image_maker
    task: "Tạo flat illustration về adaptive optics, 1080x1080 (Instagram square)"
    deps: [0]
  - department: qa
    worker: qa_reviewer
    task: "Verify caption length, hashtag relevance, image-content match"
    deps: [1, 2]
```

### Notes
- Step 2 và 3 chạy **PARALLEL** (cả 2 chỉ depend vào step 0)
- Step 4 chờ cả 2 → aggregation point

### Provider Routing
- 4 routing keys khác nhau

### Expected Output
- 1 caption file (.md) + 1 image file (.png)
- Reply: bundle 2 file, ready để post

### Edge cases
- Image gen mất 30s, content gen mất 5s → Reporter phải đợi cả 2 (`asyncio.gather`)
- 1 trong 2 fail → replan với retry hoặc partial output

### Acceptance criteria
- [ ] Parallel execution thực sự (check timestamps)
- [ ] Total time < sum(steps) — proof of parallelism
- [ ] QA pass với cả 2 outputs

---

## Scenario 8: Replan Loop (QA Fail → Retry)

> Test replan logic.

### Input
```
"Viết function tính diện tích hình tròn bằng Python.
Yêu cầu: type hints đầy đủ, docstring, có test."
```

### Expected Flow

**Iteration 1:**
- CoS → CODER.backend → viết function (có thể quên test)
- QA → review → verdict NEEDS_FIX (issue: "Missing test")
- Trigger replan

**Iteration 2 (replan):**
- CoS đọc QA feedback → adjust plan: "Add unit tests for circle_area"
- CODER.backend → viết tests
- QA → re-review → verdict PASS
- Continue to report

### Expected Output (final)
```python
def circle_area(radius: float) -> float:
    """Tính diện tích hình tròn.

    Args:
        radius: Bán kính, must be >= 0.

    Returns:
        Diện tích = pi * r^2.

    Raises:
        ValueError: nếu radius < 0.
    """
    import math
    if radius < 0:
        raise ValueError("Radius must be non-negative")
    return math.pi * radius ** 2


# tests
def test_circle_area():
    import pytest
    assert circle_area(0) == 0
    assert abs(circle_area(1) - 3.14159) < 0.001
    with pytest.raises(ValueError):
        circle_area(-1)
```

### Edge cases
- Replan loop infinite → max 3 retries (config), then give up
- QA luôn fail dù worker đã fix → có thể issue ở QA prompt, log warning

### Acceptance criteria
- [ ] Replan triggered đúng 1 lần
- [ ] Final output đầy đủ (function + tests)
- [ ] Retry counter tracked trong state
- [ ] Trace shows 2 iterations

---

## Scenario 9: Human Approval (Sensitive Action)

> Test Human-in-the-loop interrupt.

### Input (Telegram)
```
"Upload video 'optics_intro.mp4' lên YouTube với title 'Optics 101', tags optics,physics,education"
```

### Expected Flow

1. CoS plan: `media.video_maker` → `youtube_upload`
2. Pre-execute: detect `youtube_upload` ∈ `require_human_approval`
3. **Pause graph** + ask user:
   ```
   ⚠️ Hành động nhạy cảm — cần duyệt:
   Action: youtube_upload
   File: optics_intro.mp4
   Title: "Optics 101"
   Tags: optics, physics, education
   Visibility: Public

   Reply YES để duyệt, NO để hủy.
   ```
4. User reply "YES" → resume graph → execute upload
5. (User reply "NO" → abort with message)

### Tools
- `youtube_upload` (Google YouTube API)
- LangGraph `interrupt()`

### Provider Routing
- (CoS chỉ check policy, no LLM call cho approval logic)

### Expected Output
- After approval: "✓ Video uploaded. URL: youtube.com/watch?v=..."
- After reject: "✗ Hủy upload theo yêu cầu của bạn."

### Edge cases
- User không reply trong 10 phút → timeout, default = reject
- User reply không rõ ("ok"? "đồng ý"?) → CoS phải parse linh hoạt

### Acceptance criteria
- [ ] Graph thực sự pause (LangGraph state shows "interrupted")
- [ ] Resume work với user reply
- [ ] Reject path also work
- [ ] Action audit logged trong Postgres

---

## Scenario 10: Cron-Triggered Morning Brief

> Test cron + autonomous task.

### Trigger
- Cron: `0 7 * * *` (7am hàng ngày)
- Job name: `morning_brief`

### Expected Flow

1. Cron scheduler emit event → `morning_brief_handler`
2. Handler tạo synthetic request: `{"input": "Tạo morning brief: tin tức optics + crypto + AI hôm qua, 200 từ"}`, `user_id="cron"`, `channel="telegram"`
3. CoS dispatch:
   - RESEARCH.optics: tin optics
   - (extensible) RESEARCH.tech: tin AI/crypto (cần thêm worker)
   - MEDIA.content: tổng hợp 200 từ
4. QA → librarian → communicator
5. Communicator: gửi proactive Telegram message tới Sếp Linh

### Notes
- Đây là **autonomous task** — không có user request từ kênh
- Cần special handling trong communicator: push message thay vì reply

### Tools
- `web_search`
- Telegram `bot.send_message` (không reply, tự push)

### Expected Output (Telegram message lúc 7:01 AM)
```
🌅 Morning Brief — 04/05/2026

📡 Optics & Photonics:
- ...

🤖 AI:
- ...

💰 Crypto:
- ...

(Pio_lab tổng hợp lúc 07:01)
```

### Edge cases
- Cron fire khi không có internet → retry sau 5min
- Web search rate limited → reduce queries
- Empty results → message "Không có tin nổi bật hôm nay"

### Acceptance criteria
- [ ] Cron fire đúng giờ (manual test với schedule = "*/5 * * * *" để verify)
- [ ] Push message work (chứ không phải reply)
- [ ] Task archived như mọi task khác (user_id="cron")

---

## 🎬 Bonus: End-to-End Demo Script

Khi finish M11, chạy full demo:

```bash
# Terminal 1: start system
bash scripts/start_dev.sh

# Terminal 2: run scenarios
python scripts/demo_all_scenarios.py
```

Demo script chạy lần lượt 10 scenarios, output success/fail mỗi scenario, generate report HTML.

---

## 📈 Test Coverage Goals

| Scenario | Layers tested | Min coverage |
|---|---|---|
| 1 | L1 → L3 → L6 | 60% |
| 2 | L1 → L3 → L4 (CODER, QA) → L5 → L6 | 70% |
| 3 | L4 (RESEARCH, QA) + Obsidian write | 70% |
| 4 | Cross-dept (RESEARCH → MEDIA → QA) | 75% |
| 5 | MEDIA.image_maker + Image API | 65% |
| 6 | REPORT + anthropic-skills | 65% |
| 7 | Parallel dispatch (Media.content || Media.image) | 80% |
| 8 | Replan loop | 75% |
| 9 | Human approval interrupt | 70% |
| 10 | Cron + autonomous flow | 70% |

**Overall MVP target: 70% coverage** cho `pio_lab/core/` + `pio_lab/layer3_chief_of_staff/` + `pio_lab/providers/`.

---

*File này expand thêm khi có scenario mới (Phase 2+).*
