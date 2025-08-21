import os
import asyncio
import hashlib
import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)

from server.db.session import SessionLocal
from server.models.user import User
from server.models.license import License
from server.models.machine import Machine

WAITING_FOR_MACHINE_NAME = 1

# Загрузка токена
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Стартовое меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Купить лицензию", callback_data='buy')],
        [InlineKeyboardButton("➕ Добавить машину", callback_data='add_machine')],
        [InlineKeyboardButton("🖥️ Список машин", callback_data='list_machines')],
        [InlineKeyboardButton("🔐 Мои лицензии", callback_data='license')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = update.message or update.callback_query.message
    await message.reply_text(
        "Привет! 👋 Это бот для управления лицензиями рендера.\n\nВыберите команду:",
        reply_markup=reply_markup
    )

# Обработка кнопок
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    command = query.data

    if command == 'buy':
        return await buy(update, context)
    elif command == 'add_machine':
        keyboard = [[InlineKeyboardButton("❌ Не добавлять", callback_data='cancel_add')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Введите название новой машины:", reply_markup=reply_markup)
        return WAITING_FOR_MACHINE_NAME
    elif command == 'list_machines':
        return await list_machines(update, context)
    elif command == 'license':
        return await license_command(update, context)
    else:
        await query.edit_message_text("Неизвестная команда.")

# Кнопка отмены добавления
async def cancel_add_machine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)  # Показать стартовое меню
    return ConversationHandler.END  # Завершить ожидание ввода

# Команда /buy
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.callback_query.message
    await message.reply_text("💳 Напишите админу @Usachev_LAB для покупки лицензии.")

# Команда /add_machine <имя>
async def add_machine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    tg_id = str(update.effective_user.id)
    message = update.message or update.callback_query.message

    if context.args:
        machine_name = " ".join(context.args)
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            user = User(telegram_id=tg_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        raw = f"{tg_id}-{machine_name}"
        license_key = hashlib.sha256(raw.encode()).hexdigest()[:16]

        license = License(
            user_id=user.id,
            license_key=license_key,
            valid_until=datetime.datetime.now() + datetime.timedelta(days=30)
        )
        db.add(license)
        db.commit()
        db.refresh(license)

        machine = Machine(
            user_id=user.id,
            license_id=license.id,
            name=machine_name
        )
        db.add(machine)
        db.commit()

        await message.reply_text(
            f"✅ Машина '{machine_name}' добавлена.\n"
            f"🔑 Лицензия:\n<code>{license_key}</code>",
            parse_mode="HTML"
        )
    else:
        await message.reply_text("❗ Используй: /add_machine <имя>")

    db.close()

# Обработка ручного ввода имени машины
async def handle_machine_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    tg_id = str(update.effective_user.id)
    machine_name = update.message.text

    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            user = User(telegram_id=tg_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        raw = f"{tg_id}-{machine_name}"
        license_key = hashlib.sha256(raw.encode()).hexdigest()[:16]

        license = License(
            user_id=user.id,
            license_key=license_key,
            valid_until=datetime.datetime.now() + datetime.timedelta(days=30)
        )
        db.add(license)
        db.commit()
        db.refresh(license)

        machine = Machine(
            user_id=user.id,
            license_id=license.id,
            name=machine_name
        )
        db.add(machine)
        db.commit()

        await update.message.reply_text(
            f"✅ Машина '{machine_name}' добавлена.\n"
            f"🔑 Лицензия:\n<code>{license_key}</code>",
            parse_mode="HTML"
        )
    finally:
        db.close()

    return ConversationHandler.END

# Команда /list_machines
async def list_machines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = str(update.effective_user.id)
    db = SessionLocal()
    message = update.message or update.callback_query.message

    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            await message.reply_text("📭 У вас нет добавленных машин.")
            return

        machines = db.query(Machine).filter_by(user_id=user.id).all()
        if machines:
            msg = "🖥️ Ваши машины:\n" + "\n".join(f"• {m.name}" for m in machines)
        else:
            msg = "📭 У вас нет добавленных машин."

        await message.reply_text(msg)
    finally:
        db.close()

# Команда /license
async def license_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = str(update.effective_user.id)
    db = SessionLocal()
    message = update.message or update.callback_query.message

    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            await message.reply_text("📭 У вас нет активных лицензий.")
            return

        licenses = db.query(License).filter_by(user_id=user.id).all()
        if licenses:
            message_lines = []
            for lic in licenses:
                machine = db.query(Machine).filter_by(license_id=lic.id).first()
                machine_name = machine.name if machine else "неизвестно"
                message_lines.append(f"{machine_name}: <code>{lic.license_key}</code>")
            text = "🔐 Ваши лицензии:\n" + "\n".join(message_lines)
        else:
            text = "📭 У вас нет активных лицензий."

        await message.reply_text(text, parse_mode="HTML")
    finally:
        db.close()

# Conversation handler
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_buttons)],
    states={
        WAITING_FOR_MACHINE_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_machine_name),
            CallbackQueryHandler(cancel_add_machine, pattern='^cancel_add$'),
        ]
    },
    fallbacks=[
        CommandHandler("start", start),
    ],
)


# Запуск бота
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("add_machine", add_machine))
    app.add_handler(CommandHandler("list_machines", list_machines))
    app.add_handler(CommandHandler("license", license_command))
    app.add_handler(conv_handler)

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ Бот запущен. Ожидает команды...")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
