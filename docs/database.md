# 数据库设计文档

> 后端使用 **PostgreSQL 15 + TimescaleDB**（K 线表为 hypertable）+ **Redis 7**（缓存 / pubsub）。
> ORM 为 SQLAlchemy 2.0，迁移使用 Alembic。
> 本文档供前端参考数据结构，前端不直接操作数据库。

---

## 基础设施

### TimestampMixin

多数表继承 `TimestampMixin`，自动包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| created_at | DateTime(timezone=True) | 创建时间（UTC，DB 端默认值） |
| updated_at | DateTime(timezone=True) | 更新时间（行更新时自动刷新） |

### 数据库引擎

- 同步：`psycopg2`（API 层、Worker 行情写入）
- 异步：`asyncpg`（Trading / AI 模块）
- Redis：行情缓存 `latest_price:{symbol}`、pubsub `quotes:{symbol}` / `alerts:{user_id}`

---

## 1. 用户模块

### users

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK, auto | — |
| email | String(255) | UNIQUE, NOT NULL | 邮箱 |
| password_hash | String(255) | NOT NULL | bcrypt 哈希 |
| nickname | String(64) | NOT NULL | 昵称 |
| avatar_url | String(512) | NULL | 头像 |
| status | String(16) | NOT NULL, default `active` | `active` / `disabled` |
| created_at | DateTime(tz) | NOT NULL | mixin |
| updated_at | DateTime(tz) | NOT NULL | mixin |

---

## 2. 行情模块

### watchlists

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| user_id | BigInteger | FK→users.id CASCADE, index | — |
| name | String(64) | NOT NULL | 列表名 |
| created_at / updated_at | DateTime(tz) | — | mixin |

**关系：** `items` → watchlist_items（1:N）

### watchlist_items

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| watchlist_id | BigInteger | FK→watchlists.id CASCADE, index | — |
| symbol | String(16) | NOT NULL | 股票代码 |
| name | String(64) | NULL | 股票名称 |
| sort_order | Integer | NOT NULL, default 0 | 排序 |
| added_at | DateTime(tz) | NOT NULL | 添加时间 |

**唯一约束：** `(watchlist_id, symbol)` — 同列表不重复

### klines ⚡ TimescaleDB hypertable

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | String(16) | 股票代码 |
| period | String(8) | `1m/5m/15m/30m/60m/1d/1w/1M` |
| ts | DateTime(tz) | 时间戳；分钟线保存真实 UTC 时刻，日线保存交易日 UTC 00:00 |
| open | Numeric(12,3) | 开盘价 |
| high | Numeric(12,3) | 最高价 |
| low | Numeric(12,3) | 最低价 |
| close | Numeric(12,3) | 收盘价 |
| volume | Numeric(18,2) | 成交量 |
| amount | Numeric(18,2) | NULL | 成交额 |

**主键：** `(symbol, period, ts)`  
**特性：** 按 `ts` 分区的 hypertable，自动按时间压缩。

### corporate_actions

公司行为（除权除息），用于前复权计算。
主数据源为 CNINFO，AKShare 仅作降级兜底；活跃标的首次跟踪时按需同步，同一除权日的现金分红、送转和配股合并计算一次复权因子。

> 口径边界：当回购专户股份不参与分红时，交易所除权参考价使用按总股本摊薄的“虚拟分派”金额。当前 CNINFO 结构化接口只返回实际派发比例，这类差异化分红的本地复权值可能与行情商成品复权数据有小幅差异；原始不复权 K 线不受影响。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInteger | PK |
| symbol | String(16) | — |
| ex_date | Date | 除权日 |
| action_type | String(16) | 行为类型 |
| cash_per_share | Numeric(10,4) | 每股分红 |
| stock_ratio | Numeric(10,4) | 送股比例 |
| rights_price | Numeric(10,4) | 配股价 |
| rights_ratio | Numeric(10,4) | 配股比例 |
| created_at | DateTime(tz) | — |

**唯一约束：** `(symbol, ex_date, action_type)`

---

## 3. 告警模块

### alert_rules

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| user_id | BigInteger | FK→users.id CASCADE, index | — |
| symbol | String(16) | NOT NULL | — |
| rule_type | String(24) | NOT NULL | `price_above/price_below/pct_change/volume_spike/indicator` |
| condition | JSONB | NOT NULL | 条件详情（结构按 rule_type 区分） |
| notify_channels | JSONB | NOT NULL, default `["inapp"]` | 通知渠道 |
| status | String(16) | NOT NULL, default `active` | `active` / `paused` |
| created_at | DateTime(tz) | NOT NULL | — |
| baseline_price | Numeric(18,4) | NULL | 仅 pct_change + baseline=rule_created_price |
| last_triggered_at | DateTime(tz) | NULL | 去重状态机：上次触发时间 |
| last_triggered_price | Numeric(18,4) | NULL | 去重状态机：上次触发价 |
| dedup_cooldown_minutes | Integer | NULL | 冷却窗口（默认 30） |
| dedup_rearm_pct | Numeric(5,2) | NULL | 回落重置阈值（默认 2.0%） |

**关系：** `logs` → alert_logs（1:N）

### alert_logs

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| rule_id | BigInteger | FK→alert_rules.id CASCADE, index | — |
| triggered_at | DateTime(tz) | NOT NULL | 触发时间 |
| trigger_value | Numeric(18,4) | NULL | 触发时价格 |
| message | String(256) | NULL | 触发描述 |

---

## 4. 策略模块

### strategies

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| user_id | BigInteger | FK→users.id CASCADE, index | — |
| name | String(128) | NOT NULL | — |
| description | Text | NULL | — |
| code | Text | NOT NULL | backtrader 代码 |
| params | JSONB | NOT NULL, default `{}` | 策略参数 |
| status | String(16) | NOT NULL, default `draft` | `draft/backtested/paper_running/archived` |
| created_at / updated_at | DateTime(tz) | — | mixin |

**关系：** `backtest_runs` → backtest_runs（1:N，级联删除）

### backtest_runs

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| strategy_id | BigInteger | FK→strategies.id CASCADE, index | — |
| start_date | Date | NOT NULL | — |
| end_date | Date | NOT NULL | — |
| initial_capital | Numeric(18,2) | NOT NULL | 初始资金 |
| commission_rate | Numeric(10,6) | NOT NULL, default `0.001` | 手续费率快照 |
| slippage_rate | Numeric(10,6) | NOT NULL, default `0.0005` | 滑点率快照 |
| params_snapshot | JSONB | NOT NULL | 参数快照 |
| status | String(16) | NOT NULL, default `running` | `queued/running/success/failed` |
| symbols | JSONB | NOT NULL | 标的列表 |
| error_message | Text | NULL | 失败原因 |
| created_at | DateTime(tz) | NOT NULL | — |
| finished_at | DateTime(tz) | NULL | 完成时间 |

**关系：** `results` → backtest_results（1:N，目前 1:1）

### backtest_results

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInteger | PK |
| run_id | BigInteger | FK→backtest_runs.id CASCADE, index |
| total_return | Numeric(10,4) | 总收益率 |
| annual_return | Numeric(10,4) | 年化收益率 |
| max_drawdown | Numeric(10,4) | 最大回撤 |
| sharpe_ratio | Numeric(10,4) | 夏普比率 |
| win_rate | Numeric(10,4) | 胜率 |
| trade_count | Integer | 交易次数 |
| equity_curve | JSONB | 净值曲线 `[{date, equity}, ...]` |
| trade_list | JSONB | 交易明细 |

---

## 5. 交易模块

### broker_accounts

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| user_id | BigInteger | FK→users.id CASCADE | — |
| broker_type | String(32) | NOT NULL | `mock` / 真实券商 |
| account_alias | String(64) | NOT NULL | 账户别名 |
| credentials_encrypted | String | NULL | Fernet 加密的凭证 |
| status | String(16) | NOT NULL, default `inactive` | `active` / `inactive` |
| initial_cash | Numeric(18,2) | NOT NULL | 模拟账户初始资金 |
| cash_balance | Numeric(18,2) | NOT NULL | 当前可用资金 |
| frozen_cash | Numeric(18,2) | NOT NULL | 未成交买单冻结资金 |
| commission_rate | Numeric(10,6) | NOT NULL | 券商佣金率 |
| minimum_commission | Numeric(10,2) | NOT NULL | 单笔最低佣金 |
| stamp_duty_rate | Numeric(10,6) | NOT NULL | 卖出印花税率 |
| slippage_rate | Numeric(10,6) | NOT NULL | 市价单滑点率 |
| created_at | DateTime(tz) | NOT NULL | — |

### orders

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| user_id | BigInteger | FK→users.id CASCADE | — |
| broker_account_id | BigInteger | FK→broker_accounts.id | — |
| strategy_id | BigInteger | FK→strategies.id, NULL | 策略下单时关联 |
| client_order_id | String(64) | NOT NULL | 客户端订单 ID |
| symbol | String(16) | NOT NULL | — |
| side | String(8) | NOT NULL | `buy` / `sell` |
| order_type | String(16) | NOT NULL, default `limit` | `limit` / `market` |
| price | Numeric(12,3) | NULL | 限价单价格 |
| volume | Numeric(18,2) | NOT NULL | 委托量 |
| filled_volume | Numeric(18,2) | NOT NULL, default 0 | 已成交量 |
| filled_price | Numeric(12,3) | NULL | 实际成交价 |
| commission | Numeric(12,2) | NOT NULL, default 0 | 佣金 |
| stamp_duty | Numeric(12,2) | NOT NULL, default 0 | 卖出印花税 |
| reject_reason | String(255) | NULL | 拒单原因 |
| reserved_cash | Numeric(18,2) | NOT NULL, default 0 | 本订单冻结资金 |
| reserved_volume | Numeric(18,2) | NOT NULL, default 0 | 本订单冻结持仓量 |
| status | String(16) | NOT NULL, default `pending` | `pending/submitted/partial_filled/filled/cancelled/rejected` |
| broker_order_id | String(64) | NULL | 券商返回的订单 ID |
| origin | String(16) | NOT NULL, default `manual` | `manual` / `strategy` / `ai_agent` |
| created_at / updated_at | DateTime(tz) | — | mixin |

**唯一约束：** `(broker_account_id, client_order_id)`

### positions

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| broker_account_id | BigInteger | FK→broker_accounts.id | — |
| symbol | String(16) | NOT NULL | — |
| volume | Numeric(18,2) | NOT NULL | 持仓量 |
| avg_cost | Numeric(12,3) | NOT NULL | 平均成本 |
| available_volume | Numeric(18,2) | NOT NULL, default 0 | 已交收、当前可卖数量 |
| pending_settlement_volume | Numeric(18,2) | NOT NULL, default 0 | 当日买入、等待下一交易日交收数量 |
| frozen_volume | Numeric(18,2) | NOT NULL, default 0 | 未成交卖单冻结量 |
| last_buy_trade_date | Date | NULL | 最近一次买入成交的交易日 |
| updated_at | DateTime(tz) | NOT NULL | 自动更新 |

**唯一约束：** `(broker_account_id, symbol)`

### position_reconciliations

持仓对账记录（本地 vs 券商）。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInteger | PK |
| broker_account_id | BigInteger | FK |
| symbol | String(16) | — |
| local_volume | Numeric(18,2) | 本地持仓 |
| broker_volume | Numeric(18,2) | 券商持仓 |
| is_matched | Boolean | 是否一致 |
| checked_at | DateTime(tz) | 检查时间 |

### audit_logs

操作审计日志（人工 + AI 操作）。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInteger | PK |
| user_id | BigInteger | FK→users.id CASCADE |
| action | String(64) | `order_create/order_cancel/strategy_deploy/broker_bind` 等 |
| actor_type | String(16) | `user` / `ai_agent` |
| conversation_id | BigInteger | NULL（AI 操作时关联对话） |
| target_type | String(32) | NULL |
| target_id | BigInteger | NULL |
| detail | JSONB | NULL |
| ip_address | String(64) | NULL |
| created_at | DateTime(tz) | — |

### trade_outbox

交易发件箱（可靠投递到券商）。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInteger | PK |
| order_id | BigInteger | FK→orders.id CASCADE |
| adapter_name | String(50) | 券商适配器名 |
| request_json | JSONB | 请求体 |
| status | String(20) | `pending` / `processed` |
| retry_count | Integer | 重试次数 |
| last_error | Text | NULL |
| created_at | DateTime(tz) | — |
| processed_at | DateTime(tz) | NULL |

**唯一约束：** `(order_id)`

---

## 6. AI 模块

### ai_conversations

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| user_id | BigInteger | FK→users.id CASCADE | — |
| title | String(128) | NULL | 对话标题 |
| created_at / updated_at | DateTime(tz) | — | mixin |

### ai_messages

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BigInteger | PK | — |
| conversation_id | BigInteger | FK→ai_conversations.id CASCADE | — |
| role | String(16) | NOT NULL | `user` / `assistant` / `tool` |
| content | JSONB | NOT NULL | 结构按 role 不同（见下方） |
| created_at | DateTime(tz) | NOT NULL | — |

**索引：** `(conversation_id, created_at)`  
**content 结构：**
- user: `{ "text": "..." }`
- assistant: `{ "text": "...", "tool_calls": [...] }`
- tool: `{ "tool_name", "tool_input", "tool_result", "tool_call_id" }`

---

## ER 关系总览

```
users ─┬─< watchlists ─< watchlist_items
       ├─< alert_rules ─< alert_logs
       ├─< strategies ─< backtest_runs ─< backtest_results
       ├─< broker_accounts ─┬─< orders
       │                     ├─< positions
       │                     ├─< position_reconciliations
       │                     └─< trade_outbox
       ├─< audit_logs
       └─< ai_conversations ─< ai_messages

klines（hypertable，独立）
corporate_actions（独立）
```
