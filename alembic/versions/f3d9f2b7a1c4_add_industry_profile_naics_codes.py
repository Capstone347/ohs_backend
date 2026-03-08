"""add industry profile naics codes

Revision ID: f3d9f2b7a1c4
Revises: b9c822df01c0
Create Date: 2026-02-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3d9f2b7a1c4"
down_revision: Union[str, None] = "b9c822df01c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "industry_profiles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer, nullable=False),
        sa.Column("province", sa.String(50), nullable=True),
        sa.Column("business_description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", name="uq_industry_profiles_company_id"),
    )
    op.create_index("ix_industry_profiles_company_id", "industry_profiles", ["company_id"])
    op.create_foreign_key(
        "fk_industry_profiles_company_id",
        "industry_profiles",
        "company",
        ["company_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    op.create_table(
        "industry_naics_codes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("industry_profile_id", sa.Integer, nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("industry_profile_id", "code", name="uq_industry_naics_profile_code"),
    )
    op.create_index("ix_industry_naics_codes_industry_profile_id", "industry_naics_codes", ["industry_profile_id"])
    op.create_foreign_key(
        "fk_industry_naics_codes_profile_id",
        "industry_naics_codes",
        "industry_profiles",
        ["industry_profile_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    company_columns = {column["name"] for column in inspector.get_columns("company")}

    has_legacy_province = "province" in company_columns
    has_legacy_business_description = "business_description" in company_columns
    has_legacy_naics_code = "naics_code" in company_columns

    if has_legacy_province or has_legacy_business_description or has_legacy_naics_code:
        province_expr = "province" if has_legacy_province else "NULL"
        business_description_expr = "business_description" if has_legacy_business_description else "NULL"

        bind.execute(
            sa.text(
                f"""
                INSERT INTO industry_profiles (company_id, province, business_description, created_at, updated_at)
                SELECT id, {province_expr}, {business_description_expr}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                FROM company
                WHERE {province_expr} IS NOT NULL OR {business_description_expr} IS NOT NULL OR {('naics_code IS NOT NULL' if has_legacy_naics_code else '0=1')}
                """
            )
        )

    if has_legacy_naics_code:
        bind.execute(
            sa.text(
                """
                INSERT INTO industry_naics_codes (industry_profile_id, code, position, created_at, updated_at)
                SELECT industry_profiles.id, CAST(company.naics_code AS CHAR(6)), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                FROM company
                JOIN industry_profiles ON industry_profiles.company_id = company.id
                WHERE company.naics_code IS NOT NULL
                """
            )
        )


def downgrade() -> None:
    op.drop_constraint("fk_industry_naics_codes_profile_id", "industry_naics_codes", type_="foreignkey")
    op.drop_index("ix_industry_naics_codes_industry_profile_id", table_name="industry_naics_codes")
    op.drop_table("industry_naics_codes")

    op.drop_constraint("fk_industry_profiles_company_id", "industry_profiles", type_="foreignkey")
    op.drop_index("ix_industry_profiles_company_id", table_name="industry_profiles")
    op.drop_table("industry_profiles")