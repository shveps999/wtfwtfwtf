from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from ..models import Category


class CategoryRepository:
    """Асинхронный репозиторий для работы с категориями"""

    @staticmethod
    async def get_all_active(db: AsyncSession) -> List[Category]:
        result = await db.execute(select(Category).where(Category.is_active == True))
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, category_id: int) -> Optional[Category]:
        result = await db.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_category(
        db: AsyncSession, name: str, description: str = None
    ) -> Category:
        category = Category(name=name, description=description)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category
