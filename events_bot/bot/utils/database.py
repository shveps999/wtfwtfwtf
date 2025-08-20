from sqlalchemy.ext.asyncio import AsyncSession
from events_bot.database import create_async_engine_and_session


def get_db_session():
    """Получить сессию базы данных"""
    engine, session_maker = create_async_engine_and_session()
    return session_maker()
