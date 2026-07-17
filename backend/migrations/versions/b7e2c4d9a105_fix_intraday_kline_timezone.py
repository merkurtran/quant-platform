"""fix intraday kline timezone

Revision ID: b7e2c4d9a105
Revises: 9d5f2a7c3e84
Create Date: 2026-07-16 14:40:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b7e2c4d9a105"
down_revision: Union[str, Sequence[str], None] = "9d5f2a7c3e84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Historical providers returned naive Asia/Shanghai wall-clock values.
    # PostgreSQL interpreted them as UTC, so move intraday bars to the real instant.
    op.execute(
        "UPDATE klines SET ts = ts - INTERVAL '8 hours' WHERE period <> '1d'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE klines SET ts = ts + INTERVAL '8 hours' WHERE period <> '1d'"
    )
