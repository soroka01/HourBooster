from aiogram.fsm.state import State, StatesGroup

# Состояния для Steam Guard
class SteamGuardStates(StatesGroup):
    waiting_for_guard_code = State()
    waiting_for_email_code = State()
