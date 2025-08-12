from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete, insert
from sqlalchemy.orm import selectinload
from typing import List, Optional
from ..models import User, Category, user_categories


class UserRepository:
    """Асинхронный репозиторий для работы с пользователями"""

    @staticmethod
    async def get_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == telegram_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        db: AsyncSession,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
    ) -> User:
        user = User(
            id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_or_create_user(
        db: AsyncSession,
        telegram_id: int,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
    ) -> User:
        user = await UserRepository.get_by_telegram_id(db, telegram_id)
        if not user:
            user = await UserRepository.create_user(
                db, telegram_id, username, first_name, last_name
            )
        return user

    @staticmethod
    async def add_categories_to_user(
        db: AsyncSession, user_id: int, category_ids: List[int]
    ) -> User:
        # Сначала удаляем все существующие связи
        await db.execute(
            delete(user_categories).where(user_categories.c.user_id == user_id)
        )

        # Затем добавляем новые связи одним запросом
        if category_ids:
            values = [
                {"user_id": user_id, "category_id": category_id}
                for category_id in category_ids
            ]
            await db.execute(insert(user_categories).values(values))

        await db.commit()

        # Возвращаем обновленного пользователя
        result = await db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.categories))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_users_by_categories(
        db: AsyncSession, category_ids: List[int]
    ) -> List[User]:
        result = await db.execute(
            select(User)
            .join(User.categories)
            .where(Category.id.in_(category_ids))
            .options(selectinload(User.categories))
        )
        return result.scalars().all()

    @staticmethod
    async def get_users_by_city_and_categories(
        db: AsyncSession, city: str, category_ids: List[int]
    ) -> List[User]:
        """Получить пользователей по городу и категориям"""
        result = await db.execute(
            select(User)
            .join(User.categories)
            .where(and_(User.city == city, Category.id.in_(category_ids)))
            .options(selectinload(User.categories))
        )
        return result.scalars().all()
