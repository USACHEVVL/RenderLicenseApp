"""Populate the database with demo users and licenses asynchronously."""

import asyncio
from sqlalchemy import delete

from server.db.session import DATABASE_URL, SessionLocal
from server.models.license import License
from server.models.user import User

print(f"🗂 Используется база данных: {DATABASE_URL}")


async def main() -> None:
    async with SessionLocal() as session:
        print("🧹 Очищаю таблицы...")
        await session.execute(delete(License))
        await session.execute(delete(User))

        print("➕ Добавляю пользователей...")
        user = User(telegram_id=670562262)
        session.add(user)
        await session.commit()

        print("🔗 Привязываю лицензию...")
        license = License(license_key="abc123", user_id=user.id)
        session.add(license)
        await session.commit()

        print("✅ База данных успешно заполнена.")


if __name__ == "__main__":
    asyncio.run(main())
