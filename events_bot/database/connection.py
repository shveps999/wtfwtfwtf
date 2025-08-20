from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
from .models import Base
from logfire import instrument_sqlalchemy


def get_database_url():
    """Получает URL базы данных из переменных окружения или использует SQLite по умолчанию"""
    database_url = os.getenv("DATABASE_URL")

    # Если указан TEST_MODE, используем временную базу в памяти

    if database_url:
        # Преобразуем синхронный URL в асинхронный
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("mysql://"):
            return database_url.replace("mysql://", "mysql+aiomysql://", 1)
        else:
            return database_url

        
already_instrumented = False

def create_async_engine_and_session():
    """Создает асинхронный движок базы данных и сессию"""
    database_url = get_database_url()
    engine = create_async_engine(database_url, echo=False)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    global already_instrumented
    if not already_instrumented:
        instrument_sqlalchemy(engine)
        already_instrumented = True
    return engine, session_maker


async def create_tables(engine):
    """Создает все таблицы в базе данных асинхронно"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Асинхронный генератор для получения сессии базы данных"""
    engine, session_maker = create_async_engine_and_session()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# Для обратной совместимости (если нужно)
def create_engine_and_session():
    """Синхронная версия для обратной совместимости"""
    raise NotImplementedError(
        "Используйте create_async_engine_and_session() для асинхронной работы"
    )
