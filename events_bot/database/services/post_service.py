from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..repositories import PostRepository
from ..models import Post
import os
import logfire
from events_bot.bot.keyboards.moderation_keyboard import get_moderation_keyboard
from events_bot.storage import file_storage
from aiogram.types import FSInputFile
from .moderation_service import ModerationService
from datetime import datetime


class PostService:
    """Асинхронный сервис для работы с постами"""

    @staticmethod
    async def create_post_and_send_to_moderation(
        db: AsyncSession,
        title: str,
        content: str,
        author_id: int,
        category_ids: List[int],
        city: str = None,
        image_id: str = None,
        event_datetime: datetime = None,
        bot=None
    ) -> Post:
        post = await PostRepository.create_post(
            db=db,
            title=title,
            content=content,
            author_id=author_id,
            category_ids=category_ids,
            city=city,
            image_id=image_id,
            event_datetime=event_datetime
        )
        if post and bot:
            await PostService.send_post_to_moderation(bot, post, db)
        return post

    @staticmethod
    async def send_post_to_moderation(bot, post: Post, db=None):
        moderation_group_id = os.getenv("MODERATION_GROUP_ID")
        if not moderation_group_id:
            logfire.error("MODERATION_GROUP_ID не установлен")
            return

        if db:
            await db.refresh(post, attribute_names=["author", "categories"])

        author_name = post.author.first_name or post.author.username or "Аноним"
        category_names = [cat.name for cat in post.categories] if post.categories else ["Без категории"]

        text = (
            f"📬 Новый пост на модерацию\n"
            f"📝 Заголовок: {post.title}\n"
            f"👤 Автор: {author_name}\n"
            f"🏙️ Город: {post.city or 'Не указан'}\n"
            f"🏷️ Категории: {', '.join(category_names)}\n"
            f"📅 Событие: {post.event_datetime.strftime('%d.%m.%Y %H:%M') if post.event_datetime else 'Бессрочное'}"
        )

        keyboard = get_moderation_keyboard(post.id)
        try:
            if post.image_id:
                file_path = await file_storage.get_file_path(post.image_id)
                if file_path:
                    await bot.send_photo(
                        chat_id=moderation_group_id,
                        photo=FSInputFile(file_path),
                        caption=text,
                        reply_markup=keyboard
                    )
                else:
                    await bot.send_message(moderation_group_id, text, reply_markup=keyboard)
            else:
                await bot.send_message(moderation_group_id, text, reply_markup=keyboard)
        except Exception as e:
            logfire.error(f"Ошибка отправки поста на модерацию: {e}")

    @staticmethod
    async def get_user_posts(db: AsyncSession, user_id: int) -> List[Post]:
        return await PostRepository.get_user_posts(db, user_id)

    @staticmethod
    async def get_post_by_id(db: AsyncSession, post_id: int) -> Optional[Post]:
        return await PostRepository.get_post_by_id(db, post_id)

    @staticmethod
    async def approve_post(db: AsyncSession, post_id: int, moderator_id: int, comment: str = None) -> Post:
        return await PostRepository.approve_post(db, post_id, moderator_id, comment)

    @staticmethod
    async def publish_post(db: AsyncSession, post_id: int) -> Post:
        return await PostRepository.publish_post(db, post_id)

    @staticmethod
    async def reject_post(db: AsyncSession, post_id: int, moderator_id: int, comment: str = None) -> Post:
        return await PostRepository.reject_post(db, post_id, moderator_id, comment)

    @staticmethod
    async def request_changes(db: AsyncSession, post_id: int, moderator_id: int, comment: str = None) -> Post:
        return await PostRepository.request_changes(db, post_id, moderator_id, comment)

    @staticmethod
    async def get_feed_posts(db: AsyncSession, user_id: int, limit: int = 10, offset: int = 0) -> List[Post]:
        return await PostRepository.get_feed_posts(db, user_id, limit, offset)

    @staticmethod
    async def get_feed_posts_count(db: AsyncSession, user_id: int) -> int:
        return await PostRepository.get_feed_posts_count(db, user_id)
