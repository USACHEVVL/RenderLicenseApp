"""remove machines table and machine_name column

Revision ID: 55f6e4aa6fa5
Revises: 2f4c2bfb5a57
Create Date: 2024-11-24 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '55f6e4aa6fa5'
down_revision: Union[str, Sequence[str], None] = '2f4c2bfb5a57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    columns = [col['name'] for col in insp.get_columns('licenses')]
    if 'machine_name' in columns:
        with op.batch_alter_table('licenses', schema=None) as batch_op:
            batch_op.drop_column('machine_name')
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