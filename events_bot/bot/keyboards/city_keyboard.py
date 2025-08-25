from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_city_keyboard(for_post: bool = False) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для выбора города"""
    cities = [
        "СПбГУ", "ПГУПС", "СПбПУ", "ИТМО",
        "СПбГЭУ", "Горный", "РГПУ", "СПбГМТУ",
        "СПбГАСУ", "Военмех", "ЛЭТИ", "СПХФУ", "ГУАП",
        "СПбГУТ", "РГГМУ", "СПбГЛТУ", "СПбГУПТД",
        "СПбГИКиТ", "СПГХПА"
    ]
    builder = InlineKeyboardBuilder()
    
    # Используем разные префиксы для разных контекстов
    prefix = "post_city_" if for_post else "city_"
    
    for city in cities:
        builder.button(text=city, callback_data=f"{prefix}{city}")
    builder.adjust(2)
    
    buttons = []
    
    if for_post:
        buttons.append(
            InlineKeyboardButton(
                text="❌ Отмена", callback_data="cancel_post"
            )
        )
    
    if buttons:
        builder.row(*buttons)
    
    return builder.as_markup()
