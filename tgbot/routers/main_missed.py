# - *- coding: utf- 8 - *-
from aiogram import Router, Bot, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message

from tgbot.keyboards.reply_main import menu_frep
from tgbot.utils.const_functions import del_message, ded
from tgbot.utils.misc.bot_models import FSM, ARS

router = Router(name=__name__)


# Колбэк с удалением сообщения
@router.callback_query(F.data == "close_this")
async def main_missed_callback_close(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    await del_message(call.message)


# Колбэк с обработкой кнопки
@router.callback_query(F.data == "...")
async def main_missed_callback_answer(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    await call.answer(cache_time=60)


# Обработка всех колбэков которые потеряли стейты после перезапуска скрипта
@router.callback_query(StateFilter("*"))
async def main_missed_callback(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    await call.answer("❗️ Кнопка недействительна. Повторите действия заново", True)


# Обработка всех неизвестных команд
@router.message()
async def main_missed_message(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(
        ded(
            """
            👷‍♂️ Строительная Биржа RabotaPlus — ваш помощник в поиске специалистов и заказов!  
            Что вы хотите сделать? 
        """
        ),
        reply_markup=menu_frep(message.from_user.id),
    )
