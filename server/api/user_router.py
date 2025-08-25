from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from server.db.session import SessionLocal
from server.services import user_service

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
def register_user(telegram_id: int, db: Session = Depends(get_db)):
    """Register a new user by Telegram ID."""
    user = user_service.get_user_by_telegram_id(db, telegram_id)
    if user:
        return {"message": "👤 Пользователь уже существует", "id": user.id}

    new_user = user_service.create_user(db, telegram_id)
    return {"message": "✅ Пользователь зарегистрирован", "id": new_user.id}
