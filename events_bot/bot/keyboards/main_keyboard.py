from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню с кнопкой избранного"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📮 Смотреть подборку ", callback_data="feed")
    builder.button(text="❤️ Избранное ⠀  ⠀  ⠀  ⠀", callback_data="liked_posts")
    builder.button(text="✏️ Создать свой пост ⠀ ", callback_data="create_post") 
    builder.button(text="🏙 Изменить город ⠀  ⠀ ", callback_data="change_city")
    builder.button(text="⭐️ Изменить категории⠀⠀", callback_data="change_category")
    builder.button(text="💬 Помощь⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀   ", callback_data="help")
    
    builder.adjust(1)
    return builder.as_markup()
