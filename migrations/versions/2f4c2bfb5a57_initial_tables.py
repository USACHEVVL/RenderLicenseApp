"""initial tables

Revision ID: 2f4c2bfb5a57
Revises: 00bbaad016cc
Create Date: 2025-08-21 09:15:42.747336
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2f4c2bfb5a57'
down_revision: Union[str, Sequence[str], None] = '00bbaad016cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Добавляем колонку license_id и внешний ключ через batch mode
    with op.batch_alter_table("machines", schema=None) as batch_op:
        batch_op.add_column(sa.Column('license_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_machines_license_id',  # Имя нужно обязательно для SQLite
            'licenses',
            ['license_id'],
            ['id']
        )

    # Удаляем колонку username у users
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column('username')


def downgrade() -> None:
    with op.batch_alter_table("machines", schema=None) as batch_op:
        batch_op.drop_constraint('fk_machines_license_id', type_='foreignkey')
        batch_op.drop_column('license_id')

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.VARCHAR(), nullable=True))
