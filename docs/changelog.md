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
- 新增考点卡表和 Java 后端种子卡，供计划生成和评估使用。MySQL 面试笔记已整理为 43 张考点卡；Redis 面试笔记已整理为 32 张考点卡（含原有 4 张的更新）；Python 面试笔记已整理为 17 张考点卡；AI Agent 面试笔记已整理为 35 张考点卡（`agent.json` 25、`rag.json` 10）。复制、Cluster、哨兵等带 `distributed` 标签，可作为场景卡。
- 新增面试场次表和轮次表。登录后可创建面试、提交回答。
- 提交回答时一次 HTTP 跑完一张 `turn_graph`：评估、规则决定下一步、出下一问或报告。档案仍以 MySQL 为准，不用 LangGraph checkpointer。
- `interview_sessions` 增加可空 `report` 列，供结束后存放总分和阶段分。
- 登录后可 `GET /api/v1/interview-sessions` 查看自己的场次列表，支持按状态和创建时间过滤。结束后的总分来自已写入的 `report.score`。
- 进行中的场次可用 `PATCH /api/v1/interview-sessions/{id}` 标为 `abandoned` 中途结束。不生成报告，之后不能再作答。
- 新增 `POST /api/v1/users/session/refresh`：用刷新令牌换发新的访问令牌和刷新令牌，旧刷新令牌立即失效。不需要 `Authorization`。

### Changed

- 模拟面试对话改为气泡界面。提交回答时 `POST /api/v1/interview-sessions/{id}/turns` 可带 `Accept: text/event-stream`，评估后流式返回下一问。不带该头时仍返回 JSON。第一问在创建成功后由前端打字机展示。刷新或继续已有场次不再重放打字机。
- 创建面试场次的 `target_role` 改为固定取值：`Java 后端` / `Python 后端` / `AI Agent`。不再接受自由文本，不合法返回 `422`。不需要数据库迁移；历史场次仍按原文展示。
- 考点卡种子按主题拆到 `backend/data/topic_cards/`，不再使用单一的 `topic_cards.json`。导入脚本读取该目录下全部 JSON。岗位含 Python 时会打上 `python` 标签；含 Agent / LLM / 大模型 / AI 工程师时会打上 `ai`。简历技能里的 Python / Python3 归一到 `python`，LangChain / LangGraph / LLM 等归一到 `agent`，RAG / MCP 各归一到对应标签。
- 选卡不再按本场难度盖帽。简单场以 easy 为主并掺 medium；中等场 medium 为主并掺少量 easy/hard；困难场提高 hard 占比。某档不够用相邻难度补。策划挑出的三张卡会按同样规则校验。
- 接口成功时直接返回资源，不再使用 `code`、`message`、`data` 外壳。
- 每轮评估增加模型给出的分数和点评。代码按深度、跑题、「不会」钳制分数后写入；结束时按项目深挖、基础、场景加权得到总分，并写入 `interview_sessions.report`。进行中不返回点评；结束后 `GET /api/v1/interview-sessions/{id}` 优先读该列，旧场次现算后补写。

### Database / Deployment Notes

- 数据库迁移：在 `backend/` 执行 `alembic upgrade head`。顺序为 `cc267a266b69`（`users`）、`54098f4c206e`（`resumes`）、`3f212b686956`（`interview_sessions`）、`a41683e0a265`（`topic_cards`）、`1ce649d360ab`（`interview_turns`）、`c4f8a21b9d07`（`interview_sessions.report`）。当前 head 为 `c4f8a21b9d07`。`c4f8a21b9d07` 给场次表增加可空 JSON 列 `report`，进行中为 `NULL`，正常结束时写入。
- 种子数据：迁移完成后在 `backend/` 执行 `python scripts/import_topic_cards.py`，读取 `backend/data/topic_cards/*.json`，按 `key` upsert。当前 142 张（`mysql.json` 43、`redis.json` 32、`agent.json` 25、`python.json` 17、`rag.json` 10，其余按主题分文件）。跨文件 `key` 重复会导入失败。已有相同 `key` 且正文未变则跳过。
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
