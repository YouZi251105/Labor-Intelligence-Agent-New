# 规则包 Excel 中间层实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让管理员通过 Excel 下载、填写、导入和导出规则包，同时保留现有 JSON、可视化编辑、审核和发布流程。

**Architecture:** 新增独立 Excel 转换服务，把固定工作簿映射为现有 `WorkflowRulePackage`。路由只负责权限、文件读取和草稿写入，页面只负责上传下载和错误展示，规则引擎与数据库结构不变。

**Tech Stack:** FastAPI、Pydantic 2、openpyxl、Vue 3、TypeScript、Vitest、pytest、Playwright。

## Global Constraints

- JSON 始终是唯一机器格式。
- 仅接受 `.xlsx`，单文件不超过 5 MiB。
- 不执行宏、公式或外部链接。
- 工作簿固定使用中文工作表名和中文表头。
- 导入错误必须包含工作表名和 Excel 行号。
- 现有 JSON 与管理端可视化能力不能退化。
- Word 复核稿不在本计划内。

---

### Task 1: Excel 转换服务

**Files:**
- Create: `backend/app/services/rule_package_excel.py`
- Create: `backend/tests/test_rule_package_excel.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Produces: `export_rule_package_excel(content: dict[str, Any]) -> bytes`
- Produces: `import_rule_package_excel(data: bytes) -> dict[str, Any]`
- Produces: `RulePackageExcelError(errors: list[str])`

- [ ] **Step 1: Write failing round-trip and error-location tests**

```python
def test_rule_package_excel_round_trip() -> None:
    source = load_default_workflow_package().model_dump(mode="json")
    imported = import_rule_package_excel(export_rule_package_excel(source))
    package = WorkflowRulePackage.model_validate(imported)
    assert package.package_id == source["package_id"]
    assert len(package.nodes) == len(source["nodes"])


def test_excel_import_reports_sheet_and_row() -> None:
    source = load_default_workflow_package().model_dump(mode="json")
    workbook = load_workbook(BytesIO(export_rule_package_excel(source)))
    sheet = workbook["路径"]
    target_column = _header_index(sheet, "目标节点ID")
    sheet.cell(row=2, column=target_column, value="missing-node")
    buffer = BytesIO()
    workbook.save(buffer)
    with pytest.raises(RulePackageExcelError) as error:
        import_rule_package_excel(buffer.getvalue())
    assert "路径!F2" in str(error.value)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_rule_package_excel.py -q`

Expected: collection fails because `app.services.rule_package_excel` does not exist.

- [ ] **Step 3: Add the dependency**

```toml
"openpyxl==3.1.5",
```

```text
openpyxl==3.1.5
```

Run: `.\.venv\Scripts\python.exe -m pip install openpyxl==3.1.5`

- [ ] **Step 4: Implement the workbook contract**

固定工作表：

```python
SHEET_GUIDE = "填写说明"
SHEET_BASE = "基础信息"
SHEET_STAGES = "阶段"
SHEET_NODES = "节点"
SHEET_PATHS = "路径"
SHEET_REQUIREMENTS = "前置条件"
SHEET_DEADLINES = "期限规则"
SHEET_DICTIONARY = "数据字典"
```

导入器必须以文本读取单元格，拒绝公式，按路径 ID 组合条件和期限，收集全部可定位错误后再抛出 `RulePackageExcelError`。导出器必须锁定说明和表头、标记输入区域、增加下拉验证，并隐藏数据字典页。

- [ ] **Step 5: Run tests and verify GREEN**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_rule_package_excel.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/rule_package_excel.py backend/tests/test_rule_package_excel.py backend/pyproject.toml backend/requirements.txt
git commit -m "feat: add workflow rule package excel conversion"
```

### Task 2: 管理接口与权限

**Files:**
- Modify: `backend/app/routes/admin_rule_packages.py`
- Modify: `backend/app/schemas/rule_package.py`
- Modify: `backend/tests/test_rule_package_admin.py`

**Interfaces:**
- Consumes: `export_rule_package_excel(content: dict[str, Any]) -> bytes`
- Consumes: `import_rule_package_excel(data: bytes) -> dict[str, Any]`
- Produces: `RulePackageExcelErrorsResponse`

- [ ] **Step 1: Write failing API tests**

```python
def test_admin_can_download_excel_template_and_export_package() -> None:
    with TestClient(app) as client:
        headers = login(client, "admin", "Admin123!")
        template = client.get(
            "/api/v1/admin/rule-packages/template.xlsx",
            headers=headers,
        )
        assert template.status_code == 200
        assert template.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def test_worker_cannot_download_excel_template() -> None:
    with TestClient(app) as client:
        headers = login(client, "demo", "Demo123!")
        response = client.get(
            "/api/v1/admin/rule-packages/template.xlsx",
            headers=headers,
        )
        assert response.status_code == 403
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_rule_package_admin.py -q`

Expected: new routes return `404` before implementation.

- [ ] **Step 3: Implement binary responses and multipart import**

路由返回：

```python
Response(
    content=export_rule_package_excel(content),
    media_type=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
)
```

新增：

```text
GET  /api/v1/admin/rule-packages/template.xlsx
GET  /api/v1/admin/rule-packages/{package_id}/export.xlsx
POST /api/v1/admin/rule-packages/import-excel
```

导入只接受 `.xlsx`、不超过 5 MiB。转换结果继续调用 `validate_workflow_package()`；成功后复用现有草稿创建和审计逻辑。

- [ ] **Step 4: Run all admin rule tests**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/test_rule_package_admin.py tests/test_rule_package_excel.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/admin_rule_packages.py backend/app/schemas/rule_package.py backend/tests/test_rule_package_admin.py
git commit -m "feat: expose rule package excel endpoints"
```

### Task 3: 管理端 Excel 操作

**Files:**
- Modify: `frontend/src/api/http.ts`
- Modify: `frontend/src/components/RulePackageCenter.vue`
- Modify: `frontend/src/styles/base.css`
- Create: `frontend/src/components/RulePackageCenter.test.ts`

**Interfaces:**
- Produces: `apiFile(path: string, init?: RequestInit): Promise<Blob>`
- Consumes: Excel template, export and import endpoints from Task 2.

- [ ] **Step 1: Write failing helper tests**

```typescript
it('rejects a binary download when the API returns JSON errors', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ detail: '无权限' }), {
      status: 403,
      headers: { 'Content-Type': 'application/json' },
    }),
  ))
  await expect(apiFile('/admin/rule-packages/template.xlsx')).rejects.toThrow('无权限')
})
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd frontend; npm test -- RulePackageCenter.test.ts`

Expected: `apiFile` is not exported.

- [ ] **Step 3: Implement the binary helper**

`apiFile()` 复用现有 Token 和 API 地址，默认 `Accept` 为 Excel MIME。非 2xx 时读取现有 JSON 错误格式并抛出 `ApiError`。

- [ ] **Step 4: Add three visible actions**

工具栏加入：

```text
下载 Excel 模板
导出当前 Excel
导入 Excel
```

导入使用 `FormData` 调用 `/admin/rule-packages/import-excel`，成功后刷新列表并选中新草稿。失败时将 `detail.errors` 逐行展示。

- [ ] **Step 5: Run tests and build**

Run: `cd frontend; npm test -- RulePackageCenter.test.ts`

Run: `cd frontend; npm run build`

Expected: tests and production build pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/http.ts frontend/src/components/RulePackageCenter.vue frontend/src/components/RulePackageCenter.test.ts frontend/src/styles/base.css
git commit -m "feat: add excel actions to rule package center"
```

### Task 4: 模板产物、文档和契约同步

**Files:**
- Create: `docs/admin/规则包Excel填写说明.md`
- Create: `docs/templates/规则包填写模板.xlsx`
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `docs/product/当前功能与边界.md`
- Modify: `docs/admin/管理员使用手册.md`
- Modify: `docs/api/API概览.md`
- Modify: `docs/api/接口契约_v1.md`
- Modify: `docs/development/开发与测试指南.md`
- Regenerate: `docs/api/openapi.v1.json`

**Interfaces:**
- Consumes: 三个接口和固定工作簿契约。

- [ ] **Step 1: Generate the template workbook**

使用后端导出器生成 `docs/templates/规则包填写模板.xlsx`。用 openpyxl 读取并断言工作表、表头、验证规则和输出内容。

- [ ] **Step 2: Update current documents**

修正产品文档中“在线编辑属于后续阶段”的旧表述，明确：

```text
当前支持 JSON 导入、可视化编辑、Excel 模板下载、Excel 导入和 Excel 导出；
Word 复核稿与 AI 辅助生成属于后续阶段。
```

管理员手册必须完整写出下载、填写、导入、错误处理、送审、批准、发布和导出的操作顺序。

- [ ] **Step 3: Export OpenAPI**

Run: `cd backend; .\.venv\Scripts\python.exe scripts\export_openapi.py`

Expected: `docs/api/openapi.v1.json` 包含三个新路径。

- [ ] **Step 4: Check documentation consistency**

Run: `rg -n "Excel|JSON|后续阶段" README.md docs/admin docs/product docs/api`

Expected: 不再出现“Excel 尚未实现”的旧描述。

- [ ] **Step 5: Commit**

```bash
git add README.md docs
git commit -m "docs: document excel rule package workflow"
```

### Task 5: 全量验证、合并和部署

**Files:**
- No production file changes expected.

- [ ] **Step 1: Run backend tests**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest -q`

- [ ] **Step 2: Run backend quality checks**

Run: `cd backend; .\.venv\Scripts\python.exe -m ruff check app tests`

Run: `cd backend; .\.venv\Scripts\python.exe -m mypy app`

- [ ] **Step 3: Run frontend checks**

Run: `cd frontend; npm test -- --run`

Run: `cd frontend; npm run build`

- [ ] **Step 4: Run focused browser verification**

启动验证栈，登录管理员，验证模板下载、导出、导入成功和错误提示，并检查 1366×768、1920×1080 和移动端。

- [ ] **Step 5: Merge and push**

```bash
git switch main
git merge --ff-only codex/excel-rule-package
git push origin main
```

- [ ] **Step 6: Update validation server**

服务器无法直连 GitHub 时使用本地 Git bundle 快进，重建隔离 Compose 栈，验证健康接口和三个 Excel 接口。
