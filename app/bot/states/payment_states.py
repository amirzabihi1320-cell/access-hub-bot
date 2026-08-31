from aiogram.fsm.state import State, StatesGroup


class CryptoPaymentStates(StatesGroup):
    WAITING_TRX_DEPOSIT_AMOUNT = State()
