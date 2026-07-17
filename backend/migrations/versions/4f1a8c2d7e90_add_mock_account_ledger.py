"""add mock account ledger

Revision ID: 4f1a8c2d7e90
Revises: 9b2e7a4f1c6d
Create Date: 2026-07-15 17:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4f1a8c2d7e90"
down_revision: Union[str, Sequence[str], None] = "9b2e7a4f1c6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("broker_accounts", sa.Column("initial_cash", sa.Numeric(18, 2), server_default="1000000", nullable=False))
    op.add_column("broker_accounts", sa.Column("cash_balance", sa.Numeric(18, 2), server_default="1000000", nullable=False))
    op.add_column("broker_accounts", sa.Column("commission_rate", sa.Numeric(10, 6), server_default="0.000300", nullable=False))
    op.add_column("broker_accounts", sa.Column("minimum_commission", sa.Numeric(10, 2), server_default="5.00", nullable=False))
    op.add_column("broker_accounts", sa.Column("stamp_duty_rate", sa.Numeric(10, 6), server_default="0.000500", nullable=False))
    op.add_column("broker_accounts", sa.Column("slippage_rate", sa.Numeric(10, 6), server_default="0.000500", nullable=False))
    op.add_column("orders", sa.Column("filled_price", sa.Numeric(12, 3), nullable=True))
    op.add_column("orders", sa.Column("commission", sa.Numeric(12, 2), server_default="0", nullable=False))
    op.add_column("orders", sa.Column("stamp_duty", sa.Numeric(12, 2), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("orders", "stamp_duty")
    op.drop_column("orders", "commission")
    op.drop_column("orders", "filled_price")
    op.drop_column("broker_accounts", "slippage_rate")
    op.drop_column("broker_accounts", "stamp_duty_rate")
    op.drop_column("broker_accounts", "minimum_commission")
    op.drop_column("broker_accounts", "commission_rate")
    op.drop_column("broker_accounts", "cash_balance")
    op.drop_column("broker_accounts", "initial_cash")
