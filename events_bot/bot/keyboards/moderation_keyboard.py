from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


def get_moderation_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для модерации поста"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Одобрить", callback_data=f"moderate_approve_{post_id}")
    builder.button(text="❌ Отклонить", callback_data=f"moderate_reject_{post_id}")
    builder.adjust(2)
    builder.button(text="📝 Запросить изменения", callback_data=f"moderate_changes_{post_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_moderation_queue_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для очереди модерации"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="refresh_moderation")
    return builder.as_markup()
