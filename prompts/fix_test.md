# Fix Test (without breaking implementation)

## Prompt

```
@<test file> @<implementation file> @terminal

Test fail:
{paste output}

Yêu cầu:
1. **Hiểu vì sao fail** — đọc cả test và impl
2. **Quyết định**: bug ở test hay impl?
   - Bug ở test → sửa test
   - Bug ở impl → sửa impl (KHÔNG đổi acceptance criteria)
3. **Minimal change**:
   - KHÔNG refactor không liên quan
   - KHÔNG đổi public API trừ khi đó là root cause
4. **Verify**: chạy `pytest <file> -v` confirm pass
5. **No regression**: chạy full unit suite confirm

DON'T:
- ❌ Skip test (`@pytest.mark.skip`) — fix nó
- ❌ Quá relaxed assertion (vd `assert True` thay vì check thật)
- ❌ Mock thêm để giấu vấn đề
- ❌ Catch exception rộng để test pass
- ❌ Đổi acceptance criteria từ CODEX_HANDOFF.md

DO:
- ✅ Update assertion với expected value đúng
- ✅ Add fixture nếu missing setup
- ✅ Refactor test cho clearer nếu cần
- ✅ Add edge case test nếu phát hiện bug

Output:
- Root cause (1 câu)
- Diff (test or impl)
- Test pass: ✓
- Full suite still pass: ✓
```

## Khi cần thêm fixture

```
@tests/conftest.py

Test cần fixture mới: {fixture name + purpose}

Add fixture đúng cách:
1. Scope phù hợp (`function` default, `session` cho heavy)
2. Cleanup (`yield` + teardown)
3. Type hint rõ
4. Docstring 1 dòng

Vd:
```python
@pytest.fixture
async def db_session():
    """Async DB session, auto rollback after test."""
    async with async_session() as s:
        yield s
        await s.rollback()
```
```

## Khi test integration cần real service

```
@tests/integration/<test>

Test này cần real Claude API. Nếu CI không có key, gracefully skip:

```python
import os
import pytest

@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set, skipping integration test"
)
async def test_real_claude_call():
    ...
```
```
