import os
import asyncio
import uuid
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
            [InlineKeyboardButton("👥 Пригласить друга", callback_data='invite_friend')],
        ])
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            user = User(telegram_id=tg_id, referral_code=str(uuid.uuid4()))
            db.add(user)
            db.commit()
        elif not user.referral_code:
            user.referral_code = str(uuid.uuid4())
            db.commit()
    finally:
        db.close()

    keyboard = [
        [InlineKeyboardButton("🔐 Лицензии", callback_data='licenses_menu')],
        [InlineKeyboardButton("👥 Пригласить друга", callback_data='invite_friend')],
    ]
    await (update.message or update.callback_query.message).reply_text(
        "Привет! 👋 Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_licenses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = update.effective_user.id
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        license = db.query(License).filter_by(user_id=user.id).first() if user else None

        if not license:
            msg = "📭 У вас нет активных лицензий."
            kb = [[InlineKeyboardButton("💳 Купить лицензию", callback_data='pay_license')]]
        else:
            now = datetime.datetime.now()
            is_valid = license.valid_until > now
            days_left = (license.valid_until - now).days
            status = f"{days_left} дн." if is_valid else "❌ Просрочена"

            msg_lines = ["🔐 Ваша лицензия:", f"<code>{license.license_key}</code> ({status})"]
            if not is_valid:
                msg_lines.append("\n⚠️ Лицензия просрочена. Продлите её, чтобы использовать.")
            msg = "\n".join(msg_lines)

            kb = [[InlineKeyboardButton("🔁 Продлить лицензию", callback_data=f"renew_{license.id}")]]

        kb.append([InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')])

        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    finally:
        db.close()


async def invite_friend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = update.effective_user.id
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if user and not user.referral_code:
            user.referral_code = str(uuid.uuid4())
            db.commit()
        elif not user:
            user = User(telegram_id=tg_id, referral_code=str(uuid.uuid4()))
            db.add(user)
            db.commit()
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={user.referral_code}"
    finally:
        db.close()

    await query.edit_message_text(
        f"👥 Поделитесь этой ссылкой, чтобы пригласить друга:\n{link}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
        ]),
    )


async def pay_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💳 Переведите 50₽ на номер +79538569110 (Сбербанк или Тинькофф).\n\n📤 После оплаты отправьте чек прямо в этот чат.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отменить оплату", callback_data='cancel_payment')]])
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
        user = db.query(User).filter_by(telegram_id=user_id).first()
        if not user:
            user = User(telegram_id=user_id)
            db.add(user)
            db.commit()
            db.refresh(user)

        license_key = str(uuid.uuid4())
        lic = db.query(License).filter_by(user_id=user.id).first()
        if lic:
            lic.license_key = license_key
            lic.valid_until = datetime.datetime.now() + datetime.timedelta(days=30)
        else:
            lic = License(
                user_id=user.id,
                license_key=license_key,
                valid_until=datetime.datetime.now() + datetime.timedelta(days=30),
            )
            db.add(lic)
        db.commit()
        await context.bot.send_message(
            chat_id=user_id,
            text=(f"✅ Оплата подтверждена. Ваша лицензия:\n<code>{license_key}</code>\n\n"
                 "Вы можете просмотреть её в разделе 🔐 <b>«Лицензии»</b>."),
            parse_mode="HTML")
        await send_main_menu(user_id, context)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Пользователь {user_id} получил свою лицензию"
        )
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
                chat_id=user.telegram_id,
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
    elif command == 'cancel_payment':
        query = update.callback_query
        await query.answer()
        context.user_data.pop('renew_license_id', None)
        await query.edit_message_text("❌ Оплата отменена.")
        await start(update, context)
        return ConversationHandler.END
    elif command.startswith('grant_license_'):
        return await grant_license(update, context)
    elif command.startswith('confirm_renew_'):
        return await confirm_renew(update, context)
    elif command.startswith("renew_"):
        return await handle_renew_license(update, context)
    elif command == 'invite_friend':
        return await invite_friend(update, context)

async def handle_renew_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    license_id = int(query.data.split("_")[1])
    context.user_data['renew_license_id'] = license_id

    await query.edit_message_text(
        "💳 Чтобы продлить лицензию, переведите 50₽ на номер +79538569110 (Сбербанк или Тинькофф).\n\n📤 После оплаты отправьте чек прямо в этот чат.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отменить оплату", callback_data='cancel_payment')]
        ])
    )
    return WAITING_FOR_PAYMENT_PROOF


conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_buttons)],
    states={
        WAITING_FOR_PAYMENT_PROOF: [
            CallbackQueryHandler(handle_buttons),
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
