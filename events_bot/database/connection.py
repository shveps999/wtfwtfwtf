from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
from .models import Base
from logfire import instrument_sqlalchemy


def get_database_url():
    """Получает URL базы данных из переменных окружения"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL не установлен в переменных окружения")

    # Преобразуем синхронный URL в асинхронный
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "mysql+aiomysql://", 1)
    elif database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    
    return database_url


# Глобальный флаг для инструментирования
_already_instrumented = False


def create_async_engine_and_session():
    """Создает асинхронный движок базы данных и фабрику сессий"""
    database_url = get_database_url()

    # Настройка движка с оптимальными параметрами
    engine = create_async_engine(
        database_url,
        echo=False,              # Отключено для продакшена
        pool_pre_ping=True,      # Проверка соединения перед использованием
        pool_recycle=300,        # Пересоздание соединений каждые 5 минут
        pool_size=10,            # Основной пул соединений
        max_overflow=20,         # Максимум временных соединений
        pool_timeout=15,         # Таймаут ожидания соединения
    )

    # Создание фабрики сессий
    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Инструментирование SQL-запросов (один раз)
    global _already_instrumented
    if not _already_instrumented:
        instrument_sqlalchemy(engine)
        _already_instrumented = True

    return engine, session_maker


async def create_tables(engine):
    """Создает все таблицы в базе данных асинхронно"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Асинхронный генератор для получения сессии базы данных"""
    _, session_maker = create_async_engine_and_session()
    async with session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()


# Для обратной совместимости
def create_engine_and_session():
    """Синхронная версия (не используется в продакшене)"""
    raise NotImplementedError(
        "Используйте create_async_engine_and_session() для асинхронной работы"
    )
