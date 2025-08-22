#!/usr/bin/env python3
"""
Telegram Events Bot - Основной файл приложения
"""

import logfire

# Не требуем авторизации в Logfire, если нет токена
try:
    logfire.configure(scrubbing=False, send_to_logfire=False)
except Exception:
    pass

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from events_bot.database import init_database
from events_bot.bot.handlers import (
    register_start_handlers,
    register_user_handlers,
    register_post_handlers,
    register_callback_handlers,
    register_moderation_handlers,
    register_feed_handlers,
)
from events_bot.bot.middleware import DatabaseMiddleware
from events_bot.database.services.post_service import PostService
from loguru import logger

logger.configure(
    handlers=[logfire.loguru_handler()]
)


async def main():
    """Главная функция бота"""
    # Подхват переменных окружения из .env, если есть ##теперь Подхват переменных окружения из .env.production.example
    env_path = Path(__file__).parent / 'env.production.example'
    load_dotenv(env_path)

    # Получаем токен из переменных окружения
    token = os.getenv("BOT_TOKEN")
    print('token:', token)
    if not token:
        logfire.error("❌ Error: BOT_TOKEN not set")
        return

    # Инициализируем базу данных
    await init_database()
    logfire.info("✅ Database initialized")

    # Создаем бота и диспетчер
    bot = Bot(token=token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключаем middleware для базы данных
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    # Регистрируем обработчики
    register_start_handlers(dp)
    register_user_handlers(dp)
    register_post_handlers(dp)
    register_callback_handlers(dp)
    register_moderation_handlers(dp)
    register_feed_handlers(dp)

    logfire.info("🤖 Bot started...")

    async def cleanup_expired_posts_task():
        from events_bot.bot.utils import get_db_session
        from events_bot.storage import file_storage
        while True:
            try:
                async with get_db_session() as db:
                    # Сначала собираем информацию о просроченных постах (id, image_id)
                    expired = await PostService.get_expired_posts_info(db)
                    deleted = await PostService.delete_expired_posts(db)
                    if deleted:
                        logfire.info(f"🧹 Удалено просроченных постов: {deleted}")
                        # Удаляем связанные файлы из хранилища
                        for row in expired:
                            image_id = row.get("image_id")
                            if image_id:
                                try:
                                    await file_storage.delete_file(image_id)
                                except Exception:
                                    pass
            except Exception as e:
                logfire.error(f"Ошибка фоновой очистки постов: {e}")
            await asyncio.sleep(60 * 10)

    try:
        # Запускаем бота и фоновую очистку одновременно
        await asyncio.gather(
            dp.start_polling(bot),
            cleanup_expired_posts_task(),
        )
    except KeyboardInterrupt:
        logfire.info("🛑 Bot stopped")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
