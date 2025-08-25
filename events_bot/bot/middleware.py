from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from events_bot.bot.utils import get_db_session


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для автоматического получения сессии базы данных"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with get_db_session() as db:
            data['db'] = db
            return await handler(event, data)

