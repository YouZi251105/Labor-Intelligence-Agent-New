# 可配置案件决策树与规则包设计

## 目标

把当前线性阶段流程升级为配置驱动的轻量决策树，同时为后续管理端维护法律内容建立稳定的规则包边界。

第一阶段交付：

- 版本化决策树规则包 Schema。
- 内置规则包及加载器。
- 多路径评估、前置条件阻止和路径持久化。
- 工作流 API 向后兼容扩展。
- 案件工作台路径选择、结果说明和期限提示。
- 规则复核状态展示；未经法学复核的内容不得显示为正式结论。

第一阶段不包含：

- BPMN 工作流引擎。
- 管理端规则在线编辑器。
- Excel 导入和 AI 辅助生成。
- 正式法律期限计算。
- 方言能力。

## 边界

代码负责解释规则，不负责在业务分支中硬编码具体法律内容。

规则内容以规则包保存。第一阶段从内置 JSON 文件加载，后续可把同一 Schema 持久化到数据库，由管理端导入、编辑和发布。

每个规则包必须包含：

- `schema_version`
- `package_id`
- `version`
- `jurisdiction`
- `review_status`
- `disclaimer`
- `stages`
- `start_node`
- `nodes`

规则包状态：

- `draft`
- `pending_review`
- `approved`
- `published`
- `retired`

第一阶段内置规则包状态为 `pending_review`，工作流页面必须显示待复核提示。

## 决策树模型

每个节点对应一个案件阶段，包含一个或多个选项。每个选项至少包含：

- 唯一 `id`
- 显示名称
- 目标阶段和节点
- 选择后的结果说明
- 下一步操作
- 前置条件
- 期限提示

第一阶段支持三类前置条件：

- `always`
- `evidence_ready`
- `lawyer_assigned`

条件不满足时返回可解释的阻止原因。API 不得仅依靠前端禁用按钮，必须在服务端再次校验。

## 期限模型

期限规则包含：

- 标题和说明
- 法律依据说明
- 起算事件
- 计算方式
- 复核状态

第一阶段仅允许 `manual_review_required`。即使以后增加天数计算，也只有 `approved` 或 `published` 的规则才能生成正式截止日期；待复核规则只显示“期限规则待复核”。

## API 兼容

保留 `GET /cases/{case_id}/workflow` 和 `POST /cases/{case_id}/transitions`。

`WorkflowResponse` 新增：

- `current_node`
- `decision_path`
- `rule_package`

`WorkflowOption` 新增：

- `id`
- `target_node`
- `outcome`
- `next_step`
- `deadlines`

`TransitionRequest` 新增可选 `option_id`。旧调用仍可只传 `target_stage`；同时传入时 `option_id` 优先。

路径写入 `Case.classification.workflow_choices`，记录选项、来源节点、目标节点、规则包版本和选择时间。

## 前端交互

案件概览中的流程卡显示：

- 当前节点
- 所有阶段状态
- 多个可选路径
- 每个路径的结果、下一步和期限提示
- 被阻止路径的原因
- 规则包复核状态和免责声明

按钮状态只用于交互提示，最终校验以服务端为准。

## 后续管理端阶段

第二阶段在管理端增加“规则包中心”：

- 上传、下载和预览规则包。
- 使用 Excel 模板作为非技术人员入口，后端转换为统一 JSON。
- 在线修改少量文案和选项。
- Schema 校验、引用完整性检查、路径冲突检查和差异预览。
- 草稿、提交复核、批准、发布和停用。
- 已发布版本不可修改，只能创建新版本。

第三阶段增加 AI 辅助：

- 自然语言或表格生成规则包草稿。
- AI 只能生成草稿，不能发布。
- 所有 AI 输出必须经过 Schema 校验和人工复核。

## 测试策略

- 规则包 Schema 接受内置规则包。
- 引用不存在的目标节点时加载失败。
- 同一节点允许多个选项。
- 证据不足和律师未分配时返回阻止原因。
- 旧 `target_stage` 请求保持兼容。
- 新 `option_id` 请求写入决策路径。
- 非法选项返回 400。
- 前端类型检查、构建和关键工作台 E2E。
