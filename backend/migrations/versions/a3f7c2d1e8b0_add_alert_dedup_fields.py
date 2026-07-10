"""add alert dedup fields to alert_rules

Revision ID: a3f7c2d1e8b0
Revises: 401266640e95
Create Date: 2026-07-10 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f7c2d1e8b0'
down_revision: Union[str, Sequence[str], None] = '401266640e95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 4 dedup state machine columns to alert_rules table."""
    op.add_column("alert_rules", sa.Column(
        "last_triggered_at", sa.DateTime(timezone=True), nullable=True,
    ))
    op.add_column("alert_rules", sa.Column(
        "last_triggered_price", sa.Numeric(precision=18, scale=4), nullable=True,
    ))
    op.add_column("alert_rules", sa.Column(
        "dedup_cooldown_minutes", sa.Integer(), nullable=True,
        comment="冷却窗口(分钟)，None 使用引擎默认值(30min)",
    ))
    op.add_column("alert_rules", sa.Column(
        "dedup_rearm_pct", sa.Numeric(precision=5, scale=2), nullable=True,
        comment="回落百分比，None 使用引擎默认值(2.0%)",
    ))


def downgrade() -> None:
    """Remove 4 dedup state machine columns from alert_rules table."""
    op.drop_column("alert_rules", "last_triggered_at")
    op.drop_column("alert_rules", "last_triggered_price")
    op.drop_column("alert_rules", "dedup_cooldown_minutes")
    op.drop_column("alert_rules", "dedup_rearm_pct")
