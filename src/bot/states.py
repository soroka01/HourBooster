"""Finite-state inputs that still keep bot responses inside one editable screen."""

from aiogram.fsm.state import State, StatesGroup


class AccountForm(StatesGroup):
    add_title = State()
    add_username = State()
    add_password = State()
    add_games = State()
    edit_value = State()


class GuardCode(StatesGroup):
    waiting = State()
