from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..repositories import CategoryRepository
from ..models import Category


class CategoryService:
    """Асинхронный сервис для работы с категориями"""

    @staticmethod
    async def get_all_categories(db: AsyncSession) -> List[Category]:
        """Получить все доступные категории"""
        return await CategoryRepository.get_all_active(db)

    @staticmethod
    async def get_category_by_id(
        db: AsyncSession, category_id: int
    ) -> Optional[Category]:
        """Получить категорию по ID"""
        return await CategoryRepository.get_by_id(db, category_id)
