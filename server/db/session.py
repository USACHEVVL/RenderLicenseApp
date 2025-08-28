<<<<<<< ours
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", f"sqlite:///{BASE_DIR / 'database.db'}"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
=======
"""Database session and engine setup using SQLAlchemy's async API."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///server/db/database.db"

# Create an asynchronous engine and session factory. ``async_sessionmaker``
# provides ``async with SessionLocal() as session`` usage throughout the code.
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(  # type: ignore[call-arg]
    bind=engine, expire_on_commit=False, autocommit=False, autoflush=False, class_=AsyncSession
)

>>>>>>> theirs
