import logging
from datetime import datetime, timezone

from shared.redis_client import redis_client
from shared.db.session import SessionLocal
from app.models.strategy import BacktestRuns, Strategies, BacktestResults
from workers.strategy_worker.backtest_runner import BacktestConfig, run_backtest

logger = logging.getLogger(__name__)


def _build_result_dict(result) -> dict:
    """把 BacktestResult（dataclass）映射为 BacktestResults（ORM）所需的字段字典。
    equity_curve 合并 dates 字段，对上前端 [{date, equity}] 格式。"""
    equity_curve = None
    if result.equity_curve and result.dates:
        equity_curve = [
            {"date": d, "equity": v}
            for d, v in zip(result.dates, result.equity_curve)
        ]

    return {
        "total_return": result.total_return,
        "annual_return": result.annual_return,
        "max_drawdown": result.max_drawdown,
        "sharpe_ratio": result.sharpe_ratio,
        "win_rate": result.win_rate,
        "trade_count": result.trade_count,
        "equity_curve": equity_curve,
        "trade_list": result.trades if result.trades else None,
    }


def process_one_backtest(run_id: int) -> None:
    db = SessionLocal()
    run = None
    try:
        run = db.query(BacktestRuns).filter(BacktestRuns.id == run_id).first()
        if run is None:
            logger.warning(f"回测记录不存在,跳过: run_id={run_id}")
            return

        strategy = db.query(Strategies).filter(Strategies.id == run.strategy_id).first()
        if strategy is None:
            run.status = "failed"
            run.error_message = f"关联策略 {run.strategy_id} 不存在"
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            return

        run.status = "running"
        db.commit()

        # 多品种暂时取第一个，后续遍历 symbols 扩展
        symbol = run.symbols[0] if run.symbols else None
        if symbol is None:
            run.status = "failed"
            run.error_message = "回测标的为空"
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            return

        config = BacktestConfig(
            strategy_code=strategy.code,
            strategy_params=run.params_snapshot or {},
            symbol=symbol,
            start_date=run.start_date.strftime("%Y-%m-%d"),
            end_date=run.end_date.strftime("%Y-%m-%d"),
            initial_capital=run.initial_capital,
            run_id=run.id,
        )

        result = run_backtest(config)

        if result.success:
            run.status = "success"
            result_dict = _build_result_dict(result)
            db.add(BacktestResults(run_id=run.id, **result_dict))
        else:
            run.status = "failed"
            run.error_message = result.error_message

        run.finished_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            f"回测完成: run_id={run_id} symbol={symbol} "
            f"status={run.status} elapsed={result.execution_time_ms}ms"
        )

    except Exception as e:
        logger.exception(f"回测调度异常: run_id={run_id}")
        if run is not None:
            try:
                run.status = "failed"
                run.error_message = f"调度异常: {e}"
                run.finished_at = datetime.now(timezone.utc)
                db.commit()
            except Exception:
                logger.exception(f"回写失败状态时再次异常: run_id={run_id}")
    finally:
        db.close()


if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)
    logger.info("策略调度器启动,监听队列 backtest_queue...")
    while True:
        try:
            item = redis_client.blpop("backtest_queue", timeout=5)
            if item is None:
                continue
            _, run_id_str = item
            process_one_backtest(int(run_id_str))
        except Exception:
            logger.exception("主循环异常,5秒后重试")
            time.sleep(5)
