from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.market import Klines
from app.services.market_service import get_quote_snapshots


def test_get_quote_snapshots_returns_change_for_each_symbol():
    engine = create_engine("sqlite://")
    Klines.__table__.create(engine)

    with Session(engine) as db:
        for symbol, closes in {
            "600519.SH": (Decimal("1500"), Decimal("1530")),
            "000001.SZ": (Decimal("10"), Decimal("9.5")),
        }.items():
            for day, close in enumerate(closes, start=1):
                db.add(
                    Klines(
                        symbol=symbol,
                        period="1d",
                        ts=datetime(2026, 7, day, tzinfo=timezone.utc),
                        open=close,
                        high=close,
                        low=close,
                        close=close,
                        volume=Decimal("100"),
                        amount=None,
                    )
                )
        db.commit()

        snapshots = get_quote_snapshots(db, ["600519.SH", "000001.SZ"])

    assert snapshots[0]["price"] == Decimal("1530.000")
    assert snapshots[0]["change"] == Decimal("30.000")
    assert snapshots[0]["change_pct"] == Decimal("2.00")
    assert snapshots[1]["price"] == Decimal("9.500")
    assert snapshots[1]["change"] == Decimal("-0.500")
    assert snapshots[1]["change_pct"] == Decimal("-5.00")


def test_get_quote_snapshots_uses_previous_intraday_trading_day():
    engine = create_engine("sqlite://")
    Klines.__table__.create(engine)

    with Session(engine) as db:
        for day, hour, close in [
            (1, 14, Decimal("100")),
            (1, 15, Decimal("101")),
            (2, 10, Decimal("103")),
        ]:
            db.add(
                Klines(
                    symbol="300750.SZ",
                    period="1m",
                    ts=datetime(2026, 7, day, hour, tzinfo=timezone.utc),
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=Decimal("100"),
                    amount=None,
                )
            )
        db.commit()

        snapshot = get_quote_snapshots(db, ["300750.SZ"])[0]

    assert snapshot["price"] == Decimal("103.000")
    assert snapshot["previous_close"] == Decimal("101.000")
    assert snapshot["change"] == Decimal("2.000")
