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
WAITING_FOR_MACHINE_TO_DELETE = 2
WAITING_FOR_PAYMENT_PROOF = 3
WAITING_FOR_MACHINE_TO_ATTACH = 4
WAITING_FOR_PAYMENT_PROOF_RENEW = 5

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 670562262

async def cleanup_expired_licenses():
    db = SessionLocal()
    try:
        now = datetime.datetime.now()
        expired_machines = db.query(Machine).join(License).filter(
            Machine.license_id == License.id,
            License.valid_until < now
        ).all()

        for machine in expired_machines:
            machine.license_id = None

        db.commit()
        print(f"🧹 Очистка завершена. Отвязано {len(expired_machines)} машин с просроченными лицензиями.")
    finally:
        db.close()

async def send_main_menu(user_id, context):
    await context.bot.send_message(
        chat_id=user_id,
        text="Привет! 👋 Выберите раздел:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🖥️ Машины", callback_data='machines_menu')],
            [InlineKeyboardButton("🔐 Лицензии", callback_data='licenses_menu')],
        ])
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🖥️ Машины", callback_data='machines_menu')],
        [InlineKeyboardButton("🔐 Лицензии", callback_data='licenses_menu')],
    ]
    await (update.message or update.callback_query.message).reply_text("Привет! 👋 Выберите раздел:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_machines_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = str(update.effective_user.id)
    db = SessionLocal()

    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        machines = db.query(Machine).filter_by(user_id=user.id).all() if user else []

        msg_lines = ["🖥️ Ваши машины:"] if machines else []
        now = datetime.datetime.now()

        for m in machines:
            license = db.query(License).filter_by(id=m.license_id).first() if m.license_id else None

            if license and license.valid_until < now:
                # Удаляем привязку
                m.license_id = None
                db.commit()
                license = None  # обнуляем переменную для корректного отображения

            if license:
                msg_lines.append(f"• {m.name} — 🔑 {license.license_key}")
            else:
                msg_lines.append(f"• {m.name} — ❌ Без лицензии")

        msg = "\n".join(msg_lines) if machines else "📭 У вас нет машин."

        kb = [
            [InlineKeyboardButton("➕ Добавить машину", callback_data='add_machine')],
            [InlineKeyboardButton("🗑 Удалить машину", callback_data='delete_machine')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')],
        ]

        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb))

    finally:
        db.close()

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
                machine = db.query(Machine).filter_by(license_id=lic.id).first()
                is_valid = lic.valid_until > now

                # Автоотвязка, если лицензия просрочена
                if machine and not is_valid:
                    machine.license_id = None
                    db.commit()
                    machine = None  # для отображения "неизвестно"

                name = machine.name if machine else "неизвестно"
                days_left = (lic.valid_until - now).days
                status = f"{days_left} дн." if is_valid else "❌ Просрочена"

                msg_lines.append(f"{name}: <code>{lic.license_key}</code> ({status})")

                row = []
                if not machine and is_valid:
                    row.append(InlineKeyboardButton("🔗 Привязать", callback_data=f"attach_{lic.id}"))
                row.append(InlineKeyboardButton("🔁 Продлить" if is_valid else "♻️ Продлить", callback_data=f"renew_{lic.id}"))
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


async def attach_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    license_id = int(query.data.split('_')[1])
    context.user_data['attach_license_id'] = license_id
    tg_id = str(update.effective_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        machines = db.query(Machine).filter_by(user_id=user.id, license_id=None).all()
        if not machines:
            await query.edit_message_text("У вас нет машин без лицензии.")
            return ConversationHandler.END
        keyboard = [[InlineKeyboardButton(m.name, callback_data=f"attach_to_{m.id}")] for m in machines]
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="licenses_menu")])
        await query.edit_message_text("Выберите машину для привязки лицензии:", reply_markup=InlineKeyboardMarkup(keyboard))
        return WAITING_FOR_MACHINE_TO_ATTACH
    finally:
        db.close()

async def attach_license_to_machine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    machine_id = int(query.data.split('_')[-1])
    license_id = context.user_data.get('attach_license_id')

    if not license_id:
        await query.edit_message_text("Произошла ошибка: лицензия не найдена.")
        return ConversationHandler.END

    db = SessionLocal()
    try:
        machine = db.query(Machine).filter_by(id=machine_id).first()
        license = db.query(License).filter_by(id=license_id).first()

        if not machine:
            await query.edit_message_text("Машина не найдена.")
            return ConversationHandler.END

        if not license:
            await query.edit_message_text("❗ Лицензия не найдена.")
            return ConversationHandler.END

        if license.valid_until < datetime.datetime.now():
            await query.edit_message_text("❗ Лицензия просрочена и не может быть привязана.")
            return ConversationHandler.END

        machine.license_id = license_id
        db.commit()

        await query.edit_message_text("✅ Лицензия успешно привязана к машине.")
        await start(update, context)

    finally:
        db.close()

    return ConversationHandler.END

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
    admin_msg = f"🧾 Новый платёж {'(продление)' if is_renewal else ''}\nОт: @{user.username or 'неизвестно'} (id: {user.id})"

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
          "Теперь можете привязать лицензию к любой машине в разделе 🔐 <b>«Лицензии»</b>."),
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
    if command == 'machines_menu': 
        return await show_machines_menu(update, context)
    elif command == 'licenses_menu': 
        return await show_licenses_menu(update, context)
    elif command == 'renew_license': 
        return await update.callback_query.edit_message_text("🔁 Продление лицензии в разработке.")
    elif command == 'back_to_main': 
        return await start(update, context)
    elif command == 'add_machine':
        await update.callback_query.edit_message_text("Введите название новой машины:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Не добавлять", callback_data='cancel_add')]]))
        return WAITING_FOR_MACHINE_NAME
    elif command == 'delete_machine': 
        return await handle_delete_machine(update, context)
    elif command.startswith("delete_"): 
        return await confirm_delete_machine(update, context)
    elif command == 'cancel_delete': 
        return await cancel_delete_machine(update, context)
    elif command == 'cancel_add': 
        return await cancel_add_machine(update, context)
    elif command == 'pay_license': 
        return await pay_license(update, context)
    elif command.startswith('grant_license_'): 
        return await grant_license(update, context)
    elif command.startswith('confirm_renew_'):
        return await confirm_renew(update, context)
    elif command.startswith("attach_") and not command.startswith("attach_to_"):
        return await attach_license(update, context)
    elif command.startswith("attach_to_"):
        return await attach_license_to_machine(update, context)
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

async def handle_machine_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        tg_id = str(update.effective_user.id)
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            user = User(telegram_id=tg_id)
            db.add(user)
            db.commit()
            db.refresh(user)
        machine = Machine(user_id=user.id, name=update.message.text)
        db.add(machine)
        db.commit()
        await update.message.reply_text(f"✅ Машина '{machine.name}' добавлена.")
        await start(update, context)
    finally:
        db.close()
    return ConversationHandler.END

async def handle_delete_machine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = str(update.effective_user.id)
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        machines = db.query(Machine).filter_by(user_id=user.id).all() if user else []
        if not machines:
            await query.edit_message_text("📭 У вас нет машин для удаления.")
            return ConversationHandler.END
        keyboard = [[InlineKeyboardButton(m.name, callback_data=f"delete_{m.id}")] for m in machines]
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete")])
        await query.edit_message_text("Выберите машину для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
        return WAITING_FOR_MACHINE_TO_DELETE
    finally:
        db.close()

async def confirm_delete_machine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = SessionLocal()

    try:
        m_id = int(query.data.replace("delete_", ""))
        machine = db.query(Machine).filter_by(id=m_id).first()

        if not machine:
            await query.edit_message_text("❗ Машина не найдена.")
            return ConversationHandler.END

        # Если к машине привязана лицензия — проверим её актуальность
        if machine.license_id:
            license = db.query(License).filter_by(id=machine.license_id).first()
            if license and license.valid_until > datetime.datetime.now():
                await query.edit_message_text(
                    "⚠️ Нельзя удалить машину с активной лицензией.\n"
                    "Сначала отвяжите лицензию или дождитесь окончания её срока."
                )
                return ConversationHandler.END

        # Отвязываем просроченную лицензию (или если её уже нет)
        machine.license_id = None

        # Удаляем машину
        db.delete(machine)
        db.commit()

        await query.edit_message_text(f"🗑 Машина '{machine.name}' удалена.")
        await start(update, context)

    finally:
        db.close()

    return ConversationHandler.END

async def cancel_add_machine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await send_main_menu(update.effective_user.id, context)
    return ConversationHandler.END

async def cancel_delete_machine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await send_main_menu(update.effective_user.id, context)
    return ConversationHandler.END

conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_buttons)],
    states={
        WAITING_FOR_MACHINE_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_machine_name),
            CallbackQueryHandler(cancel_add_machine, pattern='^cancel_add$'),
        ],
        WAITING_FOR_MACHINE_TO_DELETE: [
            CallbackQueryHandler(confirm_delete_machine, pattern='^delete_'),
            CallbackQueryHandler(cancel_delete_machine, pattern='^cancel_delete$'),
        ],
        WAITING_FOR_PAYMENT_PROOF: [
            MessageHandler(filters.ALL, handle_payment_proof),
        ],
        WAITING_FOR_MACHINE_TO_ATTACH: [
    CallbackQueryHandler(attach_license_to_machine, pattern='^attach_to_'),
    ],

    },
    fallbacks=[CommandHandler("start", start)],
)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    await cleanup_expired_licenses()  # 👈 ВАЖНО: вызвать до запуска

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ Бот запущен. Ожидает команды...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
