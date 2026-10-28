# API 说明

本文件记录具体接口和调用流程。接口规则见 `docs/rules/API.md`。

路径和字段以 OpenAPI 为准：`/docs`、`/redoc`、`/openapi.json`。

已实现的接口以当前路由为准。尚未挂路由的接口在对应小节标明「待实现」。

## 基础信息

| 项目 | 内容 |
| --- | --- |
| API 名称 | AI 模拟面试 |
| 当前版本 | `v1` |
| 开发环境地址 | 待补充 |
| 测试环境地址 | 待补充 |
| 生产环境地址 | 待补充 |
| 认证方式 | 注册、登录、发验证码、重置密码、刷新令牌、健康检查不需要认证。其余接口使用 `Authorization: Bearer <access_token>` |
| 时间格式 | ISO 8601 UTC，响应带 `Z`，例如 `2026-10-12T08:00:00Z` |

## 接口目录

| 模块 | 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- | --- |
| 系统 | `GET` | `/health` | MySQL 与 Redis 探活 | 已实现 |
| 用户 | `POST` | `/api/v1/users/verification-codes` | 发送注册验证码 | 已实现 |
| 用户 | `POST` | `/api/v1/users` | 注册用户 | 已实现 |
| 用户 | `POST` | `/api/v1/users/session` | 登录 | 已实现 |
| 用户 | `POST` | `/api/v1/users/session/refresh` | 用刷新令牌换发新令牌 | 已实现 |
| 用户 | `DELETE` | `/api/v1/users/session` | 退出登录 | 已实现 |
| 用户 | `POST` | `/api/v1/users/password-reset/verification-codes` | 发送重置密码验证码 | 已实现 |
| 用户 | `POST` | `/api/v1/users/password-reset` | 校验验证码并重置密码 | 已实现 |
| 简历 | `POST` | `/api/v1/resumes` | 上传简历并结构化 | 已实现 |
| 简历 | `GET` | `/api/v1/resumes` | 当前用户的简历列表 | 已实现 |
| 面试 | `POST` | `/api/v1/interview-sessions` | 创建场次、生成计划、给出第一问 | 已实现 |
| 面试 | `GET` | `/api/v1/interview-sessions` | 当前用户的场次列表 | 已实现 |
| 面试 | `GET` | `/api/v1/interview-sessions/{id}` | 查询场次与问答，不返回计划 | 已实现 |
| 面试 | `PATCH` | `/api/v1/interview-sessions/{id}` | 放弃进行中的场次 | 已实现 |
| 面试 | `POST` | `/api/v1/interview-sessions/{id}/turns` | 提交本轮回答，返回下一问或报告 | 已实现 |

考点卡没有对外接口，用导入脚本写入。

## 认证

登录成功后，后续请求在 Header 中携带：

```
Authorization: Bearer <access_token>
```

缺少 Token、格式不是 Bearer、签名无效、过期或用户不存在时返回 `401`，响应体 `{"detail": "Unauthorized"}`。刷新令牌存在 Redis `token:refresh:{user_id}`，同一用户新登录或刷新成功会覆盖旧刷新令牌。访问令牌有效期由 `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` 控制，刷新令牌由 `JWT_REFRESH_TOKEN_EXPIRES_DAYS` 控制。访问令牌过期后，用刷新令牌调用 `POST /api/v1/users/session/refresh` 换发新的一对令牌；刷新令牌无效或过期则重新登录。

## 健康检查

`GET /health`

不需要认证。分别执行 MySQL `SELECT 1` 和 Redis `PING`。

成功返回 `200`：

```json
{
  "mysql": "ok",
  "redis": true
}
```

## 发送注册验证码

`POST /api/v1/users/verification-codes`

请求体：

```json
{
  "email": "user@example.com"
}
```

成功返回 `201`，响应体为空对象。验证码写入 Redis `register:code:{email}`，5 分钟过期，不在响应中返回。邮件发送失败返回 `500`，响应体 `{"detail": "发送验证码失败"}`。

## 注册用户

`POST /api/v1/users`

请求体：

```json
{
  "email": "user@example.com",
  "password": "至少 8 位",
  "verification_code": "123456"
}
```

成功返回 `201`：

```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-10-12T08:00:00Z"
}
```

验证码不存在、过期或不一致时返回 `400`。邮箱已注册时返回 `409`。邮箱格式或密码长度不合法时返回 `422`。响应中不包含 `password_hash`。

## 登录

`POST /api/v1/users/session`

请求体：

```json
{
  "email": "user@example.com",
  "password": "至少 8 位"
}
```

成功返回 `200`：

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

`expires_in` 是访问令牌剩余秒数。用户不存在或密码错误返回 `401`。不要用响应区分这两种情况给前端展示具体账号是否存在以外的细节；当前实现分别返回「用户不存在」和「邮箱或密码错误」。

## 退出登录

`DELETE /api/v1/users/session`

请求体：

```json
{
  "refresh_token": "eyJ..."
}
```

成功返回 `204`，无响应体。令牌不是刷新令牌或无法解码时返回 `401`。Redis 中已无对应令牌时仍返回 `204`。

## 刷新访问令牌

`POST /api/v1/users/session/refresh`

不需要 `Authorization`。用当前刷新令牌换发新的访问令牌和刷新令牌。校验通过后覆盖 Redis 中的刷新令牌，旧刷新令牌立即失效。

请求体：

```json
{
  "refresh_token": "eyJ..."
}
```

成功返回 `201`：

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

`expires_in` 是新访问令牌的剩余秒数。令牌无法解码、不是刷新令牌、与 Redis 中保存的不一致、已过期或用户不存在时返回 `401`，响应体 `{"detail": "无效的刷新令牌"}`。

## 发送重置密码验证码

`POST /api/v1/users/password-reset/verification-codes`

请求体：

```json
{
  "email": "user@example.com"
}
```

成功返回 `201`，响应体为空对象。验证码写入 Redis `reset:code:{email}`，5 分钟过期。邮箱未注册返回 `404`。

## 重置密码

`POST /api/v1/users/password-reset`

请求体：

```json
{
  "email": "user@example.com",
  "new_password": "至少 8 位",
  "verification_code": "123456"
}
```

成功返回 `200`：

```json
{
  "message": "密码重置成功"
}
```

验证码错误返回 `400`。用户不存在返回 `404`。

## 上传简历

`POST /api/v1/resumes`

需要认证。`multipart/form-data`，字段名 `file`。仅接受 `.pdf` 与 `.docx`，不超过 10MB。

成功返回 `201`：

```json
{
  "id": 1,
  "original_filename": "resume.pdf",
  "media_type": "application/pdf",
  "status": "ready",
  "raw_text": "……",
  "profile": {
    "name": "张三",
    "education": [],
    "experience": [],
    "projects": [],
    "skills": ["Java", "MySQL"]
  },
  "error_detail": null,
  "created_at": "2026-10-18T08:00:00Z"
}
```

`status` 为 `ready` 时可用于创建面试。解析或结构化失败时仍返回 `201`，`status` 为 `failed`，`error_detail` 说明原因（文件无法解析、无法提取文本、文本过长、结构化失败）。类型不支持或文件过大、为空时返回 `400`。未认证返回 `401`。

## 获取当前用户简历

`GET /api/v1/resumes`

需要认证。按创建时间倒序。列表项不含 `raw_text` 和 `profile`。

成功返回 `200`：

```json
[
  {
    "id": 1,
    "original_filename": "resume.pdf",
    "media_type": "application/pdf",
    "status": "ready",
    "created_at": "2026-10-18T08:00:00Z"
  }
]
```

## 创建面试场次

`POST /api/v1/interview-sessions`

需要认证。简历必须属于当前用户且 `status=ready`。服务端拷贝 `profile` 为 `resume_snapshot`，按岗位和技能过滤考点卡，调用 `llm_model_heavy` 生成计划，用模板写出第一问，`status` 设为 `in_progress`。响应不含 `plan`。当前是 service 流水线，尚未包成 `plan_graph`。

请求体：

```json
{
  "resume_id": 1,
  "target_role": "Java 后端",
  "difficulty": "medium"
}
```

`target_role`：`Java 后端` / `Python 后端` / `AI Agent`。决定考点卡的岗位标签（分别对应 `backend`+`java`、`backend`+`python`、`ai`）。

`difficulty`：`easy` / `medium` / `hard`。决定本场候选卡的难度配比（简单以 easy 为主并掺 medium，中等以 medium 为主，困难提高 hard 占比），不是只抽该档卡片。

成功返回 `201`：

```json
{
  "id": 1,
  "resume_id": 1,
  "target_role": "Java 后端",
  "difficulty": "medium",
  "status": "in_progress",
  "created_at": "2026-10-20T08:00:00Z",
  "current_turn": {
    "seq": 1,
    "action": "first",
    "question": "先做个一分钟自我介绍吧，可以结合你最近的项目。"
  }
}
```

简历不存在或不属于当前用户返回 `404`。简历未就绪返回 `400`。生成计划失败返回 `500`，文案「生成面试计划失败」。`resume_id`、`target_role` 或 `difficulty` 不合法返回 `422`。

## 面试场次列表

`GET /api/v1/interview-sessions`

需要认证。只返回当前用户的场次摘要，不含 `plan`、各轮问答和完整 `report`。按 `created_at` 倒序。查询参数：

| 参数 | 说明 |
| --- | --- |
| `status` | 可选。`planned` / `in_progress` / `completed` / `abandoned` |
| `created_after` | 可选。ISO 8601 UTC，只返回该时间及之后创建的场次 |
| `limit` | 可选。默认 50，最大 100 |

成功返回 `200`：

```json
[
  {
    "id": 2,
    "resume_id": 1,
    "target_role": "Java 后端",
    "difficulty": "medium",
    "status": "in_progress",
    "created_at": "2026-10-23T08:00:00Z",
    "score": null,
    "stages": [],
    "current_question": "你刚才提到订单系统用了 Redis，缓存和数据库不一致怎么处理？"
  },
  {
    "id": 1,
    "resume_id": 1,
    "target_role": "Java 后端",
    "difficulty": "medium",
    "status": "completed",
    "created_at": "2026-10-20T08:00:00Z",
    "score": 72,
    "stages": [
      { "kind": "project_probe", "score": 70 },
      { "kind": "fundamentals", "score": 78 },
      { "kind": "scenario", "score": 68 }
    ],
    "current_question": null
  }
]
```

`score` 和 `stages` 来自场次上已写入的 `report`。`stages` 只含 `project_probe`（项目深挖）、`fundamentals`（基础）、`scenario`（场景）中实际考到的阶段，没有报告时为空数组。尚未结束、已放弃、或旧数据尚未补写时为 `null`。打开详情 GET 会给旧的已完成场次补写 `report`。`current_question` 仅 `in_progress` 有值。`status` 取值不合法返回 `422`。

## 查询面试场次

`GET /api/v1/interview-sessions/{id}`

需要认证。只返回当前用户的场次。不含 `plan` 和各轮完整 `evaluation`。进行中不返回分数和点评。

成功返回 `200`：

```json
{
  "id": 1,
  "resume_id": 1,
  "target_role": "Java 后端",
  "difficulty": "medium",
  "status": "in_progress",
  "created_at": "2026-10-20T08:00:00Z",
  "turns": [
    {
      "seq": 1,
      "question": "先做个一分钟自我介绍吧，可以结合你最近的项目。",
      "answer": "我最近在做订单系统……",
      "score": null,
      "comment": null
    }
  ],
  "current_question": "你刚才提到订单系统用了 Redis，缓存和数据库不一致怎么处理？",
  "report": null
}
```

已结束时 `current_question` 为 `null`，各轮带 `score` 与 `comment`，`report` 为加权总分：

```json
{
  "id": 1,
  "resume_id": 1,
  "target_role": "Java 后端",
  "difficulty": "medium",
  "status": "completed",
  "created_at": "2026-10-20T08:00:00Z",
  "turns": [
    {
      "seq": 3,
      "question": "缓存和数据库不一致怎么处理？",
      "answer": "我们先更新数据库再删缓存，失败会重试。",
      "score": 58,
      "comment": "本轮 58 分。讲到了更新顺序和失败重试，没展开并发下的短暂不一致。"
    }
  ],
  "current_question": null,
  "report": {
    "score": 72,
    "stages": [
      { "kind": "project_probe", "score": 80 },
      { "kind": "fundamentals", "score": 65 },
      { "kind": "scenario", "score": 70 }
    ],
    "covered": ["intro", "p1"],
    "missing": ["p2"],
    "said_dont_know_count": 0
  }
}
```

`current_question` 为当前等待回答的问题；`completed` 或 `abandoned` 时为 `null`。`report` 仅在 `status=completed` 时有值，优先读场次列；没有则按各轮评估现算并补写。放弃的场次保留已答轮次，不带点评和报告。场次不存在或不属于当前用户返回 `404`。

## 放弃面试场次

`PATCH /api/v1/interview-sessions/{id}`

需要认证。将当前用户进行中的场次标为 `abandoned`，中途结束。不生成 `report`，不删除已有轮次。之后不能再提交回答。

请求体：

```json
{
  "status": "abandoned"
}
```

成功返回 `200`：

```json
{
  "id": 2,
  "resume_id": 1,
  "target_role": "Java 后端",
  "difficulty": "medium",
  "status": "abandoned",
  "created_at": "2026-10-23T08:00:00Z",
  "score": null,
  "current_question": null
}
```

场次不存在或不属于当前用户返回 `404`。已完成或已放弃返回 `409`，文案「当前场次无法放弃」。`status` 不是 `abandoned` 返回 `422`。

## 提交本轮回答

`POST /api/v1/interview-sessions/{id}/turns`

需要认证。将当前待答轮次写入 `answer`，对进程内已 `compile()` 的 `turn_graph` 做一次 `ainvoke`：评估、规则决定动作、生成下一问或报告。图不保存跨请求状态。

请求体：

```json
{
  "answer": "我们先更新数据库再删缓存，失败会重试。"
}
```

成功返回 `200`。未结束时带下一问：

```json
{
  "id": 1,
  "status": "in_progress",
  "current_turn": {
    "seq": 3,
    "action": "follow_up",
    "question": "你刚才说失败会重试，删除缓存一直失败的话谁来保证最终一致？"
  },
  "report": null
}
```

最后一轮完成后 `status` 为 `completed`，`current_turn` 为 `null`，`report` 为各轮评估汇总，并写入 `interview_sessions.report`。本轮点评仍不出现在这次响应里，结束后用 GET 查看：

```json
{
  "id": 1,
  "status": "completed",
  "current_turn": null,
  "report": {
    "score": 72,
    "stages": [
      { "kind": "project_probe", "score": 80 },
      { "kind": "fundamentals", "score": 65 },
      { "kind": "scenario", "score": 70 }
    ],
    "covered": ["intro", "p1"],
    "missing": ["p2"],
    "said_dont_know_count": 0
  }
}
```

没有待答轮次、场次已结束或已放弃返回 `409`。场次不存在或不属于当前用户返回 `404`。空回答返回 `422`。评估或出题失败返回 `500`，文案「处理本轮回答失败」。

请求头 `Accept` 包含 `text/event-stream` 时，同一路径改为 SSE。先校验场次能否作答：不存在仍返回 `404`，无法作答仍返回 `409`。通过后响应 `200`，`Content-Type` 为 `text/event-stream`。评估阶段先发 `status`，出题时模型 token 到达即发 `delta`，落库后再发 `done`。图仍在一次请求内跑完，不保存跨请求状态。

```
event: status
data: {"phase":"evaluating"}

event: status
data: {"phase":"asking"}

event: delta
data: {"text":"你刚才说失败会重试，"}

event: delta
data: {"text":"一直失败的话谁来保证最终一致？"}

event: done
data: {"id":1,"status":"in_progress","current_turn":{"seq":3,"action":"follow_up","question":"你刚才说失败会重试，一直失败的话谁来保证最终一致？"},"report":null}
```

`phase` 为 `evaluating` 或 `asking`。结束时 `done` 的 JSON 与上面的成功响应相同。流开始后的失败改为：

```
event: error
data: {"detail":"处理本轮回答失败"}
```

第一问仍由创建场次的 JSON 返回，不走 SSE。

用户响应中不返回本轮完整 `evaluation`。评估写入 `interview_turns.evaluation`（含模型给出的分数和点评）。代码按深度、跑题、「不会」把分数钳在区间内，并让点评开头的分数与之一致。结束时按阶段加权：`project_probe` 0.35、`fundamentals` 0.30、`scenario` 0.35；同一 `kind` 的多段先平均，开场和收尾不计分。`intro` / `closing` 用代码评估，不调模型；`closing` 问句为模板。

## 业务流程

注册与登录：

1. `POST /api/v1/users/verification-codes` 发送验证码。
2. `POST /api/v1/users` 提交邮箱、验证码和密码。
3. `POST /api/v1/users/session` 登录，拿到访问令牌。
4. 之后请求带 `Authorization: Bearer <access_token>`。
5. 访问令牌过期后，`POST /api/v1/users/session/refresh` 用刷新令牌换新的一对令牌。
6. `DELETE /api/v1/users/session` 吊销刷新令牌。

模拟面试：

1. `POST /api/v1/resumes` 上传简历，直到 `status=ready`。
2. `GET /api/v1/resumes` 选择一份简历。
3. `POST /api/v1/interview-sessions` 开始面试，拿到第一问。
4. 循环 `POST /api/v1/interview-sessions/{id}/turns` 提交回答，直到 `status=completed`。前端对话页带 `Accept: text/event-stream` 流式接收下一问。中途结束则 `PATCH /api/v1/interview-sessions/{id}`，`status` 为 `abandoned`。
5. `GET /api/v1/interview-sessions` 查看自己的场次列表；`GET /api/v1/interview-sessions/{id}` 查看某一场问答。结束后还可看各轮点评、分数和报告。进行中也可看每次 turns 响应里的 `current_turn`。

每一次提交回答对应一次 `turn_graph.ainvoke`。出题节点对模型走流式调用；SSE 把 token 即时推给客户端，JSON 调用仍等整题生成完再返回。创建场次目前走 service，语义与计划中的 `plan_graph` 相同。编排说明见 `docs/interview-design.md`。

## 待补充内容

- [ ] API 基础地址和环境地址
- [ ] 错误说明的完整文案
