"""add_core_tables

Revision ID: 6c95068c8ff8
Revises: 8202b693ce2a
Create Date: 2026-01-31 20:30:46.610335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c95068c8ff8'
down_revision: Union[str, None] = '8202b693ce2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.UniqueConstraint("slug", name="plan_slug_UNIQUE"),
    )

    op.create_table(
        "company",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("logo_id", sa.Integer, nullable=True),
        sa.Column("name", sa.String(45), nullable=True),
    
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("company_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("last_login", sa.DateTime, nullable=True),
        sa.Column("otp_token", sa.CHAR(6), nullable=True),
        sa.Column("otp_expires", sa.DateTime, nullable=True),
        sa.Column("password_hash", sa.String(45), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="customer"),
        sa.UniqueConstraint("email", name="email_UNIQUE"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("plan_id", sa.Integer, nullable=True),
        sa.Column("company_id", sa.Integer, nullable=False),
        sa.Column("jurisdiction", sa.String(100), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("is_industry_specific", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("admin_notes", sa.Text, nullable=True),
    )

    op.create_table(
        "documents",
        sa.Column("document_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer, nullable=False),
        sa.Column("content", sa.JSON, nullable=True),
        sa.Column("access_token", sa.CHAR(64), nullable=False),
        sa.Column("token_expires_at", sa.DateTime, nullable=False),
        sa.Column("generated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("downloaded_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("last_downloaded_at", sa.DateTime, nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_format", sa.String(10), nullable=True, server_default="docx"),
        sa.UniqueConstraint("access_token", name="access_token_UNIQUE"),
    )

def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("orders")
    op.drop_table("users")
    op.drop_table("company")
    op.drop_table("plans")
