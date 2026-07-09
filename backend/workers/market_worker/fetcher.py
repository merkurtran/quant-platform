import json
from datetime import timedelta, datetime
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.services.alert_service import evaluate_all_active_rules
from shared.db.session import SessionLocal
from shared.logging_config import get_logger
from app.models.market import Klines
from app.services.market_service import get_all_watched_symbols, save_corporate_actions
from shared.redis_client import redis_client
from shared.market_data.akshare_provider import AKShareProvider
from shared.market_data.exceptions import MarketDataError
from app.core.config import get_settings

logger = get_logger("market_worker.fetcher")
settings = get_settings()
provider = AKShareProvider()


def normalize_symbol(raw_symbol: str) -> str:
    """把 AKShare 的纯数字代码转成带交易所后缀格式"""
    if raw_symbol.startswith("6"):
        return f"{raw_symbol}.SH"
    elif raw_symbol.startswith(("0", "3")):
        return f"{raw_symbol}.SZ"
    elif raw_symbol.startswith(("4", "8")):
        return f"{raw_symbol}.BJ"
    else:
        raise ValueError(f"Unknown exchange for symbol: {raw_symbol}")


def _save_klines(rows: list[dict]) -> None:
    """通用落库逻辑,daily/minute 共用,批量 upsert(PostgreSQL 专属写法,换数据库需要重写这个函数)。

    设计说明：每条 K 线不独立开启事务。同一只股票的一次拉取全部合并进一个
    INSERT ... ON CONFLICT DO UPDATE 语句，单次 db.commit()，已是最小事务粒度。
    ThreadPoolExecutor 并发模型下每个线程操作不同股票，独立 SessionLocal 避免了
    跨线程 session 竞争，因此当前设计（每股票=一次事务）是最优的。
    """
    if not rows:
        return
    db = SessionLocal()
    try:
        stmt = pg_insert(Klines).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "period", "ts"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "amount": stmt.excluded.amount,
            },
        )
        db.execute(stmt)
        db.commit()
    finally:
        db.close()


def _publish_quote(symbol: str, latest: dict) -> None:
    """发布最新行情到 redis, 供 websocket 订阅"""
    try:
        message = json.dumps({
            "symbol": symbol,
            "price": float(latest["close"]),
            "ts": latest["ts"].isoformat() if hasattr(latest["ts"], "isoformat") else str(latest["ts"]),
        })
        redis_client.publish(f"quotes:{symbol}", message)
        redis_client.set(
            f"latest_price:{symbol}",
            message,
            ex=settings.redis.latest_price_cache_ttl_seconds,
        )
    except Exception as e:
        logger.error(f"发布行情到 Redis 失败 {symbol}: {e}")


def _check_alerts(symbol: str, latest_rows: list[dict]) -> None:
    """存完K线之后,检查这支股票有没有预警规则被触发
    当前挂在日线同步任务上,预警精度为"每日收盘后检查"。
    分钟级实时预警(含去重收敛策略)留到 Phase 3 规划。"""
    if not latest_rows:
        return

    current_price = Decimal(str(latest_rows[-1]["close"]))
    earliest_ts = latest_rows[0]["ts"]

    db = SessionLocal()
    try:
        prev = (
            db.query(Klines.close)
            .filter(
                Klines.symbol == symbol,
                Klines.period == "1d",
                Klines.ts < earliest_ts,
            )
            .order_by(Klines.ts.desc())
            .first()
        )
        previous_close = prev[0] if prev else None

        evaluate_all_active_rules(db, symbol, current_price, previous_close)
    except Exception as e:
        logger.error(f"预警检查失败 {symbol}: {e}")
    finally:
        db.close()


def fetch_daily_kline(symbol: str) -> None:
    """拉取日线(全市场),增量同步:只拉数据库里没有的部分"""
    normalized_symbol = normalize_symbol(symbol)

    db = SessionLocal()
    try:
        latest = (
            db.query(Klines.ts)
            .filter(Klines.symbol == normalized_symbol, Klines.period == "1d")
            .order_by(Klines.ts.desc())
            .first()
        )
    finally:
        db.close()

    start_date = (latest[0] + timedelta(days=1)).strftime("%Y%m%d") if latest else "19910101"

    try:
        rows_raw = provider.get_daily_kline(normalized_symbol, start_date)
    except MarketDataError as e:
        logger.error(f"日线拉取失败 {symbol}: {e}")
        return

    if not rows_raw:
        return

    rows = [{"symbol": normalized_symbol, "period": "1d", **r} for r in rows_raw]
    _save_klines(rows)
    _publish_quote(normalized_symbol, rows[-1])
    _check_alerts(normalized_symbol, rows)


_PERIOD_MINUTES = {"1m": 1, "5m": 5, "15m": 15}

def fetch_minute_kline(symbol: str, period: str) -> None:
    """拉取分钟线,period 取 '1m'/'5m'/'15m', 仅拉取自选股, 分线只能回溯近5个交易日"""
    normalized_symbol = normalize_symbol(symbol)

    db = SessionLocal()
    try:
        latest = (
            db.query(Klines.ts)
            .filter(
                Klines.symbol == normalized_symbol,
                Klines.period == period,
            )
            .order_by(Klines.ts.desc())
            .first()
        )
    finally:
        db.close()

    if latest:
        step_minutes = _PERIOD_MINUTES.get(period, 1)
        start_dt = latest[0] + timedelta(minutes=step_minutes)
    else:
        start_dt = datetime.now() - timedelta(days=5)
    start_date = start_dt.strftime("%Y-%m-%d %H:%M:%S")

    try:
        rows_raw = provider.get_minute_kline(normalized_symbol, period, start_date=start_date)
    except MarketDataError as e:
        logger.error(f"{period}分钟线拉取失败 {symbol}: {e}")
        return

    if not rows_raw:
        return

    rows = [{"symbol": normalized_symbol, "period": period, **r} for r in rows_raw]
    _save_klines(rows)


def get_watchlist_symbols() -> list[str]:
    """查询所有用户自选股去重列表,转成 akshare 需要的纯数字代码"""
    db = SessionLocal()
    try:
        symbols = get_all_watched_symbols(db)
        return [symbol.split(".")[0] for symbol in symbols]
    finally:
        db.close()


def get_all_a_share_symbols() -> list[str]:
    """获取所有 A 股股票代码(带交易所后缀)"""
    return provider.get_all_symbols()


def sync_corporate_actions(symbol: str) -> None:
    """拉取并保存一支股票的除权除息记录"""
    normalized_symbol = normalize_symbol(symbol)
    try:
        actions = provider.get_corporate_actions(normalized_symbol)
    except MarketDataError as e:
        logger.error(f"除权除息数据拉取失败 {symbol}: {e}")
        return
    
    if not actions:
        return

    db = SessionLocal()
    try:
        save_corporate_actions(db, normalized_symbol, actions)
        db.commit()
    finally:
        db.close()