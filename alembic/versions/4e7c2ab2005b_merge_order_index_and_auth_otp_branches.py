"""merge_order_index_and_auth_otp_branches

Revision ID: 4e7c2ab2005b
Revises: 3a8f1e2d5c9b, 9a3d1f6c4b21
Create Date: 2026-03-16 23:13:45.309570

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e7c2ab2005b'
down_revision: Union[str, None] = ('3a8f1e2d5c9b', '9a3d1f6c4b21')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
