from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import BizException, BizErrorCode
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.alert import (
    CreateAlertRuleRequest,
    UpdateAlertRuleRequest,
    AlertRulePublic,
    AlertLogPublic,
)
from app.services.alert_service import (
    create_alert_rule,
    get_alert_rules,
    update_alert_rule,
    get_alert_logs,
    delete_alert_rule,
    AlertRuleNotFoundError,
)
from shared.db.session import get_db


router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.post("", response_model=AlertRulePublic, status_code=status.HTTP_201_CREATED)
def create_alert(
    payload: CreateAlertRuleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = create_alert_rule(
        db=db,
        user_id=current_user.id,
        symbol=payload.symbol,
        condition=payload.condition,
        notify_channels=payload.notify_channels,
        dedup_cooldown_minutes=payload.dedup_cooldown_minutes,
        dedup_rearm_pct=payload.dedup_rearm_pct,
    )
    return AlertRulePublic.model_validate(rule)


@router.get("", response_model=list[AlertRulePublic])
def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rule_status: str | None = Query(None, pattern=r"^(active|paused)$"),
    symbol: str | None = Query(None, min_length=1),
):
    rules = get_alert_rules(db, user_id=current_user.id, status=rule_status, symbol=symbol)

    return [AlertRulePublic.model_validate(r) for r in rules]


@router.patch("/{rule_id}", response_model=AlertRulePublic)
def patch_alert(
    rule_id: int,
    payload: UpdateAlertRuleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        rule = update_alert_rule(
            db=db,
            rule_id=rule_id,
            user_id=current_user.id,
            condition=payload.condition,
            status=payload.status,
            dedup_cooldown_minutes=payload.dedup_cooldown_minutes,
            dedup_rearm_pct=payload.dedup_rearm_pct,
        )
    except AlertRuleNotFoundError:
        raise BizException(BizErrorCode.NOT_FOUND, "Alert rule not found", status_code=404)
    return AlertRulePublic.model_validate(rule)


@router.get("/{rule_id}/logs", response_model=list[AlertLogPublic])
def list_alert_logs(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logs = get_alert_logs(db, rule_id=rule_id, user_id=current_user.id)
    except AlertRuleNotFoundError:
        raise BizException(BizErrorCode.NOT_FOUND, "Alert rule not found", status_code=404)
    return [AlertLogPublic.model_validate(log) for log in logs]


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        delete_alert_rule(db=db, rule_id=rule_id, user_id=current_user.id)
    except AlertRuleNotFoundError:
        raise BizException(BizErrorCode.NOT_FOUND, "Alert rule not found", status_code=404)
    return None
