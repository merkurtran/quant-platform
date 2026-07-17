"""add order reject reason

Revision ID: 7a3d9e5b1c42
Revises: 4f1a8c2d7e90
Create Date: 2026-07-16 09:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a3d9e5b1c42"
down_revision: Union[str, Sequence[str], None] = "4f1a8c2d7e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("reject_reason", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "reject_reason")
