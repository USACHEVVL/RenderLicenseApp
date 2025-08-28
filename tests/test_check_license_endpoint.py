import asyncio
import datetime
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI

from server.db.base_class import Base
from server.models.license import License
from server.models.user import User
import server.api.license_router as license_router

app = FastAPI()
app.include_router(license_router.router, prefix="/api")


def setup_test_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())
    return TestingSessionLocal


def seed_db(SessionLocal):
    async def seed():
        async with SessionLocal() as db:
            user = User(telegram_id=123)
            license = License(
                license_key="abc",
                user=user,
                is_active=True,
                next_charge_at=datetime.datetime.utcnow() + datetime.timedelta(days=30),
            )
            db.add_all([user, license])
            await db.commit()

    asyncio.run(seed())


def test_check_license_returns_user(monkeypatch):
    TestingSessionLocal = setup_test_db()
    seed_db(TestingSessionLocal)

    monkeypatch.setattr(license_router, "SessionLocal", TestingSessionLocal)

    with TestClient(app) as client:
        response = client.get("/api/check_license", params={"license_key": "abc"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["user_id"] == 123
