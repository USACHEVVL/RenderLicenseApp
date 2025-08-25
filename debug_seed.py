# debug_seed.py
from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User
import datetime
import uuid

db = SessionLocal()

# Найдём первого пользователя или создадим тестового
user = db.query(User).first()
if not user:
    user = User(telegram_id=999999)
    db.add(user)
    db.commit()
    db.refresh(user)

# Генерируем ключ
key = str(uuid.uuid4())

# Создаём или обновляем лицензию с истёкшим сроком
expired_license = db.query(License).filter_by(user_id=user.id).first()
if expired_license:
    expired_license.license_key = key
    expired_license.valid_until = datetime.datetime.now() - datetime.timedelta(days=10)
else:
    expired_license = License(
        user_id=user.id,
        license_key=key,
        valid_until=datetime.datetime.now() - datetime.timedelta(days=10),
    )
    db.add(expired_license)
db.commit()
db.close()

print("✅ Добавлена просроченная лицензия.")
