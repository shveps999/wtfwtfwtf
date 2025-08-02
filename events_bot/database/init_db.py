from . import get_db_session
from .repositories import CategoryRepository
import logfire

async def init_database():
    """Инициализация начальных данных"""
    async for session in get_db_session():
        try:
            existing = await CategoryRepository.get_all_active(session)
            if not existing:
                categories = [
                    "Технологии", "Спорт", "Культура", "Наука", "Бизнес",
                    "Здоровье", "Образование", "Путешествия", "Кулинария",
                    "Авто", "Мода", "Музыка", "Кино", "Книги", "Игры"
                ]
                
                for name in categories:
                    await CategoryRepository.create_category(session, name=name)
                
                logfire.info("Добавлены категории по умолчанию")
            else:
                logfire.info(f"В БД уже есть {len(existing)} категорий")
            
            await session.commit()
        except Exception as e:
            await session.rollback()
            logfire.error(f"Ошибка инициализации БД: {e}")
            raise
