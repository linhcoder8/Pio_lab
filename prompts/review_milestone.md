# Review Milestone Template

## Prompt cho review code agent vừa làm

```
Tôi vừa nhận PR cho M{N}. Hãy review chất lượng code.

Đọc:
- @<files changed in PR>
- @CODEX_HANDOFF.md section M{N} (acceptance criteria)
- @.cursor/rules/*.mdc (conventions)

Review checklist:

1. **Architectural integrity:**
   - Có vi phạm @.cursor/rules/architecture-lock.mdc không?
   - Layer dependency direction đúng không?
   - Có tạo file ngoài cấu trúc không?

2. **Code quality:**
   - Type hints đầy đủ?
   - Async pattern đúng?
   - Error handling có?
   - No print(), no hardcoded keys?

3. **Acceptance criteria:**
   - Có cover hết tất cả criteria trong section M{N}?
   - Tests reflect criteria?

4. **Provider routing:**
   - Có call SDK trực tiếp không (vi phạm @.cursor/rules/provider-routing.mdc)?
   - Routing keys khớp `config/providers.yaml`?

5. **Security:**
   - Có path validation cho file ops?
   - Secrets không bị log/return?
   - Sensitive actions có gate Human Approval?

6. **Tests:**
   - Coverage đạt target trong @.cursor/rules/testing.mdc?
   - Mock đúng cách?
   - Integration test (nếu có) thực sự chạy?

7. **Documentation:**
   - Docstrings rõ ràng?
   - PROGRESS.md updated đúng?

8. **Performance:**
   - N+1 queries?
   - Sync code trong async function?
   - Memory leaks?

Output:
- ✅ Verdict: APPROVE / REQUEST_CHANGES
- 🔴 Critical issues (must fix)
- 🟡 Suggestions (nice to have)
- 🟢 Praise (good patterns dùng làm template sau)
```

## Quick spot check (5 phút thay vì full review)

```
@<3-5 file ngẫu nhiên trong PR>

Spot check:
1. File có làm đúng job nó claim?
2. Imports clean?
3. Test cho file này tồn tại?
4. Bug logic dễ thấy?

Output: 1-2 dòng mỗi file. Nếu nghi ngờ → flag để full review.
```
