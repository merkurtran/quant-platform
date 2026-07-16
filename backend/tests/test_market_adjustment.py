from datetime import datetime, timezone
from decimal import Decimal

from shared.market_data.adjustment import AdjustMethod, calculate_adjusted_prices


def _bar(day: int, close: str) -> dict:
    value = Decimal(close)
    return {
        "ts": datetime(2026, 6, day, tzinfo=timezone.utc),
        "open": value,
        "high": value,
        "low": value,
        "close": value,
        "volume": Decimal("100"),
        "amount": None,
    }


def test_none_adjustment_keeps_raw_prices():
    raw = [_bar(11, "11.30"), _bar(12, "11.24")]

    assert calculate_adjusted_prices(raw, [], AdjustMethod.NONE) == raw


def test_cash_dividend_qfq_matches_theoretical_ex_price():
    raw = [_bar(11, "11.30"), _bar(12, "11.24")]
    actions = [
        {
            "ex_date": raw[1]["ts"].date(),
            "cash_per_share": Decimal("0.36"),
            "stock_ratio": Decimal("0"),
            "rights_price": Decimal("0"),
            "rights_ratio": Decimal("0"),
        }
    ]

    adjusted = calculate_adjusted_prices(raw, actions, AdjustMethod.QFQ_RATIO)

    assert adjusted[0]["close"] == Decimal("10.94")
    assert adjusted[1]["close"] == Decimal("11.24")


def test_same_day_dividend_stock_and_rights_actions_are_combined():
    raw = [_bar(11, "10"), _bar(12, "8.31")]
    ex_date = raw[1]["ts"].date()
    actions = [
        {
            "ex_date": ex_date,
            "cash_per_share": Decimal("0.2"),
            "stock_ratio": Decimal("0.1"),
            "rights_price": Decimal("0"),
            "rights_ratio": Decimal("0"),
        },
        {
            "ex_date": ex_date,
            "cash_per_share": Decimal("0"),
            "stock_ratio": Decimal("0"),
            "rights_price": Decimal("5"),
            "rights_ratio": Decimal("0.2"),
        },
    ]

    adjusted = calculate_adjusted_prices(raw, actions, AdjustMethod.QFQ_RATIO)

    expected = (Decimal("10") - Decimal("0.2") + Decimal("5") * Decimal("0.2")) / Decimal("1.3")
    assert adjusted[0]["close"].quantize(Decimal("0.000001")) == expected.quantize(
        Decimal("0.000001")
    )
    assert adjusted[1]["close"] == Decimal("8.31")
