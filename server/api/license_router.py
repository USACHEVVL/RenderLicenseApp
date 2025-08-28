from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import SessionLocal
from server.services import license_service, user_service

router = APIRouter()


async def get_db():
    async with SessionLocal() as db:
        yield db


@router.post("/create_license")
async def create_license(
    telegram_id: int, license_key: str, db: AsyncSession = Depends(get_db)
):
    user = await user_service.get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {"error": "Пользователь не найден"}

    license = await license_service.create_license(db, license_key, user)
    return {"message": "🔑 Лицензия создана", "license_id": license.id}


@router.get("/check_license")
async def check_license(license_key: str, db: AsyncSession = Depends(get_db)):
    license = await license_service.get_license_by_key(db, license_key)
    if license is None:
        return {"status": "not_found", "valid": False}
    if not license.is_active or (
        license.next_charge_at and license.next_charge_at <= datetime.utcnow()
    ):
        return {"status": "inactive", "valid": False}
    days_left = 0
    if license.next_charge_at:
        days_left = (license.next_charge_at - datetime.utcnow()).days
    return {
        "status": "active",
        "valid": True,
        "user_id": license.user.telegram_id,
        "days_left": days_left,
    }
