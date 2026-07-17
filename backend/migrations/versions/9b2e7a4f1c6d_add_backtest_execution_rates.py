"""add backtest execution rates

Revision ID: 9b2e7a4f1c6d
Revises: 6fc9030a7969
Create Date: 2026-07-15 18:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b2e7a4f1c6d"
down_revision: Union[str, Sequence[str], None] = "6fc9030a7969"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "backtest_runs",
        sa.Column(
            "commission_rate",
            sa.Numeric(precision=10, scale=6),
            server_default="0.001000",
            nullable=False,
        ),
    )
    op.add_column(
        "backtest_runs",
        sa.Column(
            "slippage_rate",
            sa.Numeric(precision=10, scale=6),
            server_default="0.010000",
            nullable=False,
        ),
    )
    op.alter_column(
        "backtest_runs",
        "slippage_rate",
        server_default="0.000500",
    )


def downgrade() -> None:
    op.drop_column("backtest_runs", "slippage_rate")
    op.drop_column("backtest_runs", "commission_rate")
