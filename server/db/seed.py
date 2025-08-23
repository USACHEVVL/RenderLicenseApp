from server.db.session import SessionLocal, SQLALCHEMY_DATABASE_URL
from server.models.user import User
from server.models.license import License

print(f"🗂 Используется база данных: {SQLALCHEMY_DATABASE_URL}")

# Очистка и добавление тестовых данных
session = SessionLocal()

print("🧹 Очищаю таблицы...")
session.query(License).delete()
session.query(User).delete()

print("➕ Добавляю пользователей...")
user = User(telegram_id="670562262", username="Usachev_LAB")
session.add(user)
session.commit()

print("🔗 Привязываю лицензии...")
license1 = License(license_key="abc123", user_id=user.id)
license2 = License(license_key="def456", user_id=user.id)

session.add_all([license1, license2])
session.commit()

print("✅ База данных успешно заполнена.")
session.close()
