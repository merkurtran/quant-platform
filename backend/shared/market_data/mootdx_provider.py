"""mootdx 行情数据源（通达信 TDX 协议，TCP 直连）。

优势：TDX 协议稳定，不限流，支持全市场股票列表。
劣势：需要 TCP 连接 TDX 服务器，不支持除权除息。
"""
import logging
from datetime import date

import pandas as pd

from shared.market_data.base import MarketDataProvider
from shared.market_data.exceptions import (
    DataSourceConnectionError,
    DataFormatError,
)
from shared.market_data.utils import _safe_decimal

logger = logging.getLogger(__name__)

# mootdx frequency/category 映射
# 0: 5min, 1: 15min, 2: 30min, 3: 60min, 4: daily, 5: weekly, 6: monthly, 7: 1min
_PERIOD_TO_CATEGORY = {
    "1m": 7,
    "5m": 0,
    "15m": 1,
    "30m": 2,
    "60m": 3,
}

# 交易所后缀映射（首位数字 → market code → 交易所后缀）
_PREFIX_MAP = {
    "6": (1, "SH"),
    "0": (0, "SZ"),
    "3": (0, "SZ"),
    "8": (2, "BJ"),
    "4": (2, "BJ"),
}


class MootdxProvider(MarketDataProvider):
    """mootdx 行情数据源"""

    def __init__(self):
        try:
            from mootdx.quotes import Quotes
            self._client = Quotes.factory(market="std")
        except Exception as e:
            raise DataSourceConnectionError(f"Failed to init mootdx: {e}") from e

    def _split_symbol(self, symbol: str) -> tuple[str, int]:
        """600519.SH → ('600519', 1)  market: 0=SZ, 1=SH, 2=BJ"""
        code = symbol.split(".")[0]
        market, _ = _PREFIX_MAP.get(code[0], (1, "SH"))
        return code, market

    def _parse_bars(self, df, start_dt, symbol: str) -> list[dict]:
        """通用解析 mootdx bars 返回的 DataFrame"""
        if df is None or df.empty:
            return []
        result = []
        for _, row in df.iterrows():
            ts = row.get("date") or row.get("datetime")
            ts = pd.to_datetime(ts)
            if start_dt and ts < start_dt:
                continue
            result.append({
                "ts": ts,
                "open": _safe_decimal(row.get("open")),
                "high": _safe_decimal(row.get("high")),
                "low": _safe_decimal(row.get("low")),
                "close": _safe_decimal(row.get("close")),
                "volume": _safe_decimal(row.get("volume")),
                "amount": _safe_decimal(row.get("amount")),
            })
        return result

    def get_daily_kline(self, symbol: str, start_date: str) -> list[dict]:
        code, market = self._split_symbol(symbol)
        start_dt = pd.to_datetime(start_date[:4] + "-" + start_date[4:6] + "-" + start_date[6:]) if len(start_date) == 8 else pd.to_datetime(start_date)

        try:
            df = self._client.bars(symbol=code, frequency=4, offset=800, market=market)
        except Exception as e:
            raise DataSourceConnectionError(f"mootdx daily kline failed for {symbol}: {e}") from e

        try:
            return self._parse_bars(df, start_dt, symbol)
        except (KeyError, ValueError) as e:
            raise DataFormatError(f"mootdx daily kline format error for {symbol}: {e}") from e

    def get_minute_kline(self, symbol: str, period: str, start_date: str = "") -> list[dict]:
        code, market = self._split_symbol(symbol)
        category = _PERIOD_TO_CATEGORY.get(period)
        if category is None:
            raise ValueError(f"Unsupported minute period: {period}")

        start_dt = pd.to_datetime(start_date) if start_date else None

        try:
            df = self._client.bars(symbol=code, frequency=category, offset=800, market=market)
        except Exception as e:
            raise DataSourceConnectionError(f"mootdx minute kline failed for {symbol}: {e}") from e

        try:
            return self._parse_bars(df, start_dt, symbol)
        except (KeyError, ValueError) as e:
            raise DataFormatError(f"mootdx minute kline format error for {symbol}: {e}") from e

    def get_all_symbols(self) -> list[str]:
        """获取全市场 A 股代码列表（带交易所后缀）"""
        result = []
        for market in [0, 1, 2]:  # 0=SZ, 1=SH, 2=BJ
            try:
                df = self._client.stocks(market=market)
            except Exception as e:
                logger.warning(f"mootdx stocks(market={market}) failed: {e}")
                continue

            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                code = str(row.get("code", row.get("symbol", ""))).strip()
                if not code or not code[0].isdigit():
                    continue
                suffix = _PREFIX_MAP.get(code[0], (None, None))[1]
                if suffix is None:
                    continue
                result.append(f"{code}.{suffix}")

        if not result:
            raise DataSourceConnectionError("mootdx get_all_symbols returned empty")
        return result

    def get_corporate_actions(self, symbol: str, start_date=None) -> list[dict]:
        """mootdx 不提供除权除息数据"""
        raise NotImplementedError("mootdx provider does not support get_corporate_actions")
