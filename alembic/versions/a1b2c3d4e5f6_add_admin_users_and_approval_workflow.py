"""add admin_users table and approval workflow columns

Revision ID: a1b2c3d4e5f6
Revises: 41e2314c64cd
Create Date: 2026-04-06

"""
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9cf2a7f8c10f"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="manager"),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.add_column(
        "plans",
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="0"),
    )

    op.add_column(
        "orders",
        sa.Column("reviewed_by_admin_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_foreign_key(
        "fk_orders_reviewed_by_admin",
        "orders",
        "admin_users",
        ["reviewed_by_admin_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_orders_reviewed_by_admin", "orders", type_="foreignkey")
    op.drop_column("orders", "reviewed_at")
    op.drop_column("orders", "reviewed_by_admin_id")
    op.drop_column("plans", "requires_approval")
    op.drop_table("admin_users")
