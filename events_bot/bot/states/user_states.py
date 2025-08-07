from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """Состояния для регистрации пользователя"""

    waiting_for_city = State()
    waiting_for_categories = State()
