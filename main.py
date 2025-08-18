#!/usr/bin/env python3
"""
Telegram Events Bot - Основной файл приложения
"""

import os
import logfire

# Конфигурация Logfire должна быть ПЕРВОЙ и до всех других импортов
logfire.configure(
    token=os.getenv("LOGFIRE_TOKEN"),
    project_name="dghdrhd",  # Замените на имя вашего проекта в Logfire
    send_to_logfire=True,
    scrubbing=False,
    debug=True  # Включите для отладки, потом можно отключить
)

# Тестовое сообщение для проверки подключения
logfire.info("🟢 Logfire инициализирован! Проверка подключения...")

import asyncio
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

# Настройка интеграции loguru с Logfire
logger.configure(
    handlers=[logfire.loguru_handler()]
)


async def main():
    """Главная функция бота"""
    # Проверка критических переменных окружения
    logfire_token = os.getenv("LOGFIRE_TOKEN")
    bot_token = os.getenv("BOT_TOKEN")
    
    if not bot_token:
        logfire.critical("❌ BOT_TOKEN не установлен!")
        return
    
    logfire.info(f"🔑 Токен Logfire: {'установлен' if logfire_token else 'не установлен'}")
    logfire.info("🔄 Загрузка переменных окружения...")

    # Подхват переменных окружения из .env, если есть
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logfire.info("✅ .env файл загружен")
    except Exception as e:
        logfire.warning(f"⚠️ Не удалось загрузить .env: {e}")

    # Инициализируем базу данных
    try:
        await init_database()
        logfire.info("✅ База данных инициализирована")
    except Exception as e:
        logfire.error(f"❌ Ошибка инициализации БД: {e}")
        return

    # Создаем бота и диспетчер
    bot = Bot(token=bot_token)
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

    logfire.info("🤖 Бот запускается...")

    async def cleanup_expired_posts_task():
        """Фоновая задача для очистки старых постов"""
        from events_bot.bot.utils import get_db_session
        from events_bot.storage import file_storage
        
        while True:
            try:
                async with get_db_session() as db:
                    expired = await PostService.get_expired_posts_info(db)
                    deleted = await PostService.delete_expired_posts(db)
                    
                    if deleted:
                        logfire.info(f"🧹 Удалено просроченных постов: {deleted}")
                        for row in expired:
                            image_id = row.get("image_id")
                            if image_id:
                                try:
                                    await file_storage.delete_file(image_id)
                                except Exception as e:
                                    logfire.warning(f"⚠️ Ошибка удаления файла {image_id}: {e}")
            except Exception as e:
                logfire.error(f"❌ Ошибка фоновой очистки: {e}")
            await asyncio.sleep(60 * 10)  # Каждые 10 минут

    try:
        logfire.info("🚀 Запуск бота...")
        await asyncio.gather(
            dp.start_polling(bot),
            cleanup_expired_posts_task(),
        )
    except KeyboardInterrupt:
        logfire.info("🛑 Бот остановлен вручную")
    except Exception as e:
        logfire.critical(f"💥 Критическая ошибка: {e}")
    finally:
        await bot.session.close()
        logfire.info("🔌 Сессия бота закрыта")


if __name__ == "__main__":
    # Дополнительная проверка перед запуском
    if not os.getenv("LOGFIRE_TOKEN"):
        print("⚠️ Внимание: LOGFIRE_TOKEN не установлен! Логи не будут отправляться в Logfire")
    
    logfire.info("🔧 Запуск приложения...")
    asyncio.run(main())
