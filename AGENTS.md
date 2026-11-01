# Labor Intelligence Agent 开发协作指南

本文件供参与本仓库的开发者、AI 编码工具和代码审查工具读取。开始任何编码任务前，必须先阅读本文件和相关接口契约。

## 1. 项目定位

劳务通是面向基层劳动者的劳动纠纷法律服务平台。当前版本是可运行的业务 Demo，目标是逐步建设可用的内部试点。

首期范围：

- 中国法域、中文。
- 欠薪、违法解除、未签劳动合同、加班费、工伤待遇、劳务报酬六类纠纷。
- AI 咨询、案件、证据、合同、文书和内部律师协作。

不作为首期范围：

- 多语言、多法域、方言。
- 公开律师市场和自动分账。
- 自动立案、法院系统深度对接。
- 法医级合同、签章或笔迹鉴定。

## 2. 责任分工

### 开发 A：后端、AI、数据与安全

主要目录：

```text
backend/app/core/
backend/app/db/
backend/app/models/
backend/app/routes/auth.py
backend/app/routes/cases.py
backend/app/routes/admin.py
backend/app/routes/lawyer.py
backend/app/services/ai.py
backend/app/services/documents.py
backend/alembic/
```

负责：

- 数据模型、数据库迁移、权限、审计和对象存储。
- 案件状态机、接口契约、AI 结构化输出和测试集。
- OCR 适配、文书生成和导出。
- 后端测试、CI、部署和安全。

### 开发 B：前端、证据体验和产品交互

主要目录：

```text
frontend/src/
docs/user/
docs/lawyer/
docs/demo/
```

负责：

- Vue 页面、路由、状态、响应式和可访问性。
- 案件流程、证据验证展示、合同报告、文书编辑和律师端。
- 用户验收标准、演示脚本和业务文案。
- 前端单元测试和 Playwright。

证据上传、存储、文件权限和审计由 A 负责。B 负责独立的证据规则模块、规则样例、缺口判断、页面和验收，不在同一文件中与 A 并行修改。

### 法律内容负责人

不由两位开发兼任。负责：

- 法条、案例、纠纷分类、证据规则、期限和文书模板。
- 来源、生效日期、失效日期和版本复核。
- 法律风险与对外表述审核。

开发人员只负责数据结构、导入和展示，不自行确认法律内容正确性。

## 3. 强制规则

1. `main` 必须是可运行版本。
2. 禁止直接向 `main` 强推。阶段功能先进入 `integration/stage<N>`，再通过 Pull Request 合并。
3. 每个功能使用独立分支，并对应 `docs/development/分阶段分工与验收.md` 中的一个任务编号。
4. 修改接口前，必须先更新 `docs/api/接口契约_v1.md`。
5. 不得擅自修改对方主要目录中的业务代码。
6. 不得提交 `.env`、真实密钥、数据库、上传材料或用户隐私数据。
7. AI 输出必须有结构化校验和失败回退，不能直接修改案件状态。
8. 涉及真实案件材料时，必须使用脱敏样例测试。
9. 法律内容不得由开发工具自行补全或编造。
10. 合并前必须通过对应测试；关键流程必须通过端到端测试。

## 4. 接口契约

当前接口文档：

```text
docs/api/接口契约_v1.md
docs/api/openapi.v1.json
```

运行时文档：

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

规则：

- FastAPI 的 Pydantic Schema 是后端实现的权威来源。
- 前端类型必须与接口契约保持一致。
- 只允许增量添加字段；破坏性修改必须升级接口版本。
- 新增字段默认可选，发布后再逐步要求必填。
- 错误统一返回 `detail` 字段。
- 枚举值只能使用契约中列出的值。

## 5. 分支和提交

分支命名：

```text
feat/backend-<feature>
feat/frontend-<feature>
fix/backend-<bug>
fix/frontend-<bug>
docs/<topic>
chore/<topic>
```

提交格式：

```text
feat(scope): summary
fix(scope): summary
docs: summary
chore: summary
```

开始开发：

```powershell
git checkout main
git pull origin main
git checkout -b feat/backend-case-workflow
```

完成开发：

```powershell
git fetch origin
git rebase origin/main
git push -u origin <branch>
```

功能分支合并到集成分支使用 Pull Request + Squash Merge。集成分支通过回归后，再使用 Pull Request + Merge Commit 合并 `main`。

## 6. 常用命令

后端测试：

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

前端测试：

```powershell
cd frontend
npm run test
npm run typecheck
npm run build
npm run test:e2e
```

启动：

```text
start.bat
```

导出 OpenAPI：

```powershell
cd backend
.\.venv\Scripts\python scripts\export_openapi.py
```

## 7. 当前阶段

当前为“阶段 4：生产化”。

阶段 1 已完成并验收，验收提交为 `0b4f6ed`。
阶段 2 已完成并验收，集成分支提交为 `af66c06`。
阶段 3 已完成并验收，合并提交为 `823843c`。
阶段 4 代码、本地测试、迁移、部署配置和文档已完成；外部服务实机验证仍待 Docker、PostgreSQL、Redis 和 MinIO 环境。

阶段 4 聚焦：

1. 本地文件存储与 MinIO/S3 适配器。
2. 同步任务与 Celery 异步任务边界。
3. PostgreSQL 和 Alembic 初始迁移。
4. 请求 ID、限流、指标、日志和备份恢复。
5. Docker Compose、Nginx 和 CI。
6. 最终文档、移动端和全流程回归。

阶段 4 集成负责人为开发 B，开发 A 负责生产门禁。当前机器缺少 Docker、PostgreSQL、Redis 和 MinIO，外部服务实机验证必须标记为未执行。

## 8. AI 编码工具要求

AI 工具在修改代码前必须：

1. 阅读本文件。
2. 阅读 `docs/api/接口契约_v1.md`。
3. 确认当前任务编号、负责人和允许修改的文件。
4. 不修改任务范围外的文件。
5. 先补测试，再实现行为。
6. 同步更新接口文档、类型和用户可见错误提示。
7. 完成后报告修改文件、测试结果和未完成事项。

如果任务需要跨边界修改，先更新 `docs/development/两人并行开发约定.md` 或由负责人确认。
