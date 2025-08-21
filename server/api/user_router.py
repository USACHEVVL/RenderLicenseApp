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
def register_user(telegram_id: str, username: str, db: Session = Depends(get_db)):
    user = user_service.get_user_by_telegram_id(db, telegram_id)
    if user:
        return {"message": "👤 Пользователь уже существует"}
    
    new_user = user_service.create_user(db, telegram_id, username)
    return {"message": "✅ Пользователь зарегистрирован", "id": new_user.id}
