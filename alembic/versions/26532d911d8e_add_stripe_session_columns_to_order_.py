"""add stripe session columns to order_status

Revision ID: 26532d911d8e
Revises: b9c822df01c0
Create Date: 2026-03-07 11:47:34.885207

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26532d911d8e'
down_revision: Union[str, None] = 'b9c822df01c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("order_status", sa.Column("stripe_checkout_session_id", sa.String(255), nullable=True))
    op.add_column("order_status", sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("order_status", "stripe_payment_intent_id")
    op.drop_column("order_status", "stripe_checkout_session_id")
