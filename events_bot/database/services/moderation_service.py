from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..repositories import PostRepository, ModerationRepository
from ..models import Post, ModerationAction


class ModerationService:
    """Асинхронный сервис для работы с модерацией"""

    @staticmethod
    async def get_moderation_queue(db: AsyncSession) -> List[Post]:
        """Получить очередь модерации"""
        return await PostRepository.get_pending_moderation(db)

    @staticmethod
    async def get_moderation_history(db: AsyncSession, post_id: int) -> List:
        """Получить историю модерации поста"""
        return await ModerationRepository.get_moderation_history(db, post_id)

    @staticmethod
    async def get_actions_by_type(db: AsyncSession, action: ModerationAction) -> List:
        """Получить записи модерации по типу действия"""
        return await ModerationRepository.get_actions_by_type(db, action)

    @staticmethod
    def format_post_for_moderation(post: Post) -> str:
        """Форматировать пост для модерации"""
        # Безопасно получаем данные, избегая ленивой загрузки
        category_names = []
        if hasattr(post, 'categories') and post.categories is not None:
            category_names = [getattr(cat, 'name', 'Неизвестно') for cat in post.categories]
        
        category_str = ', '.join(category_names) if category_names else 'Неизвестно'
        
        author_name = 'Аноним'
        if hasattr(post, 'author') and post.author is not None:
            author = post.author
            author_name = (getattr(author, 'first_name', None) or 
                         getattr(author, 'username', None) or 'Аноним')
        
        post_city = getattr(post, 'city', 'Не указан')
        
        created_at = getattr(post, 'created_at', None)
        created_str = created_at.strftime('%d.%m.%Y %H:%M') if created_at else ''
        
        return (
            f"Пост на модерацию\n\n"
            f"Заголовок: {post.title}\n"
            f"Город: {post_city}\n"
            f"Категории: {category_str}\n"
            f"Автор: {author_name}\n"
            f"Создан: {created_str}\n\n"
            f"Содержание:\n{post.content}\n\n"
            f"ID поста: {post.id}"
        )

    @staticmethod
    def get_action_display_name(action: ModerationAction) -> str:
        """Получить отображаемое имя действия"""
        action_names = {
            ModerationAction.APPROVE: "Одобрено",
            ModerationAction.REJECT: "Отклонено",
            ModerationAction.REQUEST_CHANGES: "Требуются изменения",
        }
        return action_names.get(action, "Неизвестно")
