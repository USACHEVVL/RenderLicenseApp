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
    user = User(telegram_id="670562262", username="Usachev_LAB")
    session.add(user)
    session.commit()

    print("🔗 Привязываю лицензии...")
    licenses = [
        License(license_key=key, user_id=user.id)
        for key in ("abc123", "def456")
    ]
    session.add_all(licenses)
    session.commit()

    print("✅ База данных успешно заполнена.")
