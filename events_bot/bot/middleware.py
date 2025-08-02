from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from events_bot.database import get_db_session
import logging

logger = logging.getLogger(__name__)

class DatabaseMiddleware(BaseMiddleware):
    """Middleware для предоставления сессии базы данных"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Создаем асинхронный генератор сессии
        session_generator = get_db_session()
        session = await session_generator.__anext__()
        
        data['db'] = session
        try:
            result = await handler(event, data)
            await session.commit()
            return result
        except Exception as e:
            logger.error(f"Ошибка в обработчике: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
