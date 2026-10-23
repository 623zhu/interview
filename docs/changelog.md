# Changelog

本文件记录项目各版本的功能、修复、变更和已知问题，便于发布说明、回归测试和问题追踪。

## 维护规则

- 每次发布前更新本文件。
- 按版本号从新到旧排列。
- 使用 `Added`、`Changed`、`Deprecated`、`Removed`、`Fixed`、`Security` 分类。
- 面向使用者描述影响，不记录实现细节堆砌。
- 如果变更需要数据库迁移、配置修改或人工操作，必须在版本条目中明确说明。

## [Unreleased]

### Added

- 新增用户表，用于保存注册账号。邮箱不可重复，密码只存哈希。
- 新增简历表和上传、列表接口。登录后可上传 PDF / Word，服务端抽取文本并结构化。
- 新增考点卡表和 24 张 Java 后端种子卡，供计划生成和评估使用。
- 新增面试场次表和轮次表。登录后可创建面试、提交回答。
- 提交回答时一次 HTTP 跑完一张 `turn_graph`：评估、规则决定下一步、出下一问或报告。档案仍以 MySQL 为准，不用 LangGraph checkpointer。

### Changed

- 接口成功时直接返回资源，不再使用 `code`、`message`、`data` 外壳。

### Database / Deployment Notes

- 数据库迁移：在 `backend/` 执行 `alembic upgrade head`。顺序为 `cc267a266b69`（`users`）、`54098f4c206e`（`resumes`）、`3f212b686956`（`interview_sessions`）、`a41683e0a265`（`topic_cards`）、`1ce649d360ab`（`interview_turns`）。当前 head 为 `1ce649d360ab`，上述表均已建好。
- 种子数据：迁移完成后在 `backend/` 执行 `python scripts/import_topic_cards.py`，按 `key` upsert 24 张考点卡。
- 依赖：`backend/requirements.txt` 增加 `langgraph>=0.2.45`。进程启动时 `compile()` `turn_graph`，挂到 `app.state`。
- 回滚：`alembic downgrade -1` 会删除当前 head 对应的表及其数据。
- 配置变更：无。LangSmith 接入时再增加追踪相关环境变量。

## [版本号] 

### Added

- 新增功能：描述功能和适用场景。

### Changed

- 功能调整：描述行为变化和用户影响。

### Fixed

- 修复问题：描述问题表现和修复结果。

### Database / Deployment Notes

- 数据库迁移：无 / 说明迁移脚本或执行顺序。
- 配置变更：无 / 说明新增或修改的环境变量。
- 发布注意事项：无 / 说明上线前后的操作。

### Known Issues

- 当前已知问题及临时解决方案。

<!--
版本号建议遵循 SemVer：MAJOR.MINOR.PATCH，例如 1.2.0。
发布新版本时，将 [Unreleased] 中已完成的内容移动到新的版本标题下。
-->
