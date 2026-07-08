from apscheduler.schedulers.blocking import BlockingScheduler

from workers.market_worker.fetcher import (
    fetch_daily_kline,
    fetch_minute_kline,
    get_watchlist_symbols,
    get_all_a_share_symbols,
    sync_corporate_actions
)


def sync_daily_klines():
    symbols = get_all_a_share_symbols()
    for symbol in symbols:
        try:
            fetch_daily_kline(symbol)
        except Exception as e:
            print(f"日线拉取失败 {symbol}: {e}")


def sync_minute_klines_by_period(period: str):
    symbols = get_watchlist_symbols()
    for symbol in symbols:
        try:
            fetch_minute_kline(symbol, period)
        except Exception as e:
            print(f"{period}分钟线拉取失败 {symbol}: {e}")

        
def sync_all_corporate_actions():
    symbols = get_all_a_share_symbols()
    for symbol in symbols:
        try:
            sync_corporate_actions(symbol)
        except Exception as e:
            print(f"除权除息同步失败 {symbol}: {e}")


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(sync_daily_klines, "cron", hour="15", minute="0")
    scheduler.add_job(sync_all_corporate_actions, "cron", day_of_week="sun", hour="16", minute="0")
    scheduler.add_job(lambda: sync_minute_klines_by_period("1m"), "cron", day_of_week="mon-fri", hour="9-15", minute="*/1")
    scheduler.add_job(lambda: sync_minute_klines_by_period("5m"), "cron", day_of_week="mon-fri", hour="9-15", minute="*/5")
    scheduler.add_job(lambda: sync_minute_klines_by_period("15m"), "cron", day_of_week="mon-fri", hour="9-15", minute="*/15")

    print("market_worker started")
    scheduler.start()