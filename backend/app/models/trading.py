import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    Integer,
    Text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, TimestampMixin


class BrokerAccount(Base):
    __tablename__ = "broker_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    broker_type: Mapped[str] = mapped_column(String(32), nullable=False)
    account_alias: Mapped[str] = mapped_column(String(64), nullable=False)
    credentials_encrypted: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="inactive")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    broker_account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("broker_accounts.id"), nullable=False)
    strategy_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("strategies.id"), nullable=True)
    client_order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False, default="limit")
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), nullable=True)
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    filled_volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    # pending(已写库未提交) -> submitted(已提交券商)-> partial_filled(部分成交) -> filled(完全成交) -> cancelled(已撤) / rejected(被拒)
    # MockAdapter 下单是同步立即成交(pending 直接到 filled);
    # 真实券商是异步的,submitted 后需靠轮询或回调推进状态,中间可能停留数秒到数分钟
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending") 
    broker_order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="manual") # manual(手动) / strategy(策略自动) / ai_agent(AI触发)

    __table_args__ = (UniqueConstraint("broker_account_id", "client_order_id"),)


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    broker_account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("broker_accounts.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("broker_account_id", "symbol"),)


class PositionReconciliation(Base):
    __tablename__ = "position_reconciliations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    broker_account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("broker_accounts.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    local_volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    broker_volume: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    is_matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False) # order_create / order_cancel / strategy_deploy / broker_bind ...
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False, default="user") # user(人工) / ai_agent(AI触发)
    # ai_conversations 表在 Phase 4 才会创建，这里留 nullable
    conversation_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True) # actor_type=ai_agent 时关联对应会话
    target_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    target_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    detail: Mapped[Optional[dict]] = mapped_column(type_=None, nullable=True)  # JSONB via SA 2.0
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TradeOutbox(Base):
    __tablename__ = "trade_outbox"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    adapter_name: Mapped[str] = mapped_column(String(50), nullable=False)
    request_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),nullable=True)

    __table_args__ = (
        UniqueConstraint("order_id", name="uq_trade_outbox_order_id"),
    )