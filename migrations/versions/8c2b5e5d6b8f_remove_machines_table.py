"""drop machines table and machine_name column

Revision ID: 8c2b5e5d6b8f
Revises: 2f4c2bfb5a57
Create Date: 2025-08-23 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8c2b5e5d6b8f'
down_revision: Union[str, Sequence[str], None] = '2f4c2bfb5a57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    license_columns = [col['name'] for col in insp.get_columns('licenses')]
    if 'machine_name' in license_columns:
        op.execute(sa.text("UPDATE licenses SET machine_name = NULL"))
        with op.batch_alter_table('licenses', schema=None) as batch_op:
            batch_op.drop_column('machine_name')

    if 'machines' in insp.get_table_names():
        with op.batch_alter_table('machines', schema=None) as batch_op:
            batch_op.drop_constraint('fk_machines_license_id', type_='foreignkey')
        op.drop_table('machines')


def downgrade() -> None:
    op.create_table(
        'machines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('license_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['license_id'], ['licenses.id'], name='fk_machines_license_id'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_machines_id'), 'machines', ['id'], unique=False)
    with op.batch_alter_table('licenses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('machine_name', sa.String(), nullable=True))

