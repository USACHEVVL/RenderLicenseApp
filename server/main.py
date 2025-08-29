from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot

from server.admin.routes import admin_router
from server.api import license_router
from server.api.user_router import router as user_router
from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User
from sqlalchemy import select


load_dotenv()
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TG_TOKEN:
    logging.critical("TELEGRAM_BOT_TOKEN is not set; aborting startup")
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")

bot = Bot(token=TG_TOKEN)
app = FastAPI()


@app.on_event("startup")
async def startup_event():
    await bot.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    await bot.shutdown()

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Подключаем админский роутер
app.include_router(admin_router)
app.include_router(license_router.router, prefix="/api")
app.include_router(user_router, prefix="/api")

# Модель для рендера
class RenderData(BaseModel):
    license_key: str
    log: str

@app.post("/api/render_notify")
async def handle_render_notify(data: RenderData):
    """Получает лог рендера и отправляет его в Telegram.

    Если по переданному ключу найден владелец активной лицензии, сообщение
    отправляется ему. В противном случае отправка пропускается. Проверка
    лицензии не блокирует отправку уведомления, что позволяет диагностировать
    проблемы отдельно от механизма лицензирования.
    """

    user_chat_id = None
    user_id = None

    async with SessionLocal() as db:
        result = await db.execute(
            select(License).filter_by(license_key=data.license_key)
        )
        license = result.scalars().first()
        if not license:
            logging.warning(
                "License not found for key %s", data.license_key
            )
        elif (
            license.is_active
            and license.next_charge_at
            and license.next_charge_at > datetime.utcnow()
        ):
            user_id = license.user_id
            result = await db.execute(select(User).filter_by(id=user_id))
            user = result.scalars().first()
            if not user:
                logging.warning(
                    "User %s not found for license %s",
                    user_id,
                    data.license_key,
                )
            elif not user.telegram_id:
                logging.info(
                    "Missing telegram_id for user %s and license %s",
                    user.id,
                    data.license_key,
                )
            else:
                user_chat_id = user.telegram_id
        else:
            logging.info(
                "Inactive license for key %s; skipping notification",
                data.license_key,
            )

    formatted = data.log

    # Отправляем лог владельцу лицензии только при активной лицензии и наличии chat_id
    if bot and user_chat_id:
        try:
            await bot.send_message(chat_id=user_chat_id, text=formatted)
        except Exception:
            logging.exception("Failed to send Telegram message")
    elif bot:
        logging.info(
            "Telegram message skipped: license_key=%s user_id=%s",
            data.license_key,
            user_id,
        )
    else:
        logging.warning(
            "Bot is not initialized; render notification not sent."
        )

    return {"status": "ok"}
