from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.strategy import (
    StrategyCreate,
    StrategyUpdate,
    StrategyPublic,
    StrategyDetail,
    BacktestRequest,
    BacktestRunPublic,
    BacktestRunResult,
    BacktestResultDetail,
)
from app.services.strategy_service import (
    create_strategy,
    get_strategy,
    list_strategies,
    update_strategy,
    delete_strategy,
    trigger_backtest,
    get_backtest_run,
    StrategyNotFoundError,
)
from shared.db.session import get_db

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])
backtest_router = APIRouter(prefix="/api/v1/backtest_runs", tags=["strategies"])


# ── 策略 CRUD ──

@router.post("", response_model=StrategyPublic, status_code=status.HTTP_201_CREATED)
def create(
    payload: StrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    strategy = create_strategy(
        db=db,
        user_id=current_user.id,
        name=payload.name,
        code=payload.code,
        description=payload.description,
        params=payload.params,
    )
    return StrategyPublic.model_validate(strategy)


@router.get("", response_model=list[StrategyPublic])
def list_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    strategies = list_strategies(db, user_id=current_user.id)
    return [StrategyPublic.model_validate(s) for s in strategies]


@router.get("/{strategy_id}", response_model=StrategyDetail)
def get_one(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        strategy = get_strategy(db, strategy_id=strategy_id, user_id=current_user.id)
    except StrategyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return StrategyDetail.model_validate(strategy)


@router.put("/{strategy_id}", response_model=StrategyPublic)
def update(
    strategy_id: int,
    payload: StrategyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        strategy = update_strategy(
            db=db,
            strategy_id=strategy_id,
            user_id=current_user.id,
            name=payload.name,
            description=payload.description,
            code=payload.code,
            params=payload.params,
        )
    except StrategyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return StrategyPublic.model_validate(strategy)


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        delete_strategy(db, strategy_id=strategy_id, user_id=current_user.id)
    except StrategyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")


# ── 回测 ──

@router.post("/{strategy_id}/backtest", response_model=BacktestRunPublic)
def start_backtest(
    strategy_id: int,
    payload: BacktestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        run = trigger_backtest(
            db=db,
            strategy_id=strategy_id,
            user_id=current_user.id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            initial_capital=payload.initial_capital,
            symbols=payload.symbols,
            params=payload.params,
        )
    except StrategyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return BacktestRunPublic(run_id=run.id, status=run.status)


@backtest_router.get("/{run_id}", response_model=BacktestRunResult)
def get_run_result(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        run = get_backtest_run(db, run_id=run_id, user_id=current_user.id)
    except StrategyNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest run not found")

    result_detail = None
    if run.results:
        r = run.results[0]  # 目前一对一，取第一个
        result_detail = BacktestResultDetail(
            total_return=float(r.total_return) if r.total_return is not None else None,
            annual_return=float(r.annual_return) if r.annual_return is not None else None,
            max_drawdown=float(r.max_drawdown) if r.max_drawdown is not None else None,
            sharpe_ratio=float(r.sharpe_ratio) if r.sharpe_ratio is not None else None,
            win_rate=float(r.win_rate) if r.win_rate is not None else None,
            trade_count=r.trade_count,
            equity_curve=r.equity_curve,
        )

    return BacktestRunResult(
        run_id=run.id,
        status=run.status,
        result=result_detail,
        error_message=run.error_message,
    )
