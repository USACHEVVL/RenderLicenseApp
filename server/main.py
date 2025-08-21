from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from telegram import Bot
from datetime import datetime

from server.admin.routes import admin_router
from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User


load_dotenv()
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TG_TOKEN)

app = FastAPI()

# Подключаем админский роутер
app.include_router(admin_router)

# Модель для рендера
class RenderData(BaseModel):
    license_key: str
    machine_name: str
    log: str

@app.post("/api/render_notify")
async def handle_render_notify(data: RenderData):
    db = SessionLocal()

    try:
        license = db.query(License).filter_by(license_key=data.license_key).first()
        if not license:
            raise HTTPException(status_code=401, detail="❌ Недействительный ключ")

        # Здесь предполагается, что у License есть поле machine_name — проверь это
        if hasattr(license, "machine_name") and license.machine_name != data.machine_name:
            raise HTTPException(status_code=403, detail="🚫 Машина не совпадает с лицензией")

        user = db.query(User).filter_by(id=license.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="👤 Пользователь не найден")
    finally:
        db.close()

    now = datetime.now()
    formatted = (
        f"🖥️ {data.machine_name} завершила рендер\n"
        f"🕒 Время: {now.strftime('%H:%M')}\n"
        f"📅 Дата: {now.strftime('%d.%m.%Y')}\n"
        f"📝 Лог: {data.log}"
    )

    await bot.send_message(chat_id=user.telegram_id, text=formatted)
    return {"status": "ok", "message": "Лог получен и отправлен в Telegram"}
