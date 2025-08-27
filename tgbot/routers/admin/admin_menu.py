# - *- coding: utf- 8 - *-
import os

import aiofiles
from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder as IKB

from tgbot.data.config import PATH_LOGS, PATH_DATABASE, get_admins
from tgbot.database.db_users import Clientx, Userx
from tgbot.keyboards.reply_main import (
    payments_frep,
    settings_frep,
    functions_frep,
    items_frep,
)
from tgbot.utils.const_functions import convert_date, ded, get_date, get_unix
from tgbot.utils.misc.bot_models import FSM, ARS
from tgbot.utils.misc_functions import get_statistics

router = Router(name=__name__)


# Платежные системы
@router.message(F.text == "🔑 Платежные системы")
async def admin_payments(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(
        "<b>🔑 Настройка платежных системы.</b>",
        reply_markup=payments_frep(),
    )


# Настройки бота
@router.message(F.text == "⚙️ Настройки")
async def admin_settings(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(
        "<b>⚙️ Основные настройки бота.</b>",
        reply_markup=settings_frep(),
    )


# Общие функции
@router.message(F.text == "🔆 Общие функции")
async def admin_functions(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(
        "<b>🔆 Выберите нужную функцию.</b>",
        reply_markup=functions_frep(),
    )


def _sub_status_text(c) -> str:
    now = get_unix()
    paid_until = int(getattr(c, "sub_paid_until", 0) or 0)
    is_trial = bool(int(getattr(c, "sub_is_trial", 0) or 0))
    if paid_until > now:
        return (
            "Статус: <b>активна</b>\n"
            f"Действует до: <code>{convert_date(paid_until, False, False)}</code>\n"
            f"Тариф: <code>{'бесплатный месяц' if is_trial else 'платная'}</code>"
        )
    return "Статус: <b>неактивна</b>"


from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup


def _admin_sub_kb(client_id: int) -> InlineKeyboardMarkup:
    kb = IKB()
    kb.row(
        ikb("➕ Месяц (+30 дней)", data=f"admin:sub:add:{client_id}:30"),
    ).row(
        ikb("➕ Полгода (+180 дней)", data=f"admin:sub:add:{client_id}:180"),
    ).row(
        ikb("➕ Год (+365 дней)", data=f"admin:sub:add:{client_id}:365"),
    ).row(
        ikb("❌ Снять подписку", data=f"admin:sub:clear:{client_id}"),
    ).row(
        ikb("↩️ Готово", data="admin:sub:done"),
    )
    return kb.as_markup()


# ── вход в раздел подписок ───────────────────────────────────────────────────


from aiogram import F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from tgbot.data.config import get_admins
from tgbot.keyboards.reply_main import menu_frep


# клавиатура «Отмена»
def _admin_sub_cancel_rkb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[KeyboardButton(text="◀️ В меню")]],
    )


@router.message(F.text == "🎟 Подписки")
async def admin_subscriptions_entry(message: Message, state: FSMContext):
    if message.from_user.id not in get_admins():
        return
    await state.set_state("admin_sub_wait_client")
    await message.answer(
        "Введите <b>client_id</b> (числом) или <b>@username</b>.\n"
        "Либо нажмите «◀️ В меню» чтобы выйти.",
        reply_markup=_admin_sub_cancel_rkb(),
    )


# отмена из шага ввода клиента
@router.message(
    StateFilter("admin_sub_wait_client"), F.text.in_({"◀️ В меню", "отмена", "Отмена"})
)
async def admin_sub_cancel_to_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=menu_frep(message.from_user.id))


# ── ввод идентификатора клиента ──────────────────────────────────────────────


@router.message(StateFilter("admin_sub_wait_client"))
async def admin_sub_pick_client(message: Message, state: FSM):
    if message.from_user.id not in get_admins():
        return
    txt = (message.text or "").strip()
    if txt.lower() in {"отмена", "cancel"}:
        await state.clear()
        await message.answer("❌ Отменено.")
        return

    # поиск клиента
    cli = None
    if txt.startswith("@"):
        cli = Clientx.get(client_login=txt.lstrip("@"))
    else:
        try:
            cid = int(txt)
            cli = Clientx.get(client_id=cid)
        except Exception:
            cli = None

    if not cli:
        await message.answer("Клиент не найден. Введите другой ID или @username.")
        return

    # показ статуса + кнопки
    status = _sub_status_text(cli)
    txt_info = ded(
        f"""
        <b>Клиент:</b> <code>{cli.client_rlname} {cli.client_surname}</code>
        ID: <code>{cli.client_id}</code>

        {status}
    """
    )
    await message.answer(txt_info, reply_markup=_admin_sub_kb(cli.client_id))
    # можем не держать состояние — всё в callback
    await state.clear()


# ── продление: +30 / +180 / +365 дней ────────────────────────────────────────


@router.callback_query(F.data.startswith("admin:sub:add:"))
async def admin_sub_add(call: CallbackQuery):
    if call.from_user.id not in get_admins():
        await call.answer("Нет прав.", show_alert=True)
        return
    try:
        _, _, _, client_id_str, days_str = call.data.split(":")
        client_id = int(client_id_str)
        days = int(days_str)
    except Exception:
        await call.answer("Некорректные данные.", show_alert=True)
        return

    c = Clientx.get(client_id=client_id)
    if not c:
        await call.answer("Клиент не найден.", show_alert=True)
        return

    now = get_unix()
    current_until = int(getattr(c, "sub_paid_until", 0) or 0)
    base = current_until if current_until > now else now
    new_until = base + days * 24 * 60 * 60

    # платное продление: сбрасываем флаг trial
    try:
        Clientx.update(client_id, sub_paid_until=new_until, sub_is_trial=0)
    except Exception as e:
        await call.answer(f"Ошибка БД: {e}", show_alert=True)
        return

    # обновлённая карточка
    c = Clientx.get(client_id=client_id)
    status = _sub_status_text(c)
    txt = ded(
        f"""
        <b>Клиент:</b> <code>{c.client_rlname} {c.client_surname}</code>
        ID: <code>{c.client_id}</code>

        {status}
    """
    )
    try:
        await call.message.edit_text(txt, reply_markup=_admin_sub_kb(c.client_id))
    except Exception:
        await call.message.answer(txt, reply_markup=_admin_sub_kb(c.client_id))
    await call.answer(f"Продлено на {days} дн.")


# ── снять подписку ───────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("admin:sub:clear:"))
async def admin_sub_clear(call: CallbackQuery):
    if call.from_user.id not in get_admins():
        await call.answer("Нет прав.", show_alert=True)
        return
    try:
        client_id = int(call.data.split(":")[-1])
    except Exception:
        await call.answer("Некорректные данные.", show_alert=True)
        return

    c = Clientx.get(client_id=client_id)
    if not c:
        await call.answer("Клиент не найден.", show_alert=True)
        return

    try:
        Clientx.update(client_id, sub_paid_until=0, sub_is_trial=0)
    except Exception as e:
        await call.answer(f"Ошибка БД: {e}", show_alert=True)
        return

    c = Clientx.get(client_id=client_id)
    status = _sub_status_text(c)
    txt = ded(
        f"""
        <b>Клиент:</b> <code>{c.client_rlname} {c.client_surname}</code>
        ID: <code>{c.client_id}</code>

        {status}
    """
    )
    try:
        await call.message.edit_text(txt, reply_markup=_admin_sub_kb(c.client_id))
    except Exception:
        await call.message.answer(txt, reply_markup=_admin_sub_kb(c.client_id))
    await call.answer("Подписка снята.")


# ── «Готово» ────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "admin:sub:done")
async def admin_sub_done(call: CallbackQuery):
    if call.from_user.id not in get_admins():
        await call.answer()
        return
    await call.message.answer("Готово ✅:", reply_markup=menu_frep(call.from_user.id))
    await call.answer()


from tgbot.utils.const_functions import ikb
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Общие функции
@router.message(F.text == "🗂 Список пользователей")
async def admin_functions(message: Message, bot: Bot, state: FSM, arSession: ARS):
    keyboard = InlineKeyboardBuilder()

    keyboard.row(ikb("🧑🏻‍💻 Исполнитель", data="find_all_user")).row(
        ikb("💰 Клиент", data="find_all_client")
    )

    await message.answer(
        "Выберите категорию поиска:", reply_markup=keyboard.as_markup()
    )


from aiogram.types import CallbackQuery


# Обработчик для отображения всех пользователей или клиентов
@router.callback_query(F.data.in_({"find_all_user", "find_all_client"}))
async def show_user_list(callback: CallbackQuery, bot: Bot):
    # Проверяем, какая кнопка была нажата
    if callback.data == "find_all_user":
        users = Userx.get_all()  # Получаем всех пользователей
        user_type = "пользователей"
    elif callback.data == "find_all_client":
        users = Clientx.get_all()  # Получаем всех клиентов
        user_type = "клиентов"

    # Формируем текст ответа
    if not users:
        text = f"Список {user_type} пуст."
    else:
        text = f"Список {user_type}:\n\n"
        for user in users:
            text += (
                f"ID: {user.user_id if hasattr(user, 'user_id') else user.client_id}\n"
                f"Логин: {user.user_login if hasattr(user, 'user_login') else user.client_login}\n"
                f"Имя: {user.user_name if hasattr(user, 'user_name') else user.client_name}\n"
                f"Баланс: {user.user_balance if hasattr(user, 'user_balance') else user.client_balance} руб.\n"
                f"Номер: {user.user_number if hasattr(user, 'user_number') else user.client_number}\n"
                f"----------------------\n"
            )

    # Отправляем сообщение с результатами
    await callback.message.edit_text(text)


# Управление товарами
@router.message(F.text == "🧑🏻‍💻 Управление заказами")
async def admin_products(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(
        "<b>🧑🏻‍💻 Редактирование заданий.</b>",
        reply_markup=items_frep(),
    )


# Cтатистики бота
@router.message(F.text == "📊 Статистика")
async def admin_statistics(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(get_statistics())


# Получение БД
@router.message(Command(commands=["db", "database"]))
async def admin_database(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer_document(
        FSInputFile(PATH_DATABASE),
        caption=f"<b>📦 #BACKUP | <code>{get_date(full=False)}</code></b>",
    )


# Получение Логов
@router.message(Command(commands=["log", "logs"]))
async def admin_log(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    media_group = MediaGroupBuilder(
        caption=f"<b>🖨 #LOGS | <code>{get_date(full=False)}</code></b>",
    )

    if os.path.isfile(PATH_LOGS):
        media_group.add_document(media=FSInputFile(PATH_LOGS))

    if os.path.isfile("tgbot/data/sv_log_err.log"):
        media_group.add_document(media=FSInputFile("tgbot/data/sv_log_err.log"))

    if os.path.isfile("tgbot/data/sv_log_out.log"):
        media_group.add_document(media=FSInputFile("tgbot/data/sv_log_out.log"))

    await message.answer_media_group(media=media_group.build())


# Очистка логов
@router.message(
    Command(commands=["clear_log", "clear_logs", "log_clear", "logs_clear"])
)
async def admin_log_clear(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    if os.path.isfile(PATH_LOGS):
        async with aiofiles.open(PATH_LOGS, "w") as file:
            await file.write(f"{get_date()} | LOGS WAS CLEAR")

    if os.path.isfile("tgbot/data/sv_log_err.log"):
        async with aiofiles.open("tgbot/data/sv_log_err.log", "w") as file:
            await file.write(f"{get_date()} | LOGS ERR WAS CLEAR")

    if os.path.isfile("tgbot/data/sv_log_out.log"):
        async with aiofiles.open("tgbot/data/sv_log_out.log", "w") as file:
            await file.write(f"{get_date()} | LOGS OUT WAS CLEAR")

    await message.answer("<b>🖨 Логи были успешно очищены</b>")
