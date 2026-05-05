# Safe Refactor Template

## Prompt cho refactor 1 module mà không phá thứ khác

```
@<module to refactor> @<callers of this module>

Refactor mục tiêu: {GOAL}

Quy tắc safe refactor:

1. **Identify scope:**
   - File chính refactor: {FILE}
   - Public API có đổi không? (List exact methods/signatures changed)
   - Callers cần update? (search via @codebase)

2. **Plan in 3 steps:**
   - Step A: Add new code (parallel với old)
   - Step B: Migrate callers từng cái 1
   - Step C: Remove old code

3. **Tests as safety net:**
   - Trước khi refactor: confirm all current tests pass
   - Sau mỗi step: re-run full suite
   - Add new tests cho new behavior

4. **Don't:**
   - ❌ Big-bang refactor (sửa 20 files cùng lúc)
   - ❌ Refactor + add feature trong 1 commit
   - ❌ Đổi behavior mà không update tests
   - ❌ Lan ra ngoài scope (vd refactor module A → "tiện sửa luôn module B")

5. **Do:**
   - ✅ Atomic commits (1 commit = 1 logical change)
   - ✅ Backward-compat alias trong giai đoạn migrate
   - ✅ Update docstrings + type hints khi đổi signature
   - ✅ Update CODEX_HANDOFF.md nếu architecture change

6. **Approval gate:**
   - Nếu refactor đụng vào @.cursor/rules/architecture-lock.mdc protected items → STOP, ask Sếp Linh

Output:
- Diff (organized: new code → migrate → cleanup)
- Test results sau mỗi step
- List callers updated
- Reasoning ngắn cho mỗi decision
```

## Common refactor patterns

### Rename function/method

```python
# Step A: alias + deprecation warning
def new_name():
    ...

def old_name():
    """Deprecated. Use new_name()."""
    import warnings
    warnings.warn("old_name() deprecated, use new_name()", DeprecationWarning, stacklevel=2)
    return new_name()
```

### Change function signature

```python
# Step A: support both
def my_func(*, new_param: str = None, old_param: str = None):
    if old_param is not None:
        # backward compat
        new_param = convert(old_param)
    ...
```

### Move class to different module

```
# Step A: move class to new module
# Step B: keep import alias trong module cũ
# old_module.py
from new_module import MyClass  # noqa: F401  alias for backward compat
```

## Xác định callers

```
Search trong codebase:
@codebase grep_search "func_name"
```
hoặc
```
Cmd+Shift+F → "func_name" → liệt kê callers
```
