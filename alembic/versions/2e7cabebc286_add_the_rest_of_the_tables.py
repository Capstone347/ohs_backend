"""add the rest of the tables

Revision ID: 2e7cabebc286
Revises: 6c95068c8ff8
Create Date: 2026-01-31 21:08:13.122873

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e7cabebc286'
down_revision: Union[str, None] = '6c95068c8ff8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_logos",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer, nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("uploaded_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("id", name="logo_id_UNIQUE"),
    )

    op.create_table(
        "email_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer, nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("status", sa.Enum("sent", "delivered", "failed", name="email_status_enum"), nullable=False, server_default="sent"),
        sa.Column("sent_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("failure_reason", sa.Text, nullable=True),
    )

    op.create_table(
        "system_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("order_id", sa.Integer, nullable=True),
        sa.Column("log_level", sa.Enum("info", "warning", "error", name="log_level_enum"), nullable=False, server_default="info"),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "legal_acknowledgments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer, nullable=False),
        sa.Column("jurisdiction", sa.String(100), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("effective_date", sa.Date, nullable=False),
    )

    op.create_table(
        "naics_code",
        sa.Column("code", sa.Integer, primary_key=True),
        sa.Column("industry", sa.String(45), nullable=True),
    )

    op.create_table(
        "naics_user_content",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer, nullable=False),
        sa.Column("naics_code", sa.Integer, nullable=False),
        sa.Column("industry_description", sa.Text, nullable=False),
        sa.Column("suggested_sections", sa.JSON, nullable=True),
        sa.Column("procedures", sa.JSON, nullable=True),
    )

    op.create_table(
        "order_status",
        sa.Column("order_id", sa.Integer, primary_key=True),
        sa.Column("order_status", sa.Enum("draft", "processing", "review_pending", "available", "cancelled", name="order_status_enum"), nullable=False, server_default="draft"),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="CAD"),
        sa.Column("payment_provider", sa.String(35), nullable=True),
        sa.Column("payment_status", sa.Enum("pending", "paid", "failed", "refunded", name="payment_status_enum"), nullable=False, server_default="pending"),
    )
def downgrade() -> None:
    op.drop_table("order_status")
    op.drop_table("naics_user_content")
    op.drop_table("naics_code")
    op.drop_table("legal_acknowledgments")
    op.drop_table("system_logs")
    op.drop_table("email_logs")
    op.drop_table("company_logos")
