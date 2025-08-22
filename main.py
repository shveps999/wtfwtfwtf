#!/usr/bin/env python3
"""
Telegram Events Bot - Основной файл приложения
"""

import asyncio
import os
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import logfire

# Конфигурируем Logfire, не требуя токена для локальной работы.
# Отправка в облако будет работать только если LOGFIRE_TOKEN установлен.
logfire.configure()
logfire.info("Logfire сконфигурирован.")

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


async def cleanup_expired_posts_task():
    """Фоновая задача для очистки просроченных постов."""
    from events_bot.bot.utils import get_db_session
    from events_bot.storage import file_storage
    logfire.info("🌀 Запущена фоновая задача по очистке просроченных постов.")
    
    while True:
        try:
            # Пауза в начале цикла, а не в конце, чтобы не ждать при первом запуске
            await asyncio.sleep(60 * 10) # 10 минут
            
            async with get_db_session() as db:
                expired_posts_info = await PostService.get_expired_posts_info(db)
                
                if not expired_posts_info:
                    continue

                deleted_count = await PostService.delete_expired_posts(db)
                
                if deleted_count:
                    logfire.info(f"🧹 Удалено/архивировано просроченных постов: {deleted_count}")
                    for post_info in expired_posts_info:
                        image_id = post_info.get("image_id")
                        if image_id:
                            try:
                                await file_storage.delete_file(image_id)
                            except Exception as file_e:
                                logfire.error(f"Ошибка при удалении файла {image_id}: {file_e}")
        except asyncio.CancelledError:
            logfire.info("🌀 Задача по очистке постов была отменена. Завершение работы...")
            break
        except Exception as e:
            logfire.error(f"❌ Критическая ошибка в фоновой задаче очистки постов: {e}", exc_info=True)
            await asyncio.sleep(60 * 30) 


async def main():
    """Главная функция бота"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logfire.info("Переменные окружения из .env загружены.")
    except ImportError:
        logfire.info(".env файл не найден, используются системные переменные окружения.")

    token = os.getenv("BOT_TOKEN")
    if not token:
        logfire.critical("❌ КРИТИЧЕСКАЯ ОШИБКА: BOT_TOKEN не установлен!")
        return

    # --- ИСПРАВЛЕНИЕ: Добавлена критически важная проверка DATABASE_URL ---
    # Приложение не может функционировать без подключения к базе данных.
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logfire.critical("❌ КРИТИЧЕСКАЯ ОШИБКА: DATABASE_URL не установлен!")
        return

    await init_database()
    logfire.info("✅ База данных инициализирована.")

    bot = Bot(token=token, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    register_start_handlers(dp)
    register_user_handlers(dp)
    register_post_handlers(dp)
    register_callback_handlers(dp)
    register_moderation_handlers(dp)
    register_feed_handlers(dp)

    cleanup_task = asyncio.create_task(cleanup_expired_posts_task())
    
    logfire.info("🤖 Бот запускается...")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logfire.error(f"Произошла ошибка в основном цикле бота: {e}", exc_info=True)
    finally:
        logfire.info("🛑 Бот останавливается. Завершаем фоновые задачи...")
        
        cleanup_task.cancel()
        
        await asyncio.gather(cleanup_task, return_exceptions=True)
        
        await bot.session.close()
        logfire.info("✅ Бот успешно остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logfire.info("Программа прервана пользователем (Ctrl+C).")