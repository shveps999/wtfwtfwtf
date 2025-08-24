from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import quote_plus
from .models import Base
from logfire import instrument_sqlalchemy


def get_database_url():
    """Получает и корректно форматирует URL базы данных"""
    env_path = Path(__file__).parent / 'env.production.example'
    load_dotenv(env_path)
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("DATABASE_URL не установлен в переменных окружения")

    # Экранируем спецсимволы в пароле (например, ;, #, /, =)
    if "@" in database_url and "://" in database_url:
        prefix, rest = database_url.split("://", 1)
        if "@" in rest:
            user_pass, host_port_db = rest.split("@", 1)
            if ":" in user_pass:
                user, password = user_pass.split(":", 1)
                encoded_password = quote_plus(password)
                database_url = f"{prefix}://{user}:{encoded_password}@{host_port_db}"

    # Преобразуем синхронный URL в асинхронный
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("mysql://"):
        database_url = database_url.replace("mysql://", "mysql+aiomysql://", 1)

    return database_url


# Глобальные переменные
_engine = None
_session_maker = None
_already_instrumented = False


def create_async_engine_and_session():
    """Создает асинхронный движок базы данных и фабрику сессий (синглтон)"""
    global _engine, _session_maker, _already_instrumented
    
    if _engine is None:
        database_url = get_database_url()
        _engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
        )
        _session_maker = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        
        if not _already_instrumented:
            instrument_sqlalchemy(_engine)
            _already_instrumented = True
    
    return _engine, _session_maker


async def create_tables(engine=None):
    """Создает все таблицы в базе данных асинхронно"""
    if engine is None:
        engine, _ = create_async_engine_and_session()
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
