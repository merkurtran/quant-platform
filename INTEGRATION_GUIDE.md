---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 23abe49739bc9e0e32093f07f5b1dd8f_8587d68b7c4111f1baf4525400bff409
    ReservedCode1: eE04lWA+MTmSITm3ewfrP9VzpOQ9URpxDmH+33d9rSYLIWWzmCmmLya7lzeqwgi6nStFbOiFC1KQBlF7rPz/AD+Wp9RKPbM9J4nAuU4DG1wdskgO3hIbKaWVLGYKA1+m7U72+sjz4jQYneJE/CHzadnoyc3yAIvWM9uAVJizLQeSHMT1LBH9dNNKjHg=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 23abe49739bc9e0e32093f07f5b1dd8f_8587d68b7c4111f1baf4525400bff409
    ReservedCode2: eE04lWA+MTmSITm3ewfrP9VzpOQ9URpxDmH+33d9rSYLIWWzmCmmLya7lzeqwgi6nStFbOiFC1KQBlF7rPz/AD+Wp9RKPbM9J4nAuU4DG1wdskgO3hIbKaWVLGYKA1+m7U72+sjz4jQYneJE/CHzadnoyc3yAIvWM9uAVJizLQeSHMT1LBH9dNNKjHg=
---

# 告警去重策略 — 集成指南

## 新增文件

| 文件 | 位置 | 说明 |
|------|------|------|
| `alert_engine.py` | `shared/alert_engine.py` | 去重状态机（IDLE / COOLDOWN / ARMED） |
| `alert_coordinator.py` | `shared/alert_coordinator.py` | 协调器：条件评估 → 引擎判断 → 持久化 → 推送 |

## 需要修改的已有文件

### 1. `app/models/alert.py` — AlertRules 新增 4 列

在 `AlertRules` 类末尾追加：

```python
# 去重状态机字段
last_triggered_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True, default=None,
)
last_triggered_price: Mapped[Decimal | None] = mapped_column(
    Numeric(18, 4), nullable=True, default=None,
)
dedup_cooldown_minutes: Mapped[int | None] = mapped_column(
    Integer, nullable=True, default=None,
    comment="冷却窗口(分钟)，None 使用引擎默认值(30min)",
)
dedup_rearm_pct: Mapped[Decimal | None] = mapped_column(
    Numeric(5, 2), nullable=True, default=None,
    comment="回落百分比，None 使用引擎默认值(2.0%)",
)
```

### 2. `app/schemas/alert.py` — Schema 新增字段

在 `AlertRuleResponse` 和 `AlertRuleCreate` 中增加：

```python
# AlertRuleCreate
dedup_cooldown_minutes: int | None = Field(default=None, ge=1, le=1440)
dedup_rearm_pct: Decimal | None = Field(default=None, ge=Decimal("0.1"), le=Decimal("10.0"))

# AlertRuleResponse  
last_triggered_at: datetime | None = None
last_triggered_price: Decimal | None = None
dedup_cooldown_minutes: int | None = None
dedup_rearm_pct: Decimal | None = None
```

### 3. `workers/market_worker/fetcher.py` — 两处改动

**改动 A：分钟线同步接入告警检查**

在 `fetch_minute_kline` 函数末尾（`_save_klines` 之后、`_publish_quote` 之后）增加：

```python
# 分钟线告警检查（原只有日线做，分钟线不做）
latest = rows[-1] if rows else None
if latest:
    _check_alerts(db, symbol, rows)
```

**改动 B：替换 `_check_alerts` 实现**

```python
# 旧实现
def _check_alerts(db, symbol, rows):
    ...
    evaluate_all_active_rules(db, symbol, current_price, previous_close)

# 新实现
from shared.alert_coordinator import evaluate_and_notify

def _check_alerts(db, symbol, rows):
    if not rows:
        return
    latest = rows[-1]
    current_price = _extract_close(latest)  # 复用现有的收盘价提取逻辑

    # previous_close 仅在日线场景有意义，分钟线传 None
    previous_close = None
    if len(rows) >= 2:
        previous_close = _get_previous_close(db, symbol, rows[0].get("ts"))

    evaluate_and_notify(db, symbol, current_price, previous_close)
```

### 4. Alembic 迁移

```bash
cd backend
alembic revision --autogenerate -m "add_alert_dedup_fields"
alembic upgrade head
```

生成的迁移应包含：

```python
def upgrade():
    op.add_column("alert_rules", sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alert_rules", sa.Column("last_triggered_price", sa.Numeric(18, 4), nullable=True))
    op.add_column("alert_rules", sa.Column("dedup_cooldown_minutes", sa.Integer(), nullable=True))
    op.add_column("alert_rules", sa.Column("dedup_rearm_pct", sa.Numeric(5, 2), nullable=True))

def downgrade():
    op.drop_column("alert_rules", "last_triggered_at")
    op.drop_column("alert_rules", "last_triggered_price")
    op.drop_column("alert_rules", "dedup_cooldown_minutes")
    op.drop_column("alert_rules", "dedup_rearm_pct")
```

### 5. `app/ws/market_ws.py` — 新增告警推送频道（可选）

如果前端需要实时告警弹窗，在 WebSocket 中增加：

```python
# 已有行情频道
# await manager.subscribe(websocket, f"quotes:{symbol}")

# 新增告警频道（订阅用户维度的告警推送）
# 前端连接时传入 user_id，服务端 subscribe 到 Redis channel "alerts:{user_id}"
async def subscribe_alerts(websocket, user_id: int):
    channel = f"alerts:{user_id}"
    pubsub = redis_async.pubsub()
    await pubsub.subscribe(channel)
    # 循环读取并推送...
```

## 状态机行为速查

| 当前状态 | 条件满足? | 冷却期满? | 动作 |
|----------|----------|----------|------|
| IDLE | 是 | — | **发通知** → COOLDOWN |
| COOLDOWN | 是 | 否 | 抑制，保持 COOLDOWN |
| COOLDOWN | 是 | 是 | 进入 ARMED（等回落） |
| COOLDOWN | 否 | 否 | 抑制，保持 COOLDOWN |
| COOLDOWN | 否 | 是 | → IDLE（回落确认） |
| ARMED | 是 | — | 保持 ARMED |
| ARMED | 否 | — | 回落至安全区 → IDLE，否则保持 ARMED |

## 配置参数

| 参数 | 默认值 | 建议范围 |
|------|-------|---------|
| `dedup_cooldown_minutes` | 30 分钟 | 5~120 分钟（按标的波动率调整） |
| `dedup_rearm_pct` | 2.0% | 0.5%~5.0%（蓝筹股可收紧，小盘股放宽） |

## 现有数据兼容性

新增字段全部 `nullable=True, default=None`，现有告警规则不受影响：
- `last_triggered_at = None` → 引擎视为 IDLE 状态，首次触发正常通知
- `dedup_cooldown_minutes = None` → 使用引擎默认 30 分钟
- `dedup_rearm_pct = None` → 使用引擎默认 2.0%
*（内容由AI生成，仅供参考）*
