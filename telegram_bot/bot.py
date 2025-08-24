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

WAITING_FOR_PAYMENT_PROOF = 1

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 670562262

async def send_main_menu(user_id, context):
    await context.bot.send_message(
        chat_id=user_id,
        text="Привет! 👋 Выберите действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Лицензии", callback_data='licenses_menu')],
        ])
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔐 Лицензии", callback_data='licenses_menu')],
    ]
    await (update.message or update.callback_query.message).reply_text(
        "Привет! 👋 Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_licenses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = str(update.effective_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        licenses = db.query(License).filter_by(user_id=user.id).all() if user else []
        kb = []

        if not licenses:
            msg = "📭 У вас нет активных лицензий."
        else:
            active_licenses = []
            expired_licenses = []
            msg_lines = ["🔐 Ваши лицензии:"]

            now = datetime.datetime.now()

            for lic in licenses:
                is_valid = lic.valid_until > now
                days_left = (lic.valid_until - now).days
                status = f"{days_left} дн." if is_valid else "❌ Просрочена"

                msg_lines.append(f"<code>{lic.license_key}</code> ({status})")

                row = [InlineKeyboardButton("🔁 Продлить" if is_valid else "♻️ Продлить", callback_data=f"renew_{lic.id}")]
                kb.append(row)

                (active_licenses if is_valid else expired_licenses).append(lic)

            if len(expired_licenses) == len(licenses):
                msg_lines.append("\n⚠️ Все лицензии просрочены. Продлите их, чтобы использовать.")

            msg = "\n".join(msg_lines)

        kb.extend([
            [InlineKeyboardButton("💳 Купить лицензию", callback_data='pay_license')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')],
        ])

        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    finally:
        db.close()


async def pay_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💳 Переведите 50₽ на номер +79538569110 (Сбербанк или Тинькофф).\n\n📤 После оплаты отправьте чек прямо в этот чат.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='licenses_menu')]])
    )
    return WAITING_FOR_PAYMENT_PROOF

async def handle_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_renewal = 'renew_license_id' in context.user_data
    admin_msg = (
        f"🧾 Новый платёж {'(продление)' if is_renewal else ''}\n"
        f"От: {user.full_name or 'неизвестно'} (id: {user.id})"
    )

    button_callback = (
        f'confirm_renew_{context.user_data["renew_license_id"]}'
        if is_renewal else
        f'grant_license_{user.id}'
    )

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data=button_callback)]
    ])

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=admin_msg, reply_markup=reply_markup)
    elif update.message.document:
        file_id = update.message.document.file_id
        await context.bot.send_document(chat_id=ADMIN_ID, document=file_id, caption=admin_msg, reply_markup=reply_markup)
    elif update.message.text:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg + f"\n\n{update.message.text}", reply_markup=reply_markup)

    await update.message.reply_text("📩 Чек получен. Ожидайте подтверждения администратора.")
    return ConversationHandler.END

async def grant_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[-1])
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=str(user_id)).first()
        if not user:
            user = User(telegram_id=str(user_id))
            db.add(user)
            db.commit()
            db.refresh(user)

        license_key = hashlib.sha256(f"{user_id}-{datetime.datetime.now()}".encode()).hexdigest()[:16]
        lic = License(user_id=user.id, license_key=license_key, valid_until=datetime.datetime.now() + datetime.timedelta(days=30))
        db.add(lic)
        db.commit()
        await context.bot.send_message(
            chat_id=user_id,
            text=(f"✅ Оплата подтверждена. Ваша лицензия:\n<code>{license_key}</code>\n\n"
                 "Вы можете просмотреть её в разделе 🔐 <b>«Лицензии»</b>."),
            parse_mode="HTML")
        await send_main_menu(user_id, context)
        await query.edit_message_text("✅ Лицензия выдана.")
    finally:
        db.close()

async def confirm_renew(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    license_id = int(query.data.split("_")[-1])

    db = SessionLocal()
    try:
        lic = db.query(License).filter_by(id=license_id).first()
        if not lic:
            await query.edit_message_text("❗ Лицензия не найдена.")
            return

        # Продлеваем лицензию
        now = datetime.datetime.now()
        lic.valid_until = max(lic.valid_until, now) + datetime.timedelta(days=30)
        db.commit()

        # Получаем пользователя
        user = db.query(User).filter_by(id=lic.user_id).first()
        if user:
            await context.bot.send_message(
                chat_id=int(user.telegram_id),
                text=f"✅ Лицензия <code>{lic.license_key}</code> успешно продлена на 30 дней.",
                parse_mode="HTML"
            )

        await query.edit_message_text("✅ Продление подтверждено.")

    finally:
        db.close()

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.callback_query.data
    if command == 'licenses_menu':
        return await show_licenses_menu(update, context)
    elif command == 'back_to_main':
        return await start(update, context)
    elif command == 'pay_license':
        return await pay_license(update, context)
    elif command.startswith('grant_license_'):
        return await grant_license(update, context)
    elif command.startswith('confirm_renew_'):
        return await confirm_renew(update, context)
    elif command.startswith("renew_"):
        return await handle_renew_license(update, context)

async def handle_renew_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    license_id = int(query.data.split("_")[1])
    context.user_data['renew_license_id'] = license_id

    await query.edit_message_text(
        "💳 Чтобы продлить лицензию, переведите 50₽ на номер +79538569110 (Сбербанк или Тинькофф).\n\n📤 После оплаты отправьте чек прямо в этот чат.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data='licenses_menu')]
        ])
    )
    return WAITING_FOR_PAYMENT_PROOF


conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_buttons)],
    states={
        WAITING_FOR_PAYMENT_PROOF: [
            MessageHandler(filters.ALL, handle_payment_proof),
        ],
    },
    fallbacks=[CommandHandler("start", start)],
)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ Бот запущен. Ожидает команды...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
