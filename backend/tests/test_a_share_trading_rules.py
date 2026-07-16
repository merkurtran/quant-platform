from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.services.a_share_trading_rules import (
    PriceLimits,
    AShareBacktestFiller,
    ASharePercentSizer,
    TradingRuleViolation,
    calculate_price_limits,
    clamp_execution_price,
    ensure_mock_market_open,
    is_locked_against_order,
    is_trading_day,
    settle_position_for_trade_date,
    validate_order_price,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")


def test_exchange_calendar_rejects_weekend_and_statutory_holiday():
    assert is_trading_day(date(2026, 7, 16)) is True
    assert is_trading_day(date(2026, 7, 18)) is False
    assert is_trading_day(date(2026, 10, 1)) is False

    with pytest.raises(TradingRuleViolation, match="非交易日"):
        ensure_mock_market_open(datetime(2026, 10, 1, 10, tzinfo=SHANGHAI))


def test_mock_orders_only_execute_during_continuous_trading():
    assert ensure_mock_market_open(
        datetime(2026, 7, 16, 10, tzinfo=SHANGHAI)
    ) == date(2026, 7, 16)

    with pytest.raises(TradingRuleViolation, match="连续竞价"):
        ensure_mock_market_open(datetime(2026, 7, 16, 12, tzinfo=SHANGHAI))


@pytest.mark.parametrize(
    ("symbol", "expected_lower", "expected_upper"),
    [
        ("600519.SH", "9.00", "11.00"),
        ("000001.SZ", "9.00", "11.00"),
        ("300750.SZ", "8.00", "12.00"),
        ("688981.SH", "8.00", "12.00"),
        ("920000.BJ", "7.00", "13.00"),
    ],
)
def test_price_limits_follow_board_rules(symbol, expected_lower, expected_upper):
    limits = calculate_price_limits(symbol, Decimal("10"), listed_sessions=100)

    assert limits.lower == Decimal(expected_lower)
    assert limits.upper == Decimal(expected_upper)


def test_first_five_listed_sessions_have_no_daily_price_limit():
    assert calculate_price_limits(
        "600000.SH", Decimal("10"), listed_sessions=5
    ) == PriceLimits(lower=None, upper=None)


def test_out_of_range_price_is_rejected_and_locked_limit_does_not_fill():
    limits = PriceLimits(lower=Decimal("9.00"), upper=Decimal("11.00"))

    with pytest.raises(TradingRuleViolation, match="9.00 至 11.00"):
        validate_order_price(Decimal("11.01"), limits)

    assert is_locked_against_order("buy", Decimal("11.00"), limits) is True
    assert is_locked_against_order("sell", Decimal("9.00"), limits) is True
    assert is_locked_against_order("buy", Decimal("10.99"), limits) is False
    assert clamp_execution_price("buy", Decimal("11.02"), limits) == Decimal("11.00")
    assert clamp_execution_price("sell", Decimal("8.98"), limits) == Decimal("9.00")


def test_t1_pending_volume_becomes_sellable_on_next_trade_date():
    position = SimpleNamespace(
        available_volume=Decimal("200"),
        pending_settlement_volume=Decimal("100"),
        last_buy_trade_date=date(2026, 7, 16),
    )

    settle_position_for_trade_date(position, date(2026, 7, 16))
    assert position.available_volume == Decimal("200")
    assert position.pending_settlement_volume == Decimal("100")

    settle_position_for_trade_date(position, date(2026, 7, 17))
    assert position.available_volume == Decimal("300")
    assert position.pending_settlement_volume == Decimal("0")


class FakeLine:
    def __init__(self, current, previous=None):
        self.current = current
        self.previous = current if previous is None else previous

    def __getitem__(self, index):
        return self.previous if index == -1 else self.current


class FakeDateLine:
    def __init__(self, value):
        self.value = value

    def date(self, ago):
        return self.value


class FakeData:
    def __init__(self, trade_date, low, high, previous_close, length=100):
        self.datetime = FakeDateLine(trade_date)
        self.low = FakeLine(low)
        self.high = FakeLine(high)
        self.close = FakeLine(high, previous_close)
        self.length = length

    def __len__(self):
        return self.length


class FakeOrder:
    def __init__(self, data, side, volume, position_size=0):
        self.data = data
        self.side = side
        self.executed = SimpleNamespace(remsize=Decimal(str(volume)))
        self.owner = SimpleNamespace(
            getposition=lambda current_data: SimpleNamespace(size=position_size)
        )

    def isbuy(self):
        return self.side == "buy"

    def issell(self):
        return self.side == "sell"


def test_backtest_filler_blocks_one_price_limit_orders():
    filler = AShareBacktestFiller("600519.SH", listed_sessions_before_start=100)
    limit_up_data = FakeData(
        date(2026, 7, 16), low=Decimal("11"), high=Decimal("11"), previous_close=Decimal("10")
    )
    limit_down_data = FakeData(
        date(2026, 7, 16), low=Decimal("9"), high=Decimal("9"), previous_close=Decimal("10")
    )

    assert filler(FakeOrder(limit_up_data, "buy", 100), Decimal("11"), 0) == 0
    assert filler(FakeOrder(limit_down_data, "sell", 100, 100), Decimal("9"), 0) == 0


def test_backtest_filler_prevents_selling_same_day_purchase():
    filler = AShareBacktestFiller("600519.SH", listed_sessions_before_start=100)
    data = FakeData(
        date(2026, 7, 16), low=Decimal("10"), high=Decimal("10.2"), previous_close=Decimal("10")
    )

    assert filler(FakeOrder(data, "buy", 100), Decimal("10.1"), 0) == 100
    assert filler(FakeOrder(data, "sell", 100, 100), Decimal("10.1"), 0) == 0

    data.datetime.value = date(2026, 7, 17)
    assert filler(FakeOrder(data, "sell", 100, 100), Decimal("10.1"), 0) == 100


def test_backtest_default_sizer_uses_cash_and_a_share_board_lots():
    sizer = ASharePercentSizer(percents=95, lot_size=100)
    data = SimpleNamespace(close=FakeLine(Decimal("10.03")))

    assert sizer._getsizing(None, 100_000, data, True) == 9_400
