from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class StrategyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    code: str = Field(min_length=1)
    params: dict = Field(default_factory=dict)


class StrategyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    code: str | None = Field(default=None, min_length=1)
    params: dict | None = None


class StrategyPublic(BaseModel):
    """列表 / 创建响应"""
    id: int
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StrategyDetail(StrategyPublic):
    """详情响应，比 Public 多 code 和 params"""
    code: str
    params: dict



class BacktestRequest(BaseModel):
    start_date: date
    end_date: date
    initial_capital: Decimal = Field(gt=0)
    commission_rate: Decimal = Field(default=Decimal("0.001"), ge=0, le=Decimal("0.1"))
    slippage_rate: Decimal = Field(default=Decimal("0.0005"), ge=0, le=Decimal("0.1"))
    symbols: list[str] = Field(min_length=1)
    params: dict = Field(default_factory=dict)


class BacktestRunPublic(BaseModel):
    """POST /backtest 的即时响应"""
    run_id: int
    status: str

    model_config = {"from_attributes": True}


class BacktestResultDetail(BaseModel):
    total_return: float | None
    annual_return: float | None
    max_drawdown: float | None
    sharpe_ratio: float | None
    win_rate: float | None
    trade_count: int | None
    equity_curve: list | None


class BacktestResultSummary(BaseModel):
    total_return: float | None
    max_drawdown: float | None
    sharpe_ratio: float | None
    trade_count: int | None


class BacktestRunSummary(BaseModel):
    run_id: int
    strategy_id: int
    status: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    commission_rate: Decimal
    slippage_rate: Decimal
    symbols: list[str]
    params_snapshot: dict
    created_at: datetime
    finished_at: datetime | None
    result: BacktestResultSummary | None = None
    error_message: str | None = None


class BacktestRunResult(BaseModel):
    """GET /backtest_runs/{run_id} 响应"""
    run_id: int
    strategy_id: int
    status: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    commission_rate: Decimal
    slippage_rate: Decimal
    symbols: list[str]
    params_snapshot: dict
    created_at: datetime
    finished_at: datetime | None
    result: BacktestResultDetail | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}
