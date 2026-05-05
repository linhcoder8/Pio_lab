# Add New Department Template

> Dùng khi user yêu cầu thêm phòng ban mới (Phase 2+ hoặc extension).

## Prompt

```
User muốn thêm phòng ban mới:
- ID: {DEPT_ID}            (vd: "sales")
- Name: {DEPT_NAME}         (vd: "SALES")
- Tên VN: {NAME_VI}         (vd: "Bán hàng")
- Mô tả: {DESCRIPTION}
- Workers cần có: {LIST OF WORKERS}

Đọc:
- @docs/adding_departments.md
- @config/departments/_registry.yaml
- @config/departments/coder/department.yaml (template)
- @config/departments/coder/workers/frontend.yaml (worker template)

Thực hiện:

1. **Tạo department.yaml** ở `config/departments/{DEPT_ID}/department.yaml`
   - Copy structure từ existing dept
   - Customize id, name, name_vi, icon, color
   - System prompt phù hợp với role

2. **Tạo worker YAML(s)** ở `config/departments/{DEPT_ID}/workers/`
   - Mỗi worker 1 file
   - Set `provider_routing_key = "{DEPT_ID}.{WORKER_ID}"`
   - Define system_prompt, tools_enabled, max_iterations

3. **Update `config/departments/_registry.yaml`**:
```yaml
departments:
  - ...existing...
  - id: {DEPT_ID}
    name: {DEPT_NAME}
    name_vi: {NAME_VI}
    icon: {ICON}
    color: {COLOR}
    enabled: true
    config_path: ./config/departments/{DEPT_ID}/department.yaml
```

4. **Update `config/providers.yaml::routing_rules`**:
```yaml
routing_rules:
  {DEPT_ID}.{WORKER_ID}:
    - { provider: claude, model: claude-sonnet-4-6 }
    - { provider: codex, model: gpt-4o }
```

5. **Tạo Python module** (skeleton):
   - `pio_lab/layer4_departments/{DEPT_ID}/__init__.py`
   - `pio_lab/layer4_departments/{DEPT_ID}/department.py`:
```python
from pio_lab.layer4_departments.base.department_base import GenericDepartment
{DEPT_NAME_PASCAL}Department = GenericDepartment
```
   - `pio_lab/layer4_departments/{DEPT_ID}/workers/{WORKER_ID}_worker.py`:
```python
from pio_lab.layer4_departments.base.worker_base import GenericWorker
{WORKER_NAME_PASCAL}Worker = GenericWorker
```

6. **Test registry reload** (hot reload nếu enabled):
```python
# tests/integration/test_new_dept.py
async def test_new_department_loaded():
    registry = DepartmentRegistry(...)
    registry.load_all()
    assert "{DEPT_ID}" in registry.list_departments()
```

7. **Smoke test routing:**
```python
response = await router.call("{DEPT_ID}.{WORKER_ID}", [{"role": "user", "content": "test"}])
assert response is not None
```

8. **Update vault/AGENTS.md** (auto-regenerate):
```python
agents_md.regenerate(registry)
```

9. **Commit:** `Add {DEPT_NAME} department with {N} workers`

10. **Verify** trong UI Console (M11 done):
    - `/admin/org` page should show new dept
    - Click "+ Worker" để add thêm worker

DON'T:
- ❌ Hardcode department logic trong code (dùng YAML config)
- ❌ Skip update _registry.yaml (registry sẽ không load)
- ❌ Skip routing_rules (worker sẽ dùng default chain — có thể không phù hợp)
```

## Cách dùng từ CLI (alternative)

```bash
python scripts/add_department.py \
    --id {DEPT_ID} \
    --name {DEPT_NAME} \
    --vi "{NAME_VI}" \
    --icon "{ICON}" \
    --color "{COLOR}"

# Sau đó add worker:
python scripts/add_worker.py \
    --dept {DEPT_ID} \
    --id {WORKER_ID} \
    --name "{WORKER_NAME}"
```
