"""add referral fields to users

Revision ID: d7c2e2f3a1b4
Revises: 9b8b5a76b3e4
Create Date: 2025-10-09 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7c2e2f3a1b4"
down_revision: Union[str, Sequence[str], None] = "9b8b5a76b3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("referral_code", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("referred_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "referral_bonus_claimed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.create_unique_constraint(
            "uq_users_referral_code", ["referral_code"]
        )
        batch_op.create_foreign_key(
            "fk_users_referred_by_id_users",
            "users",
            ["referred_by_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_users_referred_by_id_users", type_="foreignkey"
        )
        batch_op.drop_constraint("uq_users_referral_code", type_="unique")
        batch_op.drop_column("referral_bonus_claimed")
        batch_op.drop_column("referred_by_id")
        batch_op.drop_column("referral_code")

