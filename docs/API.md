# API 说明

本文件记录具体接口和调用流程。接口规则见 `docs/rules/API.md`。

路径和字段以 OpenAPI 为准。

## 基础信息

| 项目 | 内容 |
| --- | --- |
| API 名称 | 待补充 |
| 当前版本 | `v1` |
| 开发环境地址 | 待补充 |
| 测试环境地址 | 待补充 |
| 生产环境地址 | 待补充 |
| 认证方式 | 注册接口不需要认证 |
| 时间格式 | ISO 8601 UTC |

## 接口目录

| 模块 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 用户 | `POST` | `/api/v1/users/verification-codes` | 发送注册验证码 |
| 用户 | `POST` | `/api/v1/users` | 注册用户 |

## 发送注册验证码

`POST /api/v1/users/verification-codes`

请求体：

```json
{
  "email": "user@example.com"
}
```

成功返回 `201`，响应体为空对象。验证码写入 Redis，5 分钟过期，不在响应中返回。同一邮箱 60 秒内重复发送返回 `429`。

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

## 业务流程

1. `POST /api/v1/users/verification-codes` 发送验证码。
2. `POST /api/v1/users` 提交邮箱、验证码和密码，创建用户。

## 待补充内容

- [ ] API 基础地址和环境地址
- [ ] 登录后的令牌获取、过期和无权限行为
- [ ] 错误说明的完整文案
