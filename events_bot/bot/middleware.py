from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from events_bot.bot.utils import get_db_session
import logfire


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для автоматического получения сессии базы данных"""
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
         Dict[str, Any]
    ) -> Any:
        db = None
        try:
            db = await get_db_session()
            data['db'] = db
            result = await handler(event, data)
            return result
        except Exception as e:
            logfire.error(f"Ошибка в DatabaseMiddleware: {e}")
            raise
        finally:
            if db:
                await db.close()
