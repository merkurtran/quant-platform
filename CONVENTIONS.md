# CONVENTIONS.md

> 本文件定义前后端协作的项目约定：接口格式、错误码、认证、分页、数据格式、WebSocket 协议等。
> AI 编写前端代码时**必须**遵循这些约定，确保与后端正确对接。
> 所有内容基于后端实际实现，不是设计稿。

---

## 1. API 基础

| 项 | 值 |
|----|----|
| Base URL | `http://localhost:8000`（开发环境） |
| API 前缀 | `/api/v1` |
| WebSocket | `ws://localhost:8000/ws/market` |
| 前端地址 | `http://localhost:3000`（已加入后端 CORS 白名单） |
| 请求格式 | `application/json` |
| 时间格式 | ISO 8601（带时区），如 `2026-07-11T10:30:00+08:00` |

### 建议环境变量

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/market
```

---

## 2. 统一响应格式

**所有** HTTP JSON 接口（`/health` 除外）返回统一结构：

```typescript
interface ApiResponse<T> {
  code: number;        // 业务状态码，0 = 成功，非 0 = 失败
  message: string;     // 业务消息，成功为 "success"
  data: T | null;      // 响应数据
  request_id: string;  // 请求唯一标识（UUID）
}
```

前端 axios 响应拦截器应：

1. 检查 `code === 0` → 返回 `data`
2. `code !== 0` → 抛出含 `code` / `message` 的业务错误，Toast 提示
3. HTTP 状态码非 2xx → 同样从 body 中取 `code` / `message`

> 注意：后端中间件会自动包装成功响应。异常响应由全局异常处理器生成，结构与上面一致。

---

## 3. 错误码

错误码按区间分类，前端可根据区间做不同处理：

### 3.1 错误码表

| code | 名称 | HTTP | 含义 | 前端处理 |
|------|------|------|------|----------|
| `0` | SUCCESS | 200 | 成功 | 正常处理 |
| `10001` | UNAUTHORIZED | 401 | 未认证 / token 无效 | 跳登录页 |
| `10002` | TOKEN_EXPIRED | 401 | token 过期 | 尝试 refresh，失败则跳登录 |
| `10003` | FORBIDDEN | 403 | 无权限 | 提示无权限 |
| `20001` | NOT_FOUND | 404 | 资源不存在 | 提示并返回列表页 |
| `20002` | ALREADY_EXISTS | 409 | 资源已存在 | 表单内联提示 |
| `20003` | CONFLICT | 409 | 冲突 | Toast 提示 |
| `20004` | ORDER_CANNOT_CANCEL | 400 | 订单不可撤 | Toast 提示 |
| `30001` | VALIDATION_ERROR | 422 | 参数校验失败 | 表单内联提示 |
| `40001` | RATE_LIMITED | 429 | 限流 | Toast「操作过于频繁」 |
| `40002` | TRADE_FAILED | 400 | 交易失败 | Toast 提示 |
| `40003` | LLM_ERROR | 500 | AI 服务异常 | Toast 提示 |
| `40004` | BACKTEST_FAILED | 400 | 回测失败 | Toast 提示 |

### 3.2 错误码区间约定

| 区间 | 分类 |
|------|------|
| `10xxx` | 认证 / 授权 |
| `20xxx` | 资源 |
| `30xxx` | 参数校验 |
| `40xxx` | 业务逻辑 |

### 3.3 前端错误处理策略

```typescript
// 伪代码
if (code === 0) return data;

if (code === 10001 || code === 10002) {
  // 尝试 refresh token
  // 失败 → 清除 token → 跳 /login
}

if (code === 30001) {
  // 参数校验错误，message 或 data 中可能含字段级错误
  // 映射到表单字段
}

if (code === 40001) {
  toast.error("操作过于频繁，请稍后再试");
}

// 其他 → toast.error(message)
```

---

## 4. 认证与 Token

### 4.1 认证方式

JWT Bearer Token。

```
Authorization: Bearer <access_token>
```

### 4.2 Token 结构

| Token | 有效期 | 用途 |
|-------|--------|------|
| access_token | 2 小时（7200s） | API 请求鉴权 |
| refresh_token | 30 天 | 刷新 access_token |

### 4.3 Token 存储

- access_token / refresh_token 存 `localStorage`（或 Zustand + persist）。
- 用户信息（id / email / nickname）存 store。
- 登录 / 注册 / 刷新接口返回 `TokenResponse`：

```typescript
interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;  // 秒，access_token 有效期
  user: UserPublic;
}

interface UserPublic {
  id: number;
  email: string;
  nickname: string;
}
```

### 4.4 Token 刷新流程

1. axios 请求拦截器：每个请求自动附加 `Authorization: Bearer <access_token>`
2. 响应拦截器收到 `10001` / `10002`（401）：
   - 调用 `POST /api/v1/auth/refresh`（body: `{ refresh_token }`）
   - 成功 → 用新 token 重发原请求
   - 失败 → 清除 token，跳 `/login`
3. 多个并发 401 请求应合并为一次 refresh（用 promise 锁）。

### 4.5 认证接口

| 方法 | 路径 | 说明 | 限流 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 注册 | 5 次/分钟 |
| POST | `/api/v1/auth/login` | 登录 | 10 次/分钟 |
| POST | `/api/v1/auth/refresh` | 刷新 token | 10 次/分钟 |

---

## 5. 分页规范

### 5.1 通用分页（page / page_size）

适用于订单、消息列表等：

```
GET /api/v1/trading/orders?page=1&page_size=20
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `page` | `1` | 页码，从 1 开始 |
| `page_size` | `20` | 每页条数 |

### 5.2 limit 模式（K 线数据）

K 线接口使用 `limit` 而非分页：

```
GET /api/v1/market/klines?symbol=600519.SH&period=1d&limit=300
```

| 参数 | 默认 | 范围 | 说明 |
|------|------|------|------|
| `limit` | `300` | 1 ~ 2000 | 返回最近 N 条 |

### 5.3 不分页的接口

以下接口返回全量列表（不分页）：

- `GET /api/v1/market/watchlists`
- `GET /api/v1/alerts`
- `GET /api/v1/strategies`
- `GET /api/v1/trading/broker_accounts`
- `GET /api/v1/trading/positions`
- `GET /api/v1/ai/conversations`
- `GET /api/v1/alerts/{rule_id}/logs`

---

## 6. 时间格式

- 所有时间字段为 **ISO 8601 带时区字符串**。
- 示例：`"2026-07-11T10:30:00+08:00"` / `"2026-07-11T02:30:00+00:00"`
- 前端用 `dayjs` 解析，展示时转为本地时区。
- 日期字段（无时间）：`"2026-07-11"`（如回测的 `start_date` / `end_date`）。

### 展示规范

| 场景 | 格式 | 示例 |
|------|------|------|
| 日期 | `YYYY-MM-DD` | `2026-07-11` |
| 日期时间 | `YYYY-MM-DD HH:mm` | `2026-07-11 10:30` |
| 精确到秒 | `YYYY-MM-DD HH:mm:ss` | `2026-07-11 10:30:45` |
| 相对时间 | 「3 分钟前」 | 用于告警日志 / 消息 |

---

## 7. 金额与数字格式

### 7.1 传输

- 价格 / 金额 / 数量在后端为 `Decimal`，JSON 传输时为**数字或字符串**。
- 前端统一用 `number` 接收，必要时用字符串防精度丢失。
- 百分比以数值传输（如 `2.5` 表示 2.5%），前端拼接 `%`。

### 7.2 展示

| 场景 | 小数位 | 示例 |
|------|--------|------|
| 股票价格 | 2 位 | `1689.50` |
| 涨跌幅 | 2 位 + `%` | `+2.35%` / `-1.20%` |
| 金额（元） | 2 位 | `1,000,000.00` |
| 数量（股） | 0 位，千分位 | `1,000` |
| 回测收益率 | 2 位 + `%` | `+15.32%` |
| 夏普比率 | 4 位 | `1.2345` |
| 最大回撤 | 2 位 + `%` | `-8.50%` |

### 7.3 数字展示要求

- **所有数字使用 `tabular-nums`**（等宽数字），保证列对齐。
- 大金额可缩写：`1.2万` / `3.5亿`（行情展示场景）。
- 涨跌数字带 `+` / `-` 前缀，并着色（红涨绿跌）。

---

## 8. 股票代码格式

A 股代码格式：`<6位数字>.<交易所后缀>`

| 交易所 | 后缀 | 代码前缀 | 示例 |
|--------|------|----------|------|
| 上海主板 | `.SH` | `6` | `600519.SH`（贵州茅台） |
| 深圳主板 | `.SZ` | `0` | `000001.SZ`（平安银行） |
| 创业板 | `.SZ` | `3` | `300750.SZ`（宁德时代） |
| 北交所 | `.BJ` | `4` / `8` | `830799.BJ` |

### 前端约定

- 所有涉及股票代码的输入 / 展示统一使用带后缀格式（`600519.SH`）。
- 搜索框可输入纯数字（`600519`），前端自动补全后缀。
- 展示时可同时显示代码 + 名称：`600519.SH 贵州茅台`。

---

## 9. WebSocket 协议

### 9.1 连接

```
ws://localhost:8000/ws/market?token=<access_token>
```

或通过 Header（浏览器 WebSocket 不支持自定义 Header，用 query 参数）：

```
ws://localhost:8000/ws/market
Authorization: Bearer <access_token>
```

**前端统一用 query 参数传 token。**

连接失败（token 无效）→ 服务端关闭连接，code `4001`。

### 9.2 客户端 → 服务端

#### 订阅行情

```json
{
  "action": "subscribe",
  "symbols": ["600519.SH", "000001.SZ"]
}
```

可多次调用追加订阅，不会覆盖之前的订阅。

#### 非法 JSON

服务端返回错误（不关闭连接）：

```json
{ "event": "error", "message": "Invalid JSON" }
```

### 9.3 服务端 → 客户端

连接建立后，服务端**自动**订阅当前用户的告警频道，无需客户端主动订阅。

#### 行情推送（quotes）

每次有新行情时推送：

```json
{
  "symbol": "600519.SH",
  "price": 1689.5,
  "ts": "2026-07-11T10:30:00+08:00"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 股票代码 |
| `price` | number | 最新价（收盘价） |
| `ts` | string | 行情时间（ISO 8601） |

#### 告警推送（alerts）

告警触发时推送（仅推送给该规则所属用户）：

```json
{
  "event": "alert",
  "rule_id": 42,
  "symbol": "600519.SH",
  "rule_type": "price_above",
  "trigger_value": 1689.5,
  "reason": "first_trigger",
  "triggered_at": "2026-07-11T10:30:00+00:00"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `event` | string | 固定 `"alert"` |
| `rule_id` | number | 告警规则 ID |
| `symbol` | string | 股票代码 |
| `rule_type` | string | 规则类型（见下方告警规则） |
| `trigger_value` | number | 触发时的价格 |
| `reason` | string | 触发原因 |
| `triggered_at` | string | 触发时间（ISO 8601） |

### 9.4 前端实现建议

- 封装 `useMarketSocket` hook。
- 连接管理：自动重连（指数退避）、token 过期重连。
- 行情数据用 Zustand store 维护 `Map<symbol, { price, ts }>`。
- 告警推送 → Toast 通知 + 未读计数 + 日志列表刷新。
- 页面卸载时取消订阅 / 关闭连接。

---

## 10. AI 对话规范

### 10.1 交互模式

**当前为非流式**：发送消息后等待完整响应返回（非 SSE / 非流式）。

```
POST /api/v1/ai/conversations/{id}/messages
→ 等待 LLM + Tool Use 循环完成
→ 返回完整回复文本
```

### 10.2 前端处理

- 发送消息后展示 Loading 状态（如「AI 思考中...」+ 动画）。
- 收到响应后追加到消息列表。
- 响应中 `message_id` 为 `0`（占位），实际消息从消息列表接口获取。
- 限流：每分钟最多 10 条（`40001` → Toast「请求过于频繁」）。

### 10.3 消息结构

```typescript
interface AIMessage {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | "tool";
  content: {
    text?: string;              // user / assistant 的文本
    tool_calls?: ToolCall[];    // assistant 发起的工具调用
    tool_name?: string;         // tool 消息的工具名
    tool_input?: any;           // tool 消息的输入
    tool_result?: any;          // tool 消息的结果
    tool_call_id?: string;      // tool 消息关联的调用 ID
  };
  created_at: string;
}
```

前端展示时：
- `role === "user"` → 显示用户消息气泡
- `role === "assistant"` → 显示 AI 回复气泡
- `role === "tool"` → 可折叠展示「工具调用」详情（默认折叠）

### 10.4 后续流式支持

当前后端非流式。若后续升级为 SSE 流式，前端需改造为 EventSource / fetch streaming，本约定届时更新。

---

## 11. 告警规则约定

### 11.1 规则类型（rule_type）

| rule_type | 说明 | 条件字段 |
|-----------|------|----------|
| `price_above` | 价格上穿 | `value: Decimal` |
| `price_below` | 价格下穿 | `value: Decimal` |
| `pct_change` | 涨跌幅 | `operator: "gt" \| "lt"`, `value: Decimal`, `baseline`, `custom_baseline?` |
| `volume_spike` | 量异动 | `params: dict`（待细化） |
| `indicator` | 指标触发 | `params: dict`（待细化） |

### 11.2 pct_change 的 baseline

| baseline | 说明 |
|----------|------|
| `previous_close` | 昨收价 |
| `rule_created_price` | 规则创建时的价格 |
| `custom` | 自定义基准价（需填 `custom_baseline`） |

### 11.3 去重状态机

每条规则有去重参数：

| 字段 | 默认 | 范围 | 说明 |
|------|------|------|------|
| `dedup_cooldown_minutes` | 30 | 1 ~ 1440 | 冷却窗口（分钟） |
| `dedup_rearm_pct` | 2.0 | 0.1 ~ 10.0 | 回落重置阈值（%） |

状态：`IDLE` → 触发 → `COOLDOWN`（冷却期抑制）→ `ARMED`（等回落）→ 回落确认 → `IDLE`。

前端展示规则时，`last_triggered_at` / `last_triggered_price` 可用于展示当前去重状态。

### 11.4 通知渠道

`notify_channels` 数组，支持：

- `inapp`（站内推送，通过 WebSocket 实时送达）
- `email`（占位，未实现）
- `webhook`（占位，未实现）

---

## 12. 交易相关约定

### 12.1 订单状态流转

```
pending → submitted → partial_filled → filled
                                    ↘ cancelled
                          ↘ rejected
```

Mock 券商下同步立即成交（pending → filled）。

### 12.2 订单字段

| 字段 | 说明 |
|------|------|
| `side` | `buy` / `sell` |
| `order_type` | `limit`（限价）/ `market`（市价） |
| `price` | 限价单必填，市价单为 null |
| `volume` | 委托数量 |
| `filled_volume` | 已成交数量 |
| `origin` | `manual`（手动）/ `strategy`（策略）/ `ai_agent`（AI） |

### 12.3 前端约定

- 买入按钮红色（A 股惯例），卖出按钮绿色。
- 撤单需二次确认（AlertDialog）。
- 订单列表支持按 `status` / `symbol` / `strategy_id` 筛选。

---

## 13. 策略状态

| status | 说明 |
|--------|------|
| `draft` | 草稿 |
| `backtested` | 已回测 |
| `paper_running` | 模拟运行中 |
| `archived` | 已归档 |

回测运行状态：`queued` → `running` → `success` / `failed`。

发起回测后返回 `run_id`，前端需**轮询** `GET /api/v1/backtest_runs/{run_id}` 直到 `status` 为 `success` 或 `failed`。

---

## 14. 限流约定

后端对部分接口限流（滑动窗口），超限返回 `40001`（HTTP 429）：

| 接口 | 限制 |
|------|------|
| 注册 | 5 次/分钟 |
| 登录 | 10 次/分钟 |
| 刷新 token | 10 次/分钟 |
| 下单 | 20 次/分钟 |
| AI 消息 | 10 次/分钟（可配置） |

前端收到 429 → Toast「操作过于频繁，请稍后再试」。

---

## 15. 路由命名约定（前端）

| 路由 | 页面 |
|------|------|
| `/login` | 登录 |
| `/register` | 注册 |
| `/market` | 行情 / 自选股 |
| `/market/[symbol]` | 个股详情 / K 线 |
| `/strategies` | 策略列表 |
| `/strategies/[id]` | 策略详情 / 编辑 |
| `/strategies/[id]/backtest` | 回测结果 |
| `/trading/orders` | 订单 |
| `/trading/positions` | 持仓 |
| `/trading/accounts` | 券商账户 |
| `/alerts` | 告警规则 |
| `/alerts/[id]/logs` | 告警日志 |
| `/ai` | AI 助手 |

---

## 16. K 线周期

后端支持的 period 值：

| period | 说明 |
|--------|------|
| `1m` | 1 分钟 |
| `5m` | 5 分钟 |
| `15m` | 15 分钟 |
| `30m` | 30 分钟 |
| `60m` | 60 分钟 |
| `1d` | 日线 |
| `1w` | 周线 |
| `1M` | 月线 |

复复权参数 `adjust`：`none`（不复权）/ `qfq`（前复权，默认）。
