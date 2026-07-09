from decimal import Decimal
from typing import Optional
import json

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.models.alert import AlertRules, AlertLogs
from app.schemas.alert import AlertConditionUnion, PriceAboveCondition, PriceBelowCondition, PctChangeCondition
from shared.redis_client import redis_client
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


def create_alert_rule(db: Session, user_id: int, symbol: str, condition: AlertConditionUnion, notify_channels: list[str]) -> AlertRules:
    baseline_price = None
    if isinstance(condition, PctChangeCondition) and condition.baseline == "rule_created_price":
        baseline_price = get_baseline_price(db, symbol)
    
    rule = AlertRules(
        user_id=user_id,
        symbol=symbol,
        rule_type=condition.rule_type,
        condition=condition.model_dump(),
        notify_channels=notify_channels,
        baseline_price=baseline_price,
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

def update_alert_rule(db: Session, rule_id: int, user_id: int, condition: AlertConditionUnion | None, status: str | None) -> AlertRules:
    rule = _check_rule_ownership(db, rule_id, user_id)
    if condition is not None:
        rule.condition = condition.model_dump()
    if status is not None:
        rule.status = status
    db.commit()
    db.refresh(rule)
    return rule


def get_alert_logs(db: Session, rule_id: int, user_id: int) -> list[AlertLogs]:
    rule = _check_rule_ownership(db, rule_id, user_id)
    return rule.logs


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
        cached = redis_client.get(f"latest_price:{symbol}")
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