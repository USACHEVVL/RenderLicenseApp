from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import SessionLocal
from server.services import user_service

router = APIRouter()


async def get_db():
    async with SessionLocal() as db:
        yield db


@router.post("/register")
async def register_user(
    telegram_id: int, db: AsyncSession = Depends(get_db)
):
    """Register a new user by Telegram ID."""
    user = await user_service.get_user_by_telegram_id(db, telegram_id)
    if user:
        return {"message": "👤 Пользователь уже существует", "id": user.id}

    new_user = await user_service.create_user(db, telegram_id)
    return {"message": "✅ Пользователь зарегистрирован", "id": new_user.id}
