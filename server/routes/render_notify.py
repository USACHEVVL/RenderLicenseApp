from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from telegram import Bot
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
router = APIRouter()

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TG_TOKEN)

# Временное хранилище лицензий (заменим позже на базу)
license_registry = {
    "abc123": {"machine": "HomePC", "tg_id": "670562262"},
    "def456": {"machine": "RenderBox", "tg_id": "670562262"},
}

class RenderData(BaseModel):
    license_key: str
    machine_name: str
    log: str

@router.post("/api/render_notify")
async def render_notify(data: RenderData):
    record = license_registry.get(data.license_key)

    if not record:
        raise HTTPException(status_code=401, detail="❌ Недействительный ключ")

    if record["machine"] != data.machine_name:
        raise HTTPException(status_code=403, detail="🚫 Машина не соответствует лицензии")

    now = datetime.now()
    formatted = (
        f"🖥️ {data.machine_name} завершила рендер\n"
        f"🕒 Время: {now.strftime('%H:%M')}\n"
        f"📅 Дата: {now.strftime('%d.%m.%Y')}\n"
        f"📝 Лог: {data.log}"
    )

    await bot.send_message(chat_id=record["tg_id"], text=formatted)
    return {"status": "ok", "message": "Лог получен и отправлен в Telegram"}
