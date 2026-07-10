from sqlalchemy import String, BigInteger, Integer, ForeignKey, DateTime, func, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from decimal import Decimal

from shared.db.base import Base


class AlertRules(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(24), nullable=False)
    condition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    notify_channels: Mapped[list] = mapped_column(JSONB, nullable=False, default=lambda: ["inapp"]) # inapp, email, webhook
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active") # active, paused
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    baseline_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True) # 仅 rule_type=pct_change 且 baseline=rule_created_price 时有值

    # 去重状态机字段 (Phase 3 新增)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )
    last_triggered_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True, default=None,
    )
    dedup_cooldown_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None,
        comment="冷却窗口(分钟)，None 使用引擎默认值(30min)",
    )
    dedup_rearm_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True, default=None,
        comment="回落百分比，None 使用引擎默认值(2.0%)",
    )

    logs: Mapped[list["AlertLogs"]] = relationship(back_populates="rule")


class AlertLogs(Base):
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    trigger_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    message: Mapped[str | None] = mapped_column(String(256), nullable=True)

    rule: Mapped["AlertRules"] = relationship(back_populates="logs")