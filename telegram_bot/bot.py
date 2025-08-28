import os
import asyncio
import uuid
import datetime
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    MessageHandler,
    filters,
)
from telegram.error import InvalidToken

from server.db.session import SessionLocal
from server.models.user import User
from server.models.license import License
from server.services.referral_service import get_referrals_and_bonus_days

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 670562262
PROVIDER_TOKEN = os.getenv("TELEGRAM_PROVIDER_TOKEN")

async def send_main_menu(user_id, context):
    keyboard = [
        [InlineKeyboardButton("🔐 Лицензии", callback_data='licenses_menu')],
        [InlineKeyboardButton("👥 Пригласить друга", callback_data='invite_friend')],
        [InlineKeyboardButton("📊 Мои рефералы", callback_data='referral_stats')],
    ]
    logo_path = Path(__file__).resolve().parent / "assets" / "logo.png"
    if logo_path.exists():
        with logo_path.open("rb") as logo:
            await context.bot.send_photo(chat_id=user_id, photo=logo,
                                         caption="Привет! 👋 Выберите действие:",
                                         reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await context.bot.send_message(chat_id=user_id,
                                       text="Привет! 👋 Выберите действие:",
                                       reply_markup=InlineKeyboardMarkup(keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def show_licenses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = update.effective_user.id
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        license = db.query(License).filter_by(user_id=user.id).first() if user else None

        if not license or not license.is_active:
            msg = "📭 Подписка не активна."
            kb = [[InlineKeyboardButton("💳 Оформить подписку", callback_data='subscribe_license')]]
        else:
            next_charge = (
                license.next_charge_at.strftime("%d.%m.%Y")
                if license.next_charge_at
                else "—"
            )
            msg = (
                "🔐 Ваша лицензия:\n"
                f"<code>{license.license_key}</code>\n"
                f"Следующее списание: {next_charge}"
            )
            kb = [[InlineKeyboardButton("❌ Отменить подписку", callback_data='cancel_subscription')]]

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


async def show_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        f"✅ Успешных приглашений: {len(referrals)}\n"
        f"🎁 Бонусных дней осталось: {days_left}"
    )
    if lines:
        msg += f"\n\nПриглашённые пользователи:\n{lines}"
    else:
        msg += "\n\nПока нет успешных приглашений."

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]]
    await (update.message or update.callback_query.message).reply_text(
        msg, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def subscribe_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not PROVIDER_TOKEN:
        await query.edit_message_text("Платёжный провайдер не настроен.")
        return

    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title="Подписка на лицензию",
        description="Ежемесячная подписка на RenderLicense",
        payload="license-subscription",
        provider_token=PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice("Подписка", 5000)],
        subscription_period=2592000,
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    payment = update.message.successful_payment
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not user:
            user = User(telegram_id=tg_id, referral_code=str(uuid.uuid4()))
            db.add(user)
            db.commit()
            db.refresh(user)

        lic = db.query(License).filter_by(user_id=user.id).first()
        period = payment.subscription_period or 2592000
        next_charge = datetime.datetime.utcnow() + datetime.timedelta(seconds=period)
        if lic:
            lic.subscription_id = payment.subscription_id
            lic.is_active = True
            lic.next_charge_at = next_charge
            lic.valid_until = next_charge
        else:
            lic = License(
                user_id=user.id,
                license_key=str(uuid.uuid4()),
                subscription_id=payment.subscription_id,
                is_active=True,
                next_charge_at=next_charge,
                valid_until=next_charge,
            )
            db.add(lic)
        db.commit()

        if user.referred_by_id and not user.referral_bonus_claimed:
            referrer = db.query(User).filter_by(id=user.referred_by_id).first()
            if referrer:
                ref_license = db.query(License).filter_by(user_id=referrer.id).first()
                now = datetime.datetime.utcnow()
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
                        text="🎉 Ваш приглашённый друг оформил подписку. +30 дней к вашей лицензии!",
                    )
                except Exception:
                    pass
    finally:
        db.close()

    await context.bot.send_message(chat_id=tg_id, text="✅ Подписка активирована.")
    await send_main_menu(tg_id, context)

async def cancel_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = update.effective_user.id
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(telegram_id=tg_id).first()
        lic = db.query(License).filter_by(user_id=user.id).first() if user else None
        if lic and lic.subscription_id:
            try:
                await context.bot.call_api("cancelSubscription", {"subscription_id": lic.subscription_id})
            except Exception:
                pass
            lic.subscription_id = None
            lic.is_active = False
            lic.next_charge_at = None
            db.commit()
    finally:
        db.close()

    await query.edit_message_text("❌ Подписка отменена.")
    await send_main_menu(tg_id, context)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.callback_query.data
    if command == 'licenses_menu':
        return await show_licenses_menu(update, context)
    elif command == 'back_to_main':
        return await start(update, context)
    elif command == 'subscribe_license':
        return await subscribe_license(update, context)
    elif command == 'cancel_subscription':
        return await cancel_subscription(update, context)
    elif command == 'invite_friend':
        return await invite_friend(update, context)
    elif command == 'referral_stats':
        return await show_referrals(update, context)

async def main():
    if not TOKEN:
        print("⚠️ TELEGRAM_BOT_TOKEN is not set. Bot will not start.")
        return

    try:
        app = ApplicationBuilder().token(TOKEN).build()
    except InvalidToken:
        print("⚠️ Invalid TELEGRAM_BOT_TOKEN. Bot will not start.")
        return
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("referrals", show_referrals))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("✅ Бот запущен. Ожидает команды...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
