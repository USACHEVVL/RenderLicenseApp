"""Merge heads

Revision ID: 9a979dffbf25
Revises: 1c30a7905d50, 7855115cbd60, d7c2e2f3a1b4
Create Date: 2025-08-27 11:25:16.350962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a979dffbf25'
down_revision: Union[str, Sequence[str], None] = ('1c30a7905d50', '7855115cbd60', 'd7c2e2f3a1b4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
