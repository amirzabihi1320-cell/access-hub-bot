from aiogram.fsm.state import State, StatesGroup


class ProductQuantityStates(StatesGroup):
    WAITING_QUANTITY = State()


class ShopSearchStates(StatesGroup):
    WAITING_QUERY = State()


class CouponStates(StatesGroup):
    WAITING_CODE = State()
