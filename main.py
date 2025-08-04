#!/usr/bin/env python3
"""Telegram Events Bot - Основной файл приложения"""

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
from events_bot.tasks.cleanup import cleanup_expired_posts
from loguru import logger

logger.configure(handlers=[logfire.loguru_handler()])

engine = None
sessionmaker = None


async def main():
    global engine, sessionmaker

    token = os.getenv("BOT_TOKEN")
    if not token:
        logfire.error("❌ Error: BOT_TOKEN not set")
        return

    engine, sessionmaker = await create_async_engine_and_session()
    logfire.info("✅ Database engine и sessionmaker инициализированы")

    await init_database()
    logfire.info("✅ Database initialized")

    bot = Bot(token=token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.message.middleware(DatabaseMiddleware(sessionmaker))
    dp.callback_query.middleware(DatabaseMiddleware(sessionmaker))

    register_start_handlers(dp)
    register_user_handlers(dp)
    register_post_handlers(dp)
    register_callback_handlers(dp)
    register_moderation_handlers(dp)
    register_feed_handlers(dp)

    logfire.info("🤖 Bot started...")

    polling_task = asyncio.create_task(dp.start_polling(bot))
    cleanup_task = asyncio.create_task(cleanup_expired_posts(bot, interval=3600))  # Каждый час

    await asyncio.gather(polling_task, cleanup_task)

    await bot.session.close()
    if engine:
        await engine.dispose()
        logfire.info("🗑️ Database engine disposed")


if __name__ == "__main__":
    from events_bot.database.connection import create_async_engine_and_session
    asyncio.run(main())
