# debug_seed.py
from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User
import datetime
import hashlib

db = SessionLocal()

# Найдём первого пользователя или создадим тестового
user = db.query(User).first()
if not user:
    user = User(telegram_id="999999")
    db.add(user)
    db.commit()
    db.refresh(user)

# Генерируем ключ
key = hashlib.sha256(f"{user.telegram_id}-expired".encode()).hexdigest()[:16]

# Создаём лицензию с истёкшим сроком
expired_license = License(
    user_id=user.id,
    license_key=key,
    valid_until=datetime.datetime.now() - datetime.timedelta(days=10)
)

db.add(expired_license)
db.commit()
db.close()

print("✅ Добавлена просроченная лицензия.")
