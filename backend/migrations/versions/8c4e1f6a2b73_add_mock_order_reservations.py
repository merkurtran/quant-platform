"""add mock order reservations

Revision ID: 8c4e1f6a2b73
Revises: 7a3d9e5b1c42
Create Date: 2026-07-16 09:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c4e1f6a2b73"
down_revision: Union[str, Sequence[str], None] = "7a3d9e5b1c42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("broker_accounts", sa.Column("frozen_cash", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("orders", sa.Column("reserved_cash", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("orders", sa.Column("reserved_volume", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("positions", sa.Column("frozen_volume", sa.Numeric(18, 2), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("positions", "frozen_volume")
    op.drop_column("orders", "reserved_volume")
    op.drop_column("orders", "reserved_cash")
    op.drop_column("broker_accounts", "frozen_cash")
