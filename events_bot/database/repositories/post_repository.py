from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload
from typing import List, Optional
from ..models import Post
from datetime import datetime


class PostRepository:
    """Асинхронный репозиторий для работы с постами"""

    @staticmethod
    async def create_post(
        db: AsyncSession,
        title: str,
        content: str,
        author_id: int,
        category_ids: List[int],
        city: str = None,
        image_id: str = None,
        event_datetime: datetime = None
    ) -> Post:
        post = Post(
            title=title,
            content=content,
            author_id=author_id,
            city=city,
            image_id=image_id,
            event_datetime=event_datetime
        )
        db.add(post)
        await db.commit()
        await db.refresh(post)

        for cat_id in category_ids:
            db.execute(
                post_categories.insert().values(post_id=post.id, category_id=cat_id)
            )
        await db.commit()
        await db.refresh(post)
        return post

    @staticmethod
    async def get_user_posts(db: AsyncSession, user_id: int) -> List[Post]:
        result = await db.execute(
            select(Post)
            .where(Post.author_id == user_id)
            .order_by(Post.id.desc())
            .options(selectinload(Post.categories))
        )
        return result.scalars().all()

    @staticmethod
    async def get_post_by_id(db: AsyncSession, post_id: int) -> Optional[Post]:
        result = await db.execute(
            select(Post)
            .where(Post.id == post_id)
            .options(selectinload(Post.categories))
        )
        return result.scalar()

    @staticmethod
    async def get_pending_moderation(db: AsyncSession) -> List[Post]:
        result = await db.execute(
            select(Post)
            .where(Post.is_approved == False, Post.is_published == False)
            .options(selectinload(Post.categories))
        )
        return result.scalars().all()

    @staticmethod
    async def approve_post(db: AsyncSession, post_id: int, moderator_id: int, comment: str = None) -> Post:
        stmt = (
            update(Post)
            .where(Post.id == post_id)
            .values(is_approved=True)
            .returning(Post)
        )
        result = await db.execute(stmt)
        post = result.scalar()
        await db.commit()
        return post

    @staticmethod
    async def publish_post(db: AsyncSession, post_id: int) -> Post:
        stmt = (
            update(Post)
            .where(Post.id == post_id)
            .values(is_published=True, published_at=datetime.now())
            .returning(Post)
        )
        result = await db.execute(stmt)
        post = result.scalar()
        await db.commit()
        return post

    @staticmethod
    async def reject_post(db: AsyncSession, post_id: int, moderator_id: int, comment: str = None) -> Post:
        stmt = (
            update(Post)
            .where(Post.id == post_id)
            .values(is_approved=False, is_published=False)
            .returning(Post)
        )
        result = await db.execute(stmt)
        post = result.scalar()
        await db.commit()
        return post

    @staticmethod
    async def request_changes(db: AsyncSession, post_id: int, moderator_id: int, comment: str = None) -> Post:
        stmt = (
            update(Post)
            .where(Post.id == post_id)
            .values(is_approved=False, is_published=False)
            .returning(Post)
        )
        result = await db.execute(stmt)
        post = result.scalar()
        await db.commit()
        return post

    @staticmethod
    async def get_feed_posts(db: AsyncSession, user_id: int, limit: int = 10, offset: int = 0) -> List[Post]:
        result = await db.execute(
            select(Post)
            .join(Post.categories)
            .where(
                Post.categories.any(Post.categories.id.in_(user_categories)),
                Post.author_id != user_id,
                Post.is_approved == True,
                Post.is_published == True,
                (Post.event_datetime > datetime.now()) | (Post.event_datetime.is_(None))
            )
            .order_by(Post.published_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(Post.categories))
        )
        return result.scalars().all()

    @staticmethod
    async def get_feed_posts_count(db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            select(func.count(Post.id))
            .join(Post.categories)
            .where(
                Post.categories.any(Post.categories.id.in_(user_categories)),
                Post.author_id != user_id,
                Post.is_approved == True,
                Post.is_published == True,
                (Post.event_datetime > datetime.now()) | (Post.event_datetime.is_(None))
            )
        )
        return result.scalar()

    @staticmethod
    async def get_expired_posts(db: AsyncSession, current_time: datetime) -> List[Post]:
        result = await db.execute(
            select(Post).where(
                Post.event_datetime <= current_time,
                Post.is_published == True
            )
        )
        return result.scalars().all()

    @staticmethod
    async def delete_post(db: AsyncSession, post_id: int):
        post = await db.get(Post, post_id)
        if post:
            await db.delete(post)
            await db.commit()
