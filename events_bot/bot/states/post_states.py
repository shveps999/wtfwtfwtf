from aiogram.fsm.state import State, StatesGroup


class PostStates(StatesGroup):
    creating_post = State()
    waiting_for_city_selection = State()
    waiting_for_category_selection = State()
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_image = State()
    
    # Новые состояния
    waiting_for_event_date = State()
    waiting_for_event_time = State()
