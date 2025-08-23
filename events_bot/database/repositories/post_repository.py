from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from ..models import Post, PostStatus
from typing import List, Optional


class PostRepository:
    """Асинхронный репозиторий для работы с постами"""

    @staticmethod
    async def create_post(
        db: AsyncSession,
        title: str,
        content: str,
        author_id: int,
        category_ids: List[int],
        city: str | None = None,
        image_id: str | None = None,
        event_at=None,
    ) -> Post:
        """Создать новый пост"""
        try:
            post = Post(
                title=title,
                content=content,
                author_id=author_id,
                city=city,
                image_id=image_id,
                event_at=event_at,
                status=PostStatus.PENDING_MODERATION
            )
            db.add(post)
            await db.flush()
            if category_ids:
                stmt = post.categories.insert().values([{"category_id": cid} for cid in category_ids])
                await db.execute(stmt)
            await db.commit()
            return post
        except Exception as e:
            await db.rollback()
            raise

    @staticmethod
    async def get_post_by_id(db: AsyncSession, post_id: int) -> Optional[Post]:
        """Получить пост по ID"""
        stmt = select(Post).where(Post.id == post_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_posts(db: AsyncSession, user_id: int) -> List[Post]:
        """Получить посты пользователя"""
        stmt = select(Post).where(Post.author_id == user_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_posts_by_categories(db: AsyncSession, category_ids: list[int]) -> list[Post]:
        """Получить посты по нескольким категориям"""
        stmt = (
            select(Post)
            .join(Post.categories)
            .where(Post.categories.any(Category.id.in_(category_ids)))
            .order_by(Post.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_pending_moderation(db: AsyncSession) -> List[Post]:
        """Получить посты, ожидающие модерации"""
        stmt = select(Post).where(Post.status == PostStatus.PENDING_MODERATION)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def approve_post(db: AsyncSession, post_id: int, moderator_id: int, comment: str = None) -> Post:
        """Одобрить пост"""
        stmt = (
            update(Post)
            .where(Post.id == post_id)
            .values(
                is_approved=True,
                status=PostStatus.APPROVED,
                updated_at=func.now()
            )
        )
        await db.execute(stmt)
        await db.commit()
        return await PostRepository.get_post_by_id(db, post_id)

    @staticmethod
    async def publish_post(db: AsyncSession, post_id: int) -> Post:
        """Опубликовать одобренный пост"""
        stmt = (
            update(Post)
            .where(Post.id == post_id)
            .values(
                is_published=True,
                status=PostStatus.PUBLISHED,
                published_at=func.now(),
                updated_at=func.now()
            )
        )
        await db.execute(stmt)
        await db.commit()
        return await PostRepository.get_post_by_id(db, post_id)

    @staticmethod
    async def reject_post(db: AsyncSession, post_id: int, moderator_id: int, comment: str = None) -> Post:
        """Отклонить пост"""
        stmt = (
            update(Post)
            .where(Post.id == post_id)
            .values(
                is_approved=False,
                status=PostStatus.REJECTED,
                updated_at=func.now()
            )
        )
        await db.execute(stmt)
        await db.commit()
        return await PostRepository.get_post_by_id(db, post_id)

    @staticmethod
    async def request_changes(db: AsyncSession, post_id: int, moderator_id: int, comment: str = None) -> Post:
        """Запросить изменения в посте"""
        stmt = (
            update(Post)
            .where(Post.id == post_id)
            .values(
                status=PostStatus.DRAFT,
                updated_at=func.now()
            )
        )
        await db.execute(stmt)
        await db.commit()
        return await PostRepository.get_post_by_id(db, post_id)

    @staticmethod
    async def get_feed_posts(db: AsyncSession, user_id: int, limit: int = 10, offset: int = 0) -> List[Post]:
        """Получить посты для ленты пользователя"""
        stmt = (
            select(Post)
            .join(Post.categories)
            .join(Category.users)
            .where(User.id == user_id)
            .where(Post.status == PostStatus.PUBLISHED)
            .order_by(Post.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_feed_posts_count(db: AsyncSession, user_id: int) -> int:
        """Получить общее количество постов для ленты пользователя"""
        stmt = (
            select(func.count(Post.id))
            .join(Post.categories)
            .join(Category.users)
            .where(User.id == user_id)
            .where(Post.status == PostStatus.PUBLISHED)
        )
        result = await db.execute(stmt)
        return result.scalar()

    @staticmethod
    async def get_liked_posts(db: AsyncSession, user_id: int, limit: int = 10, offset: int = 0) -> List[Post]:
        """Получить посты, которым пользователь поставил лайк"""
        stmt = (
            select(Post)
            .join(Post.likes)
            .where(Like.user_id == user_id)
            .order_by(Like.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_liked_posts_count(db: AsyncSession, user_id: int) -> int:
        """Получить количество лайкнутых постов"""
        stmt = select(func.count(Like.id)).where(Like.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar()

    @staticmethod
    async def delete_expired_posts(db: AsyncSession) -> int:
        """Удалить посты, у которых event_at < текущего времени"""
        now = func.now()
        stmt = delete(Post).where(Post.event_at < now).returning(Post.id)
        result = await db.execute(stmt)
        deleted = result.rowcount
        await db.commit()
        return deleted

    @staticmethod
    async def get_expired_posts_info(db: AsyncSession) -> list[dict]:
        """Получить ID и image_id просроченных постов"""
        stmt = select(Post.id, Post.image_id).where(Post.event_at < func.now())
        result = await db.execute(stmt)
        return [row._asdict() for row in result.fetchall()]
