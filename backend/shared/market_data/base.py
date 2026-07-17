from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import date


class MarketDataProvider(ABC):
    @abstractmethod
    def get_daily_kline(self, symbol: str, start_date: str) -> list[dict]:
        """
        获取日线数据(不复权,原始价格)
        symbol: "600519.SH"
        start_date: "YYYYMMDD" 格式
        返回: [{"ts": datetime, "open": Decimal, "high": Decimal, "low": Decimal,
                "close": Decimal, "volume": Decimal, "amount": Decimal | None}, ...]
        按时间正序排列
        """
        pass

    @abstractmethod
    def get_minute_kline(self, symbol: str, period: str, start_date: str = "") -> list[dict]:
        """
        获取分钟线数据
        symbol: "600519.SH"
        period: "1m" / "5m" / "15m" / "30m" / "60m"
        start_date: "YYYY-MM-DD HH:MM:SS" 格式
        返回格式同 get_daily_kline
        """
        pass

    @abstractmethod
    def get_all_symbols(self) -> list[str]:
        """获取全市场股票代码列表,带交易所后缀格式"""
        pass

    @abstractmethod
    def get_corporate_actions(self, symbol: str, start_date: date | None = None) -> list[dict]:
        """
        获取除权除息记录
        symbol: "600519.SH"
        start_date: 开始日期，不传则取全部
        返回: [{"ex_date": date, "action_type": str, "cash_per_share": Decimal,
                "stock_ratio": Decimal, "rights_price": Decimal, "rights_ratio": Decimal}, ...]
        """
        pass