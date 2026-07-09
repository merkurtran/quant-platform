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


class BacktestRunResult(BaseModel):
    """GET /backtest_runs/{run_id} 响应"""
    run_id: int
    status: str
    result: BacktestResultDetail | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}