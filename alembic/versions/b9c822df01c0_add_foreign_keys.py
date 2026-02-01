"""add foreign keys

Revision ID: b9c822df01c0
Revises: 2e7cabebc286
Create Date: 2026-01-31 21:55:24.778588

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9c822df01c0'
down_revision: Union[str, None] = '2e7cabebc286'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "company_id",
        "users",
        "company",
        ["company_id"],
        ["id"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
    )
    op.create_index("company_id_idx", "users", ["company_id"])

    op.create_foreign_key(
        "plan_id",
        "orders",
        "plans",
        ["plan_id"],
        ["id"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
    )
    op.create_foreign_key(
        "user_id",
        "orders",
        "users",
        ["user_id"],
        ["id"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
    )
    op.create_index("fk_orders_plans1_idx", "orders", ["plan_id"])
    op.create_index("user_id_idx", "orders", ["user_id"])

    op.create_foreign_key(
        "fk_company_logos_orders",
        "company_logos",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )
    op.create_index("fk_company_logos_orders_idx", "company_logos", ["order_id"])

    op.create_foreign_key(
        "fk_company_company_logos1",
        "company",
        "company_logos",
        ["logo_id"],
        ["id"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
    )
    op.create_index("fk_company_company_logos1_idx", "company", ["logo_id"])

    op.create_foreign_key(
        "fk_documents_orders",
        "documents",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )
    op.create_index("fk_documents_orders_idx", "documents", ["order_id"])

    op.create_foreign_key(
        "order_id_email",
        "email_logs",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )
    op.create_foreign_key(
        "recipient_email",
        "email_logs",
        "users",
        ["recipient_email"],
        ["email"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
    )
    op.create_index("fk_email_logs_orders_idx", "email_logs", ["order_id"])
    op.create_index("recipient_email_idx", "email_logs", ["recipient_email"])

    op.create_foreign_key(
        "order_id_system",
        "system_logs",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="SET NULL",
        onupdate="CASCADE",
    )
    op.create_foreign_key(
        "user_id_system",
        "system_logs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
    )
    op.create_index("orders_id", "system_logs", ["order_id"])
    op.create_index("user_id_idx_system", "system_logs", ["user_id"])

    op.create_foreign_key(
        "order_id_legal",
        "legal_acknowledgments",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
    )
    op.create_index("fk_legal_acknowledgments_orders1_idx", "legal_acknowledgments", ["order_id"])

    op.create_foreign_key(
        "fk_naics_user_content_orders1",
        "naics_user_content",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
    )
    op.create_foreign_key(
        "naics_code",
        "naics_user_content",
        "naics_code",
        ["naics_code"],
        ["code"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
    )
    op.create_index("naics_code_idx", "naics_user_content", ["naics_code"])

    op.create_foreign_key(
        "order_id_status",
        "order_status",
        "orders",
        ["order_id"],
        ["id"],
        ondelete="NO ACTION",
        onupdate="NO ACTION",
    )


def downgrade() -> None:
    op.drop_constraint("order_id_status", "order_status", type_="foreignkey")
    op.drop_constraint("naics_code", "naics_user_content", type_="foreignkey")
    op.drop_constraint("fk_naics_user_content_orders1", "naics_user_content", type_="foreignkey")
    op.drop_index("naics_code_idx", table_name="naics_user_content")
    op.drop_constraint("order_id_legal", "legal_acknowledgments", type_="foreignkey")
    op.drop_index("fk_legal_acknowledgments_orders1_idx", table_name="legal_acknowledgments")
    op.drop_constraint("user_id_system", "system_logs", type_="foreignkey")
    op.drop_constraint("order_id_system", "system_logs", type_="foreignkey")
    op.drop_index("user_id_idx_system", table_name="system_logs")
    op.drop_index("orders_id", table_name="system_logs")
    op.drop_constraint("recipient_email", "email_logs", type_="foreignkey")
    op.drop_constraint("order_id_email", "email_logs", type_="foreignkey")
    op.drop_index("recipient_email_idx", table_name="email_logs")
    op.drop_index("fk_email_logs_orders_idx", table_name="email_logs")
    op.drop_constraint("fk_documents_orders", "documents", type_="foreignkey")
    op.drop_index("fk_documents_orders_idx", table_name="documents")
    op.drop_constraint("fk_company_company_logos1", "company", type_="foreignkey")
    op.drop_index("fk_company_company_logos1_idx", table_name="company")
    op.drop_constraint("fk_company_logos_orders", "company_logos", type_="foreignkey")
    op.drop_index("fk_company_logos_orders_idx", table_name="company_logos")
    op.drop_constraint("user_id", "orders", type_="foreignkey")
    op.drop_constraint("plan_id", "orders", type_="foreignkey")
    op.drop_index("user_id_idx", table_name="orders")
    op.drop_index("fk_orders_plans1_idx", table_name="orders")
    op.drop_constraint("company_id", "users", type_="foreignkey")
    op.drop_index("company_id_idx", table_name="users")
