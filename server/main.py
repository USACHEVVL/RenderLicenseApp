from fastapi import FastAPI
from pydantic import BaseModel
import os
import logging
from dotenv import load_dotenv
from telegram import Bot
from telegram_bot.bot import ADMIN_ID

from server.admin.routes import admin_router
from server.api import license_router
from server.api.user_router import router as user_router
from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User


load_dotenv()
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = None
if not TG_TOKEN:
    logging.warning(
        "TELEGRAM_BOT_TOKEN is not set; Telegram bot initialization skipped."
    )
else:
    bot = Bot(token=TG_TOKEN)

app = FastAPI()

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

    Если по переданному ключу найден владелец лицензии, сообщение отправляется
    ему. В противном случае пользователю отправляется уведомление о
    приостановке лицензии. Проверка лицензии не блокирует отправку
    уведомления, что позволяет диагностировать проблемы отдельно от механизма
    лицензирования.
    """

    db = SessionLocal()
    user_chat_id = None

    try:
        license = db.query(License).filter_by(license_key=data.license_key).first()
        if license:
            user = db.query(User).filter_by(id=license.user_id).first()
            if user:
                user_chat_id = user.telegram_id
    finally:
        db.close()

    formatted = data.log

    # Отправляем лог владельцу лицензии; при отсутствии владельца
    # уведомляем о приостановке
    if bot:
        if user_chat_id:
            await bot.send_message(chat_id=user_chat_id, text=formatted)
        else:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text="Лицензия приостановлена. Пожалуйста, продлите лицензию",
            )
    else:
        logging.warning(
            "Bot is not initialized; render notification not sent."
        )

    return {"status": "ok", "message": "Лог получен и отправлен в Telegram"}
