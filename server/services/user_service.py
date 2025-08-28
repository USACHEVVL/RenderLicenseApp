"""Utility functions for working with :class:`User` via ``AsyncSession``."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models.user import User


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int):
    result = await db.execute(select(User).filter_by(telegram_id=telegram_id))
    return result.scalars().first()


async def create_user(db: AsyncSession, telegram_id: int):
    """Create a new user without relying on a username field."""
    user = User(telegram_id=telegram_id)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
