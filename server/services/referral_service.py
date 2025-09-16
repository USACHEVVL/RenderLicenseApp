"""Referral-related helpers using async SQLAlchemy sessions."""

from datetime import datetime, timedelta
from typing import List, Tuple

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.user import User
from server.models.license import License

# Количество бонусных дней за одного приглашённого
BONUS_DAYS_PER_REFERRAL = 7


async def get_referrals_and_bonus_days(
    db: AsyncSession, user: User
) -> Tuple[List[User], int, int]:
    """Return successful referrals, available bonus days and total bonus days accrued."""
    result = await db.execute(
        select(User).filter_by(referred_by_id=user.id, referral_bonus_claimed=True)
    )
    referrals = result.scalars().all()

    # Определяем количество приглашённых, оплативших подписку,
    # но за которых ещё не получены бонусы
    result = await db.execute(
        select(User).filter_by(referred_by_id=user.id, referral_bonus_claimed=False)
    )
    candidates = result.scalars().all()
    unclaimed_referrals = 0
    for cand in candidates:
        result_lic = await db.execute(select(License).filter_by(user_id=cand.id, is_active=True))
        if result_lic.scalars().first():
            unclaimed_referrals += 1

    bonus_days_available = unclaimed_referrals * BONUS_DAYS_PER_REFERRAL
    total_bonus_days = len(referrals) * BONUS_DAYS_PER_REFERRAL

    return referrals, bonus_days_available, total_bonus_days


async def claim_referral_bonuses(
    db: AsyncSession, user: User, days_per_referral: int = BONUS_DAYS_PER_REFERRAL
) -> int:
    """Mark eligible referrals as claimed and add bonus days to user's license.

    Returns the number of referrals processed.
    """
    result = await db.execute(
        select(User).filter_by(referred_by_id=user.id, referral_bonus_claimed=False)
    )
    candidates = result.scalars().all()

    eligible = []
    for cand in candidates:
        result_lic = await db.execute(select(License).filter_by(user_id=cand.id, is_active=True))
        if result_lic.scalars().first():
            eligible.append(cand)

    if not eligible:
        return 0

    for cand in eligible:
        cand.referral_bonus_claimed = True

    total_days = days_per_referral * len(eligible)
    now = datetime.utcnow()

    result = await db.execute(select(License).filter_by(user_id=user.id))
    lic = result.scalars().first()
    if lic:
        base = lic.valid_until or now
        new_until = max(base, now) + timedelta(days=total_days)
        lic.valid_until = new_until
        lic.next_charge_at = new_until
        lic.is_active = True
    else:
        until = now + timedelta(days=total_days)
        lic = License(
            user_id=user.id,
            license_key=str(uuid.uuid4()),
            is_active=True,
            valid_until=until,
            next_charge_at=until,
        )
        db.add(lic)

    await db.commit()
    return len(eligible)
