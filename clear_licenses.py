"""Utility script to remove all licenses for a Telegram user asynchronously."""

import asyncio
from sqlalchemy import delete, select

from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User

TG_ID = 670562262  # замените на нужный Telegram ID


async def main() -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter_by(telegram_id=TG_ID))
        user = result.scalars().first()

        if not user:
            print("Пользователь не найден.")
        else:
            result = await db.execute(delete(License).filter_by(user_id=user.id))
            await db.commit()
            print(f"Удалено лицензий: {result.rowcount}")


if __name__ == "__main__":
    asyncio.run(main())
