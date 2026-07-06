import akshare as ak
import pandas as pd

from shared.db.session import SessionLocal
from app.models.market import Klines, WatchlistItems
from app.services.market_service import get_all_watched_symbols


def _save_klines(rows: list[dict]) -> None:
    """通用落库逻辑,daily/minute 共用,merge 处理主键冲突(同一天重复拉取)"""
    db = SessionLocal()
    try:
        for row in rows:
            # 这里使用 merge 而不是 add，因为 klines 表的主键是联合主键
            # 同一天的 K 线数据可能会重复拉取，使用 add 会导致主键冲突，导致数据库插入失败
            # merge 会先查询是否存在相同主键的数据，如果存在则更新，否则插入
            db.merge(Klines(**row))
        db.commit()
    finally:
        db.close()


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


def fetch_daily_kline(symbol: str) -> None:
    """拉取日线(全市场)写入数据库"""
    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
    normalized_symbol = normalize_symbol(symbol)

    rows = [
        {
            "symbol": normalized_symbol,
            "period": "1d",
            "ts": pd.to_datetime(row["日期"]),
            "open": row["开盘"],
            "high": row["最高"],
            "low": row["最低"],
            "close": row["收盘"],
            "volume": row["成交量"],
            "amount": row.get("成交额"),  # 可能为空，用 get 安全取值
        }
        for _, row in df.iterrows()
    ]
    _save_klines(rows)


_MINUTE_PERIOD_MAP = {"1m": "1", "5m": "5", "15m": "15"}
def fetch_minute_kline(symbol: str, period: str) -> None:
    """拉取分钟线,period 取 '1m'/'5m'/'15m', 仅拉取自选股, 分线只能回溯近5个交易日"""
    ak_period = _MINUTE_PERIOD_MAP.get(period)
    if ak_period is None:
        raise ValueError(f"Unsupported minute period: {period}")

    df = ak.stock_zh_a_hist_min_em(symbol=symbol, period=ak_period, adjust="qfq")
    normalized_symbol = normalize_symbol(symbol)

    rows = [
        {
            "symbol": normalized_symbol,
            "period": period,
            "ts": pd.to_datetime(row["时间"]),
            "open": row["开盘"],
            "high": row["最高"],
            "low": row["最低"],
            "close": row["收盘"],
            "volume": row["成交量"],
            "amount": row.get("成交额"),
        }
        for _, row in df.iterrows()
    ]
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
    """获取所有 A 股股票代码(不带后缀)"""
    df = ak.stock_zh_a_spot_em()
    return df["代码"].tolist()