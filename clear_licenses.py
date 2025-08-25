"""Utility script to remove all licenses for a Telegram user."""

from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User

TG_ID = 670562262  # замените на нужный Telegram ID

with SessionLocal() as db:
    user = db.query(User).filter_by(telegram_id=TG_ID).first()

    if not user:
        print("Пользователь не найден.")
    else:
        deleted = db.query(License).filter_by(user_id=user.id).delete()
        db.commit()
        print(f"Удалено лицензий: {deleted}")
