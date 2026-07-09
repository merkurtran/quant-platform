from sqlalchemy import String, BigInteger, ForeignKey, DateTime, func, Numeric, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from decimal import Decimal

from shared.db.base import Base, TimestampMixin


class BrokerAccounts(Base):
    __tablename__ = "broker_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_type: Mapped[str] = mapped_column(String(32), nullable=False) # mock / qmt / eastmoney / pingan
    account_alias: Mapped[str] = mapped_column(String(64), nullable=False)
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active") # inactive / active / error
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
