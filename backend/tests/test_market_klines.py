from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.market import Klines
from app.services.market_service import get_klines


def test_get_klines_returns_latest_limit_in_ascending_order():
    engine = create_engine("sqlite://")
    Klines.__table__.create(engine)

    with Session(engine) as db:
        for day in range(1, 6):
            close = Decimal(str(day))
            db.add(
                Klines(
                    symbol="000001.SZ",
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

        rows = get_klines(db, "000001.SZ", "1d", limit=3)

    assert [row.ts.day for row in rows] == [3, 4, 5]
