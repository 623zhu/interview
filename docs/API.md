# API 说明

本文件记录具体接口和调用流程。接口规则见 `docs/rules/API.md`。

路径和字段以 OpenAPI 为准：`/docs`、`/redoc`、`/openapi.json`。

已实现的接口以当前路由为准。面试场次接口已设计、尚未挂路由，在对应小节标明「待实现」。

## 基础信息

| 项目 | 内容 |
| --- | --- |
| API 名称 | AI 模拟面试 |
| 当前版本 | `v1` |
| 开发环境地址 | 待补充 |
| 测试环境地址 | 待补充 |
| 生产环境地址 | 待补充 |
| 认证方式 | 注册、登录、发验证码、重置密码、健康检查不需要认证。其余接口使用 `Authorization: Bearer <access_token>` |
| 时间格式 | ISO 8601 UTC |

## 接口目录

| 模块 | 方法 | 路径 | 说明 | 状态 |
| --- | --- | --- | --- | --- |
| 系统 | `GET` | `/health` | MySQL 与 Redis 探活 | 已实现 |
| 用户 | `POST` | `/api/v1/users/verification-codes` | 发送注册验证码 | 已实现 |
| 用户 | `POST` | `/api/v1/users` | 注册用户 | 已实现 |
| 用户 | `POST` | `/api/v1/users/session` | 登录 | 已实现 |
| 用户 | `DELETE` | `/api/v1/users/session` | 退出登录 | 已实现 |
| 用户 | `POST` | `/api/v1/users/password-reset/verification-codes` | 发送重置密码验证码 | 已实现 |
| 用户 | `POST` | `/api/v1/users/password-reset` | 校验验证码并重置密码 | 已实现 |
| 简历 | `POST` | `/api/v1/resumes` | 上传简历并结构化 | 已实现 |
| 简历 | `GET` | `/api/v1/resumes` | 当前用户的简历列表 | 已实现 |
| 面试 | `POST` | `/api/v1/interview-sessions` | 创建场次、生成计划、给出第一问 | 待实现 |
| 面试 | `GET` | `/api/v1/interview-sessions/{id}` | 查询场次与问答，不返回计划 | 待实现 |
| 面试 | `POST` | `/api/v1/interview-sessions/{id}/turns` | 提交本轮回答，返回下一问或报告 | 待实现 |

考点卡没有对外接口，用导入脚本写入。

## 认证

登录成功后，后续请求在 Header 中携带：

```
Authorization: Bearer <access_token>
```

缺少 Token、格式不是 Bearer、签名无效、过期或用户不存在时返回 `401`，响应体 `{"detail": "Unauthorized"}`。刷新令牌存在 Redis `token:refresh:{user_id}`，同一用户新登录会覆盖旧刷新令牌。访问令牌有效期由 `JWT_ACCESS_TOKEN_EXPIRES_MINUTES` 控制，刷新令牌由 `JWT_REFRESH_TOKEN_EXPIRES_DAYS` 控制。目前没有刷新访问令牌的接口，过期后重新登录。

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

成功返回 `201`，响应体为空对象。验证码写入 Redis `register:code:{email}`，5 分钟过期，不在响应中返回。邮件发送失败返回 `500`。

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

## 创建面试场次（待实现）

`POST /api/v1/interview-sessions`

需要认证。简历必须属于当前用户且 `status=ready`。服务端拷贝 `profile` 为 `resume_snapshot`，跑 `plan_graph` 生成计划并写出第一问，`status` 设为 `in_progress`。响应不含 `plan`。

请求体：

```json
{
  "resume_id": 1,
  "target_role": "Java 后端",
  "difficulty": "medium"
}
```

`difficulty`：`easy` / `medium` / `hard`。

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

简历不存在或不属于当前用户返回 `404`。简历未就绪返回 `400`。`resume_id` 或 `difficulty` 不合法返回 `422`。

## 查询面试场次（待实现）

`GET /api/v1/interview-sessions/{id}`

需要认证。只返回当前用户的场次。不含 `plan` 和各轮 `evaluation`。

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
      "answer": "我最近在做订单系统……"
    }
  ],
  "current_question": "你刚才提到订单系统用了 Redis，缓存和数据库不一致怎么处理？",
  "report": null
}
```

`current_question` 为当前等待回答的问题；已结束时为 `null`。`report` 仅在 `status=completed` 时有值。场次不存在或不属于当前用户返回 `404`。

## 提交本轮回答（待实现）

`POST /api/v1/interview-sessions/{id}/turns`

需要认证。将当前待答轮次写入 `answer`，跑 `turn_graph`：评估、规则决定动作、生成下一问或报告。

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

最后一轮完成后 `status` 为 `completed`，`current_turn` 为 `null`，`report` 为汇总结果。没有待答轮次、场次已结束或已放弃返回 `409`。场次不存在或不属于当前用户返回 `404`。空回答返回 `422`。

用户响应中不返回本轮 `evaluation`。评估只写入 `interview_turns.evaluation`，结束时汇总进 `report`。

## 业务流程

注册与登录：

1. `POST /api/v1/users/verification-codes` 发送验证码。
2. `POST /api/v1/users` 提交邮箱、验证码和密码。
3. `POST /api/v1/users/session` 登录，拿到访问令牌。
4. 之后请求带 `Authorization: Bearer <access_token>`。
5. `DELETE /api/v1/users/session` 吊销刷新令牌。

模拟面试（待实现部分从第 3 步起）：

1. `POST /api/v1/resumes` 上传简历，直到 `status=ready`。
2. `GET /api/v1/resumes` 选择一份简历。
3. `POST /api/v1/interview-sessions` 开始面试，拿到第一问。
4. 循环 `POST /api/v1/interview-sessions/{id}/turns` 提交回答，直到 `status=completed`。
5. `GET /api/v1/interview-sessions/{id}` 查看问答和报告。

一次创建会话对应一次 `plan_graph`；每一次提交回答对应一次 `turn_graph`。编排说明见 `docs/interview-design.md`。

## 待补充内容

- [ ] API 基础地址和环境地址
- [ ] 刷新访问令牌接口
- [ ] 面试场次列表与放弃面试
- [ ] 错误说明的完整文案
