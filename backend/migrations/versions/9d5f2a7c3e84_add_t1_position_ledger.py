"""add T+1 position ledger

Revision ID: 9d5f2a7c3e84
Revises: 8c4e1f6a2b73
Create Date: 2026-07-16 10:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d5f2a7c3e84"
down_revision: Union[str, Sequence[str], None] = "8c4e1f6a2b73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "positions",
        sa.Column(
            "available_volume",
            sa.Numeric(18, 2),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "positions",
        sa.Column(
            "pending_settlement_volume",
            sa.Numeric(18, 2),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "positions",
        sa.Column("last_buy_trade_date", sa.Date(), nullable=True),
    )
    op.execute("UPDATE positions SET available_volume = volume")


def downgrade() -> None:
    op.drop_column("positions", "last_buy_trade_date")
    op.drop_column("positions", "pending_settlement_volume")
    op.drop_column("positions", "available_volume")
