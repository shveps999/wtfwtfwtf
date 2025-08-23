from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timezone
from ..repositories import PostRepository
from ..models import Post
import os
import logfire
from events_bot.bot.keyboards.moderation_keyboard import get_moderation_keyboard
from events_bot.storage import file_storage
from .moderation_service import ModerationService
from aiogram import Bot
from aiogram.types import InputMediaPhoto
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest


class PostService:
    """Асинхронный сервис для работы с постами"""

    @staticmethod
    async def create_post(
        db: AsyncSession,
        title: str,
        content: str,
        author_id: int,
        category_ids: List[int],
        city: str | None = None,
        image_id: str | None = None,
        event_at: str | None = None,
    ) -> Post:
        """Создать новый пост"""
        parsed_event_at = None
        if event_at is not None:
            try:
                parsed_event_at = datetime.fromisoformat(event_at)
                if parsed_event_at.tzinfo is not None:
                    parsed_event_at = parsed_event_at.astimezone(timezone.utc)
                parsed_event_at = parsed_event_at.replace(tzinfo=None)
            except Exception:
                parsed_event_at = None
        return await PostRepository.create_post(
            db, title, content, author_id, category_ids, city, image_id, parsed_event_at
        )

    @staticmethod
    async def create_post_and_send_to_moderation(
        db: AsyncSession,
        title: str,
        content: str,
        author_id: int,
        category_ids: List[int],
        city: str | None = None,
        image_id: str | None = None,
        event_at: str | None = None,
        bot=None,
    ) -> Post:
        """Создать пост и отправить на модерацию"""
        # Уникализация категорий
        category_ids = list(set(category_ids))
        if not title.strip() or not content.strip():
            logfire.error("Заголовок или содержание пусты")
            return None

        # Создаем пост
        parsed_event_at = None
        if event_at is not None:
            try:
                parsed_event_at = datetime.fromisoformat(event_at)
                if parsed_event_at.tzinfo is not None:
                    parsed_event_at = parsed_event_at.astimezone(timezone.utc)
                parsed_event_at = parsed_event_at.replace(tzinfo=None)
            except Exception:
                parsed_event_at = None
        post = await PostRepository.create_post(
            db, title, content, author_id, category_ids, city, image_id, parsed_event_at
        )

        # Отправляем на модерацию
        if post and bot:
            await PostService.send_post_to_moderation(bot, post, db)

        return post

    @staticmethod
    async def send_post_to_moderation(bot: Bot, post: Post, db=None):
        """Отправить пост на модерацию"""
        moderation_group_id_str = os.getenv("MODERATION_GROUP_ID")
        logfire.info(f"MODERATION_GROUP_ID: {moderation_group_id_str}")

        if not moderation_group_id_str:
            logfire.error("MODERATION_GROUP_ID не установлен")
            return

        try:
            moderation_group_id = int(moderation_group_id_str)
        except ValueError:
            logfire.error(f"Некорректный MODERATION_GROUP_ID: {moderation_group_id_str}")
            return

        if db:
            await db.refresh(post, attribute_names=["author", "categories"])

        moderation_text = ModerationService.format_post_for_moderation(post)
        moderation_keyboard = get_moderation_keyboard(post.id)

        logfire.info(f"Отправляем пост {post.id} на модерацию в группу {moderation_group_id}")

        try:
            if post.image_id:
                media_photo = await file_storage.get_media_photo(post.image_id)
                if media_photo:
                    await bot.send_photo(
                        chat_id=moderation_group_id,
                        photo=media_photo.media,
                        caption=moderation_text,
                        reply_markup=moderation_keyboard
                    )
                    logfire.info("Пост с фото отправлен")
                    return

            await bot.send_message(
                chat_id=moderation_group_id,
                text=moderation_text,
                reply_markup=moderation_keyboard
            )
            logfire.info("Пост без фото отправлен")

        except TelegramForbiddenError:
            logfire.error("Бот не имеет прав на отправку в группу")
        except TelegramBadRequest as e:
            logfire.error(f"Неверный запрос: {e}")
        except Exception as e:
            logfire.error(f"Неизвестная ошибка отправки: {e}")
            import traceback
            logfire.error(f"Стек: {traceback.format_exc()}")
