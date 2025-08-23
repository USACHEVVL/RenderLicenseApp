from server.db.session import SessionLocal
from server.models import User, License

tg_id = "670562262"  # замените на нужный Telegram ID

db = SessionLocal()

user = db.query(User).filter_by(telegram_id=tg_id).first()

if not user:
    print("Пользователь не найден.")
else:
    # Удаляем лицензии
    deleted = 0
    for lic in db.query(License).filter_by(user_id=user.id).all():
        db.delete(lic)
        deleted += 1

    db.commit()
    print(f"Удалено лицензий: {deleted}")
