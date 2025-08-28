"""Populate the database with a test expired license asynchronously."""

import asyncio
import datetime
import uuid
from sqlalchemy import select

from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User


async def main() -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(User))
        user = result.scalars().first()
        if not user:
            user = User(telegram_id=999999)
            db.add(user)
            await db.commit()
            await db.refresh(user)

        key = str(uuid.uuid4())

        result = await db.execute(select(License).filter_by(user_id=user.id))
        expired_license = result.scalars().first()
        if expired_license:
            expired_license.license_key = key
            # Use UTC consistently with the application's time handling.
            expired_license.valid_until = datetime.datetime.utcnow() - datetime.timedelta(days=10)
        else:
            expired_license = License(
                user_id=user.id,
                license_key=key,
                # Maintain UTC for consistency across the codebase.
                valid_until=datetime.datetime.utcnow() - datetime.timedelta(days=10),
            )
            db.add(expired_license)
        await db.commit()

    print("✅ Добавлена просроченная лицензия.")


if __name__ == "__main__":
    asyncio.run(main())
