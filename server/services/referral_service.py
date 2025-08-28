"""Referral-related helpers using async SQLAlchemy sessions."""

from datetime import datetime
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.user import User
from server.models.license import License


async def get_referrals_and_bonus_days(
    db: AsyncSession, user: User
) -> Tuple[List[User], int]:
    """Return successful referrals and remaining bonus days for the user."""
    result = await db.execute(
        select(User).filter_by(referred_by_id=user.id, referral_bonus_claimed=True)
    )
    referrals = result.scalars().all()

    result = await db.execute(select(License).filter_by(user_id=user.id))
    license = result.scalars().first()
    days_left = 0
    if license and license.is_active and license.next_charge_at:
        # Use UTC to avoid timezone-related inconsistencies.
        days_left = max((license.next_charge_at - datetime.utcnow()).days, 0)

    return referrals, days_left
