"""market_worker/fetcher.py 测试

覆盖：
  - normalize_symbol: AKShare 代码转换
  - get_alert_rule_symbols: 活跃预警规则股票查询
  - get_minute_kline_symbols: 自选股 ∪ 预警标的 并集去重
  - get_watchlist_symbols: 自选股查询
  - _check_alerts 分钟线集成
"""
import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from workers.market_worker.fetcher import (
    normalize_symbol,
    get_alert_rule_symbols,
    get_minute_kline_symbols,
    get_watchlist_symbols,
    _check_alerts,
    _publish_quote,
)


# ══════════════════════════════════════════════════════════
# 1. normalize_symbol — 代码格式转换
# ══════════════════════════════════════════════════════════

class TestNormalizeSymbol:

    def test_shanghai_main_board(self):
        assert normalize_symbol("600519") == "600519.SH"

    def test_shenzhen_main_board(self):
        assert normalize_symbol("000001") == "000001.SZ"

    def test_chi_next(self):
        assert normalize_symbol("300750") == "300750.SZ"

    def test_beijing_exchange(self):
        assert normalize_symbol("430047") == "430047.BJ"

    def test_keeps_canonical_symbol(self):
        assert normalize_symbol("600519.SH") == "600519.SH"

    def test_normalizes_lowercase_suffix(self):
        assert normalize_symbol("000001.sz") == "000001.SZ"

    def test_invalid_non_digit_raises(self):
        with pytest.raises(ValueError, match="Invalid A-share code"):
            normalize_symbol("SH600519")

    def test_unknown_prefix_raises(self):
        with pytest.raises(ValueError, match="Unknown exchange"):
            normalize_symbol("900001")


# ══════════════════════════════════════════════════════════
# 2. get_alert_rule_symbols — 查询活跃预警规则的 symbol
# ══════════════════════════════════════════════════════════

class TestGetAlertRuleSymbols:

    @patch("workers.market_worker.fetcher.SessionLocal")
    def test_returns_distinct_active_symbols(self, mock_session_factory):
        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db
        # 完整链路: query → filter → distinct → all
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = [
            ("600519.SH",),
            ("000001.SZ",),
        ]

        symbols = get_alert_rule_symbols()

        assert set(symbols) == {"600519", "000001"}  # 纯数字代码

    @patch("workers.market_worker.fetcher.SessionLocal")
    def test_excludes_paused_rules(self, mock_session_factory):
        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []

        symbols = get_alert_rule_symbols()
        assert symbols == []

    @patch("workers.market_worker.fetcher.SessionLocal")
    def test_handles_none_symbol_gracefully(self, mock_session_factory):
        """某些行可能 symbol 为空或 None，应跳过"""
        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = [
            ("600519.SH",),
            (None,),
            ("",),
        ]

        symbols = get_alert_rule_symbols()
        assert symbols == ["600519"]


# ══════════════════════════════════════════════════════════
# 3. get_minute_kline_symbols — 并集去重
# ══════════════════════════════════════════════════════════

class TestGetMinuteKlineSymbols:

    @patch("workers.market_worker.fetcher.get_alert_rule_symbols")
    @patch("workers.market_worker.fetcher.get_watchlist_symbols")
    def test_union_of_watchlist_and_alerts(self, mock_watchlist, mock_alerts):
        mock_watchlist.return_value = ["600519", "000001"]
        mock_alerts.return_value = ["000001", "300750"]  # 000001 重叠

        result = get_minute_kline_symbols()

        assert set(result) == {"600519", "000001", "300750"}
        assert len(result) == 3  # 无重复

    @patch("workers.market_worker.fetcher.get_alert_rule_symbols")
    @patch("workers.market_worker.fetcher.get_watchlist_symbols")
    def test_sorted_output(self, mock_watchlist, mock_alerts):
        mock_watchlist.return_value = ["300750", "600519"]
        mock_alerts.return_value = ["000001"]

        result = get_minute_kline_symbols()
        assert result == sorted(result)

    @patch("workers.market_worker.fetcher.get_alert_rule_symbols")
    @patch("workers.market_worker.fetcher.get_watchlist_symbols")
    def test_watchlist_only_no_alerts(self, mock_watchlist, mock_alerts):
        mock_watchlist.return_value = ["600519"]
        mock_alerts.return_value = []

        result = get_minute_kline_symbols()
        assert result == ["600519"]

    @patch("workers.market_worker.fetcher.get_alert_rule_symbols")
    @patch("workers.market_worker.fetcher.get_watchlist_symbols")
    def test_alerts_only_no_watchlist(self, mock_watchlist, mock_alerts):
        mock_watchlist.return_value = []
        mock_alerts.return_value = ["300750", "600519"]

        result = get_minute_kline_symbols()
        assert set(result) == {"300750", "600519"}


# ══════════════════════════════════════════════════════════
# 4. get_watchlist_symbols — 自选股查询
# ══════════════════════════════════════════════════════════

class TestGetWatchlistSymbols:

    @patch("workers.market_worker.fetcher.SessionLocal")
    @patch("workers.market_worker.fetcher.get_all_watched_symbols")
    def test_returns_stripped_symbols(self, mock_get_watched, mock_session_factory):
        mock_get_watched.return_value = ["600519.SH", "000001.SZ", "300750.SZ"]
        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db

        symbols = get_watchlist_symbols()

        assert set(symbols) == {"600519", "000001", "300750"}

    @patch("workers.market_worker.fetcher.SessionLocal")
    @patch("app.services.market_service.get_all_watched_symbols")
    def test_empty_watchlist(self, mock_get_watched, mock_session_factory):
        mock_get_watched.return_value = []
        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db

        symbols = get_watchlist_symbols()
        assert symbols == []


# ══════════════════════════════════════════════════════════
# 5. _check_alerts 分钟线集成
# ══════════════════════════════════════════════════════════

class TestCheckAlertsIntegration:

    @patch("workers.market_worker.fetcher.evaluate_and_notify")
    @patch("workers.market_worker.fetcher.SessionLocal")
    def test_calls_evaluate_and_notify_with_correct_params(
        self, mock_session_factory, mock_evaluate
    ):
        mock_evaluate.return_value = []
        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        # 模拟 previous_close 查询返回 None（无历史日线）
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

        rows = [{"close": "1850.00", "ts": "2026-07-10 14:30:00+00:00"}]

        _check_alerts("600519.SH", rows)
        mock_evaluate.assert_called_once()

    @patch("workers.market_worker.fetcher.evaluate_and_notify")
    def test_empty_rows_no_call(self, mock_evaluate):

        _check_alerts("600519.SH", [])
        mock_evaluate.assert_not_called()

    @patch("workers.market_worker.fetcher.evaluate_and_notify")
    @patch("workers.market_worker.fetcher.SessionLocal")
    def test_exception_caught_gracefully(self, mock_session_factory, mock_evaluate):
        mock_evaluate.side_effect = Exception("DB error")
        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        rows = [{"close": "1850.00", "ts": "2026-07-10 14:30:00+00:00"}]

        # 应该不抛异常
        _check_alerts("600519.SH", rows)


class TestPublishQuote:

    @patch("workers.market_worker.fetcher.get_redis_client")
    @patch("workers.market_worker.fetcher.SessionLocal")
    def test_publishes_change_for_watchlist_rows(
        self, mock_session_factory, mock_get_redis
    ):
        mock_db = MagicMock()
        mock_session_factory.return_value = mock_db
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            (datetime(2026, 7, 14), Decimal("1219.50")),
            (datetime(2026, 7, 13), Decimal("1200.00")),
        ]
        mock_redis = mock_get_redis.return_value

        _publish_quote(
            "600519.SH",
            {"close": Decimal("1218.00"), "ts": datetime(2026, 7, 14, 10, 30)},
        )

        message = json.loads(mock_redis.publish.call_args.args[1])
        assert message["previous_close"] == 1200.0
        assert message["change"] == 18.0
        assert message["change_pct"] == 1.5
