# API 概览

版本：0.1.0 Demo  
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
| POST | `/cases/{case_id}/contract-review` | 合同文本审查 |

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

## 8. 管理

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/admin/stats` | 数据统计 | 管理员 |
| GET | `/admin/users` | 用户列表 | 管理员 |
| POST | `/admin/users/{user_id}/reset-password` | 重置密码 | 管理员 |
| GET | `/admin/lawyers` | 律师列表 | 管理员 |
| GET | `/admin/cases` | 全部案件 | 管理员 |
| POST | `/admin/cases/{case_id}/assign` | 分配律师 | 管理员 |

分配参数：

```json
{
  "lawyer_id": 2
}
```

## 9. 错误格式

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

## 10. 当前版本说明

- 接口尚无版本兼容策略。
- 文书只返回文本内容。
- 证据未接入 OCR。
- 未提供 WebSocket，AI 回复当前为普通 JSON。
- 生产环境需要补充限流、审计查询和更细粒度权限。
