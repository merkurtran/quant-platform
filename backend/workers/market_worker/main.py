import concurrent.futures
import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.logging_config import setup_logging, get_logger
from workers.market_worker.fetcher import (
    fetch_daily_kline,
    fetch_minute_kline,
    get_minute_kline_symbols,
    get_all_a_share_symbols,
    sync_corporate_actions
)

setup_logging()
logger = get_logger("market_worker")

# A股连续竞价时间（北京时间）
_TRADING_SESSIONS = (
    (time(9, 30), time(11, 30)),
    (time(13, 0), time(15, 0)),
)


def _is_trading_time(dt: datetime) -> bool:
    t = dt.time()
    return any(start <= t <= end for start, end in _TRADING_SESSIONS)

def sync_daily_klines():
    symbols = get_all_a_share_symbols()
    # 使用线程池并发拉取，限制最大并发数避免网络压力过大
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(fetch_daily_kline, symbol): symbol for symbol in symbols}
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"日线拉取失败 {symbol}: {e}")


def sync_minute_klines_by_period(period: str):
    if not _is_trading_time(datetime.now()):
        return
    symbols = get_minute_kline_symbols()
    # 使用线程池并发拉取分钟线
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(fetch_minute_kline, symbol, period): symbol for symbol in symbols}
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"{period}分钟线拉取失败 {symbol}: {e}")

        
def sync_all_corporate_actions():
    symbols = get_all_a_share_symbols()
    # 使用线程池并发拉取除权除息数据
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(sync_corporate_actions, symbol): symbol for symbol in symbols}
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"除权除息同步失败 {symbol}: {e}")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone=ZoneInfo("Asia/Shanghai"))
    scheduler.add_job(sync_daily_klines, "cron", hour="15", minute="0")
    scheduler.add_job(sync_all_corporate_actions, "cron", day_of_week="sun", hour="16", minute="0")
    scheduler.add_job(lambda: sync_minute_klines_by_period("1m"), "cron", day_of_week="mon-fri", hour="9-15", minute="*/1")
    scheduler.add_job(lambda: sync_minute_klines_by_period("5m"), "cron", day_of_week="mon-fri", hour="9-15", minute="*/5")
    scheduler.add_job(lambda: sync_minute_klines_by_period("15m"), "cron", day_of_week="mon-fri", hour="9-15", minute="*/15")

    logger.info("market_worker started")
    scheduler.start()
