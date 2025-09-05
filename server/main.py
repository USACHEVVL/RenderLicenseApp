from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from telegram_bot.notify import send_telegram_message

from server.admin.routes import admin_router
from server.api import license_router
from server.api.user_router import router as user_router
from server.db.session import SessionLocal
from server.models.license import License
from sqlalchemy import select
from sqlalchemy.orm import selectinload

load_dotenv()
app = FastAPI()

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
    """Получает лог рендера и отправляет его в Telegram."""
    logging.info(">>> Получен render_notify: license_key=%s, log=%s", data.license_key, data.log)

    user_chat_id = None
    user_id = None

    async with SessionLocal() as db:
        result = await db.execute(
            select(License)
            .options(selectinload(License.user))
            .filter_by(license_key=data.license_key)
        )
        license = result.scalars().first()
        now = datetime.utcnow()
        if not license:
            logging.warning("License not found for key %s", data.license_key)
        elif (
            license.is_active
            and license.next_charge_at
            and license.next_charge_at > now
        ):
            user_id = license.user_id
            user = license.user
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

    if user_chat_id:
        await send_telegram_message(chat_id=user_chat_id, text=formatted)
    else:
        logging.info(
            "Telegram message not sent: license_key=%s user_id=%s (chat_id missing)",
            data.license_key,
            user_id,
        )

    return {"status": "ok"}
