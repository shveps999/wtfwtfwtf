from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_feed_keyboard(current_page: int, total_pages: int, post_id: int, is_liked: bool = False, likes_count: int = 0) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для ленты постов"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки навигации
    if current_page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"feed_prev_{current_page}_{total_pages}")
    if current_page < total_pages - 1:
        builder.button(text="Вперед ➡️", callback_data=f"feed_next_{current_page}_{total_pages}")
    
    # Кнопка сердечка (лайк) с количеством
    heart_emoji = "❤️" if is_liked else "🤍"
    heart_text = f"{heart_emoji} {likes_count}" if likes_count > 0 else heart_emoji
    builder.button(text=heart_text, callback_data=f"feed_heart_{post_id}_{current_page}_{total_pages}")
    
    # Кнопка возврата в главное меню
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    
    # Настраиваем расположение кнопок
    builder.adjust(2)
    
    return builder.as_markup() 