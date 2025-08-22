from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, insert, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

# --- ИСПРАВЛЕНИЕ: Импортируем PostStatus для использования в запросах ---
from ..models import Post, ModerationRecord, ModerationAction, Category, post_categories, User, PostStatus, Like


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
        """Создает пост и связывает его с категориями в одной транзакции."""
        # Создаем пост со статусом PENDING
        post = Post(
            title=title,
            content=content,
            author_id=author_id,
            city=city.lower() if city else None,
            image_id=image_id,
            event_at=event_at,
            status=PostStatus.PENDING,  # --- ИСПРАВЛЕНИЕ: Устанавливаем начальный статус ---
        )
        
        if category_ids:
            # Получаем реальные объекты категорий для связи
            categories_result = await db.execute(select(Category).where(Category.id.in_(category_ids)))
            post.categories = categories_result.scalars().all()

        db.add(post)
        # --- ИСПРАВЛЕНИЕ: Один commit для всех операций для атомарности ---
        await db.commit()
        await db.refresh(post)
        
        return post

    @staticmethod
    async def get_pending_moderation(db: AsyncSession) -> List[Post]:
        """Получает посты, ожидающие модерации."""
        result = await db.execute(
            select(Post)
            .where(Post.status == PostStatus.PENDING) # --- ИСПРАВЛЕНИЕ: Используем статус ---
            .options(selectinload(Post.author), selectinload(Post.categories))
            .order_by(Post.created_at.asc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_approved_posts(
        db: AsyncSession, city: str, category_ids: Optional[List[int]] = None,
        page: int = 1, page_size: int = 5
    ) -> List[Post]:
        """Получает опубликованные посты с фильтрацией и пагинацией."""
        query = (
            select(Post)
            .where(
                Post.status == PostStatus.PUBLISHED, # --- ИСПРАВЛЕНИЕ: Используем статус ---
                Post.city == city.lower(),
                # --- ИСПРАВЛЕНИЕ: Сравниваем с func.utcnow() для консистентности ---
                Post.event_at > func.utcnow() 
            )
            .options(selectinload(Post.author), selectinload(Post.categories))
            .order_by(Post.published_at.desc())
        )

        if category_ids:
            # Используем .any() для проверки вхождения хотя бы в одну из категорий
            query = query.join(Post.categories).where(Category.id.in_(category_ids))
        
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        # .unique() нужен, когда join может дублировать строки
        return result.unique().scalars().all()

    @staticmethod
    async def update_post_status(
        db: AsyncSession, post_id: int, status: PostStatus, moderator_id: int, comment: Optional[str] = None
    ) -> Optional[Post]:
        """Обновляет статус поста и создает запись модерации."""
        post = await db.get(Post, post_id, options=[selectinload(Post.author)])
        if not post:
            return None
        
        post.status = status
        post.moderator_id = moderator_id

        # Создаем запись в истории модерации
        action_map = {
            PostStatus.APPROVED: ModerationAction.APPROVE,
            PostStatus.PUBLISHED: ModerationAction.APPROVE, # Публикация - это тоже результат одобрения
            PostStatus.REJECTED: ModerationAction.REJECT,
            PostStatus.CHANGES_REQUESTED: ModerationAction.REQUEST_CHANGES,
        }
        
        # Только для релевантных статусов создаем запись
        if status in action_map:
            moderation_record = ModerationRecord(
                post_id=post_id,
                moderator_id=moderator_id,
                action=action_map[status],
                comment=comment,
            )
            db.add(moderation_record)

        if status == PostStatus.PUBLISHED:
            # --- ИСПРАВЛЕНИЕ: Используем func.utcnow() ---
            post.published_at = func.utcnow()

        await db.commit()
        await db.refresh(post)
        return post

    @staticmethod
    async def get_user_posts(db: AsyncSession, user_id: int) -> List[Post]:
        result = await db.execute(
            select(Post)
            .where(Post.author_id == user_id)
            .options(selectinload(Post.categories))
            .order_by(Post.created_at.desc())
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
    async def get_feed_posts(
        db: AsyncSession, user_id: int, limit: int = 10, offset: int = 0
    ) -> List[Post]:
        """Получить посты для ленты пользователя по его категориям."""
        user = await db.get(User, user_id, options=[selectinload(User.categories)])
        if not user or not user.categories:
            return []
        
        category_ids = [cat.id for cat in user.categories]
        
        result = await db.execute(
            select(Post)
            .join(Post.categories)
            .where(
                Category.id.in_(category_ids),
                Post.status == PostStatus.PUBLISHED,
                # --- ИСПРАВЛЕНИЕ: Сравниваем с func.utcnow() ---
                or_(Post.event_at.is_(None), Post.event_at > func.utcnow()),
            )
            .options(selectinload(Post.author), selectinload(Post.categories))
            .order_by(Post.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.unique().scalars().all()

    @staticmethod
    async def get_feed_posts_count(db: AsyncSession, user_id: int) -> int:
        """Получить общее количество постов для ленты пользователя."""
        user = await db.get(User, user_id, options=[selectinload(User.categories)])
        if not user or not user.categories:
            return 0
        
        category_ids = [cat.id for cat in user.categories]
        
        result = await db.execute(
            select(func.count(Post.id))
            .join(Post.categories)
            .where(
                Category.id.in_(category_ids),
                Post.status == PostStatus.PUBLISHED,
                # --- ИСПРАВЛЕНИЕ: Сравниваем с func.utcnow() ---
                or_(Post.event_at.is_(None), Post.event_at > func.utcnow()),
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def get_liked_posts(
        db: AsyncSession, user_id: int, limit: int = 10, offset: int = 0
    ) -> List[Post]:
        """Получает посты, которые лайкнул пользователь."""
        result = await db.execute(
            select(Post)
            .join(Like, Like.post_id == Post.id)
            .where(
                Like.user_id == user_id,
                Post.status == PostStatus.PUBLISHED,
                # --- ИСПРАВЛЕНИЕ: Сравниваем с func.utcnow() ---
                or_(Post.event_at.is_(None), Post.event_at > func.utcnow()),
            )
            .options(selectinload(Post.author), selectinload(Post.categories))
            .order_by(Post.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.unique().scalars().all()

    @staticmethod
    async def get_liked_posts_count(db: AsyncSession, user_id: int) -> int:
        """Подсчитывает количество постов, которые лайкнул пользователь."""
        result = await db.execute(
            select(func.count(Post.id))
            .join(Like, Like.post_id == Post.id)
            .where(
                Like.user_id == user_id,
                Post.status == PostStatus.PUBLISHED,
                # --- ИСПРАВЛЕНИЕ: Сравниваем с func.utcnow() ---
                or_(Post.event_at.is_(None), Post.event_at > func.utcnow()),
            )
        )
        return result.scalar() or 0
        
    @staticmethod
    async def delete_expired_posts(db: AsyncSession) -> int:
        """Находит и архивирует посты, у которых наступило event_at."""
        stmt = (
            select(Post.id)
            .where(
                Post.status == PostStatus.PUBLISHED,
                Post.event_at.is_not(None),
                # --- ИСПРАВЛЕНИЕ: Сравниваем с func.utcnow() ---
                Post.event_at <= func.utcnow()
            )
        )
        expired_post_ids = (await db.execute(stmt)).scalars().all()
        
        if not expired_post_ids:
            return 0
            
        for post_id in expired_post_ids:
            post = await db.get(Post, post_id)
            if post:
                post.status = PostStatus.ARCHIVED
        
        await db.commit()
        return len(expired_post_ids)

    @staticmethod
    async def get_expired_posts_info(db: AsyncSession) -> list[dict]:
        """Вернуть информацию о просроченных постах для очистки файлов."""
        result = await db.execute(
            select(Post.id, Post.image_id)
            .where(
                Post.status == PostStatus.PUBLISHED,
                Post.event_at.is_not(None),
                # --- ИСПРАВЛЕНИЕ: Сравниваем с func.utcnow() ---
                Post.event_at <= func.utcnow()
            )
        )
        rows = result.all()
        return [{"id": row[0], "image_id": row[1]} for row in rows]