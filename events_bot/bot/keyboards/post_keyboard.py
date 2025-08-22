from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_skip_image_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для пропуска изображения"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭️ Пропустить", callback_data="skip_image")
    return builder.as_markup() 