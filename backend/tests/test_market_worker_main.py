from datetime import datetime, timezone
from unittest.mock import patch

from workers.market_worker.main import (
    _is_trading_time,
    _prioritize_tracked_symbols,
    sync_close_minute_klines,
    sync_minute_klines_by_period,
)


def test_daily_sync_prioritizes_user_tracked_symbols():
    symbols = ["000001.SZ", "300750.SZ", "600519.SH", "601318.SH"]

    result = _prioritize_tracked_symbols(symbols, ["600519", "300750.SZ"])

    assert result == ["300750.SZ", "600519.SH", "000001.SZ", "601318.SH"]


def test_trading_time_includes_delayed_close_minute():
    assert _is_trading_time(datetime(2026, 7, 14, 15, 0, 5))
    assert not _is_trading_time(datetime(2026, 7, 14, 15, 1, 0))


def test_trading_time_uses_shanghai_timezone_on_utc_server():
    assert _is_trading_time(datetime(2026, 7, 16, 2, 0, tzinfo=timezone.utc))


def test_trading_time_rejects_statutory_holiday():
    assert not _is_trading_time(datetime(2026, 10, 1, 10, 0))


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
@patch("workers.market_worker.main.is_trading_day", return_value=True)
def test_close_sync_fetches_all_intraday_periods(mock_is_trading_day, mock_sync):
    sync_close_minute_klines()

    assert mock_sync.call_args_list == [
        (("1m",), {"force": True}),
        (("5m",), {"force": True}),
        (("15m",), {"force": True}),
    ]


@patch("workers.market_worker.main.sync_minute_klines_by_period")
@patch("workers.market_worker.main.is_trading_day", return_value=False)
def test_close_sync_skips_non_trading_day(mock_is_trading_day, mock_sync):
    sync_close_minute_klines()

    mock_sync.assert_not_called()
