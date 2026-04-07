"""add_sjp_toc_entries_and_sjp_contents_tables

Revision ID: 9cf2a7f8c10f
Revises: 41e2314c64cd
Create Date: 2026-04-06 20:11:20.994899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cf2a7f8c10f'
down_revision: Union[str, None] = '41e2314c64cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sjp_toc_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            sa.Integer,
            sa.ForeignKey("sjp_generation_jobs.id", ondelete="CASCADE", onupdate="NO ACTION"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_sjp_toc_entries_job_id", "sjp_toc_entries", ["job_id"])

    op.create_table(
        "sjp_contents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "toc_entry_id",
            sa.Integer,
            sa.ForeignKey("sjp_toc_entries.id", ondelete="CASCADE", onupdate="NO ACTION"),
            nullable=False,
        ),
        sa.Column("task_description", sa.Text, nullable=False),
        sa.Column("required_ppe", sa.JSON, nullable=False),
        sa.Column("step_by_step_instructions", sa.JSON, nullable=False),
        sa.Column("identified_hazards", sa.JSON, nullable=False),
        sa.Column("control_measures", sa.JSON, nullable=False),
        sa.Column("training_requirements", sa.JSON, nullable=False),
        sa.Column("emergency_procedures", sa.Text, nullable=False),
        sa.Column("legislative_references", sa.Text, nullable=True),
        sa.Column("raw_ai_response", sa.Text, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("generated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_sjp_contents_toc_entry_id", "sjp_contents", ["toc_entry_id"])


def downgrade() -> None:
    op.drop_table("sjp_contents")
    op.drop_table("sjp_toc_entries")

