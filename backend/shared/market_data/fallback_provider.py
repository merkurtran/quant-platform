"""多数据源降级 Provider。

按优先级依次尝试：腾讯财经 → mootdx → akshare
某个 provider 抛异常或返回空时自动切换到下一个。
"""
import logging
from datetime import date

from shared.market_data.base import MarketDataProvider
from shared.market_data.exceptions import MarketDataError

logger = logging.getLogger(__name__)


class FallbackProvider(MarketDataProvider):
    """降级链：按顺序尝试多个 provider，第一个成功即返回。"""

    def __init__(self, providers: list[MarketDataProvider]):
        self._providers = providers

    def _try_chain(self, method_name: str, *args, **kwargs) -> list[dict]:
        last_error = None
        for provider in self._providers:
            name = provider.__class__.__name__
            try:
                result = getattr(provider, method_name)(*args, **kwargs)
                if result:
                    return result
                logger.debug(f"{name}.{method_name} returned empty, trying next")
            except NotImplementedError:
                logger.debug(f"{name}.{method_name} not implemented, trying next")
            except MarketDataError as e:
                last_error = e
                logger.warning(f"{name}.{method_name} failed: {e}, trying next")
            except Exception as e:
                last_error = e
                logger.warning(f"{name}.{method_name} error: {e}, trying next")

        if last_error:
            raise last_error
        return []

    def get_daily_kline(self, symbol: str, start_date: str) -> list[dict]:
        return self._try_chain("get_daily_kline", symbol, start_date)

    def get_minute_kline(self, symbol: str, period: str, start_date: str = "") -> list[dict]:
        return self._try_chain("get_minute_kline", symbol, period, start_date=start_date)

    def get_all_symbols(self) -> list[str]:
        return self._try_chain("get_all_symbols")

    def get_corporate_actions(self, symbol: str, start_date: date | None = None) -> list[dict]:
        return self._try_chain("get_corporate_actions", symbol, start_date=start_date)


def create_default_provider() -> MarketDataProvider:
    """创建默认的降级链：腾讯 → mootdx → akshare"""
    providers: list[MarketDataProvider] = []

    # 1. 腾讯财经（HTTP，最快最稳）
    try:
        from shared.market_data.tencent_provider import TencentProvider
        providers.append(TencentProvider())
        logger.info("TencentProvider initialized")
    except Exception as e:
        logger.warning(f"TencentProvider init failed: {e}")

    # 2. mootdx（TDX 协议，不限流）
    try:
        from shared.market_data.mootdx_provider import MootdxProvider
        providers.append(MootdxProvider())
        logger.info("MootdxProvider initialized")
    except Exception as e:
        logger.warning(f"MootdxProvider init failed: {e}")

    # 3. akshare（备选）
    try:
        from shared.market_data.akshare_provider import AKShareProvider
        providers.append(AKShareProvider())
        logger.info("AKShareProvider initialized")
    except Exception as e:
        logger.warning(f"AKShareProvider init failed: {e}")

    if not providers:
        raise RuntimeError("No market data provider available")

    return FallbackProvider(providers)
