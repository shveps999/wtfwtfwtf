from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
from .models import Base
from logfire import instrument_sqlalchemy
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальные переменные для engine и session maker
_async_engine = None
_async_session_maker = None

def get_database_url():
    """Получает URL базы данных из переменных окружения"""
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./events_bot.db")
    
    # Автоматическое преобразование синхронных URL в асинхронные
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "mysql+aiomysql://", 1)
    return database_url

def create_async_engine_and_session():
    """Создает асинхронный движок и фабрику сессий (один раз при инициализации)"""
    global _async_engine, _async_session_maker
    
    if _async_engine is None:
        database_url = get_database_url()
        logger.info(f"Создание движка для БД: {database_url}")
        
        _async_engine = create_async_engine(
            database_url, 
            echo=False,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True
        )
        
        # Инструментируем SQLAlchemy для логирования запросов
        instrument_sqlalchemy(_async_engine)
        
        _async_session_maker = async_sessionmaker(
            bind=_async_engine, 
            class_=AsyncSession, 
            expire_on_commit=False,
            autoflush=False
        )
    
    return _async_engine, _async_session_maker

async def get_async_session() -> AsyncSession:
    """Получение асинхронной сессии (для использования в зависимостях FastAPI)"""
    _, session_maker = create_async_engine_and_session()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    """Создание таблиц в базе данных (асинхронно)"""
    engine, _ = create_async_engine_and_session()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def dispose_engine():
    """Закрытие соединений с БД (вызывается при завершении приложения)"""
    global _async_engine
    if _async_engine:
        await _async_engine.dispose()
        logger.info("Соединения с БД закрыты")
