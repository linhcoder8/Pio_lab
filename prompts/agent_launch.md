# Background Agent Launch Template

> Copy template tương ứng → paste vào Cursor Background Agent "Task" field.

## Template 1: Single Milestone

```
Repository: Pio_lab
Task: Implement Milestone M{N} — {NAME}

CONTEXT (đọc trước):
- @.cursorrules
- @CODEX_HANDOFF.md (section M{N})
- @PROGRESS.md
- @MILESTONES_QUICK_REF.md
- @docs/PROVIDER_API_REFERENCE.md (nếu M3-M4)
- @docs/EXAMPLES.md (scenario tương ứng)
- @.cursor/rules/*.mdc

OBJECTIVE:
Implement đầy đủ M{N} với tất cả acceptance criteria pass.

DO:
1. Plan briefly (5-10 dòng) — file changes
2. Implement following all conventions
3. Write unit tests (1+ per criterion)
4. Run pytest tests/unit/test_<milestone>.py
5. Update PROGRESS.md
6. Commit "M{N}: {description}"
7. Push to branch m{N}-<short-name>
8. Create PR with description summarizing changes

DO NOT:
- Implement M{N+1} hoặc sau
- Phá architecture (xem @.cursor/rules/architecture-lock.mdc)
- Call SDK trực tiếp (qua ProviderRouter)
- Commit secrets

STOP CONDITIONS:
- All criteria pass + tests green → DONE
- Critical blocker → note in PROGRESS.md "Blockers" + stop
- Ambiguity > 30 phút stuck → note in PROGRESS.md "Questions for Sếp Linh" + stop

OUTPUT:
- PR link
- 1-paragraph summary in Vietnamese
- Test results
- Decisions made (if any)
```

## Template 2: Bug Fix

```
Repository: Pio_lab
Task: Fix bug in {FILE}

BUG REPORT:
{Symptom, expected vs actual, reproduction steps}

REFERENCES:
- @<file with bug>
- @<related test file>
- @CODEX_HANDOFF.md "Common Pitfalls" section

OBJECTIVE:
Fix bug với minimal change. KHÔNG refactor unrelated.

DO:
1. Reproduce bug locally (run test or scenario)
2. Identify root cause (1-2 hypothesis)
3. Implement fix
4. Add regression test (test that fails before fix, passes after)
5. Run full unit suite — confirm no regression
6. Commit "fix: {short description}"
7. Push branch fix-{short-name}, create PR

OUTPUT:
- Root cause analysis (3-5 sentences)
- Diff
- Test results before/after
```

## Template 3: Refactor

```
Repository: Pio_lab
Task: Refactor {MODULE} for {GOAL}

REFERENCES:
- @<module path>
- @<callers/dependents>
- @prompts/refactor.md (workflow)
- @.cursor/rules/architecture-lock.mdc

OBJECTIVE:
{Specific goal — vd "Extract DB session management to context manager"}

CONSTRAINTS:
- Preserve public API (or document breaking changes clearly)
- Atomic commits
- Tests pass at every step
- Update @CODEX_HANDOFF.md if architecture changes

DO:
1. Snapshot current behavior (run tests, save coverage report)
2. Implement refactor in 3 steps (add → migrate → remove)
3. Re-run tests after each step
4. Update related docs
5. Commit per step

DO NOT:
- Big-bang refactor
- Mix refactor with new feature
- Lan rộng ngoài scope
```

## Template 4: Documentation Update

```
Repository: Pio_lab
Task: Update documentation for {SCOPE}

OBJECTIVE:
{Specific update needed}

DO:
1. Identify affected docs:
   - README.md
   - CODEX_HANDOFF.md
   - docs/*.md
   - PROGRESS.md
2. Update với accurate info (verify by reading current code)
3. Cross-link related docs (use @ references)
4. Update STRUCTURE.md if file structure changed
5. Commit "docs: {description}"

DO NOT:
- Change code (chỉ docs)
- Outdated information
- Generic boilerplate (specific to Pio_lab)
```

## Template 5: Multi-Milestone Parallel (Power user)

```
Repository: Pio_lab
Task: Implement {LIST_INDEPENDENT_MILESTONES}

EXAMPLE: M1 + M2 + M5 (independent)

WARNING: Chỉ dùng cho milestones DECLARED INDEPENDENT trong @MILESTONES_QUICK_REF.md
Dependencies trong handoff doc PHẢI được respect.

DO:
1. Implement each milestone in separate branch:
   - m1-postgres
   - m2-obsidian
   - m5-security
2. Per milestone: full Template 1 workflow
3. Commit + PR per milestone (3 PRs total)
4. Update PROGRESS.md once at end

DO NOT:
- Mix milestone code in same commit
- Cross-reference between branches
```

## Tips chọn model cho Background Agent

| Loại task | Model recommend |
|---|---|
| Heavy implementation (M7, M9) | claude-opus-4-6 (best reasoning) |
| Bug fix simple | claude-sonnet-4-6 hoặc gpt-5-codex |
| Refactor | claude-opus-4-6 |
| Doc update | gpt-5 hoặc claude-haiku-4-5 (cost-effective) |
| Test writing | claude-sonnet-4-6 |
