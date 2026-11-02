# 管理端规则包中心设计

## 目标

让非技术内容维护人员可以导入、编辑、校验、提交复核和发布版本化规则包，同时保持运行时代码与法律内容分离。

## 版本生命周期

```text
draft
→ pending_review
→ approved
→ published
→ retired
```

驳回状态为 `rejected`。被驳回的规则包可以重新编辑并再次提交。

规则：

- 只有 `draft` 和 `rejected` 可以修改内容。
- 只有 `draft` 和 `rejected` 可以提交复核。
- 只有 `pending_review` 可以批准或驳回。
- 只有 `approved` 可以发布。
- 发布某个规则包时，同一 `package_id` 的旧已发布版本自动停用。
- 运行时只读取最新 `published` 版本。
- 没有已发布版本时，回退到内置 `pending_review` 规则包。

## 数据模型

新增 `RulePackage`：

- `id`
- `package_type`，当前固定为 `workflow`
- `package_id`
- `version`
- `status`
- `content_json`
- `checksum`
- `created_by_id`
- `reviewed_by_id`
- `created_at`
- `updated_at`
- `published_at`

`package_id + version` 唯一。

`content_json` 使用现有 `WorkflowRulePackage` 校验，避免管理端内容和运行时引擎出现两套结构。

## API

管理端接口：

- `GET /admin/rule-packages`
- `GET /admin/rule-packages/template`
- `POST /admin/rule-packages/validate`
- `POST /admin/rule-packages/import`
- `GET /admin/rule-packages/{id}`
- `PUT /admin/rule-packages/{id}`
- `POST /admin/rule-packages/{id}/submit`
- `POST /admin/rule-packages/{id}/review`
- `POST /admin/rule-packages/{id}/publish`
- `POST /admin/rule-packages/{id}/retire`

导入和编辑只能接受通过 Schema 与引用完整性校验的内容。

## 管理端页面

在管理后台侧边栏新增“规则包”子菜单，并新增独立页面区域：

- 规则包版本列表与状态。
- 下载内置模板。
- 上传 JSON 规则包。
- 在线编辑 JSON。
- 校验结果和结构摘要。
- 保存草稿、提交复核、批准、驳回、发布和停用。
- 显示版本、校验摘要、更新时间和发布状态。

本阶段不支持 Excel 导入和 AI 生成。后续把两种入口都转换为同一个 JSON Schema，复用本页校验与发布流程。

## 运行时

工作流服务接收可选规则包。路由优先读取数据库最新已发布版本，读取或校验失败时回退内置规则包，并保持现有 API 兼容。

## 测试

- 非管理员不能访问规则包管理接口。
- 非法规则包无法导入或保存。
- 状态流转不符合规则时返回 `409`。
- 发布新版本会自动停用旧版本。
- 运行时优先使用已发布版本。
- 没有发布版本时回退内置规则包。
- 管理端页面可下载模板、导入、校验并展示版本。
