import os
import logging
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()
TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("BOT_TOKEN")
    or os.getenv("TOKEN")
)

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не найден в .env или переменных окружения")


async def send_telegram_message(chat_id: int, text: str):
    """Отправка сообщения в Telegram пользователю с заданным chat_id."""
    try:
        bot = Bot(token=TOKEN)
        logging.info(f"Отправка сообщения в Telegram: chat_id={chat_id}, text={text}")
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception:
        logging.exception(f"Ошибка при отправке Telegram-сообщения для chat_id={chat_id}")
