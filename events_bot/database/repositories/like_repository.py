from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from typing import List, Optional
from ..models import Like, User, Post


class LikeRepository:
    """Репозиторий для работы с лайками"""

    @staticmethod
    async def add_like(db: AsyncSession, user_id: int, post_id: int) -> Like:
        """Добавить лайк пользователя на пост"""
        # Проверяем, есть ли уже лайк от этого пользователя на этот пост
        existing_like = await LikeRepository.get_user_like(db, user_id, post_id)
        
        if existing_like:
            # Если лайк уже есть, возвращаем существующий
            return existing_like
        else:
            # Если лайка нет, создаём новый
            like = Like(user_id=user_id, post_id=post_id)
            db.add(like)
            await db.commit()
            await db.refresh(like)
            return like

    @staticmethod
    async def remove_like(db: AsyncSession, user_id: int, post_id: int) -> bool:
        """Удалить лайк пользователя на пост"""
        stmt = delete(Like).where(
            and_(Like.user_id == user_id, Like.post_id == post_id)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_user_like(
        db: AsyncSession, user_id: int, post_id: int
    ) -> Optional[Like]:
        """Получить лайк пользователя на конкретный пост"""
        stmt = select(Like).where(
            and_(Like.user_id == user_id, Like.post_id == post_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_post_likes(db: AsyncSession, post_id: int) -> List[Like]:
        """Получить все лайки на пост"""
        stmt = select(Like).where(Like.post_id == post_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_post_likes_count(db: AsyncSession, post_id: int) -> int:
        """Получить количество лайков на пост"""
        stmt = select(Like).where(Like.post_id == post_id)
        result = await db.execute(stmt)
        return len(result.scalars().all())

    @staticmethod
    async def get_user_likes(db: AsyncSession, user_id: int) -> List[Like]:
        """Получить все лайки пользователя"""
        stmt = select(Like).where(Like.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def toggle_like(db: AsyncSession, user_id: int, post_id: int) -> dict:
        """Переключить лайк пользователя на пост"""
        existing_like = await LikeRepository.get_user_like(db, user_id, post_id)
        
        if existing_like:
            # Если лайк уже есть - удаляем его
            await LikeRepository.remove_like(db, user_id, post_id)
            action = "removed"
        else:
            # Если лайка нет - добавляем
            await LikeRepository.add_like(db, user_id, post_id)
            action = "added"
        
        # Получаем обновленное количество лайков
        likes_count = await LikeRepository.get_post_likes_count(db, post_id)
        
        return {
            "action": action,
            "likes_count": likes_count
        } 