from aiogram.dispatcher.filters.state import State, StatesGroup


class FSMPlanning(StatesGroup):
    """Конечный автомат для планирования очередей."""
    choose_chat = State()
    queue_name = State()
    start_date = State()
    start_datetime = State()


class FSMDeletion(StatesGroup):
    """Конечный автомат удаления очереди."""
    queue_choice = State()
