from datetime import datetime
from typing import List, Tuple

from sqlalchemy.orm import Session

from server.models.user import User
from server.models.license import License


def get_referrals_and_bonus_days(db: Session, user: User) -> Tuple[List[User], int]:
    """Return successful referrals and remaining bonus days for the user."""
    referrals = db.query(User).filter_by(
        referred_by_id=user.id, referral_bonus_claimed=True
    ).all()

    license = db.query(License).filter_by(user_id=user.id).first()
    days_left = 0
    if license and license.valid_until:
        days_left = max((license.valid_until - datetime.now()).days, 0)

    return referrals, days_left
