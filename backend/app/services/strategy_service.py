from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.strategy import Strategies, BacktestRuns
from shared.redis_client import redis_client


class StrategyNotFoundError(Exception):
    pass


def _get_strategy_owned(db: Session, strategy_id: int, user_id: int) -> Strategies:
    strategy = (
        db.query(Strategies)
        .filter(Strategies.id == strategy_id, Strategies.user_id == user_id)
        .first()
    )
    if strategy is None:
        raise StrategyNotFoundError(f"Strategy {strategy_id} not found for user {user_id}")
    return strategy



def create_strategy(
    db: Session,
    user_id: int,
    name: str,
    code: str,
    description: str | None = None,
    params: dict | None = None,
) -> Strategies:
    strategy = Strategies(
        user_id=user_id,
        name=name,
        code=code,
        description=description,
        params=params or {},
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


def get_strategy(db: Session, strategy_id: int, user_id: int) -> Strategies:
    return _get_strategy_owned(db, strategy_id, user_id)


def list_strategies(db: Session, user_id: int) -> list[Strategies]:
    return (
        db.query(Strategies)
        .filter(Strategies.user_id == user_id)
        .order_by(Strategies.updated_at.desc())
        .all()
    )


def update_strategy(
    db: Session,
    strategy_id: int,
    user_id: int,
    name: str | None = None,
    description: str | None = None,
    code: str | None = None,
    params: dict | None = None,
) -> Strategies:
    strategy = _get_strategy_owned(db, strategy_id, user_id)
    if name is not None:
        strategy.name = name
    if description is not None:
        strategy.description = description
    if code is not None:
        strategy.code = code
    if params is not None:
        strategy.params = params
    db.commit()
    db.refresh(strategy)
    return strategy


def delete_strategy(db: Session, strategy_id: int, user_id: int) -> None:
    strategy = _get_strategy_owned(db, strategy_id, user_id)
    db.delete(strategy)
    db.commit()



def trigger_backtest(
    db: Session,
    strategy_id: int,
    user_id: int,
    start_date: date,
    end_date: date,
    initial_capital: Decimal,
    symbols: list[str],
    params: dict,
) -> BacktestRuns:
    # 校验策略存在且属于当前用户
    _get_strategy_owned(db, strategy_id, user_id)

    run = BacktestRuns(
        strategy_id=strategy_id,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        symbols=symbols,
        params_snapshot=params,
        status="queued",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        redis_client.rpush("backtest_queue", str(run.id))
    except Exception as e:
        run.status = "failed"
        run.error_message = f"任务入队失败: {e}"
        db.commit()

    return run


def get_backtest_run(db: Session, run_id: int, user_id: int) -> BacktestRuns:
    """查询回测记录，校验关联策略属于当前用户"""
    run = (
        db.query(BacktestRuns)
        .options(joinedload(BacktestRuns.results))
        .join(Strategies, BacktestRuns.strategy_id == Strategies.id)
        .filter(BacktestRuns.id == run_id, Strategies.user_id == user_id)
        .first()
    )
    if run is None:
        raise StrategyNotFoundError(f"Backtest run {run_id} not found for user {user_id}")
    return run
