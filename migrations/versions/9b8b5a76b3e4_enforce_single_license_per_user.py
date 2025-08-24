"""enforce single license per user

Revision ID: 9b8b5a76b3e4
Revises: 8c2b5e5d6b8f
Create Date: 2025-09-24 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9b8b5a76b3e4'
down_revision: Union[str, Sequence[str], None] = '8c2b5e5d6b8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table('licenses', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_licenses_user_id', ['user_id'])


def downgrade() -> None:
    with op.batch_alter_table('licenses', schema=None) as batch_op:
        batch_op.drop_constraint('uq_licenses_user_id', type_='unique')
