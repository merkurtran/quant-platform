# Phase 2 技术债清单

## 1. 预警系统：当前精度为日级别，不追求分钟级实时

**现状**：`_check_alerts` 挂在 `fetch_daily_kline` 末尾，每天收盘后触发一次。预警精度 = "按天检查收盘价"。

### 1a. ~~监控范围扩展~~ ✅ 已解决 (Phase 3)

**原问题**：`fetch_minute_kline` 当前只拉自选股，但预警规则可能建在全市场任意股票上。

**解决方案 (Phase 3)**：新增 `get_minute_kline_symbols()` 函数，返回 **自选股 ∪ 带活跃预警规则的股票** 的去重并集。`sync_minute_klines_by_period()` 已改用此函数。分钟线拉取范围不再遗漏非自选股的预警标的。

### 1b. ~~通知去重/收敛策略~~ ✅ 已解决 (Phase 3)

**原问题**：分钟级频率下，同一规则一天可能触发几十条通知。

**解决方案 (Phase 3)**：实现 **Cooldown + Rearm 三态状态机**（`app/services/alert_engine.py`）：
- `IDLE` → 首次触发 → 发通知 → `COOLDOWN`（冷却窗口，默认 30 分钟，可按规则自定义）
- `COOLDOWN` 期内一律抑制重复通知
- 冷却期满后若条件仍满足 → 进入 `ARMED`（等价格回落）
- `ARMED` 状态下价格回落超过阈值（默认 2%）→ 重置回 `IDLE`

新增文件：
- `app/services/alert_engine.py` — 去重状态机引擎（纯逻辑，无 DB 依赖，易测试）
- `app/services/alert_service.py` — 新增 `evaluate_and_notify()` 协调器函数

修改文件：
- `AlertRules` 模型新增 4 列：`last_triggered_at`, `last_triggered_price`, `dedup_cooldown_minutes`, `dedup_rearm_pct`
- `CreateAlertRuleRequest` / `UpdateAlertRuleRequest` / `AlertRulePublic` Schema 新增去重字段
- `fetcher.py` 的 `_check_alerts()` 改用 `evaluate_and_notify()`；`fetch_minute_kline()` 接入告警检查
- API 层 (`alerts.py`) 透传新的去重参数
- Alembic 迁移：`a3f7c2d1e8b0_add_alert_dedup_fields.py`

---

## 2. `_save_klines` 注释：ThreadPoolExecutor 并发尚未实现

`workers/market_worker/fetcher.py` 中 `_save_klines` 的 docstring 描述了 `ThreadPoolExecutor` 并发模型，但当前 `sync_daily_klines` 是单线程顺序遍历全市场股票。注释已加 TODO 标记，避免读代码时误以为优化已生效。
