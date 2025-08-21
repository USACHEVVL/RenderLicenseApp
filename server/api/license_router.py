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
def create_license(telegram_id: str, machine_name: str, license_key: str, db: Session = Depends(get_db)):
    user = user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {"error": "Пользователь не найден"}

    license = license_service.create_license(db, license_key, machine_name, user)
    return {"message": "🔑 Лицензия создана", "license_id": license.id}

@router.get("/check_license")
def check_license(license_key: str, db: Session = Depends(get_db)):
    license = license_service.get_license_by_key(db, license_key)
    if license:
        return {"status": "✅ valid", "license_key": license.license_key, "machine_name": license.machine_name}
    return {"status": "❌ invalid"}
