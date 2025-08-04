import asyncio
from datetime import datetime
import logfire
from sqlalchemy.ext.asyncio import AsyncSession
from events_bot.database.connection import get_db
from events_bot.repositories.post_repository import PostRepository
from aiogram import Bot


async def cleanup_expired_posts(bot: Bot, interval: int = 3600):
    """
    Фоновая задача: удаляет посты, у которых event_datetime <= now
    Выполняется каждые `interval` секунд (по умолчанию — раз в час)
    """
    logfire.info("Запущена фоновая задача очистки устаревших постов")
    while True:
        try:
            # Получаем сессию БД
            async for db in get_db():
                # Получаем все посты, у которых событие уже прошло
                expired_posts = await PostRepository.get_expired_posts(db, datetime.now())
                
                for post in expired_posts:
                    # Удаляем пост
                    await PostRepository.delete_post(db, post.id)
                    logfire.info(f"Пост {post.id} удален — событие прошло: {post.event_datetime}")

                    # Пытаемся уведомить автора
                    try:
                        await bot.send_message(
                            post.author_id,
                            f"🗑️ Ваш пост *{post.title}* был автоматически удалён, так как событие уже прошло.",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logfire.error(f"Не удалось уведомить автора {post.author_id}: {e}")

                # Важно: выходим из цикла сессии
                break

            # Ждём перед следующей проверкой
            await asyncio.sleep(interval)

        except Exception as e:
            logfire.exception("Ошибка в задаче cleanup_expired_posts", e=e)
            await asyncio.sleep(interval)
