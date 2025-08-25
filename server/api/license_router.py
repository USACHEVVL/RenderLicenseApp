from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from server.db.session import SessionLocal
from server.services import license_service, user_service

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/create_license")
def create_license(telegram_id: int, license_key: str, db: Session = Depends(get_db)):
    user = user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {"error": "Пользователь не найден"}

    license = license_service.create_license(db, license_key, user)
    return {"message": "🔑 Лицензия создана", "license_id": license.id}

@router.get("/check_license")
def check_license(license_key: str, db: Session = Depends(get_db)):
    license = license_service.get_license_by_key(db, license_key)
    if license and license.valid_until and license.valid_until > datetime.utcnow():
        days_left = (license.valid_until - datetime.utcnow()).days
        return {
            "status": "valid",
            "license_key": license.license_key,
            "valid": True,
            "days_left": days_left,
        }
    return {"status": "invalid", "valid": False}
