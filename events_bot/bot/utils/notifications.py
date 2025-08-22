from aiogram import Bot
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import logfire

from events_bot.database.models import User, Post
from events_bot.database.services import NotificationService
from events_bot.storage import file_storage
# --- ИСПРАВЛЕНИЕ: Прямые импорты из aiogram.types убраны, т.к. не используются ---


async def send_post_notification(bot: Bot, post: Post, users: List[User], db: AsyncSession) -> None:
    """Отправить уведомления о новом посте пользователям."""
    logfire.info(f"Начало отправки уведомлений о посте {post.id} для {len(users)} пользователей.")
    
    # --- ИСПРАВЛЕНИЕ: Удален ненужный вызов db.refresh ---
    # Предполагается, что объект `post` уже содержит все необходимые связанные данные (author, categories),
    # загруженные через `selectinload` в сервисе, который вызывает эту функцию.
    # await db.refresh(post, attribute_names=["author", "categories"])
    
    # Форматируем текст уведомления один раз
    notification_text = NotificationService.format_post_notification(post)

    success_count = 0
    error_count = 0
    
    for user in users:
        try:
            # Если у поста есть изображение, пытаемся отправить с ним
            if post.image_id:
                media_photo = await file_storage.get_media_photo(post.image_id)
                if media_photo:
                    await bot.send_photo(
                        chat_id=user.id,
                        photo=media_photo.media,
                        caption=notification_text,
                        reply_markup=NotificationService.get_like_keyboard(post.id) # Добавляем кнопку лайка
                    )
                else:
                    # Если файл не найден, отправляем только текст
                    logfire.warning(f"Изображение {post.image_id} для поста {post.id} не найдено, отправляем уведомление текстом.")
                    await bot.send_message(
                        chat_id=user.id, 
                        text=notification_text,
                        reply_markup=NotificationService.get_like_keyboard(post.id) # Добавляем кнопку лайка
                    )
            else:
                # Если изображения нет, отправляем только текст
                await bot.send_message(
                    chat_id=user.id, 
                    text=notification_text,
                    reply_markup=NotificationService.get_like_keyboard(post.id) # Добавляем кнопку лайка
                )
            
            success_count += 1
        except Exception as e:
            error_count += 1
            # Логируем ошибку, но не прерываем цикл, чтобы остальные пользователи получили уведомление
            logfire.warning(f"Ошибка при отправке уведомления пользователю {user.id} для поста {post.id}: {e}")
    
    logfire.info(f"Рассылка уведомлений о посте {post.id} завершена: успешно={success_count}, с ошибками={error_count}.")