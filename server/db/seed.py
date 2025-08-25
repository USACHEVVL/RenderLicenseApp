"""Populate the database with demo users and licenses."""

from server.db.session import SQLALCHEMY_DATABASE_URL, SessionLocal
from server.models.license import License
from server.models.user import User

print(f"🗂 Используется база данных: {SQLALCHEMY_DATABASE_URL}")

with SessionLocal() as session:
    print("🧹 Очищаю таблицы...")
    session.query(License).delete()
    session.query(User).delete()

    print("➕ Добавляю пользователей...")
    user = User(telegram_id=670562262)
    session.add(user)
    session.commit()

    print("🔗 Привязываю лицензию...")
    license = License(license_key="abc123", user_id=user.id)
    session.add(license)
    session.commit()

    print("✅ База данных успешно заполнена.")
