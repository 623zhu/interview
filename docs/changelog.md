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
- 新增考点卡表和 Java 后端种子卡，供计划生成和评估使用。MySQL 面试笔记已整理为 70 张考点卡；Redis 面试笔记已整理为 62 张考点卡（含原有 4 张的更新）；Java 面试笔记已整理为 36 张考点卡；JVM 面试笔记已整理为 32 张考点卡；Spring 面试笔记已整理为 33 张考点卡；Python 面试笔记已整理为 69 张考点卡；AI Agent 面试笔记已整理为 64 张考点卡（`agent.json` 54、`rag.json` 10）。复制、Cluster、哨兵等带 `distributed` 标签，可作为场景卡。
- MySQL 考点卡从 43 张扩充到 70 张，补上索引失效、Read View、快照读/当前读、双 1、在线 DDL、分区、备份与 PITR、SKIP LOCKED 等网页高频考点。导入后执行 `python scripts/import_topic_cards.py`。
- Redis 考点卡从 32 张扩充到 62 张，补上 Stream 消费组、Bitmap、SCAN/UNLINK、延迟队列、限流、AOF 重写与刷盘、fork/COW、Hash Tag、MOVED/ASK、Cache-Aside、逻辑过期、哨兵 SDOWN/ODOWN 等网页高频考点。导入后执行 `python scripts/import_topic_cards.py`。
- Java 考点卡从 4 张扩充到 36 张，补上 HashMap 树化与扩容、ArrayList/LinkedList、ThreadLocal、AQS、CAS/ABA、JMM、锁升级、虚拟线程、CompletableFuture、DCL 单例等网页高频考点。导入后执行 `python scripts/import_topic_cards.py`。
- JVM 考点卡从 2 张扩充到 32 张，补上运行时数据区、元空间、TLAB、逃逸分析、类加载与双亲委派、可达性、三色标记、CMS/G1/ZGC、安全点、卡表/RSet、JIT、CPU 飙高与堆外占用排查等网页高频考点。导入后执行 `python scripts/import_topic_cards.py`。
- Spring 考点卡从 3 张扩充到 33 张，补上 IoC 注入、三级缓存、AOP 通知顺序、事务传播与 REQUIRES_NEW/NESTED、UnexpectedRollback、MVC 流程、Filter/Interceptor、Boot 自动配置与启动流程、条件注解、自定义 Starter、@Async 等网页高频考点。导入后执行 `python scripts/import_topic_cards.py`。
- Agent 考点卡从 25 张扩充到 54 张，补上 LangChain/LangGraph/LangSmith 分工、State 与 Reducer、条件边与 Command、Checkpointer、一次 HTTP 跑完一张图、interrupt 恢复与幂等、Send/子图/Supervisor、流式与观测、Plan-and-Execute、LCEL、Agentic RAG、护栏与模型路由等网页高频考点。导入后执行 `python scripts/import_topic_cards.py`。
- Python 考点卡从 17 张扩充到 47 张，补上 GIL 与是否仍需加锁、可变默认参数、传参模型、上下文管理器、asyncio 阻塞与 TaskGroup、WSGI/ASGI、FastAPI 分层与 def/async def/Depends、Pydantic v2、Django/Flask 选型与 ORM N+1、Celery 幂等、Gunicorn/Uvicorn worker 等网页高频考点。导入后执行 `python scripts/import_topic_cards.py`。
- Python 考点卡从 47 张扩充到 69 张，补上描述符、元类与 `__init_subclass__`、dataclass、lru_cache 泄漏、导入与循环导入、ABC/Protocol、内存泄漏与弱引用、contextvars、asyncio 超时取消、SQLAlchemy Session、FastAPI lifespan、Flask 请求上下文、pytest、性能排查、Django 事务与行锁等网页高频考点。导入后执行 `python scripts/import_topic_cards.py`。
- 新增面试场次表和轮次表。登录后可创建面试、提交回答。
- 提交回答时一次 HTTP 跑完一张 `turn_graph`：评估、规则决定下一步、出下一问或报告。档案仍以 MySQL 为准，不用 LangGraph checkpointer。
- `interview_sessions` 增加可空 `report` 列，供结束后存放总分和阶段分。
- 登录后可 `GET /api/v1/interview-sessions` 查看自己的场次列表，支持按状态和创建时间过滤。结束后的总分来自已写入的 `report.score`。
- 进行中的场次可用 `PATCH /api/v1/interview-sessions/{id}` 标为 `abandoned` 中途结束。不生成报告，之后不能再作答。
- 新增 `POST /api/v1/users/session/refresh`：用刷新令牌换发新的访问令牌和刷新令牌，旧刷新令牌立即失效。不需要 `Authorization`。
- 面试记录页接入 `GET /api/v1/interview-sessions`。可按状态筛选，点进详情看问答和报告；进行中的场次可继续作答。
- 后端启动后向标准输出写面试处理日志：创建场次、每轮结果、评估/出题重试，以及计划生成、简历解析、提交回答和发送验证码失败。不含回答原文和简历正文。
- `compose.yaml` 增加 backend、frontend 服务。`docker compose up -d --build` 一次拉起 MySQL、Redis、API 和前端。

### Fixed

- 面试下一问改为按字打出，避免 SSE 被代理攒齐后整段弹出。
- 结束后的对话记录不再把开场自我介绍套进每一问：前端消息编号按轮次递增；出题不再粘贴自我介绍原文。
- 接口时间改为带 `Z` 的 UTC。列表和首页不再把 UTC 当成本地时间，中国时区不再慢 8 小时。
- 下一问去掉「先到这儿」「换个方向聊聊」这类客套过渡。换阶段时直接提问；因答错或含糊而追问时，可以点出问题所在，仍不给标准答案、不报分数。

### Changed

- 浏览器标签从脚手架默认的 `Vite App` 改为各页面标题加「智面」。
- 工作台改版：首屏可直接选岗位开始面试；「本周表现」按项目深挖、基础、场景显示本周已完成场次的平均分，并给出最弱一项的建议；底部为本周练习、累计面试、近 30 天能力提升和最高得分。
- `GET /api/v1/interview-sessions` 每项增加 `stages`（各计分阶段的分数），来自已写入的 `report`。新增字段，不影响现有调用方。
- 模拟面试对话改为气泡界面。提交回答时 `POST /api/v1/interview-sessions/{id}/turns` 可带 `Accept: text/event-stream`，评估后流式返回下一问。不带该头时仍返回 JSON。第一问在创建成功后由前端打字机展示。刷新或继续已有场次不再重放打字机。
- 创建面试场次的 `target_role` 改为固定取值：`Java 后端` / `Python 后端` / `AI Agent`。不再接受自由文本，不合法返回 `422`。不需要数据库迁移；历史场次仍按原文展示。
- 考点卡种子按主题拆到 `backend/data/topic_cards/`，不再使用单一的 `topic_cards.json`。导入脚本读取该目录下全部 JSON。岗位含 Python 时会打上 `python` 标签；含 Agent / LLM / 大模型 / AI 工程师时会打上 `ai`。简历技能里的 Python / Python3 归一到 `python`，LangChain / LangGraph / LLM 等归一到 `agent`，RAG / MCP 各归一到对应标签。
- 选卡不再按本场难度盖帽。简单场以 easy 为主并掺 medium；中等场 medium 为主并掺少量 easy/hard；困难场提高 hard 占比。某档不够用相邻难度补。策划挑出的三张卡会按同样规则校验。
- 接口成功时直接返回资源，不再使用 `code`、`message`、`data` 外壳。
- 每轮评估增加模型给出的分数和点评。代码按深度、跑题、「不会」钳制分数后写入；结束时按项目深挖、基础、场景加权得到总分，并写入 `interview_sessions.report`。进行中不返回点评；结束后 `GET /api/v1/interview-sessions/{id}` 优先读该列，旧场次现算后补写。
- 发送注册验证码失败时返回固定文案 `发送验证码失败`，不再把内部错误原文回给客户端。

### Database / Deployment Notes

- 数据库迁移：在 `backend/` 执行 `alembic upgrade head`。顺序为 `cc267a266b69`（`users`）、`54098f4c206e`（`resumes`）、`3f212b686956`（`interview_sessions`）、`a41683e0a265`（`topic_cards`）、`1ce649d360ab`（`interview_turns`）、`c4f8a21b9d07`（`interview_sessions.report`）。当前 head 为 `c4f8a21b9d07`。`c4f8a21b9d07` 给场次表增加可空 JSON 列 `report`，进行中为 `NULL`，正常结束时写入。
- 种子数据：迁移完成后在 `backend/` 执行 `python scripts/import_topic_cards.py`，读取 `backend/data/topic_cards/*.json`，按 `key` upsert。当前 372 张（`mysql.json` 70、`redis.json` 62、`java.json` 36、`jvm.json` 32、`spring.json` 33、`agent.json` 54、`python.json` 69、`rag.json` 10，其余按主题分文件）。跨文件 `key` 重复会导入失败。已有相同 `key` 且正文未变则跳过。
- 依赖：`backend/requirements.txt` 增加 `langgraph>=0.2.45`。进程启动时 `compile()` `turn_graph`，挂到 `app.state`。
- 回滚：`alembic downgrade -1` 会删除当前 head 对应的表及其数据。
- 配置变更：`compose.yaml` 中 MySQL 默认库名从 `trip_plan` 改为 `interview`，与 `.env.example` 一致。未设置 `MYSQL_DATABASE` 时生效。已有数据卷不会改名，需在库内自行 `CREATE DATABASE interview` 或沿用原库名。MySQL 默认 `innodb_buffer_pool_size=128M`、容器内存上限 512m，Redis 默认 `maxmemory=64mb`、容器内存上限 96m，供 2G 云主机使用。`compose.yaml` 增加 `backend` 与 `frontend`：启动时自动 `alembic upgrade head` 并导入考点卡；Nginx 容器对外提供 80 端口并反代 API。全栈命令为 `docker compose up -d --build`。本机若只跑数据库：`docker compose up -d mysql redis`。宿主机 Nginx / systemd 配置仍在 `deploy/nginx.conf` 与 `deploy/ai-interview.service`。LangSmith 接入时再增加追踪相关环境变量。

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
