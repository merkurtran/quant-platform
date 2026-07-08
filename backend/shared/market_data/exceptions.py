class MarketDataError(Exception):
    """所有数据源相关异常的基类,方便上层一次性捕获所有这类错误"""
    pass


class DataSourceConnectionError(MarketDataError):
    """数据源连接失败(网络、代理、超时、限流),这种可能值得重试"""
    pass


class SymbolNotFoundError(MarketDataError):
    """请求的股票代码,数据源查不到(格式错误/已退市/根本不存在)"""
    pass


class DataFormatError(MarketDataError):
    """数据源返回的数据,解析/转换失败(字段缺失、格式和预期不符)"""
    pass