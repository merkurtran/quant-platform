import akshare as ak
import pandas as pd
from decimal import Decimal 

from shared.market_data.utils import _safe_decimal
from shared.market_data.base import MarketDataProvider
from shared.market_data.exceptions import (
    DataSourceConnectionError,
    SymbolNotFoundError,
    DataFormatError,
)



class AKShareProvider(MarketDataProvider):

    _MINUTE_PERIOD_MAP = {"1m": "1", "5m": "5", "15m": "15"}

    def get_daily_kline(self, symbol: str, start_date: str) -> list[dict]:
        raw_symbol = symbol.split(".")[0]

        try:
            df = ak.stock_zh_a_hist(symbol=raw_symbol, period="daily", adjust="", start_date=start_date)
        except Exception as e:
            raise  DataSourceConnectionError(f"Failed to fetch daily kline for {symbol}: {e}") from e

        if df.empty:
            return []

        try:
            return [
                {
                    "ts": pd.to_datetime(row["日期"]),
                    "open": row["开盘"],
                    "high": row["最高"],
                    "low": row["最低"],
                    "close": row["收盘"],
                    "volume": row["成交量"],
                    "amount": row.get("成交额"),
                }
                for _, row in df.iterrows()
            ]
        except KeyError as e:
            raise DataFormatError(f"Unexpected data format from AKShare for {symbol}: missing {e}") from e

    def get_minute_kline(self, symbol: str, period: str, start_date: str) -> list[dict]:
        ak_period = self._MINUTE_PERIOD_MAP.get(period)
        if ak_period is None:
            raise ValueError(f"Unsupported minute period: {period}")

        raw_symbol = symbol.split(".")[0]
        try:
            df = ak.stock_zh_a_hist_min_em(symbol=raw_symbol, period=ak_period, adjust="", start_date=start_date)
        except Exception as e:
            raise DataSourceConnectionError(f"Failed to fetch minute kline for {symbol}: {e}") from e

        if df.empty:
            return []

        try:
            return [
                {
                    "ts": pd.to_datetime(row["日期"]),
                    "open": row["开盘"],
                    "high": row["最高"],
                    "low": row["最低"],
                    "close": row["收盘"],
                    "volume": row["成交量"],
                    "amount": row.get("成交额"),
                }
                for _, row in df.iterrows()
            ]
        except KeyError as e:
            raise DataFormatError(f"Unexpected data format from AKShare for {symbol}: missing {e}") from e

    def get_all_symbols(self) -> list[str]:
        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as e:
            raise SymbolNotFoundError(f"Failed to fetch symbol list: {e}") from e
        return df["代码"].tolist()
    

    def get_corporate_actions(self, symbol: str) -> list[dict]:
        raw_symbol = symbol.split(".")[0]
        results = []
        # 分红/送股/转增
        try:
            df = ak.stock_dividend_cninfo(symbol=raw_symbol)
        except Exception as e:
            raise DataSourceConnectionError(f"Failed to fetch dividend data for {symbol}: {e}") from e
        
        if not df.empty:
            try:
                for _, row in df.iterrows():
                    ex_date = row["除权日"]
                    if pd.isna(ex_date):
                        continue

                    # akshare 返回的送股/转增比例单位是每10股，这里除以10转成每股
                    stock_ratio = (_safe_decimal(row["送股比例"]) + _safe_decimal(row["转增比例"])) / Decimal("10")
                    cash_per_share = _safe_decimal(row["派息比例"]) / Decimal("10")
                    if stock_ratio == 0 and cash_per_share == 0:
                        continue

                    action_type = "stock_split" if stock_ratio > 0 else "dividend"
                    results.append({
                        "ex_date": pd.to_datetime(ex_date).date(),
                        "action_type": action_type,
                        "cash_per_share": cash_per_share,
                        "stock_ratio": stock_ratio,
                        "rights_price": Decimal("0"),
                        "rights_ratio": Decimal("0"),
                    })
                return results
            except KeyError as e:
                raise DataFormatError(f"Unexpected data format from AKShare for {symbol}: missing {e}") from e
        
        # 配股
        try:
            rights_df = ak.stock_history_dividend_detail(symbol=raw_symbol, indicator="配股")
        except Exception as e:
            raise DataSourceConnectionError(f"Failed to fetch rights data for {symbol}: {e}") from e
        
        if rights_df is not None and not rights_df.empty:
            try:
                for _, row in rights_df.iterrows():
                    ex_date = row["除权日"]
                    if pd.isna(ex_date):
                        continue
                    rights_ratio = _safe_decimal(row["配股方案"]) / Decimal("10") # 每 10 股转每股
                    rights_price = _safe_decimal(row["配股价格"])
                    if rights_ratio == 0 or rights_price == 0:
                        continue
                    results.append({
                        "ex_date": pd.to_datetime(ex_date).date(),
                        "action_type": "rights_issue",
                        "cash_per_share": Decimal("0"),
                        "stock_ratio": Decimal("0"),
                        "rights_price": rights_price,
                        "rights_ratio": rights_ratio,
                    })
            except KeyError as e:
                raise DataFormatError(f"Unexpected data format from AKShare for {symbol}: missing {e}") from e
