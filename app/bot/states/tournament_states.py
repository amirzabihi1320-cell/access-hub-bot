from aiogram.fsm.state import State, StatesGroup


class TournamentStates(StatesGroup):
    WAITING_TITLE = State()
    WAITING_METRIC = State()
    WAITING_ENTRY_FEE = State()
    WAITING_DURATION = State()
    WAITING_PRIZE_DESCRIPTION = State()
    WAITING_PRIZE_CREDIT = State()
