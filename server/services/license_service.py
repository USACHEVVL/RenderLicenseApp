"""Operations for managing :class:`License` records asynchronously."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.license import License
from server.models.user import User


async def create_license(
    db: AsyncSession, license_key: str, user: User, next_charge_at=None
):
    result = await db.execute(select(License).filter_by(user_id=user.id))
    license = result.scalars().first()
    if license:
        license.license_key = license_key
        if next_charge_at is not None:
            license.next_charge_at = next_charge_at
            license.valid_until = next_charge_at
            license.is_active = True
    else:
        license = License(
            license_key=license_key,
            user_id=user.id,
            next_charge_at=next_charge_at,
            valid_until=next_charge_at,
            is_active=True,
        )
        db.add(license)
    await db.commit()
    await db.refresh(license)
    return license


async def get_license_by_key(db: AsyncSession, license_key: str):
    result = await db.execute(select(License).filter(License.license_key == license_key))
    return result.scalars().first()
