from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import BACKEND_DIR, get_settings
from app.db.base import Base
from app.services.seed import seed_demo_data

(BACKEND_DIR / "data").mkdir(parents=True, exist_ok=True)


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        echo=settings.app_debug,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


async def initialize_database() -> None:
    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    settings = get_settings()
    if not settings.demo_seed:
        return

    async with get_session_factory()() as session:
        await seed_demo_data(session)
