"""expand license_key to 36 chars

Revision ID: 7855115cbd60
Revises: 9b8b5a76b3e4
Create Date: 2024-01-01 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7855115cbd60'
down_revision: Union[str, Sequence[str], None] = '9b8b5a76b3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table("licenses") as batch_op:
        batch_op.alter_column("license_key",
                              existing_type=sa.String(length=16),
                              type_=sa.String(length=36))

def downgrade() -> None:
    with op.batch_alter_table("licenses") as batch_op:
        batch_op.alter_column("license_key",
                              existing_type=sa.String(length=36),
                              type_=sa.String(length=16))
