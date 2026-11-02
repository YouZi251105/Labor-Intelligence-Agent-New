# API 概览

版本：0.2.0 Demo
Base URL：`http://127.0.0.1:8000/api/v1`  
Swagger：<http://127.0.0.1:8000/docs>

## 1. 认证

除注册、登录和健康检查外，接口需要：

```http
Authorization: Bearer <access_token>
```

### 登录

```http
POST /auth/login
Content-Type: application/json

{
  "username": "demo",
  "password": "Demo123!"
}
```

响应：

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": 3,
    "username": "demo",
    "role": "user",
    "display_name": "演示用户",
    "phone": "",
    "created_at": "..."
  }
}
```

## 2. 系统

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/health` | 健康检查 | 公开 |

## 3. 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 注册普通用户 |
| POST | `/auth/login` | 登录 |
| GET | `/auth/me` | 当前用户 |

## 4. 案件与咨询

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/cases` | 创建案件 |
| GET | `/cases` | 当前角色可访问案件 |
| GET | `/cases/{case_id}` | 案件详情 |
| GET | `/cases/{case_id}/messages` | 案件消息历史 |
| POST | `/cases/{case_id}/consultations` | 多轮咨询 |
| GET | `/cases/{case_id}/workflow` | 决策树节点、可用路径和期限提示 |
| POST | `/cases/{case_id}/transitions` | 选择路径并保存决策记录 |

### 创建案件

```json
{
  "title": "工地欠薪咨询",
  "dispute_type": "wage",
  "location": "上海市",
  "facts": "在工地工作三个月，老板拖欠工资。"
}
```

### 发起咨询

```json
{
  "message": "老板已经两个月没有发工资，我该怎么办？"
}
```

响应包含：

- 更新后的案件。
- 用户消息。
- AI 消息。
- 问题分类。
- 建议下一步。
- 是否为演示规则。

## 5. 证据与合同

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/cases/{case_id}/evidence` | 材料列表和缺口评估 |
| POST | `/cases/{case_id}/evidence` | multipart 上传材料 |
| POST | `/cases/{case_id}/evidence/{evidence_id}/extract` | 重新提取文本 |
| GET | `/cases/{case_id}/evidence/{evidence_id}/download` | 下载原始材料 |
| GET | `/cases/{case_id}/evidence-assessment` | 证据四性评估 |
| POST | `/cases/{case_id}/contract-review` | 合同文本审查 |
| POST | `/cases/{case_id}/contract-review/file` | 合同文件提取审查 |

上传字段：

```text
file
```

合同审查：

```json
{
  "text": "合同全文或关键条款"
}
```

## 6. 文书

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/cases/{case_id}/documents` | 文书列表 |
| POST | `/cases/{case_id}/documents` | 生成文书 |
| GET | `/cases/{case_id}/documents/{document_id}/download` | 下载 TXT |
| GET | `/cases/{case_id}/documents/{document_id}/export` | 导出 DOCX/PDF |
| POST | `/cases/{case_id}/documents/{document_id}/revisions` | 保存新版本 |

生成参数：

```json
{
  "doc_type": "arbitration"
}
```

可选值：

- `arbitration`
- `complaint`
- `settlement`

## 7. 律师

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/lawyer/cases` | 已分配案件 | 律师 |
| GET/POST | `/lawyer/opinions`、`/lawyer/cases/{id}/opinions` | 律师意见 | 律师 |
| GET/POST | `/lawyer/service-records` | 服务记录 | 律师 |
| PATCH | `/lawyer/service-records/{id}/status` | 更新服务状态 | 律师 |
| GET/POST | `/lawyer/revenue` | 收益台账 | 律师 |

## 8. 管理

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/admin/stats` | 数据统计 | 管理员 |
| GET | `/admin/dashboard` | 运营数据大屏聚合数据 | 管理员 |
| GET | `/admin/users` | 用户列表 | 管理员 |
| GET | `/admin/users/manage` | 用户分页、搜索和筛选 | 管理员 |
| GET | `/admin/users/{user_id}` | 用户脱敏详情 | 管理员 |
| POST | `/admin/users/{user_id}/reset-password` | 重置密码 | 管理员 |
| PATCH | `/admin/users/{user_id}/status` | 启用或停用账号 | 管理员 |
| GET | `/admin/lawyers` | 律师列表 | 管理员 |
| GET | `/admin/cases` | 全部案件 | 管理员 |
| POST | `/admin/cases/{case_id}/assign` | 分配律师 | 管理员 |
| GET | `/admin/materials` | 材料元数据 | 管理员 |
| GET | `/admin/audit-logs` | 审计日志 | 管理员 |
| GET/PATCH | `/admin/rules`、`/admin/rules/{id}` | 规则复核 | 管理员 |
| GET | `/admin/rule-packages` | 规则包版本列表 | 管理员 |
| GET | `/admin/rule-packages/template` | 下载内置规则包模板 | 管理员 |
| POST | `/admin/rule-packages/validate` | 校验规则包结构和引用 | 管理员 |
| POST | `/admin/rule-packages/import` | 导入新草稿版本 | 管理员 |
| GET/PUT | `/admin/rule-packages/{id}` | 查看或编辑草稿 | 管理员 |
| POST | `/admin/rule-packages/{id}/submit` | 提交复核 | 管理员 |
| POST | `/admin/rule-packages/{id}/review` | 批准或驳回 | 管理员 |
| POST | `/admin/rule-packages/{id}/publish` | 发布规则包 | 管理员 |
| POST | `/admin/rule-packages/{id}/retire` | 停用规则包 | 管理员 |
| PATCH | `/admin/lawyers/{id}/status` | 律师状态 | 管理员 |
| GET | `/admin/service-records`、`/admin/revenue` | 服务与收益 | 管理员 |
| PATCH | `/admin/revenue/{id}/status` | 收益状态 | 管理员 |

分配参数：

```json
{
  "lawyer_id": 2
}
```

## 9. 模拟、帮助与历史

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/cases/{case_id}/simulations` | 模拟会话 |
| GET | `/cases/{case_id}/simulations/{session_id}` | 模拟详情 |
| POST | `/cases/{case_id}/simulations/{session_id}/messages` | 发送表达并评分 |
| GET | `/help/resources` | 仲裁、法院和法律援助入口 |
| GET | `/help/site-lawyers` | 本站律师 |
| GET/PUT | `/users/me/profile` | 实名资料 |
| GET | `/analytics/history` | 当前用户历史 |
| GET | `/analytics/topics` | 匿名纠纷类型聚合 |

## 10. 错误格式

FastAPI 默认错误格式：

```json
{
  "detail": "错误说明"
}
```

常见状态码：

- `400`：参数或文件不符合要求。
- `401`：未登录或登录失效。
- `403`：角色权限不足。
- `404`：资源不存在或无权访问。
- `409`：用户名或材料重复。
- `500`：服务端异常。

## 11. 当前版本说明

- 新增字段保持 v1 向后兼容，破坏性变更必须使用新版本。
- 文书支持 TXT、DOCX 和 PDF 导出。
- TXT、可复制 PDF 和 DOCX 支持文本提取；图片 OCR 取决于本机或外部 Provider。
- 未提供 WebSocket，AI 回复当前为普通 JSON。
- 审计查询已提供管理员接口；生产环境仍需补充限流、监控和更细粒度权限。
