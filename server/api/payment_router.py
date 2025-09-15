# server/api/payment_router.py

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from yookassa import Configuration, Payment
from uuid import uuid4
import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
from sqlalchemy import select

from server.db.session import SessionLocal
from server.models.user import User
from server.models.license import License
from telegram_bot.notify import send_telegram_message

load_dotenv()

router = APIRouter()

# Цена и URL возврата можно вынести в .env
PLAN_PRICE = os.getenv("PLAN_PRICE_RUB", "49.00")
RETURN_URL = os.getenv("PAYMENT_RETURN_URL", "https://t.me/Ano3D_bot")


# ---------- МОДЕЛИ для красивого Swagger (используются только в create_payment) ----------
class YooKassaObject(BaseModel):
    id: str
    metadata: Dict[str, Any] = {}


class YooKassaWebhookModel(BaseModel):
    event: str
    object: YooKassaObject


def _configure_yookassa_or_raise():
    shop_id = os.getenv("YOOKASSA_SHOP_ID")
    secret_key = os.getenv("YOOKASSA_SECRET_KEY")
    if not shop_id or not secret_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "YOOKASSA credentials are not configured "
                "(set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY)."
            ),
        )
    Configuration.account_id = shop_id
    Configuration.secret_key = secret_key


# ---------- СОЗДАНИЕ ПЛАТЕЖА ----------
@router.post("/api/create_payment")
async def create_payment(request: Request):
    """
    Создаёт платёж в ЮKassa и возвращает confirmation_url.
    Тело запроса:
    {
      "telegram_id": 123456789,
      "email": "user@example.com",  # опционально (для чека)
      "phone": "+79991234567"       # опционально (для чека)
    }
    """
    body = await request.json()
    telegram_id = body.get("telegram_id")
    if not telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id is required")

    # email/phone для чека (54-ФЗ): достаточно одного из них
    customer_email = (body.get("email") or "").strip()
    customer_phone = (body.get("phone") or "").strip()
    if not customer_email and not customer_phone:
        # Для MVP подставим заглушку, лучше спрашивать у пользователя в боте
        customer_email = "test@example.com"

    _configure_yookassa_or_raise()

    payment_id = str(uuid4())

    receipt_customer: Dict[str, Any] = {}
    if customer_email:
        receipt_customer["email"] = customer_email
    if customer_phone:
        receipt_customer["phone"] = customer_phone

    try:
        payment = Payment.create(
            {
                "amount": {"value": PLAN_PRICE, "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": RETURN_URL},
                "capture": True,
                "description": f"Оплата лицензии для Telegram ID: {telegram_id}",
                "receipt": {
                    "customer": receipt_customer,
                    "items": [
                        {
                            "description": "Подписка RenderLicenseApp, 30 дней",
                            "quantity": "1.00",
                            "amount": {"value": PLAN_PRICE, "currency": "RUB"},
                            "vat_code": 1,  # без НДС
                            # "payment_subject": "service",
                            # "payment_mode": "full_prepayment",
                        }
                    ],
                    # При необходимости можно указать систему налогообложения:
                    # "tax_system_code": 1,
                },
                "metadata": {"telegram_id": telegram_id},
            },
            payment_id,
        )
        return {"confirmation_url": payment.confirmation.confirmation_url}

    except Exception as e:
        logging.exception("YooKassa Payment.create failed")
        raise HTTPException(status_code=502, detail=f"YooKassa error: {e}")


# ---------- ВЕБХУК ОТ ЮКАССЫ ----------
@router.post("/api/yookassa_webhook")
async def yookassa_webhook(payload: Dict[str, Any]):
    """
    Принимаем СЫРОЙ payload, чтобы видеть любые события и быстро диагностировать.
    Сразу логируем и отправляем 'пинг' пользователю (если есть metadata.telegram_id).
    Затем при event='payment.succeeded' активируем/продлеваем лицензию.
    """
    try:
        logging.info(f"[WEBHOOK RAW] {payload}")
    except Exception:
        pass

    event = payload.get("event")
    obj = payload.get("object", {}) or {}
    meta = obj.get("metadata", {}) or {}
    telegram_id = meta.get("telegram_id")

    # Быстрый пинг — понять, что вебхук вообще дошёл
    if telegram_id:
        try:
            await send_telegram_message(
                chat_id=int(telegram_id),
                text=f"🔔 Вебхук получен: {event}",
            )
        except Exception:
            pass

    # Обрабатываем только успешный платёж
    if event != "payment.succeeded":
        # Возвращаем 200, чтобы ЮKassa не ретраила бесконечно
        return {"status": f"ignored: {event}"}

    if not telegram_id:
        raise HTTPException(status_code=400, detail="No telegram_id in metadata")

    now = datetime.utcnow()

    async with SessionLocal() as db:
        # ищем пользователя
        result = await db.execute(select(User).filter_by(telegram_id=int(telegram_id)))
        user = result.scalars().first()
        if not user:
            user = User(telegram_id=int(telegram_id))
            db.add(user)
            await db.commit()
            await db.refresh(user)

        # ищем/создаём лицензию
        result = await db.execute(select(License).filter_by(user_id=user.id))
        lic = result.scalars().first()

        def plus_30(from_dt: datetime) -> datetime:
            return from_dt + timedelta(days=30)

        if lic:
            base = lic.valid_until or now
            lic.valid_until = plus_30(max(base, now))
            lic.is_active = True
            lic.next_charge_at = lic.valid_until
        else:
            import uuid as _uuid
            until = plus_30(now)
            lic = License(
                user_id=user.id,
                license_key=str(_uuid.uuid4()),
                is_active=True,
                valid_until=until,
                next_charge_at=until,
            )
            db.add(lic)

        await db.commit()

    # Финальное уведомление
    try:
        await send_telegram_message(
            chat_id=int(telegram_id),
            text="✅ Оплата прошла успешно. Подписка активирована на 30 дней!",
        )
    except Exception:
        pass

    return {"status": "ok"}
