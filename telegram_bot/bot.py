import os
import asyncio
import uuid
import datetime
import httpx
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
from sqlalchemy import select
from server.models.user import User
from server.models.license import License
from server.services.referral_service import (
    get_referrals_and_bonus_days,
    claim_referral_bonuses,
    BONUS_DAYS_PER_REFERRAL,
)


load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


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
    logo_path = Path(__file__).resolve().parent / "assets" / "logo.png"
    if logo_path.exists():
        logo_bytes = await asyncio.to_thread(logo_path.read_bytes)
        await context.bot.send_photo(
            chat_id=user_id,
            photo=logo_bytes,
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

    async with SessionLocal() as db:
        result = await db.execute(select(User).filter_by(telegram_id=tg_id))
        user = result.scalars().first()
        if not user:
            referred_by_id = None
            if start_param:
                result = await db.execute(
                    select(User).filter_by(referral_code=start_param)
                )
                referrer = result.scalars().first()
                if referrer:
                    referred_by_id = referrer.id
            user = User(
                telegram_id=tg_id,
                referral_code=str(uuid.uuid4()),
                referred_by_id=referred_by_id,
            )
            db.add(user)
            await db.commit()
        elif not user.referral_code:
            user.referral_code = str(uuid.uuid4())
            await db.commit()

    await send_main_menu(tg_id, context)


async def show_licenses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tg_id = update.effective_user.id
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter_by(telegram_id=tg_id))
        user = result.scalars().first()
        license = None
        if user:
            result = await db.execute(select(License).filter_by(user_id=user.id))
            license = result.scalars().first()

        if not license or not license.is_active:
            msg = (
                "На данный момент подписка не оформлена. "
                "Не трать своё время на отслеживание процесса рендеринга всего за 49 руб/мес."
            )
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


async def invite_friend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tg_id = update.effective_user.id
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter_by(telegram_id=tg_id))
        user = result.scalars().first()
        if user and not user.referral_code:
            user.referral_code = str(uuid.uuid4())
            await db.commit()
        elif not user:
            user = User(telegram_id=tg_id, referral_code=str(uuid.uuid4()))
            db.add(user)
            await db.commit()
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={user.referral_code}"

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
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter_by(telegram_id=tg_id))
        user = result.scalars().first()
        referrals, days_left, unclaimed = ([], 0, 0)
        if user:
            referrals, days_left, unclaimed = await get_referrals_and_bonus_days(db, user)

    lines = "\n".join(f"• {r.telegram_id}" for r in referrals)
    msg = (
        f"Количество приглашённых: {len(referrals)}\n"
        f"Бонусных дней доступно: {days_left}"
    )
    if unclaimed:
        msg += (
            f"\nДоступно к получению: {unclaimed * BONUS_DAYS_PER_REFERRAL}"
            f" дней за {unclaimed} приглашённых"
        )
    if lines:
        msg += f"\n\nПриглашённые пользователи:\n{lines}"
    else:
        msg += "\n\nПока нет приглашённых пользователей."

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    await (update.message or update.callback_query.message).reply_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def claim_referral_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tg_id = update.effective_user.id
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter_by(telegram_id=tg_id))
        user = result.scalars().first()
        if not user:
            await query.edit_message_text("Пользователь не найден.")
            return
        count = await claim_referral_bonuses(db, user)
    if count:
        text = f"✅ Начислено бонусных дней: {count * BONUS_DAYS_PER_REFERRAL}"
    else:
        text = "Нет бонусов к получению."
    kb = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))


async def subscribe_license(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Создаёт платёж через FastAPI и отправляет пользователю кнопку с ссылкой на оплату."""
    query = update.callback_query
    await query.answer()

    tg_id = update.effective_user.id

    try:
        # Обращаемся к нашему FastAPI-эндпоинту, который создаёт платёж в ЮKassa
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{API_BASE}/api/create_payment",
                json={"telegram_id": tg_id},
            )

        if resp.status_code != 200:
            await query.edit_message_text(
                "❌ Не удалось создать платёж. Попробуйте позже."
            )
            return

        data = resp.json()
        confirmation_url = data.get("confirmation_url")

        if not confirmation_url:
            await query.edit_message_text(
                "⚠️ Сервер не вернул ссылку на оплату. Попробуйте позже."
            )
            return

        # Кнопка перехода на оплату
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("💳 Перейти к оплате", url=confirmation_url)],
                [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")],
            ]
        )

        await query.edit_message_text(
            "Чтобы оформить подписку, нажмите кнопку ниже и завершите оплату:",
            reply_markup=kb,
        )

    except Exception as e:
        # Можно залогировать e
        await query.edit_message_text(
            "⚠️ Произошла ошибка при создании платежа. Попробуйте позже."
        )


async def cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    tg_id = update.effective_user.id
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter_by(telegram_id=tg_id))
        user = result.scalars().first()
        lic = None
        if user:
            result = await db.execute(select(License).filter_by(user_id=user.id))
            lic = result.scalars().first()
        if lic:
            if hasattr(lic, "subscription_id"):
                lic.subscription_id = None
            lic.is_active = False
            lic.next_charge_at = None
            await db.commit()

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
    elif command == "claim_referral_bonus":
        return await claim_referral_bonus(update, context)


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
