"""add username column to users

Revision ID: 1c30a7905d50
Revises: 8c2b5e5d6b8f
Create Date: 2025-02-14 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c30a7905d50"
down_revision: Union[str, Sequence[str], None] = "8c2b5e5d6b8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("username")

