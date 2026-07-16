from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from zoneinfo import ZoneInfo

import exchange_calendars as exchange_calendars
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import Klines


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
PRICE_TICK = Decimal("0.01")


@dataclass(frozen=True)
class PriceLimits:
    lower: Decimal | None
    upper: Decimal | None


@dataclass(frozen=True)
class MockMarketState:
    trade_date: date
    market_price: Decimal
    previous_close: Decimal
    price_limits: PriceLimits


class TradingRuleViolation(ValueError):
    pass


@lru_cache(maxsize=1)
def _calendar():
    return exchange_calendars.get_calendar("XSHG")


def shanghai_now() -> datetime:
    return datetime.now(SHANGHAI_TZ)


def is_trading_day(value: date) -> bool:
    return _calendar().is_session(value.isoformat())


def is_continuous_trading_time(value: datetime) -> bool:
    local = value.astimezone(SHANGHAI_TZ)
    current = local.time().replace(tzinfo=None)
    return time(9, 30) <= current <= time(11, 30) or time(13, 0) <= current <= time(15, 0)


def ensure_mock_market_open(value: datetime) -> date:
    local = value.astimezone(SHANGHAI_TZ)
    if not is_trading_day(local.date()):
        raise TradingRuleViolation("当前为非交易日")
    if not is_continuous_trading_time(local):
        raise TradingRuleViolation("当前不在连续竞价时段")
    return local.date()


def board_for_symbol(symbol: str) -> str:
    code, _, exchange = symbol.upper().partition(".")
    if exchange == "BJ" or code.startswith(("4", "8", "92")):
        return "bse"
    if code.startswith(("688", "689")):
        return "star"
    if code.startswith("3"):
        return "chinext"
    return "main"


def price_limit_ratio(symbol: str) -> Decimal:
    board = board_for_symbol(symbol)
    if board in {"star", "chinext"}:
        return Decimal("0.20")
    if board == "bse":
        return Decimal("0.30")
    return Decimal("0.10")


def calculate_price_limits(
    symbol: str,
    previous_close: Decimal,
    listed_sessions: int,
) -> PriceLimits:
    if listed_sessions <= 5:
        return PriceLimits(lower=None, upper=None)
    ratio = price_limit_ratio(symbol)
    lower = (previous_close * (Decimal("1") - ratio)).quantize(
        PRICE_TICK, rounding=ROUND_HALF_UP
    )
    upper = (previous_close * (Decimal("1") + ratio)).quantize(
        PRICE_TICK, rounding=ROUND_HALF_UP
    )
    return PriceLimits(lower=lower, upper=upper)


def validate_order_price(price: Decimal | None, limits: PriceLimits) -> None:
    if price is None or limits.lower is None or limits.upper is None:
        return
    if price < limits.lower or price > limits.upper:
        raise TradingRuleViolation(
            f"委托价必须在 {limits.lower:.2f} 至 {limits.upper:.2f} 之间"
        )


def is_locked_against_order(
    side: str,
    market_price: Decimal,
    limits: PriceLimits,
) -> bool:
    if limits.lower is None or limits.upper is None:
        return False
    rounded_price = market_price.quantize(PRICE_TICK, rounding=ROUND_HALF_UP)
    return (side == "buy" and rounded_price >= limits.upper) or (
        side == "sell" and rounded_price <= limits.lower
    )


def clamp_execution_price(
    side: str,
    price: Decimal,
    limits: PriceLimits,
) -> Decimal:
    if limits.lower is None or limits.upper is None:
        return price
    if side == "buy":
        return min(price, limits.upper)
    return max(price, limits.lower)


async def load_mock_market_state(
    session: AsyncSession,
    symbol: str,
    trade_date: date,
) -> MockMarketState:
    latest_result = await session.execute(
        select(Klines.close, Klines.ts)
        .where(Klines.symbol == symbol)
        .order_by(Klines.ts.desc())
        .limit(1)
    )
    latest = latest_result.first()
    if latest is None or latest.ts.date() != trade_date:
        raise TradingRuleViolation("证券当日无有效行情，可能停牌或行情未同步")

    previous_result = await session.execute(
        select(Klines.close)
        .where(
            Klines.symbol == symbol,
            Klines.period == "1d",
            func.date(Klines.ts) < trade_date,
        )
        .order_by(Klines.ts.desc())
        .limit(1)
    )
    previous_close = previous_result.scalar_one_or_none()
    if previous_close is None:
        raise TradingRuleViolation("缺少前收盘价，无法校验交易价格")

    count_result = await session.execute(
        select(func.count())
        .select_from(Klines)
        .where(
            Klines.symbol == symbol,
            Klines.period == "1d",
            func.date(Klines.ts) <= trade_date,
        )
    )
    listed_sessions = int(count_result.scalar_one())
    limits = calculate_price_limits(symbol, previous_close, listed_sessions)
    return MockMarketState(
        trade_date=trade_date,
        market_price=latest.close,
        previous_close=previous_close,
        price_limits=limits,
    )


def settle_position_for_trade_date(position, trade_date: date) -> None:
    last_buy_date = position.last_buy_trade_date
    if (
        last_buy_date is not None
        and last_buy_date < trade_date
        and position.pending_settlement_volume > 0
    ):
        position.available_volume += position.pending_settlement_volume
        position.pending_settlement_volume = Decimal("0")


class AShareBacktestFiller:
    """Backtrader volume filler enforcing T+1 and one-price limit locks."""

    def __init__(self, symbol: str, listed_sessions_before_start: int = 0):
        self._symbol = symbol
        self._listed_sessions_before_start = listed_sessions_before_start
        self._current_date: date | None = None
        self._today_buys: dict[int, Decimal] = {}

    def __call__(self, order, price, ago) -> float:
        trade_date = order.data.datetime.date(ago)
        if trade_date != self._current_date:
            self._current_date = trade_date
            self._today_buys.clear()

        remaining = abs(Decimal(str(order.executed.remsize)))
        if remaining == 0:
            return 0.0

        listed_sessions = self._listed_sessions_before_start + len(order.data)
        if len(order.data) > 1:
            previous_close = Decimal(str(order.data.close[-1]))
            limits = calculate_price_limits(
                self._symbol, previous_close, listed_sessions
            )
            low = Decimal(str(order.data.low[ago]))
            high = Decimal(str(order.data.high[ago]))
            if order.isbuy() and limits.upper is not None and low >= limits.upper:
                return 0.0
            if order.issell() and limits.lower is not None and high <= limits.lower:
                return 0.0

        data_key = id(order.data)
        if order.isbuy():
            self._today_buys[data_key] = self._today_buys.get(
                data_key, Decimal("0")
            ) + remaining
            return float(remaining)

        position = order.owner.getposition(order.data)
        position_size = max(Decimal(str(position.size)), Decimal("0"))
        available = max(
            position_size - self._today_buys.get(data_key, Decimal("0")),
            Decimal("0"),
        )
        return float(min(remaining, available))
