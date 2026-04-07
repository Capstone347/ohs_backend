"""add industry specific plan seed

Revision ID: 7d4a9c8e1b2f
Revises: 41e2314c64cd
Create Date: 2026-04-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7d4a9c8e1b2f"
down_revision: Union[str, None] = "41e2314c64cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            INSERT INTO plans (slug, name, description, base_price)
            SELECT :slug, :name, :description, :base_price
            WHERE NOT EXISTS (
                SELECT 1 FROM plans WHERE slug = :slug
            )
            """
        ),
        {
            "slug": "industry_specific",
            "name": "Industry Specific",
            "description": "Industry-specific SJP generation for existing manuals",
            "base_price": 50.00,
        },
    )


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            DELETE FROM plans
            WHERE slug = :slug
            """
        ),
        {"slug": "industry_specific"},
    )
