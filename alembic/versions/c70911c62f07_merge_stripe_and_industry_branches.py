"""merge_stripe_and_industry_branches

Revision ID: c70911c62f07
Revises: 26532d911d8e, e33170dab192
Create Date: 2026-03-10 21:08:07.990989

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c70911c62f07'
down_revision: Union[str, None] = ('26532d911d8e', 'e33170dab192')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
