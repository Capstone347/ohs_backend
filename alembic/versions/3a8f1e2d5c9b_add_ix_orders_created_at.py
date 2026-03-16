"""add ix_orders_created_at index

Revision ID: 3a8f1e2d5c9b
Revises: c70911c62f07
Create Date: 2026-03-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3a8f1e2d5c9b'
down_revision: Union[str, None] = 'c70911c62f07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_orders_created_at', 'orders', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_orders_created_at', table_name='orders')
