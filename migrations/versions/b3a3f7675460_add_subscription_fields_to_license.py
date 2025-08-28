"""add subscription fields to license

Revision ID: b3a3f7675460
Revises: 9a979dffbf25
Create Date: 2024-01-01 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b3a3f7675460'
down_revision: Union[str, Sequence[str], None] = '9a979dffbf25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table("licenses") as batch_op:
        batch_op.add_column(sa.Column("subscription_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column("next_charge_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("licenses") as batch_op:
        batch_op.drop_column("next_charge_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("subscription_id")
