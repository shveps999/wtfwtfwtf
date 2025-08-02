from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from events_bot.database import get_async_session
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

class DatabaseMiddleware(BaseMiddleware):
    """Middleware для предоставления сессии базы данных"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Используем асинхронный генератор для получения сессии
        async for session in get_async_session():
            data['db'] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as e:
                logger.error(f"Ошибка в middleware: {e}")
                await session.rollback()
                raise
            finally:
                await session.close()
