from aiogram import Bot
from typing import List
from events_bot.database.models import User, Post
from events_bot.database.services import NotificationService
from events_bot.storage import file_storage
from aiogram.types import FSInputFile, InputMediaPhoto
import logfire


async def send_post_notification(bot: Bot, post: Post, users: List[User], db) -> None:
    """Отправить уведомления о новом посте"""
    logfire.info(f"Отправляем уведомления о посте {post.id} {len(users)} пользователям")
    
    # Загружаем связанные объекты
    await db.refresh(post, attribute_names=["author", "categories"])
    notification_text = NotificationService.format_post_notification(post)

    success_count = 0
    error_count = 0
    
    for user in users:
        try:
            logfire.debug(f"Отправляем уведомление пользователю {user.id}")
            
            # Если у поста есть изображение, отправляем с фото
            if post.image_id:
                media_photo = await file_storage.get_media_photo(post.image_id)
                if media_photo:
                    logfire.debug(f"Отправляем уведомление с изображением пользователю {user.id}")
                    await bot.send_photo(
                        chat_id=user.id,
                        photo=media_photo.media,
                        caption=notification_text
                    )
                else:
                    # Если файл не найден, отправляем только текст
                    logfire.warning(f"Изображение для поста {post.id} не найдено, отправляем только текст")
                    await bot.send_message(chat_id=user.id, text=notification_text)
            else:
                # Если нет изображения, отправляем только текст
                logfire.debug(f"Отправляем уведомление без изображения пользователю {user.id}")
                await bot.send_message(chat_id=user.id, text=notification_text)
            
            success_count += 1
            logfire.debug(f"Уведомление успешно отправлено пользователю {user.id}")
            
        except Exception as e:
            error_count += 1
            logfire.warning(f"Ошибка отправки уведомления пользователю {user.id}: {e}")
    
    logfire.info(f"Уведомления отправлены: успешно={success_count}, ошибок={error_count}")
