from abc import ABC, abstractmethod

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
    def get_minute_kline(self, symbol: str, start_date: str) -> list[dict]:
        """获取分钟线,period 取 '1m'/'5m'/'15m',返回格式同上"""
        pass


    @abstractmethod
    def get_all_symbols(self) -> list[str]:
        """获取全市场股票代码列表,带交易所后缀格式"""
        pass


    @abstractmethod
    def get_corporate_actions(self):
        pass