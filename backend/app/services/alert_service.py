from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
import json

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.models.alert import AlertRules, AlertLogs
from app.schemas.alert import AlertConditionUnion, PriceAboveCondition, PriceBelowCondition, PctChangeCondition
from app.services.alert_engine import evaluate as dedup_evaluate, AlertDedupDecision
from shared.redis_client import get_redis_client
from shared.logging_config import get_logger
from app.models.market import Klines

class AlertRuleNotFoundError(Exception):
    pass


logger = get_logger("alert_service")
_condition_adapter = TypeAdapter(AlertConditionUnion)

def _check_rule_ownership(db: Session, rule_id: int, user_id: int) -> AlertRules:
    rule = db.query(AlertRules).filter(AlertRules.id == rule_id, AlertRules.user_id == user_id).first()
    if rule is None:
        raise AlertRuleNotFoundError(f"Alert rule {rule_id} not found for user {user_id}")
    return rule


def create_alert_rule(
    db: Session,
    user_id: int,
    symbol: str,
    condition: AlertConditionUnion,
    notify_channels: list[str],
    dedup_cooldown_minutes: int | None = None,
    dedup_rearm_pct: Decimal | None = None,
) -> AlertRules:
    baseline_price = None
    if isinstance(condition, PctChangeCondition) and condition.baseline == "rule_created_price":
        baseline_price = get_baseline_price(db, symbol)
    
    rule = AlertRules(
        user_id=user_id,
        symbol=symbol,
        rule_type=condition.rule_type,
        condition=condition.model_dump(mode="json"),
        notify_channels=notify_channels,
        baseline_price=baseline_price,
        dedup_cooldown_minutes=dedup_cooldown_minutes,
        dedup_rearm_pct=dedup_rearm_pct,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def get_alert_rules(db: Session, user_id: int, status: str | None = None, symbol: str | None = None) -> list[AlertRules]:
    query = db.query(AlertRules).filter(AlertRules.user_id == user_id)
    if status:
        query = query.filter(AlertRules.status == status)
    if symbol:
        query = query.filter(AlertRules.symbol == symbol)
    return query.all()

def update_alert_rule(
    db: Session,
    rule_id: int,
    user_id: int,
    condition: AlertConditionUnion | None = None,
    status: str | None = None,
    dedup_cooldown_minutes: int | None = None,
    dedup_rearm_pct: Decimal | None = None,
) -> AlertRules:
    rule = _check_rule_ownership(db, rule_id, user_id)
    if condition is not None:
        rule.condition = condition.model_dump(mode="json")
    if status is not None:
        rule.status = status
    if dedup_cooldown_minutes is not None:
        rule.dedup_cooldown_minutes = dedup_cooldown_minutes
    if dedup_rearm_pct is not None:
        rule.dedup_rearm_pct = dedup_rearm_pct
    db.commit()
    db.refresh(rule)
    return rule


def get_alert_logs(db: Session, rule_id: int, user_id: int) -> list[AlertLogs]:
    rule = _check_rule_ownership(db, rule_id, user_id)
    return rule.logs


def delete_alert_rule(db: Session, rule_id: int, user_id: int) -> None:
    rule = _check_rule_ownership(db, rule_id, user_id)
    db.delete(rule)
    db.commit()


def check_condition_triggered(
    condition: AlertConditionUnion,
    current_price: Decimal,
    previous_close: Decimal | None,
    baseline_price: Decimal | None,
) -> bool:
    if isinstance(condition, PriceAboveCondition):
        return current_price > condition.value

    if isinstance(condition, PriceBelowCondition):
        return current_price < condition.value

    if isinstance(condition, PctChangeCondition):
        if condition.baseline == "previous_close":
            baseline = previous_close
        elif condition.baseline == "rule_created_price":
            baseline = baseline_price
        else:
            baseline = condition.custom_baseline

        if baseline is None or baseline == 0:
            return False

        pct = (current_price - baseline) / baseline * 100
        if condition.operator == "gt":
            return pct > condition.value
        return pct < -condition.value

    # TODO volume_spike / indicator 还没实现
    return False
    

def evaluate_all_active_rules(db: Session, symbol: str, current_price: Decimal, previous_close: Decimal | None) -> None:
    """
    给 market_worker 调用: 传入某支股票的最新行情,检查所有关注这支股票的active规则
    """
    rules = (
        db.query(AlertRules)
        .filter(AlertRules.symbol == symbol, AlertRules.status == "active")
        .all()
    )

    triggered_logs: list[AlertLogs] = []

    for rule in rules:
        condition = _condition_adapter.validate_python(rule.condition)

        triggered = check_condition_triggered(
            condition=condition,
            current_price=current_price,
            previous_close=previous_close,
            baseline_price=rule.baseline_price,
        )

        if triggered:
            log = AlertLogs(
                rule_id=rule.id,
                trigger_value=current_price,
                message=f"Alert triggered for {symbol} at {current_price}",
            )
            db.add(log)
            triggered_logs.append(log)
    if triggered_logs:
        db.commit()
        for log in triggered_logs:
            db.refresh(log)
    return triggered_logs
        

def get_baseline_price(db: Session, symbol: str) -> Decimal | None:
    """
    三级降级策略获取最新价格:
    1. Redis (latest_price:{symbol})
    2. klines 表最新日线收盘价
    3. 返回 None(不在此处调 AKShare,由调用方决定是否异步补数据)
    """
    try:
        cached = get_redis_client().get(f"latest_price:{symbol}")
        if cached:
            data = json.loads(cached)
            return Decimal(str(data["price"]))
    except Exception as e:
        logger.warning(f"读取 Redis 最新价失败 {symbol}: {e}")
    
    try:
        latest_kline = (
            db.query(Klines.close)
            .filter(Klines.symbol == symbol, Klines.period == "1d")
            .order_by(Klines.ts.desc())
            .first()
        )
        if latest_kline:
            return latest_kline[0]
    except Exception as e:
        logger.warning(f"查询数据库最新价失败 {symbol}: {e}")
    

    logger.info(f"{symbol} 无可用价格数据，返回 None")
    return None


def _get_threshold_price(condition: AlertConditionUnion) -> Decimal | None:
    """从条件对象中提取阈值价格，供去重引擎计算回落幅度使用"""
    if isinstance(condition, (PriceAboveCondition, PriceBelowCondition)):
        return condition.value
    if isinstance(condition, PctChangeCondition):
        # pct_change 的 threshold 由 baseline + value 动态决定，
        # 此处无法直接给出固定值，由调用方按需传入
        return None
    return None


def evaluate_and_notify(db: Session, symbol: str, current_price: Decimal, previous_close: Decimal | None) -> list[AlertLogs]:
    """协调器：条件评估 → 去重状态机判断 → 持久化触发记录 + 更新规则去重状态。

    替代旧的 evaluate_all_active_rules，增加 Cooldown+Rearm 去重逻辑。
    同时兼容日线和分钟线两种调用场景（分钟线场景 previous_close 可为 None）。

    Args:
        db: 同步数据库会话
        symbol: 股票代码
        current_price: 当前最新价
        previous_close: 昨收价（日线有意义，分钟线可传 None）

    Returns:
        本次实际触发的 AlertLogs 列表（经过去重后真正发出通知的）
    """
    rules = (
        db.query(AlertRules)
        .filter(AlertRules.symbol == symbol, AlertRules.status == "active")
        .all()
    )

    notified_logs: list[AlertLogs] = []

    for rule in rules:
        condition = _condition_adapter.validate_python(rule.condition)

        # 1. 条件评估
        condition_met = check_condition_triggered(
            condition=condition,
            current_price=current_price,
            previous_close=previous_close,
            baseline_price=rule.baseline_price,
        )

        # 2. 去重状态机决策
        threshold = _get_threshold_price(condition)
        decision: AlertDedupDecision = dedup_evaluate(
            condition_met=condition_met,
            rule_last_triggered_at=rule.last_triggered_at,
            rule_last_triggered_price=rule.last_triggered_price,
            cooldown_minutes=rule.dedup_cooldown_minutes,
            rearm_pct=rule.dedup_rearm_pct,
            current_price=current_price,
            threshold_price=threshold,
            condition_type=rule.rule_type,
        )

        # 3. 持久化：更新规则去重状态
        if decision.new_state.value != "idle" or decision.should_notify:
            # 只在有状态变化或需要通知时才写回规则表，减少无意义更新
            if decision.should_notify:
                rule.last_triggered_at = datetime.now(timezone.utc)  # type: ignore[name-defined]
                rule.last_triggered_price = current_price

        # 4. 记录日志 + 推送通知
        if decision.should_notify:
            log = AlertLogs(
                rule_id=rule.id,
                trigger_value=current_price,
                message=f"Alert triggered for {symbol} at {current_price} [{decision.reason}]",
            )
            db.add(log)
            notified_logs.append(log)

            _dispatch_notifications(rule, symbol, current_price, decision.reason)

        logger.debug(
            f"Rule #{rule.id} {symbol}: met={condition_met}, "
            f"decision={decision}"
        )

    if notified_logs:
        db.commit()
        for log in notified_logs:
            db.refresh(log)

    return notified_logs


# ── 通知分发（按 notify_channels 路由到各渠道）─────────────

def _dispatch_notifications(
    rule: AlertRules,
    symbol: str,
    current_price: Decimal,
    reason: str,
) -> None:
    """根据规则的 notify_channels 配置，将告警推送到对应渠道。

    当前支持的渠道：
      - inapp: 通过 Redis pubsub → WebSocket 实时推送（已实现）
      - email: 占位符（待接入邮件服务）
      - webhook: 占位符（待接入 HTTP 回调）

    注意：本函数在 db.commit() 之后被调用，推送失败不影响已持久化的 AlertLog。
    """
    channels = rule.notify_channels or []
    if not channels:
        return

    payload = json.dumps({
        "event": "alert",
        "rule_id": rule.id,
        "symbol": symbol,
        "rule_type": rule.rule_type,
        "trigger_value": float(current_price),
        "reason": reason,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False)

    for channel in channels:
        try:
            if channel == "inapp":
                _notify_inapp(rule.user_id, payload)
            elif channel == "email":
                _notify_email(rule, symbol, current_price)
            elif channel == "webhook":
                _notify_webhook(rule, symbol, current_price)
            else:
                logger.warning(f"Rule #{rule.id}: unknown notify_channel '{channel}', skipped")
        except Exception as e:
            # 单渠道推送失败不阻断其他渠道
            logger.error(f"Rule #{rule.id} notification failed on '{channel}': {e}")


def _notify_inapp(user_id: int, payload: str) -> None:
    """inapp 推送：publish 到 Redis alerts:{user_id} 频道，由 WebSocket 服务端订阅并转发给在线用户"""
    rc = get_redis_client()
    rc.publish(f"alerts:{user_id}", payload)


def _notify_email(rule: AlertRules, symbol: str, current_price: Decimal) -> None:
    """email 渠道：占位符，后续可接入 SMTP / SendGrid 等"""
    logger.info(f"[email placeholder] Rule #{rule.id}: {symbol} triggered at {current_price}")


def _notify_webhook(rule: AlertRules, symbol: str, current_price: Decimal) -> None:
    """webhook 渠道：占位符，后续可接入 HTTP POST 回调"""
    logger.info(f"[webhook placeholder] Rule #{rule.id}: {symbol} triggered at {current_price}")