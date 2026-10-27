# 项目说明

本文件是仓库索引。按任务读取对应文档，文档正文留在原文件中。

## 文档索引

| 何时阅读 | 文件 |
| --- | --- |
| 创建或修改数据表、字段、约束、索引、迁移或 ORM 模型 | 先读 `docs/rules/database.md`，再把表设计写入 `docs/database.md` |
| 改接口、认证、请求响应或业务规则 | 先读 `docs/rules/API.md`，再读 `docs/api.md` |
| 设计或实现面试计划、追问、评估、题库或报告 | `docs/interview-design.md` |
| 记录发布说明、数据库迁移或配置变更 | `docs/changelog.md` |

## 维护

- 创建或修改数据表时，先读 `docs/rules/database.md`，并按其中的规则实现 ORM 模型和 Alembic 迁移。完成后把表、字段、关系、索引和迁移记录写入 `docs/database.md`。实际表结构以迁移脚本为准。
- 改接口前先读 `docs/rules/API.md`。接口遵循该文件中的 REST 约定。改完后同时更新路由、Pydantic 模型和 `docs/api.md`。规则有变化时更新规则文件。路径与字段以 OpenAPI 为准。
- 上述变更若需要迁移、改配置或人工操作，在 `docs/changelog.md` 写明。

## 代码位置

| 内容 | 路径 |
| --- | --- |
| 应用入口 | `backend/main.py` |
| 配置 | `backend/app/core/config.py`，环境变量在仓库根目录 `.env` |
| MySQL、Redis | `backend/app/infrastructure/` |
| 迁移 | `backend/alembic/` |
| 容器 | `compose.yaml`（MySQL、Redis、backend、frontend）；镜像定义在 `backend/Dockerfile`、`frontend/Dockerfile` |
