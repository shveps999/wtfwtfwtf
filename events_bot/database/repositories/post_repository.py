from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, insert, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
from ..models import Post, ModerationRecord, ModerationAction, Category, post_categories
from ..models import User


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
        event_at: datetime | None = None,
    ) -> Post:
        # Создаем пост
        post = Post(
            title=title,
            content=content,
            author_id=author_id,
            city=city,
            image_id=image_id,
            event_at=event_at,
        )
        db.add(post)
        await db.commit()
        
        # Добавляем категории к посту в отдельной транзакции
        await db.execute(
            insert(post_categories).values(
                [{'post_id': post.id, 'category_id': category} for category in category_ids]
            )
        )
        await db.commit()
        await db.refresh(post)
        
        return post

    @staticmethod
    async def get_pending_moderation(db: AsyncSession) -> List[Post]:
        result = await db.execute(
            select(Post)
            .where(and_(Post.is_approved == False, Post.is_published == False))
            .options(selectinload(Post.author), selectinload(Post.categories))
        )
        return result.scalars().all()

    @staticmethod
    async def get_approved_posts(db: AsyncSession) -> List[Post]:
        result = await db.execute(
            select(Post)
            .where(
                and_(
                    Post.is_approved == True,
                    (Post.event_at.is_(None) | (Post.event_at > func.now())),
                )
            )
            .options(selectinload(Post.author), selectinload(Post.categories))
        )
        return result.scalars().all()

    @staticmethod
    async def get_posts_by_categories(
        db: AsyncSession, category_ids: List[int]
    ) -> List[Post]:
        result = await db.execute(
            select(Post)
            .join(Post.categories)
            .where(
                and_(
                    Post.categories.any(Category.id.in_(category_ids)),
                    Post.is_approved == True,
                    Post.is_published == True,
                    (Post.event_at.is_(None) | (Post.event_at > func.now())),
                )
            )
            .options(selectinload(Post.author), selectinload(Post.categories))
        )
        return result.scalars().all()

    @staticmethod
    async def approve_post(
        db: AsyncSession, post_id: int, moderator_id: int, comment: str = None
    ) -> Post:
        result = await db.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()
        if post:
            post.is_approved = True
            post.is_published = True
            post.published_at = func.now()
            moderation_record = ModerationRecord(
                post_id=post_id,
                moderator_id=moderator_id,
                action=ModerationAction.APPROVE,
                comment=comment,
            )
            db.add(moderation_record)
            await db.commit()
            await db.refresh(post)
        return post

    @staticmethod
    async def reject_post(
        db: AsyncSession, post_id: int, moderator_id: int, comment: str = None
    ) -> Post:
        result = await db.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()
        if post:
            post.is_approved = False
            post.is_published = False
            moderation_record = ModerationRecord(
                post_id=post_id,
                moderator_id=moderator_id,
                action=ModerationAction.REJECT,
                comment=comment,
            )
            db.add(moderation_record)
            await db.commit()
            await db.refresh(post)
        return post

    @staticmethod
    async def request_changes(
        db: AsyncSession, post_id: int, moderator_id: int, comment: str = None
    ) -> Post:
        result = await db.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()
        if post:
            moderation_record = ModerationRecord(
                post_id=post_id,
                moderator_id=moderator_id,
                action=ModerationAction.REQUEST_CHANGES,
                comment=comment,
            )
            db.add(moderation_record)
            await db.commit()
            await db.refresh(post)
        return post

    @staticmethod
    async def get_user_posts(db: AsyncSession, user_id: int) -> List[Post]:
        result = await db.execute(
            select(Post)
            .where(Post.author_id == user_id)
            .options(selectinload(Post.categories))
        )
        return result.scalars().all()

    @staticmethod
    async def get_post_by_id(db: AsyncSession, post_id: int) -> Optional[Post]:
        result = await db.execute(
            select(Post)
            .where(Post.id == post_id)
            .options(selectinload(Post.author), selectinload(Post.categories))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def publish_post(db: AsyncSession, post_id: int) -> Post:
        result = await db.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()
        if post:
            post.is_published = True
            post.published_at = func.now()
            await db.commit()
            await db.refresh(post)
        return post

    @staticmethod
    async def get_feed_posts(
        db: AsyncSession, user_id: int, limit: int = 10, offset: int = 0
    ) -> List[Post]:
        """Получить посты для ленты пользователя (по его категориям, исключая его посты)"""
        # Получаем категории пользователя
        user_categories_result = await db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.categories))
        )
        user = user_categories_result.scalar_one_or_none()
        if not user or not user.categories:
            return []
        
        category_ids = [cat.id for cat in user.categories]
        
        # Получаем посты по категориям пользователя, исключая его собственные
        now_utc = func.now()
        result = await db.execute(
            select(Post)
            .join(Post.categories)
            .where(
                and_(
                    Post.categories.any(Category.id.in_(category_ids)),
                    Post.is_approved == True,
                    Post.is_published == True,
                    or_(Post.event_at.is_(None), Post.event_at > now_utc),
                )
            )
            .options(selectinload(Post.author), selectinload(Post.categories))
            .order_by(Post.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def get_feed_posts_count(db: AsyncSession, user_id: int) -> int:
        """Получить общее количество постов для ленты пользователя"""
        # Получаем категории пользователя
        user_categories_result = await db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.categories))
        )
        user = user_categories_result.scalar_one_or_none()
        if not user or not user.categories:
            return 0
        
        category_ids = [cat.id for cat in user.categories]
        
        # Подсчитываем количество постов
        result = await db.execute(
            select(func.count(Post.id))
            .join(Post.categories)
            .where(
                and_(
                    Post.categories.any(Category.id.in_(category_ids)),
                    Post.is_approved == True,
                    Post.is_published == True,
                    or_(Post.event_at.is_(None), Post.event_at > func.now()),
                )
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def get_liked_posts(
        db: AsyncSession, user_id: int, limit: int = 10, offset: int = 0
    ) -> List[Post]:
        from ..models import Like
        result = await db.execute(
            select(Post)
            .join(Like, Like.post_id == Post.id)
            .where(
                and_(
                    Like.user_id == user_id,
                    Post.is_approved == True,
                    Post.is_published == True,
                    or_(Post.event_at.is_(None), Post.event_at > func.now()),
                )
            )
            .options(selectinload(Post.author), selectinload(Post.categories))
            .order_by(Post.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def get_liked_posts_count(db: AsyncSession, user_id: int) -> int:
        from ..models import Like
        result = await db.execute(
            select(func.count(Post.id))
            .join(Like, Like.post_id == Post.id)
            .where(
                and_(
                    Like.user_id == user_id,
                    Post.is_approved == True,
                    Post.is_published == True,
                    or_(Post.event_at.is_(None), Post.event_at > func.now()),
                )
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def delete_expired_posts(db: AsyncSession) -> int:
        """Удалить посты, у которых наступило event_at, вместе со связями"""
        from ..models import Like, ModerationRecord
        # Ищем просроченные посты
        expired_posts = await db.execute(
            select(Post.id).where(Post.event_at.is_not(None), Post.event_at <= func.now())
        )
        post_ids = [pid for pid in expired_posts.scalars().all()]
        if not post_ids:
            return 0
        # Удаляем связанные лайки
        await db.execute(
            Like.__table__.delete().where(Like.post_id.in_(post_ids))
        )
        # Удаляем записи модерации
        await db.execute(
            ModerationRecord.__table__.delete().where(ModerationRecord.post_id.in_(post_ids))
        )
        # Удаляем связи постов с категориями
        await db.execute(
            post_categories.delete().where(post_categories.c.post_id.in_(post_ids))
        )
        # Удаляем сами посты
        result = await db.execute(
            Post.__table__.delete().where(Post.id.in_(post_ids))
        )
        await db.commit()
        return result.rowcount or 0

    @staticmethod
    async def get_expired_posts_info(db: AsyncSession) -> list[dict]:
        """Вернуть информацию о просроченных постах (id, image_id)"""
        result = await db.execute(
            select(Post.id, Post.image_id).where(
                and_(Post.event_at.is_not(None), Post.event_at <= func.now())
            )
        )
        rows = result.all()
        return [{"id": row[0], "image_id": row[1]} for row in rows]
