from aiogram.fsm.state import State, StatesGroup


class ModerationStates(StatesGroup):
    """Состояния для модерации (ввод комментария)"""
    waiting_for_comment = State()

