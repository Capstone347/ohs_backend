"""add_sjp_generation_jobs_table

Revision ID: 41e2314c64cd
Revises: 4e7c2ab2005b
Create Date: 2026-03-30 23:00:21.513619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41e2314c64cd'
down_revision: Union[str, None] = '4e7c2ab2005b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sjp_generation_jobs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "order_id",
            sa.Integer,
            sa.ForeignKey("orders.id", ondelete="CASCADE", onupdate="NO ACTION"),
            nullable=False,
        ),
        sa.Column("province", sa.String(50), nullable=False),
        sa.Column("naics_codes", sa.JSON, nullable=False),
        sa.Column("business_description", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("toc_generated_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("failed_at", sa.DateTime, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_sjp_generation_jobs_idempotency_key"),
    )
    op.create_index("ix_sjp_generation_jobs_order_id", "sjp_generation_jobs", ["order_id"])


def downgrade() -> None:
    op.drop_table("sjp_generation_jobs")