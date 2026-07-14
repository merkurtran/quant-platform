import json
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.market import Klines
from app.services.market_service import get_quote_snapshots


class FakeQuoteCache:
    def __init__(self, values: dict[str, dict]):
        self.values = values

    def mget(self, keys: list[str]) -> list[str | None]:
        return [
            json.dumps(self.values[key]) if key in self.values else None
            for key in keys
        ]


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


def test_get_quote_snapshots_prefers_newer_cached_quote():
    engine = create_engine("sqlite://")
    Klines.__table__.create(engine)
    symbol = "600519.SH"

    with Session(engine) as db:
        db.add(
            Klines(
                symbol=symbol,
                period="1m",
                ts=datetime(2026, 7, 14, 10, 0, tzinfo=timezone.utc),
                open=Decimal("1500"),
                high=Decimal("1500"),
                low=Decimal("1500"),
                close=Decimal("1500"),
                volume=Decimal("100"),
                amount=None,
            )
        )
        db.commit()
        cache = FakeQuoteCache(
            {
                f"latest_price:{symbol}": {
                    "symbol": symbol,
                    "price": 1502.5,
                    "previous_close": 1490,
                    "change": 12.5,
                    "change_pct": 0.8389,
                    "ts": "2026-07-14T10:01:00+08:00",
                }
            }
        )

        snapshot = get_quote_snapshots(db, [symbol], cache)[0]

    assert snapshot["price"] == 1502.5
    assert snapshot["ts"] == "2026-07-14T10:01:00+08:00"


def test_get_quote_snapshots_keeps_database_quote_when_cache_is_older():
    engine = create_engine("sqlite://")
    Klines.__table__.create(engine)
    symbol = "000001.SZ"

    with Session(engine) as db:
        db.add(
            Klines(
                symbol=symbol,
                period="1m",
                ts=datetime(2026, 7, 14, 10, 2, tzinfo=timezone.utc),
                open=Decimal("10.5"),
                high=Decimal("10.5"),
                low=Decimal("10.5"),
                close=Decimal("10.5"),
                volume=Decimal("100"),
                amount=None,
            )
        )
        db.commit()
        cache = FakeQuoteCache(
            {
                f"latest_price:{symbol}": {
                    "symbol": symbol,
                    "price": 10.3,
                    "previous_close": 10.2,
                    "change": 0.1,
                    "change_pct": 0.98,
                    "ts": "2026-07-14T10:01:00+08:00",
                }
            }
        )

        snapshot = get_quote_snapshots(db, [symbol], cache)[0]

    assert snapshot["price"] == Decimal("10.500")
    assert snapshot["ts"].replace(tzinfo=None) == datetime(2026, 7, 14, 10, 2)


def test_get_quote_snapshots_keeps_change_fields_from_complete_database_quote():
    engine = create_engine("sqlite://")
    Klines.__table__.create(engine)
    symbol = "000001.SZ"

    with Session(engine) as db:
        for day, close in ((13, Decimal("10.2")), (14, Decimal("10.5"))):
            db.add(
                Klines(
                    symbol=symbol,
                    period="1m",
                    ts=datetime(2026, 7, day, 15, 0, tzinfo=timezone.utc),
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=Decimal("100"),
                    amount=None,
                )
            )
        db.commit()
        cache = FakeQuoteCache(
            {
                f"latest_price:{symbol}": {
                    "symbol": symbol,
                    "price": 10.5,
                    "ts": "2026-07-14T15:00:00",
                }
            }
        )

        snapshot = get_quote_snapshots(db, [symbol], cache)[0]

    assert snapshot["previous_close"] == Decimal("10.200")
    assert snapshot["change"] == Decimal("0.300")
    assert snapshot["change_pct"] == Decimal("0.300") / Decimal("10.200") * 100
