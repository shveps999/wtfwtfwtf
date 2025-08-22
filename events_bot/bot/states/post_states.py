from aiogram.fsm.state import State, StatesGroup


class PostStates(StatesGroup):
    """Состояния для создания поста"""

    creating_post = State()  # Начальное состояние для создания поста
    waiting_for_city_selection = State()
    waiting_for_category_selection = State()
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_image = State()
    waiting_for_event_datetime = State()
