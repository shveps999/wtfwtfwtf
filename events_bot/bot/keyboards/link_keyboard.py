from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def get_skip_link_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для пропуска ссылки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭️ Пропустить", callback_data="skip_link")
    return builder.as_markup()


def get_post_link_keyboard(link: str) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура с кнопкой ссылки под постом"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 Перейти по ссылке", url=link)
    return builder.as_markup()
