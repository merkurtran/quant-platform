from sqlalchemy import String, BigInteger, ForeignKey, DateTime, func, Integer, UniqueConstraint, Numeric, PrimaryKeyConstraint, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime,date
from typing import Optional
from decimal import Decimal

from shared.db.base import Base, TimestampMixin


class Watchlists(Base, TimestampMixin):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    items: Mapped[list["WatchlistItems"]] = relationship(back_populates="watchlist")


class WatchlistItems(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    watchlist_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    watchlist: Mapped["Watchlists"] = relationship(back_populates="items")

    # 这里添加唯一键约束：同一自选股列表下不允许重复添加同一支股票
    # 这是为了在数据库层面保证数据一致性
    # 而不是依赖应用层校验，因为应用层校验无法保证数据库的并发一致性
    # PostgreSQL 中 UNIQUE 约束会自动创建索引，所以这里不需要显式创建索引
    __table_args__ = (
        UniqueConstraint("watchlist_id", "symbol", name="uq_watchlist_items_watchlist_id_symbol"),
    )


class Klines(Base):
    __tablename__ = "klines"

    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    period: Mapped[str] = mapped_column(String(8), nullable=False) # 1m / 5m / 15m / 1d
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint("symbol", "period", "ts", name='pk_klines'),
    )


class CorporateActions(Base):
    __tablename__ = "corporate_actions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    action_type: Mapped[str] = mapped_column(String(16), nullable=False)
    cash_per_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), default=0)
    stock_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), default=0)
    rights_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), default=0)
    rights_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), default=0)  # 配股比例
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('symbol', 'ex_date', 'action_type', name='uq_corporate_actions_symbol_ex_date_action_type'),
    )