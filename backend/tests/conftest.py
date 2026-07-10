"""全局 pytest fixtures：共享的 mock 对象和辅助工具"""
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest
from decimal import Decimal


# ── 固定时间点（避免时区/时间相关 flaky test）─────────────
FIXED_NOW = __import__("datetime").datetime(
    2026, 7, 10, 14, 30, 0,
    tzinfo=__import__("datetime").timezone.utc,
)


@pytest.fixture()
def now():
    """固定的时间点，用于注入去重引擎"""
    return FIXED_NOW


# @pytest.fixture()
# def fake_redis():
#     """Mock Redis 同步客户端"""
#     rc = MagicMock()
#     return rc


@pytest.fixture()
def fake_redis():
    """Mock Redis 同步客户端"""
    from asyncio import Future
    rc = MagicMock(spec=None) 
    rc.publish.return_value = Future()
    rc.publish.return_value.set_result(0)
    return rc

@pytest.fixture()
def fake_async_session():
    """Mock SQLAlchemy AsyncSession"""
    session = MagicMock()
    return session


def make_alert_rule(
    rule_id: int = 1,
    user_id: int = 100,
    symbol: str = "600519.SH",
    rule_type: str = "price_above",
    condition: dict | None = None,
    status: str = "active",
    last_triggered_at: datetime | None = None,
    last_triggered_price: Decimal | None = None,
    dedup_cooldown_minutes: int | None = None,
    dedup_rearm_pct: Decimal | None = None,
) -> MagicMock:
    """快速构造 AlertRule ORM mock 对象"""
    rule = MagicMock()
    rule.id = rule_id
    rule.user_id = user_id
    rule.symbol = symbol
    rule.rule_type = rule_type
    rule.condition = condition or {"rule_type": rule_type, "value": "1800"}
    rule.notify_channels = ["inapp"]
    rule.status = status
    rule.baseline_price = None

    # 去重字段
    rule.last_triggered_at = last_triggered_at
    rule.last_triggered_price = last_triggered_price
    rule.dedup_cooldown_minutes = dedup_cooldown_minutes
    rule.dedup_rearm_pct = dedup_rearm_pct

    return rule
