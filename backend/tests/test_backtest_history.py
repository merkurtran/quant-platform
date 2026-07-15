from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api.strategies import _backtest_summary
from app.schemas.strategy import BacktestRequest


def test_backtest_history_summary_keeps_run_context_and_metrics():
    result = SimpleNamespace(
        total_return=Decimal("0.1532"),
        max_drawdown=Decimal("8.5"),
        sharpe_ratio=Decimal("1.23"),
        trade_count=42,
    )
    run = SimpleNamespace(
        id=7,
        strategy_id=3,
        status="success",
        start_date=date(2025, 1, 1),
        end_date=date(2026, 6, 30),
        initial_capital=Decimal("1000000"),
        commission_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        symbols=["600519.SH"],
        params_snapshot={"fast_period": 5, "slow_period": 20},
        created_at=datetime(2026, 7, 15, tzinfo=timezone.utc),
        finished_at=datetime(2026, 7, 15, 0, 0, 3, tzinfo=timezone.utc),
        results=[result],
        error_message=None,
    )

    summary = _backtest_summary(run)

    assert summary.run_id == 7
    assert summary.symbols == ["600519.SH"]
    assert summary.commission_rate == Decimal("0.001")
    assert summary.slippage_rate == Decimal("0.0005")
    assert summary.params_snapshot["fast_period"] == 5
    assert summary.result is not None
    assert summary.result.total_return == 0.1532


def test_backtest_request_uses_realistic_execution_defaults():
    request = BacktestRequest(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        initial_capital=Decimal("1000000"),
        symbols=["600519.SH"],
    )

    assert request.commission_rate == Decimal("0.001")
    assert request.slippage_rate == Decimal("0.0005")


def test_backtest_request_rejects_unreasonable_execution_rates():
    with pytest.raises(ValidationError):
        BacktestRequest(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            initial_capital=Decimal("1000000"),
            commission_rate=Decimal("0.2"),
            symbols=["600519.SH"],
        )
