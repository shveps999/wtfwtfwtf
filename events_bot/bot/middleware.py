from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from typing import Callable, Dict, Any
from events_bot.database import get_db

class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware для автоматического предоставления сессии БД
    через event.db в обработчики.
    """

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        self.sessionmaker = sessionmaker

    async def __call__(
        self,
        handler: Callable,
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        async with self.sessionmaker() as session:
            data["db"] = session
            return await handler(event, data)
