"""
راه‌اندازی SQLAlchemy Async Engine و Session Factory.
تمام سرویس‌ها باید از get_session() به‌عنوان context manager استفاده کنند
تا تراکنش‌ها به‌درستی commit/rollback شوند (به‌خصوص عملیات مالی).
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=(settings.environment == "development"),
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """کلاس پایه‌ی تمام مدل‌های ORM."""
    pass


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """
    استفاده:
        async with get_session() as session:
            ...
            await session.commit()
    در صورت بروز خطا، rollback خودکار انجام می‌شود.
    """
    session = async_session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
