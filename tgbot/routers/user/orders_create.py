# tgbot/routers/user/orders_create.py
from aiogram import Router, F, types, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from datetime import datetime
import json


from tgbot.database.db_category import Categoryx
from tgbot.database.db_position import Positionx
from tgbot.database.db_users import Clientx
from tgbot.utils.const_functions import ded, clear_html

# is_number, to_number — твои же utils

router = Router()

class OrderStates(StatesGroup):
    city = State()
    address = State()
    categories = State()
    desc = State()
    budget = State()
    dates = State()
    photos = State()
    confirm = State()
