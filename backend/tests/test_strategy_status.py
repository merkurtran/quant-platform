from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.strategy_service import update_strategy
from workers.strategy_worker.scheduler import process_one_backtest


def test_editing_backtested_strategy_returns_it_to_draft():
    db = MagicMock()
    strategy = MagicMock(status="backtested")
    db.query.return_value.filter.return_value.first.return_value = strategy

    update_strategy(db, strategy_id=1, user_id=1, code="class Updated: pass")

    assert strategy.status == "draft"
    db.commit.assert_called_once()


@patch("workers.strategy_worker.scheduler.BacktestResults")
@patch("workers.strategy_worker.scheduler.run_backtest")
@patch("workers.strategy_worker.scheduler.SessionLocal")
def test_successful_backtest_marks_strategy_backtested(
    mock_session_factory, mock_run_backtest, mock_result_model
):
    db = MagicMock()
    mock_session_factory.return_value = db
    run = MagicMock(
        id=7,
        strategy_id=3,
        symbols=["600519.SH"],
        params_snapshot={},
        start_date=SimpleNamespace(strftime=lambda _: "2026-01-01"),
        end_date=SimpleNamespace(strftime=lambda _: "2026-06-30"),
        initial_capital=1_000_000,
    )
    strategy = MagicMock(code="class Test: pass", status="draft")
    db.query.return_value.filter.return_value.first.side_effect = [run, strategy]
    mock_run_backtest.return_value = SimpleNamespace(
        success=True,
        total_return=10.0,
        annual_return=8.0,
        max_drawdown=-3.0,
        sharpe_ratio=1.2,
        win_rate=55.0,
        trade_count=8,
        equity_curve=[],
        dates=[],
        trades=[],
        error_message=None,
        execution_time_ms=20,
    )

    process_one_backtest(7)

    assert run.status == "success"
    assert strategy.status == "backtested"
    db.add.assert_called_once_with(mock_result_model.return_value)
