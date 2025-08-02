from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
from .models import Base
import logging
from contextlib import asynccontextmanager

# Настройка логирования
logger = logging.getLogger(__name__)

class Database:
    _engine = None
    _session_factory = None

    @classmethod
    def get_engine(cls):
        """Получить или создать движок базы данных"""
        if cls._engine is None:
            database_url = cls.get_database_url()
            logger.info(f"Инициализация движка БД: {database_url}")
            
            cls._engine = create_async_engine(
                database_url,
                echo=False,
                pool_size=10,
                max_overflow=5,
                pool_pre_ping=True
            )
        return cls._engine

    @classmethod
    def get_session_factory(cls):
        """Получить или создать фабрику сессий"""
        if cls._session_factory is None:
            engine = cls.get_engine()
            cls._session_factory = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )
        return cls._session_factory

    @staticmethod
    def get_database_url():
        """Получить URL базы данных из переменных окружения"""
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./events_bot.db")
        
        # Автоматическое преобразование URL
        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("mysql://"):
            return database_url.replace("mysql://", "mysql+aiomysql://", 1)
        return database_url

    @classmethod
    @asynccontextmanager
    async def get_session(cls):
        """Асинхронный контекстный менеджер для работы с сессией"""
        session_factory = cls.get_session_factory()
        session = session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка в сессии: {e}")
            raise
        finally:
            await session.close()

    @classmethod
    async def create_tables(cls):
        """Создать таблицы в базе данных"""
        engine = cls.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы БД успешно созданы")

    @classmethod
    async def dispose(cls):
        """Закрыть все соединения с БД"""
        if cls._engine:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            logger.info("Соединения с БД закрыты")
