from sqlalchemy import String, BigInteger, ForeignKey, DateTime, func, Numeric, Text, Integer, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from decimal import Decimal

from shared.db.base import Base, TimestampMixin


class Strategies(Base, TimestampMixin):
    __tablename__ = "strategies"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=lambda: {})
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft") # draft / backtested / paper_running / archived

    backtest_runs: Mapped[list["BacktestRuns"]] = relationship(
        back_populates="strategy", 
        cascade="all, delete-orphan"  # 删除策略时级联删除所有回测记录
    )

class BacktestRuns(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, server_default="0.001000"
    )
    slippage_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, server_default="0.000500"
    )
    params_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running") # queued / running / success / failed
    symbols: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    strategy: Mapped["Strategies"] = relationship(back_populates="backtest_runs")
    
    results: Mapped[list["BacktestResults"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan"  # 删除回测记录时级联删除结果
    )


class BacktestResults(Base):
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    total_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    annual_return: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    win_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    trade_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    equity_curve: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [{date, equity}, ...]
    trade_list: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)

    run: Mapped["BacktestRuns"] = relationship(back_populates="results")
