# 架构说明

当前项目采用模块化单体架构：

```text
Vue 3 Web
    |
Nginx
    |
FastAPI
    |-- PostgreSQL + pgvector
    |-- Redis / Celery
    |-- MinIO
    `-- AI / OCR Provider
```

首期不拆分微服务。案件、证据、文书、律师和审计模块在同一个 API 服务内按领域分包，通过清晰的 service 和 repository 边界保持可拆分性。

## 当前已实现

- 前后端目录与依赖管理。
- API 版本前缀 `/api/v1`。
- 健康检查和统一配置读取。
- PostgreSQL 异步连接和 Alembic 初始迁移。
- Celery 任务入口、同步/异步任务边界。
- 本地对象存储与 MinIO/S3 适配器。
- Vue 路由、状态管理和法律风格工作台。
- JWT 登录、用户角色和对象级案件访问控制。
- 案件、会话、消息、证据、文书、律师档案和审计日志模型。
- 本地 SQLite 演示数据库与自动演示数据。
- 多轮咨询上下文、证据提取、四性评估与缺口提示。
- 合同文本风险审查和三类法律文书草稿。
- TXT/DOCX/PDF 文书导出、版本和证据目录。
- 管理员案件分配、律师意见、服务记录和收益台账。
- AI 角色模拟、帮助目录、实名资料、匿名话题和管理后台。
- 请求 ID、认证接口限流、`/metrics`、备份与恢复脚本。
- Compose、CI、HTTPS 示例和生产部署文档。

## 仍需外部条件

- 生产 OCR 服务和扫描版 PDF 识别。
- 真实法律规则版本与程序期限提醒。
- 公开律师资质审核、在线支付和分账。
- Docker、PostgreSQL、Redis、MinIO 和 HTTPS 实机验证。
