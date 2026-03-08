"""add_industry_intake_responses_table

Revision ID: e33170dab192
Revises: b9c822df01c0
Create Date: 2026-03-01 23:11:21.301277

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e33170dab192'
down_revision: Union[str, None] = 'b9c822df01c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "industry_intake_responses",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "order_id",
            sa.Integer,
            sa.ForeignKey("orders.id", ondelete="NO ACTION", onupdate="NO ACTION"),
            nullable=False,
            unique=True,
        ),
        sa.Column("answers", sa.JSON, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_industry_intake_responses_order_id", "industry_intake_responses", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_industry_intake_responses_order_id", table_name="industry_intake_responses")
    op.drop_table("industry_intake_responses")
