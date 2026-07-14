from datetime import datetime
from unittest.mock import patch

from workers.market_worker.main import (
    _is_trading_time,
    sync_close_minute_klines,
    sync_minute_klines_by_period,
)


def test_trading_time_includes_delayed_close_minute():
    assert _is_trading_time(datetime(2026, 7, 14, 15, 0, 5))
    assert not _is_trading_time(datetime(2026, 7, 14, 15, 1, 0))


@patch("workers.market_worker.main.fetch_minute_kline")
@patch("workers.market_worker.main.get_minute_kline_symbols", return_value=["000001"])
@patch("workers.market_worker.main._is_trading_time", return_value=False)
def test_forced_minute_sync_runs_after_trading_hours(
    mock_is_trading_time, mock_symbols, mock_fetch
):
    sync_minute_klines_by_period("1m", force=True)

    mock_fetch.assert_called_once_with("000001", "1m")
    mock_is_trading_time.assert_not_called()


@patch("workers.market_worker.main.sync_minute_klines_by_period")
def test_close_sync_fetches_all_intraday_periods(mock_sync):
    sync_close_minute_klines()

    assert mock_sync.call_args_list == [
        (("1m",), {"force": True}),
        (("5m",), {"force": True}),
        (("15m",), {"force": True}),
    ]
