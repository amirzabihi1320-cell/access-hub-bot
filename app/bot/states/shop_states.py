from aiogram.fsm.state import State, StatesGroup


class ProductQuantityStates(StatesGroup):
    WAITING_QUANTITY = State()
