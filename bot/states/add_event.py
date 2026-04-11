from aiogram.fsm.state import State, StatesGroup


class AddEventStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_time = State()
    waiting_category = State()
    waiting_day_type = State()
    waiting_specific_date = State()
    confirm = State()


class EditItemStates(StatesGroup):
    waiting_new_time = State()
    waiting_new_description = State()
