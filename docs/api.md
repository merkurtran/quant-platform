# API 接口文档

> 后端基于 FastAPI，所有接口前缀 `/api/v1`。
> 响应格式、错误码、认证方式见 `CONVENTIONS.md`。
> 所有需认证接口要求 `Authorization: Bearer <access_token>`。
> 所有响应被统一包装为 `{ code, message, data, request_id }`，下方仅展示 `data` 的结构。

---

## 目录

- [Auth 认证](#auth-认证)
- [Market 行情](#market-行情)
- [Alerts 告警](#alerts-告警)
- [Strategies 策略](#strategies-策略)
- [Backtest 回测](#backtest-回测)
- [Trading 交易](#trading-交易)
- [AI 助手](#ai-助手)
- [WebSocket 实时推送](#websocket-实时推送)

---

## Auth 认证

> 前缀 `/api/v1/auth`，无需认证。

### POST /auth/register

注册，成功直接返回 token。

| 字段 | 类型 | 约束 |
|------|------|------|
| email | EmailStr | 合法邮箱 |
| password | string | 8~64 位 |
| nickname | string | 1~16 字符 |

**响应 data：** `TokenResponse`（限流 5/min，错误 `20002` 邮箱已存在 409）

```json
{ "access_token": "...", "refresh_token": "...", "expires_in": 7200, "user": { "id": 1, "email": "...", "nickname": "..." } }
```

### POST /auth/login

| 字段 | 类型 |
|------|------|
| email | EmailStr |
| password | string |

**响应 data：** `TokenResponse`（限流 10/min，错误 `10001` 凭证无效 401）

### POST /auth/refresh

| 字段 | 类型 |
|------|------|
| refresh_token | string |

**响应 data：** `TokenResponse`（限流 10/min，错误 `10002` token 无效 401）

---

## Market 行情

> 前缀 `/api/v1/market`，全部 🔐 需认证。

### GET /market/klines

| Query | 类型 | 必填 | 默认 | 说明 |
|-------|------|------|------|------|
| symbol | string | ✅ | — | `600519.SH` |
| period | string | — | `1d` | `1m/5m/15m/30m/60m/1d/1w/1M` |
| limit | int | — | 300 | 1~2000 |
| adjust | string | — | `qfq` | `none` / `qfq` |
| start | string | — | — | `YYYY-MM-DD` |
| end | string | — | — | `YYYY-MM-DD` |

**响应 data：**

```json
{
  "symbol": "600519.SH", "period": "1d", "adjust": "qfq",
  "items": [
    { "ts": "2026-07-10T00:00:00+00:00", "open": "1680.000", "high": "1695.000",
      "low": "1678.000", "close": "1689.500", "volume": "12345.67", "amount": "20860230.00" }
  ]
}
```

### GET /market/watchlists

**响应 data：** `WatchlistPublic[]`（含 items）

```json
[{ "id": 1, "name": "我的关注", "items": [
  { "symbol": "600519.SH", "name": "贵州茅台", "sort_order": 0, "added_at": "..." }
]}]
```

### POST /market/watchlists

**请求体：** `{ "name": "我的关注" }`  
**响应 data：** `WatchlistPublic`（错误 `20002` 名称已存在 409）

### POST /market/watchlists/{watchlist_id}/items

**请求体：** `{ "symbol": "600519.SH", "name": "贵州茅台" }`  
**响应 data：** `WatchlistItemPublic`（错误 `20001` 列表不存在 404；`20002` 已存在 409）

### DELETE /market/watchlists/{watchlist_id}/items/{symbol}

**响应 data：** `{ "code": 0, "message": "deleted" }`（错误 `20001` 列表不存在 404）

---

## Alerts 告警

> 前缀 `/api/v1/alerts`，全部 🔐 需认证。

### POST /alerts

创建规则（HTTP 201）。

**请求体：**

```json
{
  "symbol": "600519.SH",
  "condition": { "rule_type": "price_above", "value": "1700.00" },
  "notify_channels": ["inapp"],
  "dedup_cooldown_minutes": 30,
  "dedup_rearm_pct": "2.0"
}
```

condition 按 `rule_type` 区分（discriminated union）：

| rule_type | 字段 |
|-----------|------|
| `price_above` | `value: Decimal(>0)` |
| `price_below` | `value: Decimal(>0)` |
| `pct_change` | `operator: "gt"\|"lt"`, `value: Decimal(0~1000)`, `baseline: "previous_close"\|"rule_created_price"\|"custom"`, `custom_baseline?: Decimal` |
| `volume_spike` | `params: object`（待细化） |
| `indicator` | `params: object`（待细化） |

去重参数：`dedup_cooldown_minutes`(1~1440, 默认30)、`dedup_rearm_pct`(0.1~10.0, 默认2.0)。

**响应 data：** `AlertRulePublic`

```json
{
  "id": 42, "symbol": "600519.SH", "rule_type": "price_above",
  "condition": { "rule_type": "price_above", "value": "1700.00" },
  "notify_channels": ["inapp"], "status": "active",
  "created_at": "...",
  "last_triggered_at": null, "last_triggered_price": null,
  "dedup_cooldown_minutes": 30, "dedup_rearm_pct": "2.00"
}
```

### GET /alerts

| Query | 类型 | 说明 |
|-------|------|------|
| rule_status | string | `active` / `paused` |
| symbol | string | 按股票筛选 |

**响应 data：** `AlertRulePublic[]`

### PATCH /alerts/{rule_id}

仅可改 condition / status / 去重参数（不可改 symbol / rule_type）。所有字段可选。

```json
{ "condition": { "rule_type": "price_above", "value": "1750.00" }, "status": "paused" }
```

**响应 data：** `AlertRulePublic`（错误 `20001` 不存在 404）

### GET /alerts/{rule_id}/logs

**响应 data：** `AlertLogPublic[]`

```json
[{ "id": 1, "triggered_at": "...", "trigger_value": "1701.50", "message": "Alert triggered for 600519.SH at 1701.50 [first_trigger]" }]
```

---

## Strategies 策略

> 前缀 `/api/v1/strategies`，全部 🔐 需认证。

### POST /strategies（201）

**请求体：** `{ "name": "双均线", "description": "...", "code": "...", "params": {"fast":5,"slow":20} }`

**响应 data：** `StrategyPublic` — `{ id, name, description, status, created_at, updated_at }`

### GET /strategies

**响应 data：** `StrategyPublic[]`

### GET /strategies/{strategy_id}

**响应 data：** `StrategyDetail`（比 Public 多 `code` / `params`）（错误 `20001` 404）

### PUT /strategies/{strategy_id}

全量更新，字段可选：`name` / `description` / `code` / `params`。**响应 data：** `StrategyPublic`

### DELETE /strategies/{strategy_id}

级联删除回测记录。**响应：** HTTP 204（错误 `20001` 404）

### POST /strategies/{strategy_id}/backtest

**请求体：**

```json
{ "start_date": "2025-01-01", "end_date": "2026-06-30",
  "initial_capital": "1000000.00", "symbols": ["600519.SH"], "params": {} }
```

**响应 data：** `{ "run_id": 7, "status": "running" }`（错误 `20001` 策略不存在 404）

---

## Backtest 回测

> 前缀 `/api/v1/backtest_runs`，全部 🔐 需认证。

### GET /backtest_runs/{run_id}

前端需轮询直到 `status` 为 `success` / `failed`。

**响应 data：**

```json
{
  "run_id": 7,
  "status": "success",
  "result": {
    "total_return": 15.32, "annual_return": 12.50,
    "max_drawdown": -8.50, "sharpe_ratio": 1.2345,
    "win_rate": 55.00, "trade_count": 42,
    "equity_curve": [{ "date": "2025-01-02", "equity": 1000000 }]
  },
  "error_message": null
}
```

status 值：`queued` / `running` / `success` / `failed`（错误 `20001` 404）

---

## Trading 交易

> 前缀 `/api/v1`，全部 🔐 需认证。

### POST /broker_accounts

**请求体：** `{ "broker_type": "mock", "account_alias": "模拟账户1" }`  
**响应 data：** `BrokerAccountOut` — `{ id, broker_type, account_alias, status, created_at }`

### GET /broker_accounts

**响应 data：** `BrokerAccountOut[]`

### POST /orders

限流 20/min。

```json
{ "broker_account_id": 1, "symbol": "600519.SH", "side": "buy",
  "order_type": "limit", "price": "1689.50", "volume": "100.00" }
```

side: `buy`/`sell`；order_type: `limit`/`market`；price 市价单为 null。

**响应 data：** `OrderOut`

```json
{ "id": 1, "user_id": 1, "broker_account_id": 1, "strategy_id": null,
  "client_order_id": "...", "symbol": "600519.SH", "side": "buy",
  "order_type": "limit", "price": "1689.500", "volume": "100.00",
  "filled_volume": "100.00", "status": "filled",
  "broker_order_id": null, "origin": "manual", "created_at": "...", "updated_at": "..." }
```

status 流转：`pending → submitted → partial_filled → filled / cancelled / rejected`

### GET /orders

| Query | 类型 | 默认 | 说明 |
|-------|------|------|------|
| status | string | — | 状态筛选 |
| symbol | string | — | 股票筛选 |
| strategy_id | int | — | 策略筛选 |
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页 |

**响应 data：** `OrderOut[]`

### DELETE /orders/{order_id}

撤单。**响应 data：** `OrderOut`（错误 `20004` 不可撤 400）

### GET /positions

**响应 data：** `PositionOut[]`

```json
[{ "broker_account_id": 1, "symbol": "600519.SH", "volume": "100.00", "avg_cost": "1689.500", "updated_at": "..." }]
```

---

## AI 助手

> 前缀 `/api/v1/ai`，全部 🔐 需认证。当前为**非流式**。

### POST /ai/conversations

**请求体：** `{}`  
**响应 data：** `ConversationOut` — `{ id, title, created_at, updated_at }`

### GET /ai/conversations

按 `updated_at` 倒序。**响应 data：** `ConversationOut[]`

### GET /ai/conversations/{conversation_id}/messages

| Query | 默认 |
|-------|------|
| page | 1 |
| page_size | 50 |

按 `created_at` 正序。**响应 data：** `MessageOut[]`

```json
[{ "id": 1, "conversation_id": 1, "role": "user",
  "content": { "text": "帮我写一个双均线策略" }, "created_at": "..." }]
```

role 值：`user` / `assistant` / `tool`。content 结构因 role 不同（详见 CONVENTIONS.md 第 10 节）。

### POST /ai/conversations/{conversation_id}/messages

限流 10/min。

**请求体：** `{ "content": "帮我写一个双均线策略" }`（1~4096 字符）

**响应 data：** `SendMessageResponse`

```json
{ "message_id": 0, "role": "assistant", "content": "好的，这是策略代码...", "tool_calls": null }
```

> `message_id` 固定为 0（占位），实际消息从列表接口获取。  
> 后端在响应前完成 LLM + Tool Use 循环（最多 5 轮），前端需展示等待动画。

---

## WebSocket 实时推送

### 连接

```
ws://localhost:8000/ws/market?token=<access_token>
```

连接后自动订阅当前用户的告警频道。

### 客户端 → 服务端

订阅行情：

```json
{ "action": "subscribe", "symbols": ["600519.SH", "000001.SZ"] }
```

### 服务端 → 客户端

**行情推送：**

```json
{ "symbol": "600519.SH", "price": 1689.5, "ts": "2026-07-11T10:30:00+08:00" }
```

**告警推送：**

```json
{ "event": "alert", "rule_id": 42, "symbol": "600519.SH",
  "rule_type": "price_above", "trigger_value": 1701.5,
  "reason": "first_trigger", "triggered_at": "2026-07-11T10:30:00+00:00" }
```

**错误：**

```json
{ "event": "error", "message": "Invalid JSON" }
```

> 完整 WebSocket 协议详见 `CONVENTIONS.md` 第 9 节。
