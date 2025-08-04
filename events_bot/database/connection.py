from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy import URL
import os
import asyncio
from typing import AsyncGenerator
import logfire

# Единственный экземпляр engine и sessionmaker
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_lock = asyncio.Lock()  # Для потокобезопасной инициализации


def _get_database_url() -> str:
    """Преобразует синхронный DATABASE_URL в асинхронный"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL не установлен в переменных окружения")

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://")
    elif database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "mysql+aiomysql://")
    elif database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    return database_url


async def create_async_engine_and_session() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    Создаёт асинхронный engine и sessionmaker.
    Вызывается один раз при старте приложения.
    """
    global _engine, _sessionmaker

    if _engine is not None and _sessionmaker is not None:
        return _engine, _sessionmaker

    async with _lock:
        if _engine is not None and _sessionmaker is not None:
            return _engine, _sessionmaker

        database_url = _get_database_url()
        logfire.info("Создание асинхронного engine для БД", url=database_url)

        _engine = AsyncEngine.create(
            url=URL.create(database_url),
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,
        )
        _sessionmaker = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )

        return _engine, _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость для получения сессии БД (аналог FastAPI).
    Гарантирует закрытие сессии после использования.
    """
    global _sessionmaker
    if _sessionmaker is None:
        await create_async_engine_and_session()

    async with _sessionmaker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Для обратной совместимости (не рекомендуется использовать напрямую)
def get_db_session() -> AsyncSession:
    """
    Устаревший способ. Используйте get_db() как асинхронный контекст.
    """
    raise NotImplementedError("Используйте асинхронный `get_db()` как зависимость.")
