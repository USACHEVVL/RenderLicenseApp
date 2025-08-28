import asyncio
import datetime
import sys
from pathlib import Path
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

sys.path.append(str(Path(__file__).resolve().parents[1]))

from server.models.user import User
from server.models.license import License
from server.db.base_class import Base


class DummyRequest:
    pass


def setup_test_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())
    return engine, TestingSessionLocal


def count_queries(engine, func):
    queries = {"count": 0}

    def before_cursor_execute(*args, **kwargs):
        queries["count"] += 1

    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    try:
        asyncio.run(func())
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
    return queries["count"]


def dummy_template_response(*args, **kwargs):
    return None


def test_admin_dashboard_query_count(monkeypatch):
    class DummyTemplates:
        def __init__(self, *args, **kwargs):
            pass

        def TemplateResponse(self, *args, **kwargs):
            return None

    monkeypatch.setattr("fastapi.templating.Jinja2Templates", DummyTemplates)
    monkeypatch.setattr(
        "fastapi.dependencies.utils.ensure_multipart_is_installed", lambda: None
    )
    import importlib
    admin_routes = importlib.import_module("server.admin.routes")

    engine, TestingSessionLocal = setup_test_db()

    async def seed():
        async with TestingSessionLocal() as db:
            user = User(telegram_id=1)
            lic = License(license_key="lk1", user=user, is_active=True)
            db.add_all([user, lic])
            await db.commit()

    asyncio.run(seed())

    monkeypatch.setattr(admin_routes, "SessionLocal", TestingSessionLocal)

    async def call():
        await admin_routes.admin_dashboard(DummyRequest())

    query_count = count_queries(engine, call)
    assert query_count == 1


def test_admin_users_query_count(monkeypatch):
    class DummyTemplates:
        def __init__(self, *args, **kwargs):
            pass

        def TemplateResponse(self, *args, **kwargs):
            return None

    monkeypatch.setattr("fastapi.templating.Jinja2Templates", DummyTemplates)
    monkeypatch.setattr(
        "fastapi.dependencies.utils.ensure_multipart_is_installed", lambda: None
    )
    import importlib
    admin_routes = importlib.import_module("server.admin.routes")

    engine, TestingSessionLocal = setup_test_db()

    async def seed():
        async with TestingSessionLocal() as db:
            user1 = User(telegram_id=1)
            user2 = User(telegram_id=2)
            lic1 = License(license_key="lk1", user=user1)
            db.add_all([user1, user2, lic1])
            await db.commit()

    asyncio.run(seed())

    monkeypatch.setattr(admin_routes, "SessionLocal", TestingSessionLocal)

    async def call():
        await admin_routes.admin_users(DummyRequest())

    query_count = count_queries(engine, call)
    assert query_count == 1
