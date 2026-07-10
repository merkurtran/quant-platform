"""alert_service.py 协调器 + 通知分发测试

覆盖：
  - evaluate_and_notify: 条件评估 → 去重 → 持久化 → 推送
  - _dispatch_notifications: inapp/email/webhook 各渠道
  - create/update_alert_rule: dedup 字段透传
"""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest

from app.services.alert_service import (
    evaluate_and_notify,
    _dispatch_notifications,
    _notify_inapp,
    _notify_email,
    _notify_webhook,
)
from app.schemas.alert import PriceAboveCondition


# ── 固定时间 ───────────────────────────────────────────────
NOW = datetime(2026, 7, 10, 14, 30, 0, tzinfo=timezone.utc)


# ══════════════════════════════════════════════════════════
# 1. evaluate_and_notify 协调器
# ══════════════════════════════════════════════════════════

class TestEvaluateAndNotify:
    """协调器的端到端测试：条件 + 去重 + DB 写入"""

    def test_single_rule_triggers_and_creates_log(self):
        db = MagicMock()
        rule = MagicMock()
        rule.id = 1
        rule.user_id = 100
        rule.symbol = "600519.SH"
        rule.rule_type = "price_above"
        rule.condition = {"rule_type": "price_above", "value": "1800"}
        rule.notify_channels = ["inapp"]
        rule.status = "active"
        rule.baseline_price = None
        rule.last_triggered_at = None
        rule.last_triggered_price = None
        rule.dedup_cooldown_minutes = None
        rule.dedup_rearm_pct = None

        db.query.return_value.filter.return_value.all.return_value = [rule]

        logs = evaluate_and_notify(db, "600519.SH", Decimal("1850"), None)

        assert len(logs) == 1
        # 验证 AlertLog 被创建
        added_calls = [c for c in db.add.call_args_list]
        assert len(added_calls) >= 1
        log_obj = added_calls[0][0][0]
        assert log_obj.rule_id == 1
        assert log_obj.trigger_value == Decimal("1850")

    def test_rule_suppressed_by_cooldown(self, monkeypatch):
        """冷却期内不创建 log、不更新规则"""
        db = MagicMock()
        rule = MagicMock()
        rule.id = 2
        rule.user_id = 200
        rule.symbol = "000001.SZ"
        rule.rule_type = "price_above"
        rule.condition = {"rule_type": "price_above", "value": "10"}
        rule.notify_channels = ["inapp"]
        rule.status = "active"
        rule.baseline_price = None
        rule.last_triggered_at = NOW  # 假设就是 NOW，在冷却期内
        rule.last_triggered_price = Decimal("10.5")
        rule.dedup_cooldown_minutes = None
        rule.dedup_rearm_pct = None

        db.query.return_value.filter.return_value.all.return_value = [rule]

        logs = evaluate_and_notify(db, "000001.SZ", Decimal("11.0"), None)
        assert len(logs) == 0
        db.add.assert_not_called()

    def test_multiple_rules_mixed_results(self):
        """多条规则：部分触发、部分抑制"""
        db = MagicMock()

        rule1 = MagicMock()  # IDLE, 会触发
        rule1.id = 1; rule1.user_id = 100; rule1.symbol = "600519.SH"
        rule1.rule_type = "price_above"; rule1.condition = {"rule_type": "price_above", "value": "1800"}
        rule1.notify_channels = ["inapp"]; rule1.status = "active"; rule1.baseline_price = None
        rule1.last_triggered_at = None; rule1.last_triggered_price = None
        rule1.dedup_cooldown_minutes = None; rule1.dedup_rearm_pct = None

        rule2 = MagicMock()  # COOLDOWN 中, 抑制
        rule2.id = 2; rule2.user_id = 100; rule2.symbol = "600519.SH"
        rule2.rule_type = "price_below"; rule2.condition = {"rule_type": "price_below", "value": "1700"}
        rule2.notify_channels = ["inapp"]; rule2.status = "active"; rule2.baseline_price = None
        rule2.last_triggered_at = NOW; rule2.last_triggered_price = Decimal("1680")
        rule2.dedup_cooldown_minutes = None; rule2.dedup_rearm_pct = None

        db.query.return_value.filter.return_value.all.return_value = [rule1, rule2]

        logs = evaluate_and_notify(db, "600519.SH", Decimal("1850"), None)

        # 只有 rule1 触发
        assert len(logs) == 1
        assert logs[0].rule_id == 1

    def test_commit_called_only_when_logs_exist(self):
        db = MagicMock()
        rule = MagicMock()
        rule.id = 1; rule.user_id = 100; rule1_symbol = "600519.SH"
        rule.rule_type = "price_above"; rule.condition = {"rule_type": "price_above", "value": "1800"}
        rule.notify_channels = ["inapp"]; rule.status = "active"; rule.baseline_price = None
        rule.last_triggered_at = NOW  # 冷却中
        rule.last_triggered_price = Decimal("1850")
        rule.dedup_cooldown_minutes = None; rule.dedup_rearm_pct = None

        db.query.return_value.filter.return_value.all.return_value = [rule]

        evaluate_and_notify(db, "600519.SH", Decimal("1860"), None)
        db.commit.assert_not_called()

    def test_no_active_rules_returns_empty(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        logs = evaluate_and_notify(db, "600519.SH", Decimal("1850"), None)
        assert logs == []
        db.commit.assert_not_called()


# ══════════════════════════════════════════════════════════
# 2. _dispatch_notifications 通知分发
# ══════════════════════════════════════════════════════════

class TestDispatchNotifications:
    """_dispatch_notifications 需要 rule 上有具体的 id/user_id/symbol 值（用于 JSON 序列化）"""

    @staticmethod
    def _make_rule(**overrides):
        rule = MagicMock()
        rule.id = overrides.get("id", 42)
        rule.user_id = overrides.get("user_id", 999)
        rule.symbol = overrides.get("symbol", "600519.SH")
        rule.rule_type = "price_above"
        rule.notify_channels = overrides.get("notify_channels", ["inapp"])
        return rule

    @patch("app.services.alert_service._notify_inapp")
    @patch("app.services.alert_service._notify_email")
    @patch("app.services.alert_service._notify_webhook")
    def test_all_channels_dispatched(self, mock_webhook, mock_email, mock_inapp):
        rule = self._make_rule(notify_channels=["inapp", "email", "webhook"])

        _dispatch_notifications(rule, "600519.SH", Decimal("1850"), "首次触发")

        assert mock_inapp.called
        mock_email.assert_called_once()
        mock_webhook.assert_called_once()

    @patch("app.services.alert_service._notify_inapp")
    def test_only_inapp(self, mock_inapp):
        rule = self._make_rule()

        _dispatch_notifications(rule, "600519.SH", Decimal("1850"), "test")

        mock_inapp.assert_called_once()
        assert isinstance(mock_inapp.call_args[0][1], str)

    @patch("app.services.alert_service.logger")
    def test_unknown_channel_skipped(self, mock_logger):
        rule = self._make_rule(notify_channels=["sms"])

        _dispatch_notifications(rule, "600519.SH", Decimal("1850"), "test")

        mock_logger.warning.assert_called_once()
        assert "unknown" in str(mock_logger.warning.call_args[0][0]).lower()

    @patch("app.services.alert_service._notify_inapp", side_effect=Exception("Redis down"))
    @patch("app.services.alert_service.logger")
    def test_channel_failure_doesnt_block_others(self, mock_logger, mock_inapp):
        """单渠道失败不阻断其他渠道"""
        rule = self._make_rule(notify_channels=["inapp", "email"])

        with patch("app.services.alert_service._notify_email") as mock_email:
            _dispatch_notifications(rule, "600519.SH", Decimal("1850"), "test")

        mock_email.assert_called_once()  # email 仍然正常调用
        mock_logger.error.assert_called_once()

    @patch("app.services.alert_service._notify_inapp")
    def test_empty_channels_noop(self, mock_inapp):
        rule = self._make_rule(notify_channels=[])
        _dispatch_notifications(rule, "600519.SH", Decimal("1850"), "test")
        mock_inapp.assert_not_called()


class TestNotifyInapp:
    """inapp 推送：Redis pubsub"""

    @patch("app.services.alert_service.get_redis_client")
    def test_publishes_to_user_channel(self, mock_rc_factory):
        fake_redis = MagicMock()
        mock_rc_factory.return_value = fake_redis

        _notify_inapp(user_id=42, payload='{"event":"alert"}')

        fake_redis.publish.assert_called_once_with("alerts:42", '{"event":"alert"}')


class TestNotifyEmailWebhookPlaceholders:

    def test_email_placeholder_logs(self):
        rule = MagicMock(); rule.id = 1
        with patch("app.services.alert_service.logger") as mock_log:
            _notify_email(rule, "600519.SH", Decimal("1850"))
            mock_log.info.assert_called_once()
            assert "[email placeholder]" in str(mock_log.info.call_args)

    def test_webhook_placeholder_logs(self):
        rule = MagicMock(); rule.id = 1
        with patch("app.services.alert_service.logger") as mock_log:
            _notify_webhook(rule, "600519.SH", Decimal("1850"))
            mock_log.info.assert_called_once()
            assert "[webhook placeholder]" in str(mock_log.info.call_args)


# ══════════════════════════════════════════════════════════
# 3. create / update alert_rule dedup 参数透传
# ══════════════════════════════════════════════════════════

class TestCreateUpdateDedupParams:

    @patch("app.services.alert_service.get_baseline_price")
    def test_create_with_dedup_params(self, mock_baseline):
        from app.services.alert_service import create_alert_rule

        mock_baseline.return_value = None
        db = MagicMock()
        # PriceAboveCondition 是 discriminated union，必须包含 rule_type
        condition = PriceAboveCondition(rule_type="price_above", value=Decimal("1800"))
        rule_mock = MagicMock()

        with patch.object(db, "add"):
            with patch.object(db, "commit"):
                with patch.object(db, "refresh", return_value=rule_mock):
                    result = create_alert_rule(
                        db=db, user_id=1, symbol="600519.SH",
                        condition=condition, notify_channels=["inapp"],
                        dedup_cooldown_minutes=15, dedup_rearm_pct=Decimal("3.0"),
                    )
                    # 验证构造时传入了 dedup 字段
                    add_call = db.add.call_args[0][0]
                    assert add_call.dedup_cooldown_minutes == 15
                    assert add_call.dedup_rearm_pct == Decimal("3.0")

    def test_update_with_dedup_params(self):
        from app.services.alert_service import update_alert_rule

        db = MagicMock()
        rule = MagicMock()

        with patch("app.services.alert_service._check_rule_ownership", return_value=rule):
            update_alert_rule(
                db=db, rule_id=1, user_id=1,
                status="active",
                dedup_cooldown_minutes=60,
                dedup_rearm_pct=Decimal("1.5"),
            )

        assert rule.dedup_cooldown_minutes == 60
        assert rule.dedup_rearm_pct == Decimal("1.5")

    def test_update_partial_dedup_params(self):
        """只更新一个 dedup 参数，另一个不变"""
        from app.services.alert_service import update_alert_rule

        db = MagicMock()
        rule = MagicMock()
        rule.dedup_cooldown_minutes = 30
        rule.dedup_rearm_pct = Decimal("2.0")

        with patch("app.services.alert_service._check_rule_ownership", return_value=rule):
            update_alert_rule(
                db=db, rule_id=1, user_id=1,
                dedup_cooldown_minutes=120,  # 只改这个
            )

        assert rule.dedup_cooldown_minutes == 120
        assert rule.dedup_rearm_pct == Decimal("2.0")  # 不变
