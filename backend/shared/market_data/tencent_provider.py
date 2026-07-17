"""腾讯财经行情数据源（HTTP API，无需额外依赖）。

优势：纯 HTTP 调用，速度快，不易被封。
劣势：不支持除权除息数据，日K无成交额字段。
"""
import logging

import httpx
import pandas as pd

from shared.market_data.base import MarketDataProvider
from shared.market_data.exceptions import (
    DataSourceConnectionError,
    DataFormatError,
)
from shared.market_data.utils import _safe_decimal

logger = logging.getLogger(__name__)


class TencentProvider(MarketDataProvider):
    """腾讯财经行情数据源"""

    # fqkline 接口（kline/get 已废弃）
    _DAILY_URL = "https://ifzq.gtimg.cn/appstock/app/fqkline/get"
    _MKLINE_URL = "https://ifzq.gtimg.cn/appstock/app/kline/mkline"

    _PERIOD_MAP = {
        "1m": "m1",
        "5m": "m5",
        "15m": "m15",
        "30m": "m30",
        "60m": "m60",
    }

    def __init__(self):
        self._client = httpx.Client(timeout=15, trust_env=False)

    def _to_tencent_symbol(self, symbol: str) -> str:
        """600519.SH → sh600519"""
        code, exchange = symbol.split(".")
        return f"{exchange.lower()}{code}"

    @staticmethod
    def _parse_row(row: list) -> dict:
        """解析一行 K 线数据。

        腾讯格式: [date/datetime, open, close, high, low, volume, (amount?) ]
        注意：open 和 close 在 high 和 low 之前。
        """
        return {
            "ts": pd.to_datetime(row[0]),
            "open": _safe_decimal(row[1]),
            "close": _safe_decimal(row[2]),
            "high": _safe_decimal(row[3]),
            "low": _safe_decimal(row[4]),
            "volume": _safe_decimal(row[5]) if len(row) > 5 else None,
            "amount": None,
        }

    def get_daily_kline(self, symbol: str, start_date: str) -> list[dict]:
        """获取日线数据（不复权）

        symbol: "600519.SH"
        start_date: "YYYYMMDD" 格式
        """
        tc_symbol = self._to_tencent_symbol(symbol)
        # YYYYMMDD → YYYY-MM-DD
        if len(start_date) == 8:
            start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
        else:
            start = start_date

        # param=symbol,day,start,end,count,adjust  (空 adjust = 不复权)
        params = {"param": f"{tc_symbol},day,{start},,800,"}

        try:
            resp = self._client.get(self._DAILY_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise DataSourceConnectionError(f"Tencent daily kline failed for {symbol}: {e}") from e

        body = resp.json()
        if body.get("code") != 0:
            raise DataFormatError(f"Tencent API error: {body.get('msg', 'unknown')}")

        data = body.get("data", {})
        if not isinstance(data, dict):
            raise DataFormatError(f"Tencent daily kline: unexpected data type {type(data)}")

        symbol_data = data.get(tc_symbol, {})
        # 优先取 day（不复权），次取 qfqday（前复权，不应出现但兜底）
        day_list = symbol_data.get("day") or symbol_data.get("qfqday") or []

        if not day_list:
            return []

        try:
            return [self._parse_row(row) for row in day_list]
        except (IndexError, ValueError) as e:
            raise DataFormatError(f"Tencent daily kline format error for {symbol}: {e}") from e

    def get_minute_kline(self, symbol: str, period: str, start_date: str = "") -> list[dict]:
        """获取分钟线数据

        symbol: "600519.SH"
        period: "1m" / "5m" / "15m" / "30m" / "60m"
        start_date: "YYYY-MM-DD HH:MM:SS" 格式
        """
        tc_period = self._PERIOD_MAP.get(period)
        if tc_period is None:
            raise ValueError(f"Unsupported minute period: {period}")

        tc_symbol = self._to_tencent_symbol(symbol)
        params = {"param": f"{tc_symbol},{tc_period},,640"}

        try:
            resp = self._client.get(self._MKLINE_URL, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise DataSourceConnectionError(f"Tencent minute kline failed for {symbol}: {e}") from e

        body = resp.json()
        if body.get("code") != 0:
            raise DataFormatError(f"Tencent API error: {body.get('msg', 'unknown')}")

        data = body.get("data", {})
        if not isinstance(data, dict):
            raise DataFormatError(f"Tencent minute kline: unexpected data type {type(data)}")

        symbol_data = data.get(tc_symbol, {})
        min_list = symbol_data.get(tc_period, [])

        if not min_list:
            return []

        try:
            start_dt = pd.to_datetime(start_date) if start_date else None
            result = []
            for row in min_list:
                parsed = self._parse_row(row)
                if start_dt and parsed["ts"] < start_dt:
                    continue
                result.append(parsed)
            return result
        except (IndexError, ValueError) as e:
            raise DataFormatError(f"Tencent minute kline format error for {symbol}: {e}") from e

    def get_all_symbols(self) -> list[str]:
        """腾讯不提供全市场股票列表，由 fallback 链交给下一个 provider"""
        raise NotImplementedError("Tencent provider does not support get_all_symbols")

    def get_corporate_actions(self, symbol: str, start_date=None) -> list[dict]:
        """腾讯不提供除权除息数据"""
        raise NotImplementedError("Tencent provider does not support get_corporate_actions")
