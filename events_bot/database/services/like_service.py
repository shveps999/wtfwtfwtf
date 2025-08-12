from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from ..repositories import LikeRepository
from ..models import Like


class LikeService:
    """Сервис для работы с лайками"""

    @staticmethod
    async def add_like(db: AsyncSession, user_id: int, post_id: int) -> Like:
        """Добавить лайк пользователя на пост"""
        return await LikeRepository.add_like(db, user_id, post_id)

    @staticmethod
    async def remove_like(db: AsyncSession, user_id: int, post_id: int) -> bool:
        """Удалить лайк пользователя на пост"""
        return await LikeRepository.remove_like(db, user_id, post_id)

    @staticmethod
    async def get_user_like(
        db: AsyncSession, user_id: int, post_id: int
    ) -> Optional[Like]:
        """Получить лайк пользователя на конкретный пост"""
        return await LikeRepository.get_user_like(db, user_id, post_id)

    @staticmethod
    async def get_post_likes(db: AsyncSession, post_id: int) -> List[Like]:
        """Получить все лайки на пост"""
        return await LikeRepository.get_post_likes(db, post_id)

    @staticmethod
    async def get_post_likes_count(db: AsyncSession, post_id: int) -> int:
        """Получить количество лайков на пост"""
        return await LikeRepository.get_post_likes_count(db, post_id)

    @staticmethod
    async def get_user_likes(db: AsyncSession, user_id: int) -> List[Like]:
        """Получить все лайки пользователя"""
        return await LikeRepository.get_user_likes(db, user_id)

    @staticmethod
    async def toggle_like(
        db: AsyncSession, user_id: int, post_id: int
    ) -> Dict[str, Any]:
        """Переключить лайк пользователя на пост"""
        return await LikeRepository.toggle_like(db, user_id, post_id)

    @staticmethod
    async def is_post_liked_by_user(
        db: AsyncSession, user_id: int, post_id: int
    ) -> bool:
        """Проверить, поставил ли пользователь лайк на пост"""
        like = await LikeService.get_user_like(db, user_id, post_id)
        return like is not None 