from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import logfire
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..repositories import UserRepository
from ..models import User, Post


class NotificationService:
    """Асинхронный сервис для работы с уведомлениями"""

    @staticmethod
    async def get_users_to_notify(db: AsyncSession, post: Post) -> List[User]:
        """
        Получить пользователей для уведомления о новом посте.
        Предполагается, что `post.categories` уже загружены через `selectinload`.
        """
        # --- ИСПРАВЛЕНИЕ: Удален ненужный вызов db.refresh для повышения производительности ---
        # Ответственность за загрузку связей (categories, author) лежит на коде,
        # который изначально получает объект `post` из БД.
        # await db.refresh(post, attribute_names=["author", "categories"])
        
        # Безопасно получаем ID категорий, проверяя, что связь загружена
        if not hasattr(post, 'categories') or not post.categories:
            logfire.warning(f"У поста {post.id} не загружены или отсутствуют категории. Уведомления не будут отправлены.")
            return []
        
        category_ids = [cat.id for cat in post.categories]
        post_city = getattr(post, 'city', None)
        logfire.info(f"Поиск пользователей для уведомления: город={post_city}, категории={category_ids}")
        
        users = await UserRepository.get_users_by_city_and_categories(
            db, post_city, category_ids
        )

        # Исключаем автора поста из списка получателей
        filtered_users = [user for user in users if user.id != post.author_id]
        logfire.info(f"Найдено {len(filtered_users)} пользователей для уведомления (автор поста исключен).")
        
        return filtered_users

    @staticmethod
    def format_post_notification(post: Post) -> str:
        """Форматировать текст уведомления о посте."""
        # Безопасно получаем данные, чтобы избежать ошибок ленивой загрузки (lazy load)
        category_names = []
        if hasattr(post, 'categories') and post.categories:
            category_names = [getattr(cat, 'name', 'Неизвестно') for cat in post.categories]
        
        category_str = ', '.join(category_names) if category_names else 'Без категории'
        
        author_name = 'Аноним'
        if hasattr(post, 'author') and post.author:
            author = post.author
            author_name = getattr(author, 'first_name', None) or getattr(author, 'username', 'Аноним')
        
        event_at = getattr(post, 'event_at', None)
        event_str = event_at.strftime('%d.%m.%Y %H:%M (UTC)') if event_at else 'Бессрочно'
        
        return (
            f"📬 Новое событие в категориях: {category_str}\n\n"
            f"<b>{post.title}</b>\n\n"
            f"<i>{post.content}</i>\n\n"
            f"👤 Автор: {author_name}\n"
            f"📅 Актуально до: {event_str}"
        )

    @staticmethod
    def get_like_keyboard(post_id: int, liked: bool = False) -> InlineKeyboardMarkup:
        """Создать клавиатуру с кнопкой лайка."""
        button_text = "❤️ В избранном" if liked else "🤍 В избранное"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=button_text, callback_data=f"like_post_{post_id}")]
            ]
        )
        return keyboard