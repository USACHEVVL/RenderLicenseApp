import os
import asyncio
import uuid
import datetime
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from server.db.session import SessionLocal
from server.models.user import User
from server.models.license import License
from server.services.referral_service import get_referrals_and_bonus_days


load_dotenv()


def _load_bot_token() -> str:
    """Load and validate Telegram bot token from environment or .env.

    Looks for TELEGRAM_BOT_TOKEN, BOT_TOKEN, or TOKEN. Strips quotes/spaces
    and validates basic format before building the Application.
    """
    token = (
        os.getenv("TELEGRAM_BOT_TOKEN")
        or os.getenv("BOT_TOKEN")
        or os.getenv("TOKEN")
    )
    if token:
        token = token.strip().strip("'\"")

    if not token:
        raise RuntimeError(
            "Не найден токен бота. Задайте переменную окружения TELEGRAM_BOT_TOKEN "
            "или создайте файл .env с TELEGRAM_BOT_TOKEN=123456789:ABCDEF..."
        )

    # Бот-токен от BotFather имеет вид '<digits>:<rest>'
    if ":" not in token:
        raise RuntimeError(
            "Неверный формат TELEGRAM_BOT_TOKEN. Проверьте токен от @BotFather без кавычек."
        )
    return token


TOKEN = _load_bot_token()
ADMIN_ID = 670562262


async def send_main_menu(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🎫 Подписка/Лицензия", callback_data="licenses_menu")],
        [InlineKeyboardButton("👥 Пригласить друга", callback_data="invite_friend")],
        [InlineKeyboardButton("📊 Реферальная статистика", callback_data="referral_stats")],
    ]

    # Пытаемся отправить логотип, если есть локальный файл
    logo_path = (Path(__file__).resolve().parent / "assets" / "logo.png")
    if logo_path.exists():
        with logo_path.open("rb") as logo:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=logo,
                caption="Добро пожаловать! Выберите действие:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text="Добро пожаловать! Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    start_param = context.args[0] if context.args else None

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            referred_by_id = None
            if start_param:
                referrer = db.query(User).filter_by(referral_code=start_param).first()
                if referrer:
                    referred_by_id = referrer.id
            user = User(
                telegram_id=tg_id,
                referral_code=str(uuid.uuid4()),
                referred_by_id=referred_by_id,
            )
            db.add(user)
            db.commit()
        elif not user.referral_code:
            user.referral_code = str(uuid.uuid4())
            db.commit()
    finally:
        db.close()

    await send_main_menu(tg_id, context)


async def show_licenses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tg_id = update.effective_user.id

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        license = db.query(License).filter_by(user_id=user.id).first() if user else None

        if not license or not license.is_active:
            msg = "У вас нет активной подписки."
            kb = [[InlineKeyboardButton("🛒 Оформить подписку", callback_data="subscribe_license")]]
        else:
            next_charge = (
                license.next_charge_at.strftime("%d.%m.%Y") if license.next_charge_at else "-"
            )
            msg = (
                "Ваша лицензия:\n"
                f"<code>{license.license_key}</code>\n"
                f"Следующее продление: {next_charge}"
            )
            kb = [[InlineKeyboardButton("🚫 Отменить подписку", callback_data="cancel_subscription")]]

        kb.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])

        await query.edit_message_text(
            msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb)
        )
    finally:
        db.close()


async def invite_friend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        f"Поделитесь этой ссылкой, чтобы получить бонусные дни:\n{link}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
        ),
    )


async def show_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()

    tg_id = update.effective_user.id
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        referrals, days_left = ([], 0)
        if user:
            referrals, days_left = get_referrals_and_bonus_days(db, user)
    finally:
        db.close()

    lines = "\n".join(f"• {r.telegram_id}" for r in referrals)
    msg = (
        f"Количество приглашённых: {len(referrals)}\n"
        f"Бонусных дней доступно: {days_left}"
    )
    if lines:
        msg += f"\n\nПриглашённые пользователи:\n{lines}"
    else:
        msg += "\n\nПока нет приглашённых пользователей."

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    await (update.message or update.callback_query.message).reply_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def subscribe_license(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Заглушка: активируем/продлеваем лицензию на 30 дней без оплаты
    query = update.callback_query
    await query.answer()

    tg_id = update.effective_user.id
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            user = User(telegram_id=tg_id, referral_code=str(uuid.uuid4()))
            db.add(user)
            db.commit()
            db.refresh(user)

        lic = db.query(License).filter_by(user_id=user.id).first()
        now = datetime.datetime.utcnow()
        next_charge = now + datetime.timedelta(days=30)
        if lic:
            if not getattr(lic, "license_key", None):
                lic.license_key = str(uuid.uuid4())
            lic.is_active = True
            lic.next_charge_at = next_charge
            lic.valid_until = next_charge
        else:
            lic = License(
                user_id=user.id,
                license_key=str(uuid.uuid4()),
                is_active=True,
                next_charge_at=next_charge,
                valid_until=next_charge,
            )
            db.add(lic)
        db.commit()

        # Реферальный бонус один раз при первой активации
        if getattr(user, "referred_by_id", None) and not getattr(user, "referral_bonus_claimed", False):
            referrer = db.query(User).filter_by(id=user.referred_by_id).first()
            if referrer:
                ref_license = db.query(License).filter_by(user_id=referrer.id).first()
                if ref_license:
                    ref_license.valid_until = max(ref_license.valid_until or now, now) + datetime.timedelta(days=30)
                    ref_license.is_active = True
                    ref_license.next_charge_at = ref_license.valid_until
                else:
                    ref_license = License(
                        user_id=referrer.id,
                        license_key=str(uuid.uuid4()),
                        valid_until=now + datetime.timedelta(days=30),
                        is_active=True,
                        next_charge_at=now + datetime.timedelta(days=30),
                    )
                    db.add(ref_license)
                user.referral_bonus_claimed = True
                db.commit()
                try:
                    await context.bot.send_message(
                        chat_id=referrer.telegram_id,
                        text="✅ Ваш приглашённый активировал подписку. +30 дней к вашей лицензии!",
                    )
                except Exception:
                    pass
    finally:
        db.close()

    await query.edit_message_text("✅ Подписка активирована на 30 дней (заглушка).")
    await send_main_menu(tg_id, context)


async def cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tg_id = update.effective_user.id

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        lic = db.query(License).filter_by(user_id=user.id).first() if user else None
        if lic:
            # В режиме заглушки просто выключаем подписку
            if hasattr(lic, "subscription_id"):
                lic.subscription_id = None
            lic.is_active = False
            lic.next_charge_at = None
            db.commit()
    finally:
        db.close()

    await query.edit_message_text("❌ Подписка отменена.")
    await send_main_menu(tg_id, context)


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    command = update.callback_query.data
    if command == "licenses_menu":
        return await show_licenses_menu(update, context)
    elif command == "back_to_main":
        return await start(update, context)
    elif command == "subscribe_license":
        return await subscribe_license(update, context)
    elif command == "cancel_subscription":
        return await cancel_subscription(update, context)
    elif command == "invite_friend":
        return await invite_friend(update, context)
    elif command == "referral_stats":
        return await show_referrals(update, context)


async def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("referrals", show_referrals))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("🤖 Бот запущен. Ожидаю команды...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
