"""预警去重状态机：IDLE / COOLDOWN / ARMED 三态转换

经典 Cooldown + Rearm 双阈值策略，解决分钟级高频触发导致的告警风暴问题。

状态转换规则:
  IDLE    --条件满足--> 发通知 → COOLDOWN
  COOLDOWN --冷却期内且条件满足--> 保持（抑制）
  COOLDOWN --冷却期满且条件满足--> ARMED（等价格回落）
  COOLDOWN --冷却期满且条件不满足--> IDLE（回落确认）
  ARMED   --条件仍满足--> 保持 ARMED
  ARMED   --价格回落超过 rearm_pct--> IDLE
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Literal

from shared.logging_config import get_logger

logger = get_logger("alert_engine")

# ── 引擎默认参数 ──────────────────────────────────────────────
DEFAULT_COOLDOWN_MINUTES: int = 30
DEFAULT_REARM_PCT: Decimal = Decimal("2.0")


class DedupState(str, Enum):
    IDLE = "idle"
    COOLDOWN = "cooldown"
    ARMED = "armed"


class AlertDedupDecision:
    """状态机一次评估的结果"""

    __slots__ = ("should_notify", "new_state", "reason")

    def __init__(self, should_notify: bool, new_state: DedupState, reason: str):
        self.should_notify = should_notify
        self.new_state = new_state
        self.reason = reason

    def __repr__(self) -> str:
        return f"AlertDedupDecision(notify={self.should_notify}, state={self.new_state.value}, {self.reason})"


def _infer_state(rule_last_triggered_at: datetime | None) -> DedupState:
    """根据 rule.last_triggered_at 推断当前状态。

    last_triggered_at is None → 从未触发过 → IDLE
    否则 → 需要结合冷却时间判断，由 _evaluate 进一步决定是 COOLDOWN 还是 ARMED
    """
    if rule_last_triggered_at is None:
        return DedupState.IDLE
    # 有历史触发记录，具体状态由 _evaluate 根据时间差判定
    return DedupState.COOLDOWN  # 占位，_evaluate 会修正


def _is_cooldown_expired(
    last_triggered_at: datetime,
    cooldown_minutes: int,
    now: datetime,
) -> bool:
    """检查冷却窗口是否已过期"""
    elapsed = (now - last_triggered_at).total_seconds() / 60.0
    return elapsed >= cooldown_minutes


def _price_retraced(
    triggered_price: Decimal,
    current_price: Decimal,
    threshold_price: Decimal,
    rearm_pct: Decimal,
    condition_type: str,
) -> bool:
    """判断价格是否已回落到安全区（ARMED → IDLE 的条件）。

    对于 price_above 规则：当前价 < (触发价 * (1 - rearm_pct)) 即为回落
    对于 price_below 规则：当前价 > (触发价 * (1 + rearm_pct)) 即为回落
    pct_change 规则：比较与阈值的距离百分比
    """
    if condition_type == "price_above":
        safe_price = triggered_price * (Decimal("1") - rearm_pct / Decimal("100"))
        return current_price < safe_price

    if condition_type == "price_below":
        safe_price = triggered_price * (Decimal("1") + rearm_pct / Decimal("100"))
        return current_price > safe_price

    # pct_change: 回落到阈值距离的 rearm_pct% 以内视为安全
    if condition_type == "pct_change":
        distance = abs(current_price - threshold_price)
        trigger_distance = abs(triggered_price - threshold_price)
        if trigger_distance == 0:
            return False
        retraced_ratio = (trigger_distance - distance) / trigger_distance
        return retraced_ratio >= rearm_pct / Decimal("100")

    # 未知的 rule_type，保守处理：不自动重置
    return False


def evaluate(
    *,
    condition_met: bool,
    rule_last_triggered_at: datetime | None,
    rule_last_triggered_price: Decimal | None,
    cooldown_minutes: int | None,
    rearm_pct: Decimal | None,
    current_price: Decimal,
    threshold_price: Decimal | None,
    condition_type: str,
    now: datetime | None = None,
) -> AlertDedupDecision:
    """执行去重状态机评估，返回是否应该发通知及新状态。

    Args:
        condition_met: 当前价格是否满足触发条件
        rule_last_triggered_at: 规则上次触发时间（DB 字段，None 表示从未触发）
        rule_last_triggered_price: 上次触发时的价格
        cooldown_minutes: 该规则的冷却窗口（分钟），None 用默认值 30
        rearm_pct: 回落百分比，None 用默认值 2.0%
        current_price: 当前最新价
        threshold_price: 条件阈值价（如 price_above.value），用于计算回落幅度
        condition_type: 规则类型 ("price_above" / "price_below" / "pct_change")
        now: 当前时间，主要供测试注入；生产环境用 utcnow

    Returns:
        AlertDedupDecision 包含 should_notify / new_state / reason
    """
    if now is None:
        now = datetime.now(timezone.utc)

    cd_min = cooldown_minutes or DEFAULT_COOLDOWN_MINUTES
    rearm = rearm_pct or DEFAULT_REARM_PCT

    # ── 从未触发过 ──
    if rule_last_triggered_at is None:
        if condition_met:
            return AlertDedupDecision(True, DedupState.COOLDOWN, "首次触发")
        return AlertDedupDecision(False, DedupState.IDLE, " idle, 条件不满足")

    # ── 冷却期内 ──
    if not _is_cooldown_expired(rule_last_triggered_at, cd_min, now):
        # 无论条件是否都满足，冷却期内一律抑制
        remaining = cd_min - (now - rule_last_triggered_at).total_seconds() / 60.0
        return AlertDedupDecision(
            False, DedupState.COOLDOWN, f"冷却中, 剩余 {remaining:.1f} 分钟"
        )

    # ── 冷却期已过 ──
    if condition_met:
        # 条件仍满足 → 进入 ARMED 等回落（不发新通知）
        return AlertDedupDecision(
            False, DedupState.ARMED, "冷却期满但条件仍满足, 进入 ARMED 等回落"
        )

    # 条件不满足 → 需检查是否真的回落了
    if rule_last_triggered_price is not None and threshold_price is not None:
        if _price_retraced(
            rule_last_triggered_price,
            current_price,
            threshold_price,
            rearm,
            condition_type,
        ):
            return AlertDedupDecision(False, DedupState.IDLE, "回落确认, 重置为 IDLE")

        # 价格还没回落足够多 → 保持 ARMED
        return AlertDedupDecision(
            False, DedupState.ARMED, "冷却期满但价格回落不足, 仍处于 ARMED"
        )

    # 没有足够的历史价格信息做回落判断，直接回 IDLE
    return AlertDedupDecision(False, DedupState.IDLE, "冷却期满, 无历史价格数据, 重置 IDLE")
