"""add_llm_usage_logs_table

Revision ID: a4f1b2c3d9e8
Revises: 9cf2a7f8c10f
Create Date: 2026-04-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4f1b2c3d9e8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            sa.Integer,
            sa.ForeignKey("sjp_generation_jobs.id", ondelete="CASCADE", onupdate="NO ACTION"),
            nullable=False,
        ),
        sa.Column(
            "toc_entry_id",
            sa.Integer,
            sa.ForeignKey("sjp_toc_entries.id", ondelete="CASCADE", onupdate="NO ACTION"),
            nullable=True,
        ),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, nullable=False),
        sa.Column("completion_tokens", sa.Integer, nullable=False),
        sa.Column("total_tokens", sa.Integer, nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_llm_usage_logs_job_id", "llm_usage_logs", ["job_id"])
    op.create_index("ix_llm_usage_logs_toc_entry_id", "llm_usage_logs", ["toc_entry_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_usage_logs_toc_entry_id", table_name="llm_usage_logs")
    op.drop_index("ix_llm_usage_logs_job_id", table_name="llm_usage_logs")
    op.drop_table("llm_usage_logs")

