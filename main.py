#!/usr/bin/env python3
"""
Telegram Events Bot - Основной файл приложения
"""

import logfire

logfire.configure(scrubbing=False)

import asyncio
import os
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
from loguru import logger

logger.configure(
    handlers=[logfire.loguru_handler()]
)


async def main():
    """Главная функция бота"""
    # Получаем токен из переменных окружения
    token = os.getenv("BOT_TOKEN")
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

    try:
        # Запускаем бота
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logfire.info("🛑 Bot stopped")
    finally:
        await bot.session.close(


if __name__ == "__main__":
    asyncio.run(main())
