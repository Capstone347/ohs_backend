"""add_auth_otp_requests_table

Revision ID: 9a3d1f6c4b21
Revises: c70911c62f07
Create Date: 2026-03-16 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a3d1f6c4b21"
down_revision: Union[str, None] = "c70911c62f07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_otp_requests",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("otp_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_sent_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("request_ip", sa.String(64), nullable=True),
        sa.Column("lockout_until", sa.DateTime, nullable=True),
    )
    op.create_index("ix_auth_otp_requests_email", "auth_otp_requests", ["email"])
    op.create_index("ix_auth_otp_requests_request_ip", "auth_otp_requests", ["request_ip"])


def downgrade() -> None:
    op.drop_index("ix_auth_otp_requests_request_ip", table_name="auth_otp_requests")
    op.drop_index("ix_auth_otp_requests_email", table_name="auth_otp_requests")
    op.drop_table("auth_otp_requests")

