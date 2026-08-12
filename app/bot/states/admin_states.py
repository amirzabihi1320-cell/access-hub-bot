from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    WAITING_NEW_PRICE = State()
    WAITING_SETTING_VALUE = State()
    WAITING_CATEGORY_NAME = State()
    WAITING_CATEGORY_ICON = State()
    WAITING_PRODUCT_NAME = State()
    WAITING_PRODUCT_FIXED_PRICE = State()
    WAITING_PRODUCT_UNIT_PRICE = State()
    WAITING_PRODUCT_MIN_QTY = State()
    WAITING_PRODUCT_MAX_QTY = State()
