# server/models/payment.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, UniqueConstraint, Index
from server.db.base_class import Base  # у тебя уже есть Base в проекте

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    # Идентификатор платежа в ЮKassa (object.id) — для идемпотентности
    payment_id = Column(String(64), nullable=False, unique=True, index=True)

    # Кто платил (для удобства связываем с твоей системой)
    telegram_id = Column(Integer, nullable=False, index=True)

    # Статус платежа (ожидаем в итоге 'succeeded')
    status = Column(String(32), nullable=False, index=True)

    # Сумма и валюта (на будущее; можно хранить как строки, но Numeric точнее)
    amount_value = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(8), nullable=True)

    # Описание (то, что ты передавал в create_payment)
    description = Column(Text, nullable=True)

    # Сырые данные вебхука (для отладки; можно хранить JSON как Text)
    payload = Column(Text, nullable=True)

    # Метки времени
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("payment_id", name="uq_payments_payment_id"),
        Index("ix_payments_telegram_status", "telegram_id", "status"),
    )
