from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
import logging

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Глобальные объекты (инициализируются один раз)
_async_engine = None
_async_session_maker = None

def get_database_url():
    """Получает URL базы данных из переменных окружения"""
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./events_bot.db")
    
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("mysql://"):
        return database_url.replace("mysql://", "mysql+aiomysql://", 1)
    return database_url

def initialize_database():
    """Инициализация движка и фабрики сессий (вызывается один раз при старте)"""
    global _async_engine, _async_session_maker
    
    if _async_engine is None:
        database_url = get_database_url()
        logger.info(f"Инициализация БД: {database_url}")
        
        _async_engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True
        )
        
        _async_session_maker = async_sessionmaker(
            bind=_async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
    
    return _async_engine, _async_session_maker

async def get_db_session() -> AsyncSession:
    """Получение сессии для использования в обработчиках"""
    if _async_session_maker is None:
        initialize_database()
    
    session = _async_session_maker()
    try:
        yield session
    finally:
        await session.close()

async def create_tables():
    """Создание таблиц в базе данных"""
    if _async_engine is None:
        initialize_database()
    
    async with _async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Таблицы БД успешно созданы")

async def close_connections():
    """Закрытие всех соединений с БД"""
    global _async_engine
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        logger.info("Соединения с БД закрыты")
