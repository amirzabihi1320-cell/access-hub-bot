from aiogram.fsm.state import State, StatesGroup


class DepositStates(StatesGroup):
    WAITING_AMOUNT = State()
    WAITING_RECEIPT = State()
