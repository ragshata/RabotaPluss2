# - *- coding: utf- 8 - *-
import asyncio
import html
import sqlite3
from typing import Union

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from tgbot.database.db_category import Categoryx
from aiogram.types import ReplyKeyboardRemove

from tgbot.data.config import BOT_VERSION, PATH_DATABASE, get_desc
from tgbot.database.db_purchases import Purchasesx
from tgbot.database.db_responses import Responsesx
from tgbot.database.db_settings import Settingsx
from tgbot.database.db_users import Clientx, Userx
from tgbot.keyboards.inline_admin_page import (
    admin_position_edit_category_swipe_fp,
    admin_position_edit_swipe_fp,
    client_position_edit_swipe_fp,
    position_add_swipe_fp,
    position_edit_category_swipe_fp,
    position_edit_swipe_fp,
    user_position_edit_category_swipe_fp,
    user_position_edit_swipe_fp,
)
from tgbot.keyboards.inline_admin_prod import (
    baza_znanii,
    category_edit_open_finl,
    knowledge_base,
    position_edit_cancel_finl,
    position_edit_open_finl,
    privacy_policy,
    users_admire,
)
from tgbot.keyboards.inline_user import user_support_finl
from tgbot.keyboards.inline_user_page import *
from tgbot.keyboards.reply_main import (
    client_functions_codexk,
    items_frep_client,
    menu_help_clients,
    menu_help_users,
    menu_second_start,
    menu_second_start_clients,
    order_category,
    user_functions_codexk,
)
from tgbot.routers.user.user_products import confirm_tusk_button
from tgbot.utils.const_functions import (
    clear_html,
    ded,
    del_message,
    convert_date,
    get_unix,
    is_number,
    to_number,
)
from tgbot.utils.misc.bot_models import FSM, ARS
from tgbot.utils.misc_functions import (
    upload_photo,
    upload_text,
    insert_tags,
    get_items_available,
)
from tgbot.utils.subscriptions_in_clients import (
    _human,
    client_sub_get,
    client_sub_is_active,
    client_sub_start_free_month,
    paywall_text,
    subscribe_kb,
    subscribe_kb_contact_admin,
)
from tgbot.utils.text_functions import (
    category_open_admin,
    open_profile_client,
    open_profile_user,
    position_open_admin,
    position_open_not_admin_user,
)

router = Router()

# -*- coding: utf-8 -*-
from aiogram import Router, F, types, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from datetime import datetime
import json

from tgbot.utils.const_functions import ded, clear_html


def _assign_worker_by_unix(punix: int, worker_id: int, status: int = 1) -> bool:
    """Надёжно назначаем исполнителя по position_unix."""
    try:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.execute(
                "UPDATE storage_position SET worker_id = ?, position_status = ? WHERE position_unix = ?",
                [worker_id, status, punix],
            )
        return True
    except Exception:
        return False


# ────────────────────────── Клавиатуры / вспомогалки ──────────────────────────
# --- Responses (optional) ---------------------------------------------
HAS_RESPONSES_TABLE: bool = False
try:
    # если модуль есть — используем реальный класс
    from tgbot.database.db_responses import Responsesx as _ResponsesxReal

    Responsesx = _ResponsesxReal  # имя для использования ниже
    HAS_RESPONSES_TABLE = True
except Exception:
    # заглушка, чтобы линтер/рантайм не падали, если таблицы пока нет
    class Responsesx:  # type: ignore
        @staticmethod
        def gets(**kwargs):
            return []

        @staticmethod
        def add(*args, **kwargs):
            return 0

        @staticmethod
        def update(*args, **kwargs):
            pass


# ----------------------------------------------------------------------


def cancel_order_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Прервать создание заказа", callback_data="order:cancel"
                )
            ]
        ]
    )


CITIES = [
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
    "Нижний Новгород",
    "Челябинск",
    "Самара",
    "Омск",
    "Ростов-на-Дону",
    "Уфа",
    "Красноярск",
    "Пермь",
    "Воронеж",
    "Волгоград",
    "Краснодар",
    "Сочи",
    "Тюмень",
    "Иркутск",
    "Хабаровск",
]


def cities_swipe(page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    start = page * per_page
    chunk = CITIES[start : start + per_page]
    rows, row = [], []
    for i, name in enumerate(chunk, 1):
        row.append(InlineKeyboardButton(text=name, callback_data=f"order:city:{name}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"order:city_page:{page-1}")
        )
    if start + per_page < len(CITIES):
        nav.append(
            InlineKeyboardButton(text="➡️", callback_data=f"order:city_page:{page+1}")
        )
    if nav:
        rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Прервать создание заказа", callback_data="order:cancel"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_multiselect_kb(
    selected_ids: set[int] | list[int], page: int = 0, per_page: int = 8
) -> InlineKeyboardMarkup:
    if not isinstance(selected_ids, set):
        selected_ids = set(selected_ids or [])
    all_cats = Categoryx.get_all()
    start = page * per_page
    chunk = all_cats[start : start + per_page]

    rows, row = [], []
    for i, cat in enumerate(chunk, 1):
        mark = "✅" if cat.category_id in selected_ids else "•"
        text = f"{mark} {cat.category_name}"
        row.append(
            InlineKeyboardButton(
                text=text, callback_data=f"order:cat_toggle:{cat.category_id}:{page}"
            )
        )
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"order:cat_page:{page-1}")
        )
    if start + per_page < len(all_cats):
        nav.append(
            InlineKeyboardButton(text="➡️", callback_data=f"order:cat_page:{page+1}")
        )
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="Готово", callback_data="order:cat_done")])
    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Прервать создание заказа", callback_data="order:cancel"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data=cb)],
            [
                InlineKeyboardButton(
                    text="❌ Прервать создание заказа", callback_data="order:cancel"
                )
            ],
        ]
    )


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data="order:confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить описание", callback_data="order:confirm_edit"
                )
            ],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="order:cancel")],
        ]
    )


def _parse_date(s: str):
    try:
        return datetime.strptime(s, "%d.%m.%Y")
    except Exception:
        return None


@router.message(F.text.in_(("Подписка", "/subscribe")))
async def sub_status(message: Message):
    c = client_sub_get(message.from_user.id)
    if not c or int(getattr(c, "sub_paid_until", 0) or 0) <= 0:
        await message.answer(paywall_text(), reply_markup=subscribe_kb_contact_admin())
        return

    if client_sub_is_active(message.from_user.id):
        await message.answer(
            f"🔔 Подписка активна до <code>{_human(c.sub_paid_until)}</code>."
        )
    else:
        await message.answer(
            f"⛔ Подписка истекла <code>{_human(c.sub_paid_until)}</code>.",
            reply_markup=subscribe_kb_contact_admin(),
        )


# ────────────────────────── Старт сценария ──────────────────────────
# где у тебя router = Router()
from aiogram import F
from aiogram.types import CallbackQuery


@router.callback_query(F.data == "sub:info")
async def sub_info(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        "Подписка открывает возможность создавать заказы.\n"
        "Первый месяц — бесплатно, потом 100 ₽ в неделю.\n"
        "Оплата проводится через администратора.",
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "sub:pay")
async def sub_pay(call: CallbackQuery):
    await call.answer()
    settings = Settingsx.get()
    await call.message.answer(
        "<b>☎️ Нажмите кнопку ниже для связи с Администратором для оплаты.</b>",
        reply_markup=user_support_finl(settings.misc_support),
    )


import time
from datetime import datetime


def _to_int_unix(v) -> int:
    """
    Приводим v к unix-времени в СЕКУНДАХ.
    Поддерживает int/str, возможно миллисекунды, поддержка 'ДД.ММ.ГГГГ'.
    """
    if v is None:
        return 0

    # уже int?
    if isinstance(v, int):
        # если похоже на миллисекунды (13 знаков) — переведём в секунды
        return v // 1000 if v > 10**12 else v

    s = str(v).strip()
    if not s:
        return 0

    # чистые цифры
    if s.isdigit():
        val = int(s)
        return val // 1000 if val > 10**12 else val

    # формат ДД.ММ.ГГГГ
    try:
        dt = datetime.strptime(s, "%d.%m.%Y")
        return int(dt.timestamp())
    except Exception:
        return 0


def get_client_sub_active_until(client) -> int:
    """
    Возвращает unix до какого момента действует подписка
    (берём максимум из trial и paid), не глядя на текст статуса.
    """
    trial_u = _to_int_unix(getattr(client, "sub_trial_until", 0))
    paid_u = _to_int_unix(getattr(client, "sub_paid_until", 0))
    return max(trial_u, paid_u)


def is_client_sub_active(client) -> bool:
    return get_client_sub_active_until(client) > int(time.time())


from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from tgbot.database.db_users import Clientx


@router.message(F.text.in_(("➕ Создать заказ",)))
async def start_order(message: Message, state: FSMContext):
    # 1) достаём клиента
    client = Clientx.get(client_id=message.from_user.id)

    # 2) если в БД ещё нет записи клиента — создайте (или блокируйте)
    if not client:
        # (опционально) создать запись клиента
        # Clientx.add(message.from_user.id, message.from_user.username or "", message.from_user.full_name or "", "", "", 0)
        # client = Clientx.get(client_id=message.from_user.id)
        # Либо сразу просить завести профиль:
        await message.answer(
            "Пожалуйста, откройте профиль заказчика и заполните данные перед созданием заказа."
        )
        return

    # 3) проверяем только по дате действия
    #if not is_client_sub_active(client):
    #    await message.answer(
    #        "<b>🔒 Подписка нужна для создания заказов</b>\n\n"
    #        "Первый месяц — бесплатно.\n"
    #        "Далее — 100 ₽ в неделю.\n\n"
    #        "Оформите подписку, чтобы продолжить.",
    #        reply_markup=subscribe_kb(),  # ваша кнопка «Подписка»
    #    )
    #    return

    # ---- дальше обычный сценарий создания заказа ----
    await state.clear()
    await message.answer("<b>🏙 Выберите город:</b>", reply_markup=cities_swipe(0))
    await state.set_state("order_city")


# пагинация городов
@router.callback_query(StateFilter("order_city"), F.data.startswith("order:city_page:"))
async def city_page(call: CallbackQuery):
    page = int(call.data.split(":")[2])
    await call.message.edit_reply_markup(reply_markup=cities_swipe(page))
    await call.answer()


# выбор города
@router.callback_query(StateFilter("order_city"), F.data.startswith("order:city:"))
async def city_choose(call: CallbackQuery, state: FSMContext):
    city = call.data.split(":")[2]
    await state.update_data(city=city)
    await call.message.edit_text(
        f"🏙 Город: <b>{city}</b>\n\n📍 Введите адрес объекта (улица, дом, кв/офис):",
        reply_markup=cancel_order_button(),
    )
    await state.set_state("order_address")
    await call.answer()


# ────────────────────────── Адрес ──────────────────────────


@router.message(StateFilter("order_address"))
async def get_address(message: Message, state: FSMContext):
    address = clear_html(message.text or "").strip()
    if not address or len(address) < 5:
        await message.answer(
            "❌ Слишком короткий адрес. Введите адрес подробнее:",
            reply_markup=cancel_order_button(),
        )
        return
    await state.update_data(address=address)

    # категории — мультивыбор
    await message.answer(
        "🧰 Выберите категории работ (можно несколько), затем нажмите «Готово».",
        reply_markup=categories_multiselect_kb(selected_ids=set(), page=0),
    )
    await state.set_state("order_categories")


# пагинация категорий
@router.callback_query(
    StateFilter("order_categories"), F.data.startswith("order:cat_page:")
)
async def cats_page(call: CallbackQuery, state: FSMContext):
    page = int(call.data.split(":")[2])
    data = await state.get_data()
    selected = set(data.get("cats", []))
    await call.message.edit_reply_markup(
        reply_markup=categories_multiselect_kb(selected, page)
    )
    await call.answer()


# переключение категории
@router.callback_query(
    StateFilter("order_categories"), F.data.startswith("order:cat_toggle:")
)
async def cats_toggle(call: CallbackQuery, state: FSMContext):
    _, _, cat_id_str, page_str = call.data.split(":")
    cat_id = int(cat_id_str)
    page = int(page_str)
    data = await state.get_data()
    selected = set(data.get("cats", []))
    if cat_id in selected:
        selected.remove(cat_id)
    else:
        selected.add(cat_id)
    await state.update_data(cats=list(selected))
    await call.message.edit_reply_markup(
        reply_markup=categories_multiselect_kb(selected, page)
    )
    await call.answer()


# завершили выбор категорий
@router.callback_query(StateFilter("order_categories"), F.data == "order:cat_done")
async def cats_done(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = list(data.get("cats", []))
    if not selected:
        await call.answer("Выберите хотя бы одну категорию.", show_alert=True)
        return
    await call.message.edit_text(
        "📝 Опишите задачу (что нужно сделать):", reply_markup=cancel_order_button()
    )
    await state.set_state("order_desc")
    await call.answer()


# ────────────────────────── Описание ──────────────────────────


@router.message(StateFilter("order_desc"))
async def get_desc(message: Message, state: FSMContext):
    desc = clear_html(message.text or "").strip()
    if not desc or len(desc) < 10:
        await message.answer(
            "❌ Слишком короткое описание. Добавьте деталей:",
            reply_markup=cancel_order_button(),
        )
        return
    await state.update_data(desc=desc)
    await message.answer(
        "💰 Укажите бюджет в рублях (число).\nИли нажмите «Пропустить» — будет «договорная».",
        reply_markup=skip_button("order:budget_skip"),
    )
    await state.set_state("order_budget")


# пропуск бюджета
@router.callback_query(StateFilter("order_budget"), F.data == "order:budget_skip")
async def budget_skip(call: CallbackQuery, state: FSMContext):
    await state.update_data(budget="договорная")
    await call.message.edit_text(
        "📅 Укажите сроки выполнения.\nФормат: <code>дд.мм.гггг — дд.мм.гггг</code>\nИли напишите: <code>пока не определился</code>",
        reply_markup=cancel_order_button(),
    )
    await state.set_state("order_dates")
    await call.answer()


# бюджет числом
@router.message(StateFilter("order_budget"))
async def get_budget(message: Message, state: FSMContext):
    txt = (message.text or "").replace(" ", "")
    if not txt.isdigit():
        await message.answer(
            "❌ Введите число (без пробелов), либо нажмите «Пропустить».",
            reply_markup=skip_button("order:budget_skip"),
        )
        return
    val = int(txt)
    if not (0 <= val <= 10_000_000):
        await message.answer(
            "❌ Бюджет должен быть от 0 до 10 000 000.",
            reply_markup=skip_button("order:budget_skip"),
        )
        return
    await state.update_data(budget=val)
    await message.answer(
        "📅 Укажите сроки выполнения.\nФормат: <code>дд.мм.гггг — дд.мм.гггг</code>\nИли напишите: <code>пока не определился</code>",
        reply_markup=cancel_order_button(),
    )
    await state.set_state("order_dates")


# ────────────────────────── Сроки ──────────────────────────


@router.message(StateFilter("order_dates"))
async def get_dates(message: Message, state: FSMContext):
    raw = (message.text or "").strip().lower()
    if raw in ("пока не определился", "не определился", "не знаю"):
        await state.update_data(dates="пока не определился")
    else:
        parts = [p.strip() for p in raw.replace("—", "-").split("-")]
        if len(parts) != 2:
            await message.answer(
                "❌ Формат неверный. Пример: 10.08.2025 - 20.08.2025\nИли напишите: пока не определился",
                reply_markup=cancel_order_button(),
            )
            return
        d1 = _parse_date(parts[0])
        d2 = _parse_date(parts[1])
        if not d1 or not d2 or d2 < d1:
            await message.answer(
                "❌ Даты неверные или окончание раньше начала.",
                reply_markup=cancel_order_button(),
            )
            return
        await state.update_data(
            dates=f"{d1.strftime('%d.%m.%Y')} – {d2.strftime('%d.%m.%Y')}"
        )

    await message.answer(
        "📸 Пришлите до 5 фото (по желанию), или нажмите «Пропустить».",
        reply_markup=skip_button("order:photos_skip"),
    )
    await state.set_state("order_photos")


# ────────────────────────── Фото (опционально) ──────────────────────────


# ---------- Клавиатура для шага с фото ----------
def photos_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="order:photos_done")],
            [
                InlineKeyboardButton(
                    text="⏭ Пропустить", callback_data="order:photos_skip"
                )
            ],
        ]
    )


# Если у тебя уже есть skip_button/cancel_order_button — можешь оставить их.
# Тут отдельная клавиатура именно для шага с фото.


# ---------- Вспомогательно: переход на следующий шаг ----------
async def proceed_to_next_step(state: FSMContext, message_or_cb):
    await state.set_state("order_comment")
    text = "✍️ Добавьте комментарий к заказу (по желанию) или напишите «нет»."
    if isinstance(message_or_cb, Message):
        await message_or_cb.answer(text)
    else:
        await message_or_cb.message.answer(text)


# ────────────────────────── Фото (до 5 шт) ──────────────────────────


@router.message(StateFilter("order_photos"), F.photo, flags={"rate": 0})
async def add_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = list(data.get("photos", []))

    # Берём самое большое превью (последний элемент)
    file_id = message.photo[-1].file_id

    if file_id in photos:
        await message.answer(
            f"⚠️ Это фото уже добавлено. Сейчас сохранено: {len(photos)}/5.",
            reply_markup=photos_kb(),
        )
        return

    if len(photos) >= 5:
        await message.answer(
            "⚠️ Лимит 5 фото уже достигнут. Нажмите «Готово» или «Пропустить».",
            reply_markup=photos_kb(),
        )
        return

    photos.append(file_id)
    await state.update_data(photos=photos)

    if len(photos) < 5:
        await message.answer(
            f"✅ Фото сохранено ({len(photos)}/5). "
            f"Можете отправить ещё или нажмите «Готово».",
            reply_markup=photos_kb(),
        )
    else:
        await message.answer(
            "✅ Добавлено 5/5 фото. Нажмите «Готово» для перехода дальше.",
            reply_markup=photos_kb(),
        )


@router.message(StateFilter("order_photos"))
async def non_photo_in_photos_step(message: Message, state: FSMContext):
    # Разрешаем текст «пропустить» в любом регистре
    txt = (message.text or "").strip().lower()
    if txt in {"пропустить", "skip"}:
        # Если фото уже есть — не теряем их, идём как «Готово»
        data = await state.get_data()
        if data.get("photos"):
            await message.answer("➡️ Переходим дальше с уже добавленными фото.")
            await proceed_to_next_step(state, message)
        else:
            await message.answer("➡️ Пропускаем фото и идём дальше.")
            await state.update_data(photos=[])
            await proceed_to_next_step(state, message)
        return

    await message.answer(
        "🖼 Пришлите фото (до 5 шт). "
        "После загрузки нажмите «Готово» или «Пропустить».",
        reply_markup=photos_kb(),
    )


@router.callback_query(
    StateFilter("order_photos"), F.data == "order:photos_done", flags={"rate": 0}
)
async def photos_done(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])

    if not photos:
        # Ничего не добавили, предложим либо прислать, либо пропустить
        await cq.message.answer(
            "Пока нет фото. Пришлите хотя бы одно или нажмите «Пропустить».",
            reply_markup=photos_kb(),
        )
        await cq.answer()
        return

    await cq.message.answer(f"✅ Фото сохранены ({len(photos)}/5). Переходим дальше.")
    await cq.answer()
    await proceed_to_next_step(state, cq)


@router.callback_query(
    StateFilter("order_photos"), F.data == "order:photos_skip", flags={"rate": 0}
)
async def photos_skip(cq: CallbackQuery, state: FSMContext):
    # ВАЖНО: если фото уже есть — не удаляем их, идём дальше как «Готово»
    data = await state.get_data()
    if data.get("photos"):
        await cq.message.answer("➡️ Переходим дальше с уже добавленными фото.")
    else:
        await state.update_data(photos=[])
        await cq.message.answer("➡️ Пропускаем фото и идём дальше.")
    await cq.answer()
    await proceed_to_next_step(state, cq)


# ────────────────────────── Комментарий → Подтверждение ──────────────────────────
@router.message(StateFilter("order_comment"))
async def get_comment(message: Message, state: FSMContext):
    raw = (message.text or "").strip()
    comment = (
        "" if raw.lower() in {"нет", "не", "без комментария", "-", "—"} else raw[:1000]
    )
    await state.update_data(comment=comment)

    # показать подтверждение
    await _show_confirmation(message, state)
    await state.set_state("order_confirm")


# ────────────────────────── Подтверждение ──────────────────────────
async def _show_confirmation(msg: Message, state: FSMContext):
    data = await state.get_data()

    # Безопасные значения + экранирование для HTML
    city = html.escape(str(data.get("city", "—")))
    address = html.escape(str(data.get("address", "—")))
    desc = html.escape(str(data.get("desc", "—")))
    budget = data.get("budget", "договорная")
    dates = html.escape(str(data.get("dates", "пока не определился")))
    photos = list(data.get("photos", []))
    cats_ids = list(data.get("cats", []))
    comment = html.escape(str(data.get("comment", "")))

    # Формат бюджета: число с пробелами
    if isinstance(budget, int):
        budget_text = f"{budget:,}".replace(",", " ") + " руб."
    else:
        budget_text = html.escape(str(budget))

    # Категории
    cats_map = {c.category_id: c.category_name for c in Categoryx.get_all()}
    cats_titles = [cats_map.get(cid, str(cid)) for cid in cats_ids]
    cats_text = html.escape(", ".join(cats_titles)) if cats_titles else "—"

    # Если есть фото — отправим как media group (без подписи),
    # а затем отдельным сообщением — текст с кнопками.
    if photos:
        media = [InputMediaPhoto(type="photo", media=file_id) for file_id in photos[:5]]
        await msg.answer_media_group(media=media)

    # Текст подтверждения
    txt = (
        f"<b>Проверьте заказ:</b>\n\n"
        f"🏙 Город: <code>{city}</code>\n"
        f"📍 Адрес: <code>{address}</code>\n"
        f"🧰 Категории: <code>{cats_text}</code>\n\n"
        f"📝 Описание:\n{desc}\n\n"
        f"💰 Бюджет: <code>{budget_text}</code>\n"
        f"📅 Сроки: <code>{dates}</code>\n"
        f"🖼 Фото: <code>{len(photos)} шт.</code>\n"
        f"💬 Комментарий: {comment if comment else '—'}"
    )
    await msg.answer(txt, reply_markup=confirm_kb())
    await state.set_state("order_confirm")


# ────────────────────────── Обработка «Подтвердить / Изменить» ──────────────────────────


@router.callback_query(StateFilter("order_confirm"), F.data == "order:edit")
async def edit_order(cq: CallbackQuery, state: FSMContext):
    # Верни пользователя на нужный шаг (например, к описанию или категориям)
    # Пример: вернуться в описание
    await state.set_state("order_desc")
    await cq.message.answer("✏️ Измените описание заказа и отправьте новое сообщение.")
    await cq.answer()


@router.callback_query(StateFilter("order_confirm"), F.data == "order:confirm_edit")
async def confirm_edit(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "Введите новое ОПИСАНИЕ задачи:", reply_markup=cancel_order_button()
    )
    await state.set_state("order_desc")
    await call.answer()


from aiogram import F
from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram import Bot
import html, json


@router.callback_query(StateFilter("order_confirm"), F.data == "order:confirm")
async def confirm_ok(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()

    city = str(data.get("city", "—"))
    address = str(data.get("address", "—"))
    desc = str(data.get("desc", "")).strip()
    budget = data.get("budget", "договорная")
    dates = data.get("dates", "пока не определился")
    photos = list(data.get("photos", []) or [])
    cats_ids = list(data.get("cats", []) or [])

    main_cat_id = cats_ids[0] if cats_ids else 0
    position_name = (desc[:50] + "…") if len(desc) > 53 else desc

    # расширенное описание для дальнейшей фильтрации/поиска
    ext = {
        "city": city,
        "address": address,
        "categories": cats_ids,
        "budget": budget,
        "dates": dates,
        "photos": photos,
        "raw_desc": desc,
    }
    position_desc = "[ORDER]\n" + json.dumps(ext, ensure_ascii=False, indent=2)

    # бюджет в числовое поле — только если это число
    price_val = int(budget) if isinstance(budget, int) else 0

    # сохраняем и получаем уникальный идентификатор заказа (punix)
    punix = Positionx.add(
        main_cat_id,  # category_id
        call.from_user.id,  # position_id (владелец заявки)
        position_name,
        float(price_val),  # position_price
        position_desc,
        0.0,  # position_time (legacy)
        0,  # worker_id (ещё не назначен)
        0,  # position_status (актуален)
    )

    # дальше только показ пользователю — состояние можно очистить
    await state.clear()

    # красивые подписи категорий
    cats_map = {c.category_id: c.category_name for c in Categoryx.get_all()}
    cats_titles = [cats_map.get(cid, str(cid)) for cid in cats_ids]
    cats_text = ", ".join(cats_titles) if cats_titles else "—"

    # бюджет красивым текстом
    budget_text = (
        f"{price_val:,}".replace(",", " ") + " ₽" if price_val > 0 else str(budget)
    )

    # если есть фото — отправим как медиагруппу (без подписи)
    if photos:
        media = [InputMediaPhoto(type="photo", media=fid) for fid in photos[:5]]
        try:
            await call.message.answer_media_group(media=media)
        except Exception:
            # если по какой-то причине не отправилось — просто продолжаем
            pass

    # финальный, «украшенный» текст
    txt = (
        f"✅ <b>Ваш заказ создан!</b>\n"
        f"───────────────\n"
        f"🆔 Номер: <code>{punix}</code>\n"
        f"🏙 Город: <code>{html.escape(city)}</code>\n"
        f"📍 Адрес: <code>{html.escape(address)}</code>\n"
        f"🧰 Категории: <code>{html.escape(cats_text)}</code>\n"
        f"💰 Бюджет: <code>{html.escape(budget_text)}</code>\n"
        f"📅 Сроки: <code>{html.escape(str(dates))}</code>\n"
        f"🖼 Фото: <code>{len(photos)} шт.</code>\n\n"
        f"📝 <b>Описание</b>:\n{html.escape(desc) if desc else '—'}"
    )

    await call.message.answer(txt)
    await call.answer()


# ────────────────────────── Отмена из любого шага ──────────────────────────


@router.callback_query(F.data == "order:cancel")
async def order_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("<b>Создание заказа отменено.</b>")
    await call.message.answer(
        "Главное меню:", reply_markup=menu_second_start_clients(call.from_user.id)
    )
    await call.answer()


################################################################################
############################### ИЗМЕНЕНИЕ ПОЗИЦИИ ##############################
# Перемещение по страницам категорий для редактирования позиции
@router.callback_query(F.data.startswith("position_edit_category_swipe:"))
async def prod_position_edit_category_swipe(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    remover = int(call.data.split(":")[1])

    await call.message.edit_text(
        "<b>📁 Выберите заказ для изменения 🖍</b>",
        reply_markup=position_edit_category_swipe_fp(remover),
    )


# Перемещение по страницам категорий для редактирования позиции
@router.callback_query(F.data.startswith("admin_position_edit_category_swipe:"))
async def prod_position_edit_category_swipe(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    remover = int(call.data.split(":")[1])

    await call.message.edit_text(
        "<b>📁 Выберите заказ </b>",
        reply_markup=position_edit_category_swipe_fp(remover),
    )


# Перемещение по страницам категорий для редактирования позиции
@router.callback_query(F.data.startswith("user_position_edit_category_swipe:"))
async def prod_position_edit_category_swipe(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    remover = int(call.data.split(":")[1])

    await call.message.edit_text(
        "<b>📁 Выберите заказ </b>",
        reply_markup=user_position_edit_category_swipe_fp(remover),
    )


# Выбор категории с нужной позицией
@router.callback_query(F.data.startswith("position_edit_category_open:"))
async def prod_position_edit_category_open(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    category_id = call.data.split(":")[1]

    get_category = Categoryx.get(category_id=category_id)
    get_positions = Positionx.gets(category_id=category_id)

    if len(get_positions) >= 1:
        await call.message.edit_text(
            "<b>📁 Выберите заказ для изменения 🖍</b>",
            reply_markup=position_edit_swipe_fp(0, category_id, call),
        )
    else:
        await call.answer(
            f"📁 Заказы в категории {get_category.category_name} отсутствуют"
        )


# Выбор категории с нужной позицией
@router.callback_query(F.data.startswith("user_position_edit_category_open:"))
async def prod_position_edit_category_open(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    category_id = call.data.split(":")[1]

    get_category = Categoryx.get(category_id=category_id)
    get_positions = Positionx.gets(category_id=category_id)

    if len(get_positions) >= 1:
        await call.message.edit_text(
            "<b>📁 Выберите заказ</b>",
            reply_markup=user_position_edit_swipe_fp(0, category_id, call),
        )
    else:
        await call.answer(
            f"📁 Заказы в категории {get_category.category_name} отсутствуют"
        )


# Выбор категории с нужной позицией
@router.callback_query(F.data.startswith("admin_position_edit_category_open:"))
async def prod_position_edit_category_open(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    category_id = call.data.split(":")[1]

    get_category = Categoryx.get(category_id=category_id)
    get_positions = Positionx.gets(category_id=category_id)

    if len(get_positions) >= 1:
        await call.message.edit_text(
            "<b>📁 Выберите заказ для изменения 🖍</b>",
            reply_markup=admin_position_edit_swipe_fp(0, category_id, call),
        )
    else:
        await call.answer(
            f"📁 Заказы в категории {get_category.category_name} отсутствуют"
        )


@router.message(F.text == "🗣 Пользовательское соглашение")
async def prod_removes(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(
        "<b> Пользовательское соглашение</b>\n",
        reply_markup=users_admire(),
    )


@router.message(F.text == "📚 База знаний")
async def prod_removes(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(
        "<b> База знаний</b>\n",
        reply_markup=baza_znanii(),
    )


@router.message(F.text == "👤 Политика конфиденциальности")
async def prod_removes(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(
        "<b> Политика конфиденциальности</b>\n",
        reply_markup=privacy_policy(),
    )


@router.message(F.text == "📚 Помощь")
async def prod_removes(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(
        "<b> Помощь </b>\n",
        reply_markup=knowledge_base(),
    )


'''# Открытие профиля
@router.message(F.text == "💡 Мои заказы")
async def user_profile(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await message.answer(
        "<b>📁 Куда хотите перейте дальше?</b>",
        reply_markup=order_category(),
    )

@router.message(F.text == "📁 Все заказы")
async def user_all_orders(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    get_positions = Positionx.gets(position_id=message.from_user.id)
    get_categories = Categoryx.get_all()

    if len(get_categories) >= 1:
        await message.answer(
            """
            <b>Ваши заказы:</b>
            """,
            reply_markup=position_edit_category_swipe_fp(0),
        )
    else:
        await message.answer("<b>❌ Отсутствуют категории для изменения позиций</b>")


@router.message(F.text == "👤 В работе")
async def user_profile(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    # Получаем заказы пользователя со статусом 0
    get_positions = Positionx.get_by_id_and_status(message.from_user.id, position_status=0)
    get_categories = Categoryx.get_all()

    if len(get_categories) >= 1:
        await message.answer(
            """
            <b>Ваши заказы:</b>
            """,
            reply_markup=position_edit_category_swipe_fp(0),
        )
    else:
        await message.answer("<b>❌ Отсутствуют категории для изменения позиций</b>")




@router.message(F.text == "✅ Выполненные")
async def user_profile(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    get_categories = Categoryx.get_all()
    get_positions = Positionx.get_by_id_and_status(message.from_user.id, position_status=1)

    if len(get_categories) >= 1:
        await message.answer(
            """
            <b>Ваши заказы:</b>
            """,
            reply_markup=position_edit_category_swipe_fp(0),
        )
    else:
        await message.answer("<b>❌ Отсутствуют категории для изменения позиций</b>")'''


#! Открытие заказов
@router.message(F.text == "📦 Все заказы")
async def prod_position_edit(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    get_categories = Categoryx.get_all()

    if len(get_categories) >= 1:
        await message.answer(
            """
            <b>Ваши заказы:</b>
            """,
            reply_markup=admin_position_edit_category_swipe_fp(0),
        )
    else:
        await message.answer("<b>❌ Отсутствуют категории для изменения позиций</b>")


def _short(t: str, n: int = 48) -> str:
    t = (t or "").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def _pos_ext(desc: str) -> dict:
    if not desc:
        return {}
    try:
        s = (
            desc.split("\n", 1)[1]
            if desc.startswith("[ORDER]") and "\n" in desc
            else desc
        )
        return json.loads(s or "{}")
    except Exception:
        return {}


def _status_label(pos_dict: dict, worker_id: int) -> str:
    st = pos_dict.get("position_status", 0) or 0
    assigned = (pos_dict.get("worker_id", 0) or 0) == worker_id
    if not assigned:
        return "ожидает подтверждения"
    if st == 2:
        return "выполнен"
    if st == 1:
        return "в работе"
    return "назначен"


def _pos_to_dict(pos) -> dict:
    return {
        "position_id": pos.position_id,
        "position_unix": pos.position_unix,
        "position_name": getattr(pos, "position_name", "") or "",
        "position_price": getattr(pos, "position_price", 0) or 0,
        "position_desc": getattr(pos, "position_desc", "") or "",
        "category_id": getattr(pos, "category_id", 0) or 0,
        "worker_id": getattr(pos, "worker_id", 0) or 0,
        "position_status": getattr(pos, "position_status", 0) or 0,
    }


def _collect_my_responses(worker_id: int) -> dict:
    """
    Показываем ТОЛЬКО заказы, где этот пользователь назначен исполнителем:
      - current: все, где position_status != 2
      - done:    где position_status == 2
    Ключ элемента — position_unix (если >0), иначе position_id.
    """
    DONE_STATUSES = {2}  # при необходимости подстрой

    current: list[int] = []
    done: list[int] = []
    mp: dict[str, dict] = {}

    positions = Positionx.gets(worker_id=worker_id) or []

    def to_int(x, default=0):
        try:
            return int(x)
        except Exception:
            return default

    for pos in positions:
        d = _pos_to_dict(pos)

        punix = to_int(d.get("position_unix", 0))
        pid = to_int(d.get("position_id", 0))
        key = punix if punix > 0 else pid
        if key == 0:
            continue  # пропускаем совсем кривые записи

        # записываем в map
        if str(key) not in mp:
            # можно добавить служебные пометки, не ломая существующую логику
            d.setdefault("_key_is_punix", punix > 0)
            d.setdefault("_key_val", key)
            mp[str(key)] = d

        status = to_int(d.get("position_status", 0))
        if status in DONE_STATUSES:
            done.append(key)
        else:
            current.append(key)

    # дедуп и сортировка: новые выше (по punix, иначе по id)
    def sort_key(k: int) -> int:
        dd = mp.get(str(k), {})
        pu = to_int(dd.get("position_unix", 0))
        return pu if pu > 0 else to_int(dd.get("position_id", 0))

    current = sorted(set(current), key=sort_key, reverse=True)
    done = sorted(set(done), key=sort_key, reverse=True)

    return {"current": current, "done": done, "map": mp}


def _tabs(
    current_count: int, done_count: int, active: str
) -> list[list[InlineKeyboardButton]]:
    cur = ("• " if active == "current" else "") + f"⏳ Текущие ({current_count})"
    don = ("• " if active == "done" else "") + f"✅ Завершённые ({done_count})"
    return [
        [
            InlineKeyboardButton(text=cur, callback_data="myresp:tab:current"),
            InlineKeyboardButton(text=don, callback_data="myresp:tab:done"),
        ]
    ]


def _list_kb(
    tab: str,
    items_unix: list[int],
    mp: dict,
    page: int,
    per_page: int,
    total: int,
    worker_id: int,
    tot_cur: int,
    tot_done: int,
):
    rows = []
    rows.extend(_tabs(tot_cur, tot_done, tab))
    for punix in items_unix:
        p = mp.get(str(punix), {})
        ext = _pos_ext(p.get("position_desc", ""))
        name = _short(p.get("position_name") or "Заказ", 30)
        budget = p.get("position_price") or ext.get("budget")
        budget_text = (
            f"{budget}₽"
            if isinstance(budget, (int, float))
            else str(budget or "договорная")
        )
        status_text = _status_label(p, worker_id)
        addr = _short(ext.get("address") or "—", 18)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{name} • {budget_text} • {status_text} • {addr}",
                    callback_data=f"myresp:view:{punix}",
                )
            ]
        )
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"myresp:page:{tab}:{page-1}"
            )
        )
    if (page + 1) * per_page < total:
        nav.append(
            InlineKeyboardButton(
                text="Вперёд ➡️", callback_data=f"myresp:page:{tab}:{page+1}"
            )
        )
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _show_myresp(
    message: Message,
    state: FSMContext,
    worker_id: int,
    tab: str,
    page: int,
    per_page: int = 6,
):
    data = await state.get_data()
    dataset = data.get("myresp_data") or _collect_my_responses(worker_id)
    await state.update_data(myresp_data=dataset)

    mp = dataset["map"]
    cur = dataset["current"]
    don = dataset["done"]
    src = cur if tab == "current" else don
    total = len(src)
    start = page * per_page
    items = src[start : start + per_page]
    kb = _list_kb(tab, items, mp, page, per_page, total, worker_id, len(cur), len(don))

    txt = "<b>📋 Мои отклики</b>\nВыберите заказ:"
    try:
        await message.edit_text(txt, reply_markup=kb)
    except Exception:
        await message.answer(txt, reply_markup=kb)

    await state.update_data(myresp_tab=tab, myresp_page=page, myresp_per=per_page)


@router.callback_query(StateFilter("myresp_list"), F.data.startswith("myresp:tab:"))
async def myresp_tab(call: CallbackQuery, state: FSMContext):
    tab = call.data.split(":")[2]
    await _show_myresp(call.message, state, call.from_user.id, tab=tab, page=0)
    await call.answer()


@router.callback_query(StateFilter("myresp_list"), F.data.startswith("myresp:page:"))
async def myresp_page(call: CallbackQuery, state: FSMContext):
    _, _, tab, page_str = call.data.split(":")
    await _show_myresp(
        call.message, state, call.from_user.id, tab=tab, page=int(page_str)
    )
    await call.answer()


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@router.callback_query(StateFilter("myresp_list"), F.data.startswith("myresp:view:"))
async def myresp_view(call: CallbackQuery, state: FSMContext):
    punix = int(call.data.split(":")[2])
    data = await state.get_data()
    dataset = data.get("myresp_data") or {}
    rec = (dataset.get("map") or {}).get(str(punix))

    # подстрахуемся: подтянем напрямую
    if not rec:
        pos = Positionx.get(position_unix=punix)
        if not pos:
            await call.answer("Заказ не найден.", show_alert=True)
            return
        rec = _pos_to_dict(pos)

    ext = _pos_ext(rec.get("position_desc", ""))
    cats_map = {c.category_id: c.category_name for c in Categoryx.get_all()}
    cat_ids = ext.get("categories") or (
        [rec.get("category_id")] if rec.get("category_id") else []
    )
    cats_text = (
        ", ".join([cats_map.get(cid, str(cid)) for cid in cat_ids]) if cat_ids else "—"
    )

    budget = int(rec.get("position_price", 0) or 0)
    budget_text = (
        f"{budget} руб." if budget > 0 else (ext.get("budget") or "договорная")
    )
    city = ext.get("city", "—")
    address = ext.get("address", "—")
    dates = ext.get("dates", "—")
    desc = ext.get("raw_desc", rec.get("position_name") or "")

    txt = ded(
        f"""
        <b>Заказ</b>

        🏙 Город: <code>{city}</code>
        📍 Адрес: <code>{address}</code>
        🧰 Категории: <code>{cats_text}</code>
        💰 Бюджет: <code>{budget_text}</code>
        📅 Сроки: <code>{dates}</code>

        📝 Описание:
        {desc}
    """
    )

    worker_id = call.from_user.id
    assigned_id = int(rec.get("worker_id", 0) or 0)
    pid = int(rec.get("position_id", 0) or 0)  # ID заказчика
    status = int(rec.get("position_status", 0) or 0)  # 0=свободен,1=в работе,2=завершён
    assigned = assigned_id == worker_id

    buttons: list[list[InlineKeyboardButton]] = []

    # 1) «Сдать работу» — только если назначен и не завершён
    if assigned and status != 2:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🚚 Сдать работу", callback_data=f"myresp:handoff:{punix}"
                )
            ]
        )

    # 2) либо «Связаться», либо «Ожидает подтверждения»
    if assigned:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📞 Связаться с заказчиком", url=f"tg://user?id={pid}"
                )
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⏳ Ожидает подтверждения", callback_data="noop"
                )
            ]
        )

    # 3) Назад к списку
    tab = data.get("myresp_tab", "current")
    page = int(data.get("myresp_page", 0))
    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к списку", callback_data=f"myresp:page:{tab}:{page}"
            )
        ]
    )

    await call.message.edit_text(
        txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await call.answer()


# -*- coding: utf-8 -*-
from aiogram import Router, F, types, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
import json
from typing import List, Dict, Any, Optional


from tgbot.utils.const_functions import ded, clear_html


# ────────────────────────── Вспомогалки ──────────────────────────


def _short(text: str, maxlen: int = 80) -> str:
    t = (text or "").strip()
    if len(t) <= maxlen:
        return t
    return t[: maxlen - 1] + "…"


def _pos_ext(desc: str) -> Dict[str, Any]:
    """
    В Positionx.add мы паковали JSON как:
    position_desc = "[ORDER]\n{json}"
    Здесь достанем словарь ext.
    """
    if not desc:
        return {}
    try:
        # срежем префикс "[ORDER]\n" если он есть
        s = desc
        if s.startswith("[ORDER]"):
            s = s.split("\n", 1)[1] if "\n" in s else ""
        return json.loads(s or "{}")
    except Exception:
        return {}


def _user_allowed_category_ids(user) -> List[int]:
    """
    Преобразуем специализации пользователя (строка с названиями через запятую)
    в список category_id по совпадению имени категории.
    """
    specs_titles = [
        t.strip() for t in (user.specializations or "").split(",") if t.strip()
    ]
    if not specs_titles:
        return []

    cats = Categoryx.get_all()
    title_to_id = {c.category_name.strip().lower(): c.category_id for c in cats}
    ids = []
    for title in specs_titles:
        cid = title_to_id.get(title.strip().lower())
        if cid is not None:
            ids.append(cid)
    return ids


def _filter_orders_for_worker(all_orders: List[Any], worker) -> List[Any]:
    """
    Фильтр: город совпадает, и есть пересечение категорий заказа и специализаций исполнителя.
    """
    worker_city = (worker.city or "").strip()
    allowed_cat_ids = set(_user_allowed_category_ids(worker))
    result = []
    for p in all_orders:
        ext = _pos_ext(p.position_desc)
        city_ok = (
            (ext.get("city") or "").strip() == worker_city if worker_city else False
        )

        order_cat_ids = set(ext.get("categories") or [])
        # если в ext пусто, попробуем обычный category_id
        if not order_cat_ids and getattr(p, "category_id", None) is not None:
            order_cat_ids = {p.category_id}

        spec_ok = bool(allowed_cat_ids & order_cat_ids) if allowed_cat_ids else False

        if city_ok and spec_ok:
            result.append(p)
    return result


def _orders_category_swipe(
    cat_ids: List[int], page: int = 0, per_page: int = 8
) -> InlineKeyboardMarkup:
    """
    Пагинация по категориям, но показываем только категории, которые входят в специализации исполнителя.
    """
    all_cats = [c for c in Categoryx.get_all() if c.category_id in set(cat_ids)]
    start = page * per_page
    chunk = all_cats[start : start + per_page]

    rows, row = [], []
    for i, c in enumerate(chunk, 1):
        row.append(
            InlineKeyboardButton(
                text=c.category_name,
                callback_data=f"orders:cat_pick:{c.category_id}:{page}",
            )
        )
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"orders:cat_page:{page-1}")
        )
    if start + per_page < len(all_cats):
        nav.append(
            InlineKeyboardButton(text="➡️", callback_data=f"orders:cat_page:{page+1}")
        )
    if nav:
        rows.append(nav)

    return (
        InlineKeyboardMarkup(inline_keyboard=rows)
        if rows
        else InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Нет подходящих категорий", callback_data="noop"
                    )
                ]
            ]
        )
    )


def _orders_list_kb(
    cat_id: int, page: int, has_prev: bool, has_next: bool
) -> InlineKeyboardMarkup:
    nav = []
    if has_prev:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"orders:list_page:{cat_id}:{page-1}"
            )
        )
    if has_next:
        nav.append(
            InlineKeyboardButton(
                text="Вперёд ➡️", callback_data=f"orders:list_page:{cat_id}:{page+1}"
            )
        )
    rows = [nav] if nav else []
    return (
        InlineKeyboardMarkup(inline_keyboard=rows)
        if rows
        else types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Обновить",
                        callback_data=f"orders:list_page:{cat_id}:{page}",
                    )
                ]
            ]
        )
    )


def _order_item_kb(p) -> InlineKeyboardMarkup:
    # Идентифицируем заказ по (position_id (=client_id), position_unix)
    pid = getattr(p, "position_id", 0)  # это client_id, по твоей логике
    punix = getattr(p, "position_unix", 0)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="ℹ️ Подробнее", callback_data=f"orders:view:{pid}:{punix}"
                ),
                InlineKeyboardButton(
                    text="✋ Откликнуться",
                    callback_data=f"orders:respond:{pid}:{punix}",
                ),
            ]
        ]
    )


def _respond_back_kb(pid: int, punix: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="↩️ Назад к заказу", callback_data=f"orders:view:{pid}:{punix}"
                )
            ],
            [InlineKeyboardButton(text="Отмена", callback_data="orders:cancel_resp")],
        ]
    )


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def _orders_category_kb_with_back(allowed_cat_ids, page_idx=0) -> InlineKeyboardMarkup:
    kb = _orders_category_swipe(
        allowed_cat_ids, page_idx
    )  # твоя существующая клавиатура
    # добавим низом кнопку «Назад»
    kb.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="← Режимы просмотра", callback_data="orders:back_modes"
            )
        ]
    )
    return kb


def _orders_list_inline(
    cat_id: int,
    items_unix: list[int],
    orders_map: dict,
    page: int,
    per_page: int,
    total: int,
) -> InlineKeyboardMarkup:
    rows = []

    # Кнопки заказов
    for punix in items_unix:
        p = orders_map.get(str(punix), {})
        ext = _pos_ext(p.get("position_desc", ""))
        pid = int(p.get("position_id", 0))

        name = _short(p.get("position_name", ""), 30) or "Заказ"
        budget = p.get("position_price", 0)
        budget_text = f"{budget}₽" if budget else (ext.get("budget") or "договорная")
        address = ext.get("address", "—")

        # Текст кнопки: Название • Бюджет • Адрес(коротко)
        btn_text = f"{name} • {budget_text} • { _short(address, 18) }"
        rows.append(
            [
                InlineKeyboardButton(
                    text=btn_text, callback_data=f"orders:view:{pid}:{punix}"
                )
            ]
        )

    # Навигация
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"orders:list_page:{cat_id}:{page-1}"
            )
        )
    if (page + 1) * per_page < total:
        nav.append(
            InlineKeyboardButton(
                text="Вперёд ➡️", callback_data=f"orders:list_page:{cat_id}:{page+1}"
            )
        )
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ────────────────────────── Открытие: «Актуальные заказы» ──────────────────────────


from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
import html
from textwrap import shorten


# =============== Клавиатуры ===============


def _orders_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 ЗАказы из других городов", callback_data="orders:mode_all"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗂 Заказы из моего города ", callback_data="orders:mode_cats"
                )
            ],
        ]
    )


# helpers для парсинга ext и компактного текста кнопки
import json


def _ext_from_desc(desc: str) -> dict:
    if not desc:
        return {}
    s = str(desc)
    if s.startswith("[ORDER]"):
        try:
            _, js = s.split("\n", 1)
            return json.loads(js)
        except Exception:
            return {}
    return {}


def _trim_btn(text: str, limit: int = 64) -> str:
    # Telegram ограничивает длину подписи кнопки (~64 символа)
    if len(text) <= limit:
        return text
    # максимально режем название заказа, остальное оставляем
    return text[: limit - 1] + "…"


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def _orders_all_kb(
    slice_keys, mp, page: int, per_page: int, total: int
) -> InlineKeyboardMarkup:
    rows = []

    # одна "широкая" кнопка на строку
    for punix in slice_keys:
        rec = mp.get(str(punix)) or {}
        pid = int(rec.get("position_id", 0) or 0)
        name = (rec.get("position_name") or "").strip() or "Без названия"

        # ext: город, человекочитаемый бюджет
        ext = _ext_from_desc(rec.get("position_desc", "") or "")
        city = str(ext.get("city") or "—")

        price = int(rec.get("position_price", 0) or 0)
        budget_text = (
            f"{price} ₽" if price > 0 else str(ext.get("budget") or "договорная")
        )

        # компактная подпись в одну строку
        # пример: "🏙 Москва • 💰 25 000 ₽ • Установить двери"
        label = f"🏙 {city} • 💰 {budget_text} • {name}"
        label = _trim_btn(label)

        rows.append(
            [
                InlineKeyboardButton(
                    text=label, callback_data=f"orders:view:{pid}:{punix}"
                )
            ]
        )

    # пагинация
    last_page = max((total - 1) // per_page, 0)
    rows.append(
        [
            InlineKeyboardButton(
                text="«", callback_data=f"orders:all:page:{max(page-1, 0)}"
            ),
            InlineKeyboardButton(text=f"{page+1}/{last_page+1}", callback_data="noop"),
            InlineKeyboardButton(
                text="»", callback_data=f"orders:all:page:{min(page+1, last_page)}"
            ),
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


# =============== Хелперы ===============


def _to_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default


def _order_key(d: dict) -> int:
    """Ключ заказа: position_unix если >0, иначе position_id."""
    pu = _to_int(d.get("position_unix", 0))
    if pu > 0:
        return pu
    return _to_int(d.get("position_id", 0))


def _iter_all_positions():
    """Достаём все позиции без фильтра. Поддержка и get_all(), и gets()."""
    try:
        items = Positionx.get_all() or []
    except Exception:
        try:
            items = Positionx.gets() or []  # если твой gets работает без фильтров
        except TypeError:
            items = []
    return items


def _pos_is_active(d: dict) -> bool:
    """Считаем активным всё, что НЕ со статусом 2 (подстрой при необходимости)."""
    return _to_int(d.get("position_status", 0)) != 2


def _pos_to_public_dict(pos) -> dict:
    """Если у тебя уже есть _pos_to_dict, используй его. Иначе – лёгкий слепок."""
    try:
        return _pos_to_dict(pos)
    except NameError:
        return {
            "position_id": getattr(pos, "position_id", 0),
            "position_unix": getattr(pos, "position_unix", 0),
            "position_name": getattr(pos, "position_name", ""),
            "position_price": getattr(pos, "position_price", 0),
            "position_desc": getattr(pos, "position_desc", ""),
            "category_id": getattr(pos, "category_id", 0),
            "worker_id": getattr(pos, "worker_id", 0),
            "position_status": getattr(pos, "position_status", 0),
        }


import json, html, re
from aiogram import F
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext


def _ext_from_desc(position_desc: str) -> dict:
    if not position_desc:
        return {}
    s = str(position_desc)
    if s.startswith("[ORDER]"):
        try:
            _, js = s.split("\n", 1)
            return json.loads(js)
        except Exception:
            return {}
    return {}


def _key_for(p) -> int:
    pu = int(getattr(p, "position_unix", 0) or 0)
    return pu if pu > 0 else int(getattr(p, "position_id", 0) or 0)


def _sort_val(rec: dict) -> int:
    pu = int(rec.get("position_unix", 0) or 0)
    return pu if pu > 0 else int(rec.get("position_id", 0) or 0)


def _budget_text(price: int, ext_budget) -> str:
    if isinstance(price, int) and price > 0:
        return f"{price:,}".replace(",", " ") + " руб."
    return html.escape(str(ext_budget or "договорная"))


async def _ensure_orders_all_dataset(state: FSMContext):
    data = await state.get_data()
    keys = data.get("orders_all_list")
    mp_json = data.get("orders_all_map")
    if keys and mp_json:
        try:
            return keys, json.loads(mp_json)
        except Exception:
            pass

    # забираем только свободные и активные
    # (если ваш ORM не поддерживает пустой gets(), можно сделать gets(worker_id=0))
    all_free = Positionx.gets(worker_id=0) or []
    records = []
    for p in all_free:
        if int(getattr(p, "position_status", 0) or 0) == 2:
            continue
        k = _key_for(p)
        if not k:
            continue
        records.append(
            {
                "position_id": getattr(p, "position_id", 0),
                "position_name": getattr(p, "position_name", ""),
                "position_price": int(getattr(p, "position_price", 0) or 0),
                "position_desc": getattr(p, "position_desc", ""),
                "category_id": getattr(p, "category_id", 0),
                "position_unix": getattr(p, "position_unix", 0),
                "worker_id": getattr(p, "worker_id", 0),
                "position_status": getattr(p, "position_status", 0),
            }
        )

    # сортировка: новые выше
    records.sort(key=_sort_val, reverse=True)
    mp = {
        str(_key_for_obj := (rec["position_unix"] or rec["position_id"])): rec
        for rec in records
    }
    keys = [int(k) for k in mp.keys()]

    await state.update_data(
        orders_all_list=keys,
        orders_all_map=json.dumps(mp, ensure_ascii=False),
    )
    return keys, mp


# хелперы рядом с функцией (один раз добавь где-то выше)
import json


def _pos_ext(desc: str) -> dict:
    if not desc:
        return {}
    s = str(desc)
    if s.startswith("[ORDER]"):
        try:
            _, js = s.split("\n", 1)
            return json.loads(js)
        except Exception:
            return {}
    return {}


def _pos_cats(rec: dict) -> set[int]:
    cats = set()
    cid = rec.get("category_id")
    try:
        if cid is not None:
            cats.add(int(cid))
    except Exception:
        pass
    ext = _pos_ext(rec.get("position_desc", "") or "")
    for x in ext.get("categories") or []:
        try:
            cats.add(int(x))
        except Exception:
            pass
    return cats


def _pos_has_cat(rec: dict, cat_id: int) -> bool:
    try:
        cat_id = int(cat_id)
    except Exception:
        return False
    return cat_id in _pos_cats(rec)


def _match_city(rec: dict, city: str) -> bool:
    if not city:
        return True
    ext = _pos_ext(rec.get("position_desc", "") or "")
    rc = str(ext.get("city", "") or "").strip().lower()
    return rc == city.strip().lower()


# замена функции
async def _show_orders_all_page(
    msg_or_cb, page: int, state: FSMContext, per_page: int = 6
):
    keys, mp = await _ensure_orders_all_dataset(state)

    # читаем (необязательные) фильтры, если ты их где-то устанавливаешь
    data = await state.get_data()
    selected_cat = int(data.get("orders_cat_filter", 0) or 0)  # 0 = без фильтра
    city_filter = (data.get("orders_city_filter") or "").strip()  # "" = без фильтра

    # фильтруем с учётом ДОП. категорий и города
    filtered_keys = []
    for k in keys:
        rec = mp.get(str(k)) or {}
        if selected_cat and not _pos_has_cat(rec, selected_cat):
            continue
        if city_filter and not _match_city(rec, city_filter):
            continue
        filtered_keys.append(k)

    total = len(filtered_keys)
    last_page = max((total - 1) // per_page, 0)
    page = max(0, min(page, last_page))
    slice_keys = filtered_keys[page * per_page : page * per_page + per_page]

    kb = _orders_all_kb(slice_keys, mp, page, per_page, total)

    # подпись — покажем, что стоят фильтры (если стоят)
    suffix = []
    if city_filter:
        suffix.append(f"город: {city_filter}")
    if selected_cat:
        suffix.append(f"категория: {selected_cat}")
    filt_txt = f" ({', '.join(suffix)})" if suffix else ""

    text = f"<b>🧾 Актуальные заказы (все){filt_txt}</b>\nВыберите заказ:"

    try:
        from aiogram.types import CallbackQuery

        if isinstance(msg_or_cb, CallbackQuery):
            await msg_or_cb.message.edit_text(text, reply_markup=kb)
            await msg_or_cb.answer()
        else:
            await msg_or_cb.answer(text, reply_markup=kb)
    except Exception:
        if isinstance(msg_or_cb, CallbackQuery):
            await msg_or_cb.message.answer(text, reply_markup=kb)
            await msg_or_cb.answer()
        else:
            await msg_or_cb.answer(text, reply_markup=kb)

    await state.update_data(orders_all_page=page, orders_all_per_page=per_page)


# =============== Роуты ===============


@router.message(F.text == "📝 Актуальные заказы")
async def orders_root(message: Message, state: FSMContext):
    # Показываем выбор режима: «Все» / «По категориям»
    await state.clear()
    await message.answer(
        "<b>Как показать заказы?</b>",
        reply_markup=_orders_mode_kb(),
    )
    await state.set_state("orders_mode")


@router.callback_query(F.data == "orders:back_modes")
async def orders_back_modes(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text(
        "<b>Как показать заказы?</b>", reply_markup=_orders_mode_kb()
    )
    await cq.answer()
    await state.set_state("orders_mode")


# --- режим: ВСЕ ЗАКАЗЫ ---
@router.callback_query(F.data == "orders:mode_all")
async def orders_mode_all(cq: CallbackQuery, state: FSMContext):
    # Сразу показываем первую страницу «все заказы»
    await _show_orders_all_page(cq, page=0, state=state)
    await state.set_state("orders_all")


@router.callback_query(StateFilter("orders_all"), F.data.startswith("orders:all:page:"))
async def orders_all_page(cq: CallbackQuery, state: FSMContext):
    page = int(cq.data.split(":")[-1])
    await _show_orders_all_page(cq, page=page, state=state)
    await cq.answer()


import json
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def _ext_from_desc(position_desc: str) -> dict:
    if not position_desc:
        return {}
    s = str(position_desc)
    if s.startswith("[ORDER]"):
        try:
            _, js = s.split("\n", 1)
            return json.loads(js)
        except Exception:
            return {}
    return {}


@router.callback_query(StateFilter("orders_all"), F.data.startswith("orders:all:view:"))
async def orders_all_view(cq: CallbackQuery, state: FSMContext):
    # data: orders:all:view:{punix}:{page}
    try:
        _, _, _, punix_str, page_str = cq.data.split(":")
        punix = int(punix_str)
        page = int(page_str)
    except Exception:
        await cq.answer("Ошибка данных", show_alert=True)
        return

    data = await state.get_data()
    # карта создаётся в _show_orders_all_page / _ensure_orders_all_dataset
    mp_json = data.get("orders_all_map") or "{}"
    try:
        mp = json.loads(mp_json)
    except Exception:
        mp = {}

    rec = mp.get(str(punix))
    if not rec:
        # на всякий — подтянем напрямую
        pos = Positionx.get(position_unix=punix)
        if not pos:
            await cq.answer("Заказ не найден.", show_alert=True)
            return
        rec = {
            "position_id": getattr(pos, "position_id", 0),
            "position_name": getattr(pos, "position_name", ""),
            "position_price": getattr(pos, "position_price", 0),
            "position_desc": getattr(pos, "position_desc", ""),
            "category_id": getattr(pos, "category_id", 0),
            "position_unix": getattr(pos, "position_unix", 0),
            "worker_id": getattr(pos, "worker_id", 0),
            "position_status": getattr(pos, "position_status", 0),
        }

    ext = _ext_from_desc(rec.get("position_desc", ""))

    cats_map = {c.category_id: c.category_name for c in Categoryx.get_all()}
    cat_ids = ext.get("categories") or (
        [rec.get("category_id")] if rec.get("category_id") else []
    )
    cats_text = (
        ", ".join([cats_map.get(cid, str(cid)) for cid in cat_ids]) if cat_ids else "—"
    )

    budget = int(rec.get("position_price", 0) or 0)
    budget_text = (
        f"{budget} руб." if budget > 0 else (ext.get("budget") or "договорная")
    )
    city = ext.get("city", "—")
    address = ext.get("address", "—")
    dates = ext.get("dates", "—")
    desc = ext.get("raw_desc", rec.get("position_name", ""))

    txt = (
        "<b>Заказ</b>\n\n"
        f"🏙 Город: <code>{city}</code>\n"
        f"📍 Адрес: <code>{address}</code>\n"
        f"🧰 Категории: <code>{cats_text}</code>\n"
        f"💰 Бюджет: <code>{budget_text}</code>\n"
        f"📅 Сроки: <code>{dates}</code>\n\n"
        "📝 Описание:\n"
        f"{desc}"
    )

    # Кнопки: согласиться (если свободный) + назад
    worker_id = cq.from_user.id
    already_taken = int(rec.get("worker_id", 0) or 0) != 0
    buttons = []
    if not already_taken:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Согласиться на заказ",
                    callback_data=f"orders:all:agree:{punix}:{page}",
                )
            ]
        )
    else:
        buttons.append(
            [InlineKeyboardButton(text="⛔ Заказ уже занят", callback_data="noop")]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к списку", callback_data=f"orders:all:page:{page}"
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text="← Режимы просмотра", callback_data="orders:back_modes"
            )
        ]
    )

    await cq.message.edit_text(
        txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await cq.answer()


from aiogram import Bot

import json, html
from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Bot
from tgbot.utils.const_functions import ded

# convert_date может быть в другом модуле — если у тебя другой импорт, поправь
try:
    from tgbot.utils.const_functions import convert_date
except Exception:
    convert_date = None


@router.callback_query(
    StateFilter("orders_all"), F.data.startswith("orders:all:agree:")
)
async def orders_all_agree(cq: CallbackQuery, state: FSMContext, bot: Bot):
    # data: orders:all:agree:{punix}:{page}
    try:
        _, _, _, punix_str, page_str = cq.data.split(":")
        punix = int(punix_str)
        page = int(page_str)
    except Exception:
        await cq.answer("Ошибка данных", show_alert=True)
        return

    pos = Positionx.get(position_unix=punix)
    if not pos:
        await cq.answer("Заказ не найден.", show_alert=True)
        return

    # доступен?
    if (
        int(getattr(pos, "worker_id", 0) or 0) != 0
        or int(getattr(pos, "position_status", 0) or 0) == 2
    ):
        await cq.answer("Этот заказ уже недоступен.", show_alert=True)
        await _show_orders_all_page(cq, page=page, state=state)
        return

    worker_id = cq.from_user.id

    # 1) назначаем исполнителя и переводим в «в работе»
    try:
        _update_position_by_unix(punix, worker_id=worker_id, position_status=1)
    except Exception:
        await cq.answer("Не удалось взять заказ. Попробуйте ещё раз.", show_alert=True)
        return

    # 2) Показать исполнителю «Ждите ответа заказчика»
    try:
        await cq.message.edit_text("<b>🔄 Ждите ответа заказчика</b>")
    except Exception:
        pass

    # 3) Отправить заказчику карточку-уведомление с кнопками подтверждения (твоя логика)
    try:
        get_position = Positionx.get(position_unix=punix)
        get_user = Userx.get(user_id=worker_id)
        client_id = int(get_position.position_id)  # id заказчика
        purchase_price = round(float(get_position.position_price or 0), 2)
        if get_user:
            rating_val = getattr(get_user, "user_rating_avg", None)
            user_rating = round(rating_val, 2) if rating_val else "Нет оценок"
            reg_date = (
                convert_date(get_user.user_unix, False, False)
                if convert_date
                else str(get_user.user_unix)
            )
            user_name = (
                f"{get_user.user_name or ''} {get_user.user_surname or ''}".strip()
                or "Исполнитель"
            )
        else:
            user_rating = "Нет оценок"
            reg_date = "-"
            user_name = "Исполнитель"

        await bot.send_message(
            chat_id=client_id,
            text=ded(
                f"""
                <b>📦 Исполнитель отправил заявку на выполнение вашего заказа:</b>
                ➖➖➖➖➖➖➖➖➖➖
                ▪️ Заказ: <code>{html.escape(get_position.position_name or 'Заказ')}</code>
                ▪️ Цена: <code>{purchase_price}₽</code>

                <b>👤 Профиль исполнителя:</b>
                🆔 Имя: <code>{html.escape(user_name)}</code>
                ⭐ Средняя оценка: <code>{user_rating}</code>
                🕰 Регистрация: <code>{html.escape(reg_date)}</code>
            """
            ),
            reply_markup=confirm_tusk_button(
                int(get_position.position_id),
                purchase_price,
                worker_id,
                int(get_position.position_unix or 0),
            ),
            disable_web_page_preview=True,
        )
    except Exception:
        # не критично, если заказчик не запускал бота — просто игнорируем
        pass

    # 4) Обновляем кэш «все заказы», чтобы убрать взятый заказ
    data = await state.get_data()
    lst = list(data.get("orders_all_list") or [])
    try:
        mp = json.loads(data.get("orders_all_map") or "{}")
    except Exception:
        mp = {}
    if punix in lst:
        lst = [k for k in lst if k != punix]
    mp.pop(str(punix), None)
    await state.update_data(
        orders_all_list=lst,
        orders_all_map=json.dumps(mp, ensure_ascii=False),
    )

    await cq.answer("Вы отправили заявку заказчику ✔️")
    # при желании можно вернуть список:
    # await _show_orders_all_page(cq, page=page, state=state)


@router.callback_query(F.data.startswith("orders:all:p:"))
async def orders_all_pagination(cq: CallbackQuery, state: FSMContext):
    try:
        page = int(cq.data.split(":")[-1])
    except Exception:
        page = 0
    await _show_orders_all_page(cq, page=page, state=state)


import json, html
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram import F
from aiogram.types import CallbackQuery


def _ext_from_desc(position_desc: str) -> dict:
    if not position_desc:
        return {}
    s = str(position_desc)
    if s.startswith("[ORDER]"):
        try:
            _, js = s.split("\n", 1)
            return json.loads(js)
        except Exception:
            return {}
    return {}


@router.callback_query(F.data.startswith("orders:open:"))
async def orders_open(cq: CallbackQuery, state: FSMContext):
    # Поддерживаем два формата:
    #  - orders:open:{punix}
    #  - orders:open:{punix}:{page}
    parts = cq.data.split(":")
    try:
        punix = int(parts[2])
        if len(parts) > 3:
            page = int(parts[3])
        else:
            data_tmp = await state.get_data()
            page = int(data_tmp.get("orders_all_page", 0) or 0)
    except Exception:
        await cq.answer("Ошибка данных.", show_alert=True)
        return

    data = await state.get_data()
    mp_json = data.get("orders_all_map") or "{}"
    try:
        mp = json.loads(mp_json)
    except Exception:
        mp = {}

    rec = mp.get(str(punix))
    if not rec:
        pos = Positionx.get(position_unix=punix)
        if not pos:
            await cq.answer("Заказ не найден.", show_alert=True)
            return
        rec = {
            "position_id": getattr(pos, "position_id", 0),
            "position_name": getattr(pos, "position_name", ""),
            "position_price": int(getattr(pos, "position_price", 0) or 0),
            "position_desc": getattr(pos, "position_desc", ""),
            "category_id": getattr(pos, "category_id", 0),
            "position_unix": getattr(pos, "position_unix", 0),
            "worker_id": getattr(pos, "worker_id", 0),
            "position_status": getattr(pos, "position_status", 0),
        }

    ext = _ext_from_desc(rec.get("position_desc", ""))

    # --- Поля для вывода (с экранированием как в _show_confirmation) ---
    city = html.escape(str(ext.get("city", "—")))
    address = html.escape(str(ext.get("address", "—")))
    dates = html.escape(str(ext.get("dates", "—")))
    desc = html.escape(str(ext.get("raw_desc", rec.get("position_name", ""))))

    price = int(rec.get("position_price", 0) or 0)
    if price > 0:
        budget_text = f"{price:,}".replace(",", " ") + " руб."
    else:
        budget_text = html.escape(str(ext.get("budget", "договорная")))

    photos = list(ext.get("photos", []) or [])[:5]

    cats_map = {c.category_id: c.category_name for c in Categoryx.get_all()}
    cat_ids = ext.get("categories") or (
        [rec.get("category_id")] if rec.get("category_id") else []
    )
    cats_titles = [cats_map.get(cid, str(cid)) for cid in cat_ids]
    cats_text = html.escape(", ".join(cats_titles)) if cats_titles else "—"

    # --- Если есть фото — отправим медиа-группу (без подписи) ---
    if photos:
        media = [InputMediaPhoto(type="photo", media=fid) for fid in photos]
        try:
            await cq.message.answer_media_group(media=media)
        except Exception:
            # не критично — просто пропустим отправку фото
            pass

    # --- Текст карточки ---
    txt = (
        f"<b>Заказ</b>\n\n"
        f"🏙 Город: <code>{city}</code>\n"
        f"📍 Адрес: <code>{address}</code>\n"
        f"🧰 Категории: <code>{cats_text}</code>\n\n"
        f"📝 Описание:\n{desc}\n\n"
        f"💰 Бюджет: <code>{budget_text}</code>\n"
        f"📅 Сроки: <code>{dates}</code>\n"
        f"🖼 Фото: <code>{len(photos)} шт.</code>"
    )

    # --- Кнопки: «Согласиться» (если свободен), назад к списку, назад к режимам ---
    is_free = (
        int(rec.get("worker_id", 0) or 0) == 0
        and int(rec.get("position_status", 0) or 0) != 2
    )
    rows = []
    if is_free:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Согласиться на заказ",
                    callback_data=f"orders:all:agree:{punix}:{page}",
                )
            ]
        )
    else:
        rows.append(
            [InlineKeyboardButton(text="⛔ Заказ недоступен", callback_data="noop")]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к списку", callback_data=f"orders:all:page:{page}"
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="← Режимы просмотра", callback_data="orders:back_modes"
            )
        ]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    # Публикация карточки
    try:
        await cq.message.answer(txt, reply_markup=kb)
    except Exception:
        # fallback через edit_text, если нужно переписать предыдущее сообщение
        try:
            await cq.message.edit_text(txt, reply_markup=kb)
        except Exception:
            pass

    await cq.answer()


@router.callback_query(F.data == "orders:all:back")
async def orders_all_back(cq: CallbackQuery, state: FSMContext):
    page = (await state.get_data()).get("orders_all_page", 0)
    await _show_orders_all_page(cq, page=page, state=state)


@router.callback_query(F.data == "orders:mode_cats")
async def orders_mode_cats(cq: CallbackQuery, state: FSMContext):
    worker = Userx.get(user_id=cq.from_user.id)
    if not worker or not worker.city or not worker.specializations:
        await cq.message.edit_text(
            "❗ Для просмотра заказов по категориям заполните профиль: город и специализации.",
            reply_markup=_orders_mode_kb(),
        )
        await cq.answer()
        return

    allowed_cat_ids = _user_allowed_category_ids(worker)
    if not allowed_cat_ids:
        await cq.message.edit_text(
            "<b>🔎 По вашим специализациям пока нет категорий.</b>",
            reply_markup=_orders_mode_kb(),
        )
        await cq.answer()
        return

    await cq.message.edit_text(
        "<b>🔎 Выберите категорию:</b>",
        reply_markup=_orders_category_kb_with_back(allowed_cat_ids, 0),
    )
    await cq.answer()
    await state.set_state("orders_pick_category")


@router.callback_query(
    StateFilter("orders_pick_category"), F.data.startswith("orders:cat_page:")
)
async def orders_cat_page(call: CallbackQuery, state: FSMContext):
    page = int(call.data.split(":")[2])
    worker = Userx.get(user_id=call.from_user.id)
    kb = _orders_category_swipe(_user_allowed_category_ids(worker), page)
    await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@router.callback_query(
    StateFilter("orders_pick_category"), F.data.startswith("orders:cat_pick:")
)
async def orders_cat_pick(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    # формат: orders:cat_pick:{cat_id}:{src_page}
    try:
        _, _, cat_id_str, src_page = parts
        cat_id = int(cat_id_str)
    except Exception:
        await call.answer("Ошибка данных.", show_alert=True)
        return

    # 1) Берём все заказы категории
    all_in_cat = Positionx.gets(category_id=cat_id) or []

    # 2) Показываем только свободные и активные
    free_open = [
        p
        for p in all_in_cat
        if getattr(p, "worker_id", 0) == 0
        and int(getattr(p, "position_status", 0) or 0) != 2
    ]

    # 3) Фильтр под исполнителя (город/специализации и т.п.)
    worker = Userx.get(user_id=call.from_user.id)
    filtered = _filter_orders_for_worker(free_open, worker)

    if not filtered:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="← К категориям", callback_data="orders:mode_cats"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="← Режимы просмотра", callback_data="orders:back_modes"
                    )
                ],
            ]
        )
        await call.message.edit_text(
            "Пока нет свободных заказов по этой категории в вашем городе.",
            reply_markup=kb,
        )
        await call.answer()
        return

    # 4) Ключ заказа: position_unix (если >0), иначе position_id
    def _key_for(p) -> int:
        pu = int(getattr(p, "position_unix", 0) or 0)
        return pu if pu > 0 else int(getattr(p, "position_id", 0) or 0)

    orders_list = []
    orders_map = {}

    for p in filtered:
        key = _key_for(p)
        if not key:
            continue  # пропускаем совсем кривые записи
        orders_list.append(key)
        orders_map[str(key)] = {
            "position_id": getattr(p, "position_id", 0),
            "position_name": getattr(p, "position_name", ""),
            "position_price": getattr(p, "position_price", 0),
            "position_desc": getattr(p, "position_desc", ""),
            "category_id": getattr(p, "category_id", 0),
            "position_unix": getattr(p, "position_unix", 0),
            "worker_id": getattr(p, "worker_id", 0),
            "position_status": getattr(p, "position_status", 0),
        }

    # 5) Сортировка: новые выше (по punix, иначе по id)
    def _sort_val(k: int) -> int:
        d = orders_map[str(k)]
        pu = int(d.get("position_unix", 0) or 0)
        return pu if pu > 0 else int(d.get("position_id", 0) or 0)

    orders_list = sorted(set(orders_list), key=_sort_val, reverse=True)

    # 6) Пагинация/рендер
    await state.update_data(
        orders_cat_id=cat_id,
        orders_list=orders_list,
        orders_map=json.dumps(orders_map, ensure_ascii=False),
    )

    await _show_orders_page(call.message, cat_id, page=0, state=state)
    await state.set_state("orders_list_page")
    await call.answer()


async def _show_orders_page(
    msg: Message, cat_id: int, page: int, state: FSMContext, per_page: int = 5
):
    data = await state.get_data()
    orders_map = json.loads(data.get("orders_map", "{}"))
    order_unix_ids = data.get("orders_list", [])
    total = len(order_unix_ids)

    start = page * per_page
    items_unix = order_unix_ids[start : start + per_page]
    if not items_unix:
        await msg.edit_text("Заказов на этой странице нет.")
        return

    # Заголовок + инлайн кнопки вместо длинного текста
    kb = _orders_list_inline(cat_id, items_unix, orders_map, page, per_page, total)

    # если сообщение уже с текстом, то просто обновим и текст, и клаву
    try:
        await msg.edit_text("<b>📝 Актуальные заказы:</b>", reply_markup=kb)
    except Exception:
        await msg.answer("<b>📝 Актуальные заказы:</b>", reply_markup=kb)


@router.callback_query(
    StateFilter("orders_list_page"), F.data.startswith("orders:list_page:")
)
async def orders_list_page(call: CallbackQuery, state: FSMContext):
    _, _, cat_id_str, page_str = call.data.split(":")
    await _show_orders_page(call.message, int(cat_id_str), int(page_str), state=state)
    await call.answer()


# ────────────────────────── Подробнее / Отклик ──────────────────────────


def _find_by_pid_punix(state_data, pid: int, punix: int) -> Optional[Dict[str, Any]]:
    orders_map = json.loads(state_data.get("orders_map", "{}"))
    rec = orders_map.get(str(punix))
    if rec and rec.get("position_id") == pid and rec.get("position_unix") == punix:
        return rec
    return None


import html, json
from aiogram import F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext


def _budget_text(price: int, ext_budget) -> str:
    return (
        (f"{price:,}".replace(",", " ") + " руб.")
        if (isinstance(price, int) and price > 0)
        else html.escape(str(ext_budget or "договорная"))
    )


@router.callback_query(F.data.startswith("orders:view:"))
async def orders_view(call: CallbackQuery, state: FSMContext):
    # orders:view:{pid}:{punix}  или orders:view:{pid}:{punix}:{page}
    parts = call.data.split(":")
    try:
        _, _, pid_str, punix_str, *rest = parts
        pid, punix = int(pid_str), int(punix_str)
        data = await state.get_data()
        page = int(rest[0]) if rest else int(data.get("orders_all_page", 0) or 0)
    except Exception:
        await call.answer("Ошибка данных.", show_alert=True)
        return

    data = await state.get_data()
    rec = _find_by_pid_punix(data, pid, punix)
    if not rec:
        pos = Positionx.get(position_unix=punix)
        if not pos:
            await call.answer("Заказ не найден. Обновите список.", show_alert=True)
            return
        rec = _pos_to_dict(pos)  # твоя утилита в проекте

    ext = _pos_ext(rec.get("position_desc", ""))  # твоя утилита в проекте

    # Категории
    cats_map = {c.category_id: c.category_name for c in Categoryx.get_all()}
    cat_ids = ext.get("categories") or (
        [rec.get("category_id")] if rec.get("category_id") else []
    )
    cats_text = (
        ", ".join([cats_map.get(cid, str(cid)) for cid in cat_ids]) if cat_ids else "—"
    )
    cats_text = html.escape(cats_text)

    # Поля (экранируем)
    city = html.escape(str(ext.get("city", "—")))
    address = html.escape(str(ext.get("address", "—")))
    dates = html.escape(str(ext.get("dates", "—")))
    desc = html.escape(str(ext.get("raw_desc", "")))

    price = int(rec.get("position_price", 0) or 0)
    budget_text = _budget_text(price, ext.get("budget"))
    photos = list(ext.get("photos", []) or [])[:5]

    # Если есть фото — отправим медиа-группу
    if photos:
        media = [InputMediaPhoto(type="photo", media=fid) for fid in photos]
        try:
            await call.message.answer_media_group(media=media)
        except Exception:
            pass

    txt = (
        f"<b>Заказ</b>\n\n"
        f"🏙 Город: <code>{city}</code>\n"
        f"📍 Адрес: <code>{address}</code>\n"
        f"🧰 Категории: <code>{cats_text}</code>\n"
        f"💰 Бюджет: <code>{budget_text}</code>\n"
        f"📅 Сроки: <code>{dates}</code>\n\n"
        f"📝 Описание:\n{desc}"
    )

    # Кнопки: «Согласиться» если свободен, «Назад», «Режимы»
    is_free = (int(rec.get("worker_id", 0) or 0) == 0) and (
        int(rec.get("position_status", 0) or 0) != 2
    )

    rows = []
    if is_free:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Согласиться",
                    callback_data=f"orders:respond:{pid}:{punix}:{page}",
                )
            ]
        )
    else:
        rows.append(
            [InlineKeyboardButton(text="⛔ Заказ недоступен", callback_data="noop")]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к списку", callback_data=f"orders:all:page:{page}"
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="← Режимы просмотра", callback_data="orders:back_modes"
            )
        ]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    # Публикуем карточку (новым сообщением безопаснее, чтобы фото не терялись)
    try:
        await call.message.answer(txt, reply_markup=kb)
    except Exception:
        await call.message.edit_text(txt, reply_markup=kb)

    await state.set_state("orders_viewing")
    await call.answer()


def _pos_get_time_legacy(pos) -> int:
    return int(getattr(pos, "time", 0) or getattr(pos, "position_time", 0) or 0)


def _update_position_by_unix(punix: int, **changes):
    """
    Обновляет ровно один заказ по position_unix.
    Пробуем только безопасные вызовы: keyword-only / data=... / set / edit / instance.save().
    НИКАКИХ позиционных аргументов.
    """
    pos = Positionx.get(position_unix=punix)
    if not pos:
        raise RuntimeError("position not found")

    # Считываем текущее состояние
    fields = {}

    # базовые поля (только то, что реально встречается в модели)
    if hasattr(pos, "category_id"):
        fields["category_id"] = int(getattr(pos, "category_id") or 0)
    if hasattr(pos, "position_id"):
        fields["position_id"] = int(getattr(pos, "position_id") or 0)  # id заказчика
    if hasattr(pos, "position_name"):
        fields["position_name"] = getattr(pos, "position_name", "") or ""
    if hasattr(pos, "position_price"):
        fields["position_price"] = int(getattr(pos, "position_price") or 0)
    if hasattr(pos, "position_desc"):
        fields["position_desc"] = getattr(pos, "position_desc", "") or ""
    if hasattr(pos, "worker_id"):
        fields["worker_id"] = int(getattr(pos, "worker_id") or 0)
    if hasattr(pos, "position_status"):
        fields["position_status"] = int(getattr(pos, "position_status") or 0)

    # время — как есть, если поле существует (названия могут отличаться)
    if hasattr(pos, "time"):
        fields["time"] = int(getattr(pos, "time") or 0)
    if hasattr(pos, "position_time"):
        fields["position_time"] = int(getattr(pos, "position_time") or 0)

    # применяем изменения
    for k, v in changes.items():
        fields[k] = v

    last_err = None

    # 1) update(...) keyword-only
    if hasattr(Positionx, "update"):
        try:
            return Positionx.update_unix(position_unix=punix, **fields)
        except Exception as e:
            last_err = e
        # 1b) update(position_unix=..., data=fields)
        try:
            return Positionx.update_unix(position_unix=punix, data=fields)
        except Exception as e:
            last_err = e

    # 2) set(position_unix=..., data=fields)
    if hasattr(Positionx, "set"):
        try:
            return Positionx.set(position_unix=punix, data=fields)
        except Exception as e:
            last_err = e

    # 3) edit(...) keyword-only
    if hasattr(Positionx, "edit"):
        try:
            return Positionx.edit(position_unix=punix, **fields)
        except Exception as e:
            last_err = e

    # 4) Последний шанс: обновить инстанс и сохранить
    try:
        for k, v in fields.items():
            # обновим только существующие атрибуты модели
            if hasattr(pos, k):
                setattr(pos, k, v)
        if hasattr(pos, "update"):
            try:
                return pos.update()
            except Exception as e:
                last_err = e
        if hasattr(pos, "save"):
            return pos.save()
        if hasattr(pos, "commit"):
            return pos.commit()
    except Exception as e:
        last_err = e

    raise last_err or RuntimeError("No suitable update method on Positionx")


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def worker_request_kb(punix: int, worker_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить исполнителя",
                    callback_data=f"resp:approve:{punix}:{worker_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"resp:decline:{punix}:{worker_id}",
                )
            ],
        ]
    )


from aiogram import F, Bot
from aiogram.types import CallbackQuery
import html
from tgbot.database.db_position import Positionx

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import html


def orders_request_kb(punix: int, worker_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Профиль исполнителя",
                    callback_data=f"orders:worker_profile:{punix}:{worker_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Принять исполнителя",
                    callback_data=f"orders:approve_worker:{punix}:{worker_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"orders:decline_worker:{punix}:{worker_id}",
                )
            ],
        ]
    )


async def send_orders_decision(
    bot: Bot, chat_id: int, punix: int, worker_id: int, title: str
):
    text = (
        "✅ <b>На ваш заказ откликнулся исполнитель</b>\n\n"
        f"📦 Заказ: <code>{html.escape(title)}</code>\n\n"
        "Вы можете посмотреть профиль исполнителя (фото работ), а затем принять или отклонить."
    )
    await bot.send_message(
        chat_id,
        text,
        reply_markup=orders_request_kb(punix, worker_id),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data.startswith("orders:respond:"))
async def orders_respond(call: CallbackQuery, state: FSMContext, bot: Bot):
    # orders:respond:{pid}:{punix}:{page}
    try:
        _, _, pid_str, punix_str, page_str = call.data.split(":")
        punix = int(punix_str)
        page = int(page_str)
    except Exception:
        await call.answer("Ошибка данных.", show_alert=True)
        return

    pos = Positionx.get(position_unix=punix)
    if not pos:
        await call.answer("Заказ не найден.", show_alert=True)
        return

    # Если уже есть исполнитель или завершён — нельзя
    if (
        int(getattr(pos, "worker_id", 0) or 0) != 0
        or int(getattr(pos, "position_status", 0) or 0) == 2
    ):
        await call.answer("Этот заказ уже недоступен.", show_alert=True)
        await _show_orders_all_page(call, page=page, state=state)
        return

    client_id = int(getattr(pos, "position_id", 0) or 0)
    title = getattr(pos, "position_name", "Заказ")
    worker_id = call.from_user.id

    # 👉 не назначаем сразу; даём заказчику принять/отклонить после просмотра профиля
    await send_orders_decision(bot, client_id, punix, worker_id, title)

    await call.answer("Заявка отправлена заказчику. Ожидайте решения.")
    await _show_orders_all_page(call, page=page, state=state)


import json
from aiogram.types import InputMediaPhoto


@router.callback_query(F.data.startswith("orders:worker_profile:"))
async def orders_worker_profile(cq: CallbackQuery, bot: Bot):
    # orders:worker_profile:{punix}:{worker_id}
    try:
        _, _, punix_s, wid_s = cq.data.split(":")
        punix = int(punix_s)
        worker_id = int(wid_s)
    except Exception:
        await cq.answer("Ошибка данных", show_alert=True)
        return

    # проверим, что кнопку нажал именно заказчик этого заказа
    pos = Positionx.get(position_unix=punix)
    if not pos:
        await cq.answer("Заказ не найден", show_alert=True)
        return
    owner_id = int(getattr(pos, "position_id", 0) or 0)
    if cq.from_user.id != owner_id:
        await cq.answer(
            "Профиль может смотреть только заказчик по этому заказу.", show_alert=True
        )
        return

    u = Userx.get(user_id=worker_id)
    if not u:
        await cq.answer("Профиль исполнителя не найден.", show_alert=True)
        return

    # базовая информация
    rlname = getattr(u, "user_rlname", "") or ""
    surname = getattr(u, "user_surname", "") or ""
    name_line = (rlname + (" " + surname if surname else "")).strip() or "—"

    city = getattr(u, "city", "") or "—"
    exp = getattr(u, "experience_years", 0) or 0
    specs = getattr(u, "specializations", "") or "—"
    rating = getattr(u, "user_rating_avg", None)
    rating_txt = f"{round(rating,2)} / 5" if rating else "нет оценок"
    reg_unix = int(getattr(u, "user_unix", 0) or 0)
    try:
        reg_txt = convert_date(reg_unix, False, False)
    except Exception:
        reg_txt = "—"

    txt = (
        f"<b>👤 Профиль исполнителя</b>\n\n"
        f"Имя: <code>{html.escape(name_line)}</code>\n"
        f"Город: <code>{html.escape(str(city))}</code>\n"
        f"Опыт: <code>{exp} лет</code>\n"
        f"Специализации: <code>{html.escape(specs)}</code>\n"
        f"Рейтинг: <code>{rating_txt}</code>\n"
        f"Регистрация: <code>{reg_txt}</code>\n\n"
        f"Фото работ: ниже (если добавлены)."
    )

    # фото работ (media group до 10 шт.)
    photos_json = getattr(u, "work_photos_json", "[]") or "[]"
    try:
        photos = json.loads(photos_json)
        if not isinstance(photos, list):
            photos = []
    except Exception:
        photos = []

    # отправим профиль текстом
    await cq.message.answer(txt, disable_web_page_preview=True)

    # и медиа-группу, если есть
    if photos:
        media = [
            InputMediaPhoto(type="photo", media=file_id) for file_id in photos[:10]
        ]
        try:
            await cq.message.answer_media_group(media=media)
        except Exception:
            # если вдруг не вышло media_group — отправим по одному
            for fid in photos[:5]:
                try:
                    await cq.message.answer_photo(fid)
                except Exception:
                    pass

    # кнопка «назад к подтверждению»
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к подтверждению",
                    callback_data=f"orders:back_to_approve:{punix}:{worker_id}",
                )
            ]
        ]
    )
    await cq.message.answer("Готовы выбрать действие?", reply_markup=back_kb)
    await cq.answer()


@router.callback_query(F.data.startswith("orders:back_to_approve:"))
async def orders_back_to_approve(cq: CallbackQuery, bot: Bot):
    try:
        _, _, punix_s, wid_s = cq.data.split(":")
        punix = int(punix_s)
        worker_id = int(wid_s)
    except Exception:
        await cq.answer()
        return

    pos = Positionx.get(position_unix=punix)
    if not pos:
        await cq.answer("Заказ не найден", show_alert=True)
        return

    owner_id = int(getattr(pos, "position_id", 0) or 0)
    if cq.from_user.id != owner_id:
        await cq.answer("Недоступно.", show_alert=True)
        return

    title = getattr(pos, "position_name", "Заказ")
    # просто отправим ещё раз экран выбора (можно было бы отредактировать, но сообщение могло быть не тем)
    await send_orders_decision(bot, owner_id, punix, worker_id, title)
    await cq.answer()


@router.callback_query(F.data.startswith("orders:approve_worker:"))
async def orders_approve_worker(cq: CallbackQuery, bot: Bot):
    # orders:approve_worker:{punix}:{worker_id}
    try:
        _, _, punix_s, wid_s = cq.data.split(":")
        punix = int(punix_s)
        worker_id = int(wid_s)
    except Exception:
        await cq.answer("Ошибка данных", show_alert=True)
        return

    pos = Positionx.get(position_unix=punix)
    if not pos:
        await cq.answer("Заказ не найден", show_alert=True)
        return

    owner_id = int(getattr(pos, "position_id", 0) or 0)
    if cq.from_user.id != owner_id:
        await cq.answer("Подтвердить может только заказчик.", show_alert=True)
        return

    # Назначаем исполнителя и переводим в работу
    try:
        Positionx.update_unix(punix, worker_id=worker_id, position_status=1)
    except Exception:
        try:
            Positionx.update_gpt(
                "position_unix", punix, worker_id=worker_id, position_status=1
            )
        except Exception:
            await cq.answer("Не удалось назначить исполнителя.", show_alert=True)
            return

    try:
        await cq.message.edit_text(
            cq.message.html_text + "\n\n✅ Исполнитель назначен. Заказ в работе.",
            reply_markup=None,
        )
    except Exception:
        pass

    # уведомим исполнителя
    title = getattr(pos, "position_name", "Заказ")
    try:
        await bot.send_message(
            worker_id,
            f"✅ Вас назначили исполнителем по заказу «{html.escape(title)}». Удачной работы!",
        )
    except Exception:
        pass

    await cq.answer("Назначено ✔️")


@router.callback_query(F.data.startswith("orders:decline_worker:"))
async def orders_decline_worker(cq: CallbackQuery, bot: Bot):
    # orders:decline_worker:{punix}:{worker_id}
    try:
        _, _, punix_s, wid_s = cq.data.split(":")
        punix = int(punix_s)
        worker_id = int(wid_s)
    except Exception:
        await cq.answer("Ошибка данных", show_alert=True)
        return

    pos = Positionx.get(position_unix=punix)
    if not pos:
        await cq.answer("Заказ не найден", show_alert=True)
        return

    owner_id = int(getattr(pos, "position_id", 0) or 0)
    if cq.from_user.id != owner_id:
        await cq.answer("Отклонить может только заказчик.", show_alert=True)
        return

    # Ничего в заказе не меняем (оставляем свободным), просто уведомим исполнителя
    try:
        await cq.message.edit_text(
            cq.message.html_text + "\n\n❌ Отклонено.", reply_markup=None
        )
    except Exception:
        pass

    try:
        await bot.send_message(worker_id, "❌ Заказчик отклонил ваш отклик.")
    except Exception:
        pass

    await cq.answer("Отклонено")


@router.callback_query(F.data.startswith("resp:approve:"))
async def resp_approve(cq: CallbackQuery, bot: Bot):
    # data: resp:approve:{punix}:{worker_id}
    try:
        _, _, punix_s, wid_s = cq.data.split(":")
        punix = int(punix_s)
        wid = int(wid_s)
    except Exception:
        await cq.answer("Ошибка данных", show_alert=True)
        return

    pos = Positionx.get(position_unix=punix)
    if not pos:
        await cq.answer("Заказ не найден", show_alert=True)
        return

    owner_id = int(getattr(pos, "position_id", 0) or 0)
    if cq.from_user.id != owner_id:
        await cq.answer("Эта кнопка доступна только владельцу заказа.", show_alert=True)
        return

    current_worker = int(getattr(pos, "worker_id", 0) or 0)
    if current_worker and current_worker != wid:
        # уже назначен другой — просто уберём кнопки
        try:
            await cq.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await cq.answer("Заказ уже назначен другому исполнителю.", show_alert=True)
        return

    # Назначаем исполнителя и ставим статус «в работе» (1)
    try:
        Positionx.update_unix(punix, worker_id=wid, position_status=1)
    except Exception:
        try:
            Positionx.update_gpt(
                "position_unix", punix, worker_id=wid, position_status=1
            )
        except Exception:
            await cq.answer("Не удалось назначить исполнителя.", show_alert=True)
            return

    # Обновим сообщение и уведомим исполнителя
    try:
        await cq.message.edit_text(
            cq.message.html_text + "\n\n✅ Исполнитель подтверждён.", reply_markup=None
        )
    except Exception:
        pass
    try:
        title = getattr(pos, "position_name", "Заказ")
        await bot.send_message(
            wid,
            "✅ Вас назначили исполнителем по заказу "
            f"«{html.escape(title)}». "
            f'Свяжитесь с заказчиком: <a href="tg://user?id={owner_id}">профиль</a>',
            disable_web_page_preview=True,
        )
    except Exception:
        pass

    await cq.answer("Подтверждено ✔️")


@router.callback_query(F.data.startswith("resp:decline:"))
async def resp_decline(cq: CallbackQuery, bot: Bot):
    # data: resp:decline:{punix}:{worker_id}
    try:
        _, _, punix_s, wid_s = cq.data.split(":")
        punix = int(punix_s)
        wid = int(wid_s)
    except Exception:
        await cq.answer("Ошибка данных", show_alert=True)
        return

    pos = Positionx.get(position_unix=punix)
    if not pos:
        await cq.answer("Заказ не найден", show_alert=True)
        return

    owner_id = int(getattr(pos, "position_id", 0) or 0)
    if cq.from_user.id != owner_id:
        await cq.answer("Эта кнопка доступна только владельцу заказа.", show_alert=True)
        return

    # Если именно этот исполнитель уже был назначен — снимаем
    try:
        cur_w = int(getattr(pos, "worker_id", 0) or 0)
    except Exception:
        cur_w = 0
    if cur_w == wid:
        try:
            Positionx.update_unix(punix, worker_id=0, position_status=0)
        except Exception:
            try:
                Positionx.update_gpt(
                    "position_unix", punix, worker_id=0, position_status=0
                )
            except Exception:
                pass

    try:
        await cq.message.edit_text(
            cq.message.html_text + "\n\n❌ Заявка отклонена.", reply_markup=None
        )
    except Exception:
        pass
    try:
        await bot.send_message(wid, "❌ Заказчик отклонил вашу заявку.")
    except Exception:
        pass

    await cq.answer("Отклонено")


@router.callback_query(StateFilter("orders_viewing"), F.data == "orders:back_to_list")
async def back_to_list(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cat_id = int(data.get("orders_cat_id", 0))
    await _show_orders_page(call.message, cat_id, page=0, state=state)
    await state.set_state("orders_list_page")
    await call.answer()


# ── шаг 1 отклика: спросить комментарий
@router.callback_query(F.data.startswith("orders:respond:"))
async def orders_respond_begin(call: CallbackQuery, state: FSMContext):
    _, _, pid_str, punix_str = call.data.split(":")
    pid, punix = int(pid_str), int(punix_str)

    await state.update_data(resp_pid=pid, resp_punix=punix)
    await call.message.edit_text(
        "✍️ Напишите комментарий/предложение для заказчика (что сделаете, сроки и т.п.):",
        reply_markup=_respond_back_kb(pid, punix),
    )
    await state.set_state("orders_resp_comment")
    await call.answer()


@router.message(StateFilter("orders_resp_comment"))
async def orders_resp_comment_get(message: Message, state: FSMContext):
    comment = clear_html(message.text or "").strip()
    if not comment or len(comment) < 5:
        await message.answer(
            "❌ Слишком короткий комментарий. Опишите предложение подробнее:"
        )
        return
    await state.update_data(resp_comment=comment)
    await message.answer(
        "💰 Укажите ваше предложение по цене (число в рублях), либо отправьте слово <code>договорная</code>.",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    await state.set_state("orders_resp_offer")


# helper: безопасно получить позицию по unix
def _get_position_by_unix(punix: int):
    try:
        return Positionx.get(position_unix=punix)
    except Exception:
        return None


# ✅ Принять исполнителя
@router.callback_query(F.data.startswith("resp:approve:"))
async def resp_approve(call: CallbackQuery, bot: Bot):
    try:
        _, _, punix_str, worker_id_str = call.data.split(":")
        punix = int(punix_str)
        worker_id = int(worker_id_str)
    except Exception:
        await call.answer("Некорректные данные.", show_alert=True)
        return

    # если нет _get_position_by_unix, используй: pos = Positionx.get(position_unix=punix)
    pos = _get_position_by_unix(punix)
    if not pos:
        await call.answer("Заказ не найден.", show_alert=True)
        return

    if call.from_user.id != int(pos.position_id):
        await call.answer("Подтверждать может только владелец заказа.", show_alert=True)
        return

    current = int(getattr(pos, "worker_id", 0) or 0)
    if current and current != worker_id:
        await call.answer("Уже выбран другой исполнитель.", show_alert=True)
        return

    # 🔧 НАЗНАЧАЕМ ИСПОЛНИТЕЛЯ «ЖЕЛЕЗНО» по position_unix
    if not _assign_worker_by_unix(punix, worker_id, status=1):  # 1 = в работе/назначен
        await call.answer(
            "Не удалось сохранить выбор. Сообщите администратору.", show_alert=True
        )
        return

    # 📝 Обновляем статус отклика → одобрен (status=1)
    try:
        if HAS_RESPONSES_TABLE:
            r = Responsesx.get_by_worker_and_punix(worker_id, punix)
            if r:
                Responsesx.update(r.response_id, status=1)
            else:
                # на всякий случай создадим запись, если её не было
                Responsesx.add(
                    worker_id=worker_id,
                    position_unix=punix,
                    comment="",
                    offer="договорная",
                    status=1,
                )
    except Exception:
        pass

    kb_client = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Связаться с исполнителем", url=f"tg://user?id={worker_id}"
                )
            ]
        ]
    )
    kb_worker = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Связаться с заказчиком", url=f"tg://user?id={pos.position_id}"
                )
            ]
        ]
    )

    try:
        await call.message.edit_text(
            "✅ Вы подтвердили исполнителя. Можете связаться с ним.",
            reply_markup=kb_client,
        )
    except Exception:
        await call.message.answer(
            "✅ Вы подтвердили исполнителя. Можете связаться с ним.",
            reply_markup=kb_client,
        )

    try:
        await bot.send_message(
            worker_id,
            "🎉 Вас выбрали исполнителем по заказу! Теперь вы можете связаться с заказчиком.",
            reply_markup=kb_worker,
        )
    except Exception:
        pass

    await bot.send_message(
        chat_id=call.from_user.id,
        text="Главное меню:",
        reply_markup=menu_second_start_clients(call.from_user.id),
    )
    await bot.send_message(
        chat_id=worker_id,
        text="Главное меню:",
        reply_markup=menu_second_start(worker_id),
    )


# ❌ Отклонить отклик
@router.callback_query(F.data.startswith("resp:reject:"))
async def resp_reject(call: CallbackQuery, bot: Bot):
    try:
        _, _, punix_str, worker_id_str = call.data.split(":")
        punix = int(punix_str)
        worker_id = int(worker_id_str)
    except Exception:
        await call.answer("Некорректные данные.", show_alert=True)
        return

    pos = _get_position_by_unix(punix)
    if not pos:
        await call.answer("Заказ не найден.", show_alert=True)
        return

    if call.from_user.id != int(pos.position_id):
        await call.answer("Отклонять может только владелец заказа.", show_alert=True)
        return

    # можно отправить исполнителю уведомление
    try:
        await bot.send_message(worker_id, "❌ Заказчик отклонил ваш отклик.")
    except Exception:
        pass

    try:
        await call.message.edit_text("Отклик отклонён.")
        await bot.send_message(
            chat_id=call.from_user.id,
            text="Главное меню:",
            reply_markup=menu_second_start_clients(call.from_user.id),
        )
    except Exception:
        await call.message.answer("Отклик отклонён.")
    await call.answer()


# ───────── helpers ─────────


def _short(text: str, maxlen: int = 48) -> str:
    t = (text or "").strip()
    return t if len(t) <= maxlen else (t[: maxlen - 1] + "…")


def _pos_ext(desc: str) -> Dict[str, Any]:
    if not desc:
        return {}
    try:
        s = desc
        if s.startswith("[ORDER]"):
            s = s.split("\n", 1)[1] if "\n" in s else ""
        return json.loads(s or "{}")
    except Exception:
        return {}


def _status_label(pos, worker_id: int) -> str:
    """Возвращает человекочитаемый статус для элемента списка откликов."""
    st = getattr(pos, "position_status", 0) or 0
    assigned = (getattr(pos, "worker_id", 0) or 0) == worker_id
    if not assigned:
        return "ожидает подтверждения"
    if st == 2:
        return "выполнен"
    if st == 1:
        return "в работе"
    return "назначен"


def _pos_to_dict(pos) -> Dict[str, Any]:
    return {
        "position_id": pos.position_id,
        "position_unix": pos.position_unix,
        "position_name": getattr(pos, "position_name", "") or "",
        "position_price": getattr(pos, "position_price", 0) or 0,
        "position_desc": getattr(pos, "position_desc", "") or "",
        "category_id": getattr(pos, "category_id", 0) or 0,
        "worker_id": getattr(pos, "worker_id", 0) or 0,
        "position_status": getattr(pos, "position_status", 0) or 0,
    }


def _tabs_kb(
    current_count: int, done_count: int, active: str
) -> List[List[InlineKeyboardButton]]:
    cur_text = f"⏳ Текущие ({current_count})"
    done_text = f"✅ Завершённые ({done_count})"
    # пометим активную вкладку символом •
    if active == "current":
        cur_text = "• " + cur_text
    if active == "done":
        done_text = "• " + done_text
    return [
        [
            InlineKeyboardButton(text=cur_text, callback_data="myresp:tab:current"),
            InlineKeyboardButton(text=done_text, callback_data="myresp:tab:done"),
        ]
    ]


def _list_kb(
    tab: str,
    items_unix: list[int],
    orders_map: dict,
    page: int,
    per_page: int,
    total: int,
    worker_id: int,
    tot_cur: int,
    tot_done: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    # первая строка — вкладки с корректными счетчиками
    cur_text = ("• " if tab == "current" else "") + f"⏳ Текущие ({tot_cur})"
    don_text = ("• " if tab == "done" else "") + f"✅ Завершённые ({tot_done})"
    rows.append(
        [
            InlineKeyboardButton(text=cur_text, callback_data="myresp:tab:current"),
            InlineKeyboardButton(text=don_text, callback_data="myresp:tab:done"),
        ]
    )

    # элементы
    for punix in items_unix:
        p = orders_map.get(str(punix), {})
        ext = _pos_ext(p.get("position_desc", ""))
        name = _short(p.get("position_name") or "Заказ", 30)
        budget = p.get("position_price") or ext.get("budget")
        budget_text = (
            f"{budget}₽"
            if isinstance(budget, (int, float))
            else str(budget or "договорная")
        )
        status_text = _status_label(p, worker_id)
        addr = _short(ext.get("address") or "—", 18)

        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{name} • {budget_text} • {status_text} • {addr}",
                    callback_data=f"myresp:view:{punix}",
                )
            ]
        )

    # навигация
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"myresp:page:{tab}:{page-1}"
            )
        )
    if (page + 1) * per_page < total:
        nav.append(
            InlineKeyboardButton(
                text="Вперёд ➡️", callback_data=f"myresp:page:{tab}:{page+1}"
            )
        )
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


from aiogram.types import InlineKeyboardButton


async def _show_myresp_tab(
    msg: Message,
    tab: str,
    page: int,
    state: FSMContext,
    worker_id: int,
    per_page: int = 6,
):
    data = await state.get_data()
    dataset = data.get("myresp_data")
    if not dataset:
        dataset = _collect_my_responses(worker_id)
        await state.update_data(myresp_data=dataset)

    order_map = dataset.get("map", {}) or {}
    current_list = dataset.get("current", []) or []
    done_list = dataset.get("done", []) or []

    total_cur, total_done = len(current_list), len(done_list)
    source = current_list if tab == "current" else done_list
    total = len(source)

    # Нормализация пагинации
    per_page = per_page if per_page > 0 else 6
    last_page = max((total - 1) // per_page, 0)
    page = max(0, min(page, last_page))

    start = page * per_page
    items = source[start : start + per_page]

    # Генерим текущую клавиатуру (как раньше), НО снимаем первую строку-вкладки
    kb = _list_kb(
        tab, items, order_map, page, per_page, total, worker_id, total_cur, total_done
    )

    # если первой строкой идут вкладки — уберём её
    if kb.inline_keyboard:
        first_row = kb.inline_keyboard[0]
        if all(
            getattr(b, "callback_data", "")
            and getattr(b, "callback_data").startswith("myresp:tab:")
            for b in first_row
        ):
            kb.inline_keyboard.pop(0)

    # добавим «шаг назад»
    kb.inline_keyboard.append(
        [
            InlineKeyboardButton(
                text="← К выбору типа", callback_data="myresp:back_modes"
            )
        ]
    )

    # Заголовок по выбранному типу
    head = "🟢 Актуальные отклики" if tab == "current" else "✅ Завершённые отклики"
    if total == 0:
        text = f"<b>{head}</b>\nВ этом разделе пока пусто."
        try:
            await msg.edit_text(text, reply_markup=kb)
        except Exception:
            await msg.answer(text, reply_markup=kb)
        await state.update_data(myresp_tab=tab, myresp_page=0, myresp_per_page=per_page)
        return

    text = f"<b>{head}</b>\nВыберите заказ:"
    try:
        await msg.edit_text(text, reply_markup=kb)
    except Exception:
        await msg.answer(text, reply_markup=kb)

    # Запомним активную вкладку/страницу
    await state.update_data(myresp_tab=tab, myresp_page=page, myresp_per_page=per_page)


# ───────── entrypoint ─────────


from aiogram import F
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
)
from aiogram.fsm.context import FSMContext


def _myresp_mode_kb(total_cur: int = 0, total_done: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🟢 Актуальные ({total_cur})",
                    callback_data="myresp:mode:current",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"✅ Завершённые ({total_done})",
                    callback_data="myresp:mode:done",
                )
            ],
        ]
    )


# 1) Сначала стейт, потом сообщение
@router.message(F.text == "📋 Мои отклики")
async def my_responses_root(message: Message, state: FSMContext):
    await state.clear()
    worker_id = message.from_user.id

    dataset = _collect_my_responses(worker_id)
    await state.update_data(myresp_data=dataset)

    total_cur = len(dataset.get("current", []) or [])
    total_done = len(dataset.get("done", []) or [])

    # Сначала ставим стейт!
    await state.set_state("myresp_mode")

    await message.answer(
        "<b>Что показать?</b>",
        reply_markup=_myresp_mode_kb(total_cur, total_done),
    )


# 2) Режим: без StateFilter (чтобы не промахиваться при гонках стейта)
@router.callback_query(F.data.startswith("myresp:mode:"))
async def myresp_mode_pick(call: CallbackQuery, state: FSMContext):
    tab = call.data.split(":")[-1]  # current | done
    await _show_myresp_tab(
        call.message, tab=tab, page=0, state=state, worker_id=call.from_user.id
    )
    await state.set_state("myresp_list")
    await call.answer()


# 3) «Назад к выбору типа» — тоже без StateFilter
@router.callback_query(F.data == "myresp:back_modes")
async def myresp_back_modes(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    dataset = data.get("myresp_data") or {"current": [], "done": []}
    total_cur = len(dataset.get("current", []) or [])
    total_done = len(dataset.get("done", []) or [])

    await call.message.edit_text(
        "<b>Что показать?</b>",
        reply_markup=_myresp_mode_kb(total_cur, total_done),
    )
    await state.set_state("myresp_mode")
    await call.answer()


# Пагинация
@router.callback_query(StateFilter("myresp_list"), F.data.startswith("myresp:page:"))
async def myresp_page(call: CallbackQuery, state: FSMContext):
    _, _, tab, page_str = call.data.split(":")
    page = int(page_str)
    await _show_myresp_tab(
        call.message, tab=tab, page=page, state=state, worker_id=call.from_user.id
    )
    await call.answer()


from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List


@router.callback_query(StateFilter("myresp_list"), F.data.startswith("myresp:view:"))
async def myresp_view(call: CallbackQuery, state: FSMContext):
    punix = int(call.data.split(":")[2])
    data = await state.get_data()
    dataset = data.get("myresp_data") or {}
    mp = dataset.get("map", {})
    rec = mp.get(str(punix))

    # Если в карте нет — подтянем напрямую
    if not rec:
        pos = Positionx.get(position_unix=punix)
        if not pos:
            await call.answer("Заказ не найден.", show_alert=True)
            return
        rec = _pos_to_dict(pos)

    ext = _pos_ext(rec.get("position_desc", ""))

    cats_map = {c.category_id: c.category_name for c in Categoryx.get_all()}
    cat_ids = ext.get("categories") or (
        [rec.get("category_id")] if rec.get("category_id") else []
    )
    cats_text = (
        ", ".join([cats_map.get(cid, str(cid)) for cid in cat_ids]) if cat_ids else "—"
    )

    budget = int(rec.get("position_price", 0) or 0)
    budget_text = (
        f"{budget} руб." if budget > 0 else (ext.get("budget") or "договорная")
    )
    city = ext.get("city", "—")
    address = ext.get("address", "—")
    dates = ext.get("dates", "—")
    desc = ext.get("raw_desc", rec.get("position_name", ""))

    txt = ded(
        f"""
        <b>Заказ</b>

        🏙 Город: <code>{city}</code>
        📍 Адрес: <code>{address}</code>
        🧰 Категории: <code>{cats_text}</code>
        💰 Бюджет: <code>{budget_text}</code>
        📅 Сроки: <code>{dates}</code>

        📝 Описание:
        {desc}
    """
    )

    # Кнопки (без дублей)
    worker_id = call.from_user.id
    assigned_id = int(rec.get("worker_id", 0) or 0)
    pid = int(rec.get("position_id", 0) or 0)  # id заказчика
    status = int(rec.get("position_status", 0) or 0)
    assigned = assigned_id == worker_id

    buttons: List[List[InlineKeyboardButton]] = []

    # 1) «Сдать работу» — только если назначен и не завершён
    if assigned and status != 2:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🚚 Сдать работу", callback_data=f"myresp:handoff:{punix}"
                )
            ]
        )

    # 2) Либо «Связаться», либо «Ожидает подтверждения»
    if assigned:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📞 Связаться с заказчиком", url=f"tg://user?id={pid}"
                )
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⏳ Ожидает подтверждения", callback_data="noop"
                )
            ]
        )

    # 3) Назад к списку
    tab = data.get("myresp_tab", "current")
    page = int(data.get("myresp_page", 0))
    buttons.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к списку", callback_data=f"myresp:page:{tab}:{page}"
            )
        ]
    )

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text(txt, reply_markup=kb)
    await call.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text(txt, reply_markup=kb)
    await call.answer()


from aiogram import Bot


@router.callback_query(StateFilter("myresp_list"), F.data.startswith("myresp:handoff:"))
async def myresp_handoff(call: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        punix = int(call.data.split(":")[-1])
    except Exception:
        await call.answer("Ошибка данных", show_alert=True)
        return

    pos = Positionx.get(position_unix=punix)
    if not pos:
        await call.answer("Заказ не найден", show_alert=True)
        return

    # проверяем, что именно этот воркер назначен
    worker_id = call.from_user.id
    if int(getattr(pos, "worker_id", 0) or 0) != worker_id:
        await call.answer("Вы не назначены на этот заказ.", show_alert=True)
        return

    client_id = int(
        getattr(pos, "position_id", 0) or 0
    )  # у вас position_id = id заказчика
    name = getattr(pos, "position_name", "Заказ")
    worker_mention = call.from_user.full_name or "Исполнитель"

    notify = ded(
        f"""
        ✅ <b>Исполнитель сообщил о завершении работы</b>

        📦 Заказ: <code>{name}</code>
        👤 Исполнитель: <a href="tg://user?id={worker_id}">{worker_mention}</a>

        Проверьте результат и подтвердите завершение в разделе «💡 Мои заказы».
    """
    )

    sent_ok = True
    try:
        await bot.send_message(client_id, notify, disable_web_page_preview=True)
    except Exception:
        sent_ok = False

    # ответ исполнителю
    if sent_ok:
        await call.answer("Уведомили заказчика ✔️", show_alert=False)
        # можно визуально отметить в карточке:
        try:
            await call.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="📨 Уведомление отправлено", callback_data="noop"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="⬅️ Назад к списку",
                                callback_data=f"myresp:page:{(await state.get_data()).get('myresp_tab','current')}:{int((await state.get_data()).get('myresp_page',0))}",
                            )
                        ],
                    ]
                )
            )
        except Exception:
            pass
    else:
        await call.answer(
            "Не удалось отправить уведомление заказчику (он мог не запускать бота).",
            show_alert=True,
        )


@router.message(StateFilter("orders_resp_offer"))
async def orders_resp_offer_get(message: Message, state: FSMContext, bot: Bot):
    offer_raw = (message.text or "").strip().lower()
    if offer_raw != "договорная":
        if not offer_raw.replace(" ", "").isdigit():
            await message.answer("❌ Введите число или слово <code>договорная</code>.")
            return
        offer = int(offer_raw.replace(" ", ""))
    else:
        offer = "договорная"

    data = await state.get_data()
    pid = int(data["resp_pid"])  # client_id владельца заказа
    punix = int(data["resp_punix"])  # идентификатор заказа (unix)
    comment = (data.get("resp_comment") or "").strip()

    # Проверяем, что заказ есть в локальной карте
    orders_map = json.loads(data.get("orders_map", "{}"))
    rec = orders_map.get(str(punix))
    if not rec or int(rec.get("position_id", 0)) != pid:
        await message.answer("Заказ не найден. Обновите список.")
        await state.clear()
        return

    worker = Userx.get(user_id=message.from_user.id)
    budget_text = f"{offer} руб." if isinstance(offer, int) else "договорная"

    # 1) Сохраняем/обновляем отклик в БД
    try:
        if HAS_RESPONSES_TABLE:
            existing = Responsesx.get_by_worker_and_punix(message.from_user.id, punix)
            if existing:
                # обновим комментарий/предложение и вернём в статус «ожидание»
                Responsesx.update(
                    existing.response_id, comment=comment, offer=str(offer), status=0
                )
            else:
                Responsesx.add(
                    worker_id=message.from_user.id,
                    position_unix=punix,
                    comment=comment,
                    offer=offer,
                    status=0,  # ожидание подтверждения заказчиком
                )
    except Exception:
        # не валим сценарий, если таблицы нет/ошибка БД
        pass

    # 2) Отправляем заказчику карточку отклика с кнопками
    kb_approve = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="✅ Принять исполнителя",
                    callback_data=f"resp:approve:{punix}:{message.from_user.id}",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"resp:reject:{punix}:{message.from_user.id}",
                )
            ],
        ]
    )

    try:
        await bot.send_message(
            chat_id=pid,
            text=ded(
                f"""
                📩 <b>Новый отклик на ваш заказ</b>

                Исполнитель: <b>{worker.user_rlname} {worker.user_surname}</b>
                Город: <code>{worker.city or '—'}</code>
                Специализации: <code>{worker.specializations or '—'}</code>

                💬 Комментарий:
                {comment or '—'}

                💰 Предложение: <b>{budget_text}</b>

                Выберите действие ниже:
            """
            ),
            reply_markup=kb_approve,
        )
    except Exception:
        # например, бот не может писать первым — просто пропустим
        pass

    await state.clear()
    await message.answer(
        "✅ Вы откликнулись на заказ! Ожидайте ответа заказчика.\n"
        "После подтверждения появится кнопка «Связаться с заказчиком».",
        reply_markup=menu_second_start(message.from_user.id),
    )


@router.callback_query(F.data == "orders:cancel_resp")
async def orders_cancel_resp(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Отклик отменён.")
    await call.answer()


# ✅ Открытие «Мои заказы» — список кнопками + пагинация
@router.message(F.text == "💡 Мои заказы")
async def my_orders_root(message: Message, state: FSM):
    await state.clear()

    user_id = message.from_user.id
    my_positions = Positionx.gets(position_id=user_id) or []
    # отсортируем по дате, новые выше (если есть поле position_unix)
    try:
        my_positions.sort(key=lambda p: p.position_unix, reverse=True)
    except Exception:
        pass

    if not my_positions:
        await message.answer("<b>❌ У вас пока нет заказов.</b>")
        return

    # сложим в state лёгкую карту для отображения
    await state.update_data(
        my_orders_list=[p.position_unix for p in my_positions],
        my_orders_map=json.dumps(
            {
                str(p.position_unix): {
                    "position_id": p.position_id,
                    "position_unix": p.position_unix,
                    "position_name": p.position_name,
                    "position_price": p.position_price,
                    "position_desc": p.position_desc,
                    "category_id": getattr(p, "category_id", 0),
                    "worker_id": getattr(p, "worker_id", 0),
                    "position_status": getattr(p, "position_status", 0),
                }
                for p in my_positions
            },
            ensure_ascii=False,
        ),
    )

    await _show_my_orders_page(message, page=0, state=state)
    await state.set_state("my_orders_list")


from aiogram.utils.keyboard import InlineKeyboardBuilder


def client_myorders_all_button_kb(owner_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(ikb("📄 Все категории", data=f"client_position_all_swipe:{owner_id}:0"))
    return kb.as_markup()


from math import ceil


def client_position_all_swipe_fp(remover: int, owner_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    positions = Positionx.gets(worker_id=owner_id) or []
    total = len(positions)
    if total == 0:
        # на всякий случай — вернём кнопку «Назад»
        kb.row(ikb("⬅️ Назад к категориям", data="position_edit_category_swipe:0"))
        return kb.as_markup()

    page_size = 10
    # зажимаем remover в границы
    if remover < 0:
        remover = 0
    if remover >= total:
        remover = ((total - 1) // page_size) * page_size

    # карта категорий для подписи
    cats = {c.category_id: c.category_name for c in (Categoryx.get_all() or [])}

    # текущая страница
    page = positions[remover : remover + page_size]
    for p in page:
        cat = cats.get(getattr(p, "category_id", 0), "")
        title = f"{p.position_name} · {cat}" if cat else p.position_name
        kb.row(
            ikb(
                title,
                data=f"client_position_edit_open:{p.position_unix}:{p.position_id}:{remover}",
            )
        )

    # пагинация
    pages = ceil(total / page_size)
    curr = (remover // page_size) + 1
    has_prev = remover > 0
    has_next = (remover + page_size) < total

    nav = []
    if pages > 1:
        if has_prev:
            nav.append(
                ikb(
                    "⬅️",
                    data=f"client_position_all_swipe:{owner_id}:{remover - page_size}",
                )
            )
        nav.append(ikb(f"{curr}/{pages}", data="..."))
        if has_next:
            nav.append(
                ikb(
                    "➡️",
                    data=f"client_position_all_swipe:{owner_id}:{remover + page_size}",
                )
            )
        kb.row(*nav)

    # кнопка обратно к категориям
    kb.row(ikb("📂 По категориям", data="position_edit_category_swipe:0"))

    return kb.as_markup()


@router.callback_query(F.data.startswith("client_position_all_swipe:"))
async def client_position_all_swipe(call: CallbackQuery, state: FSM, arSession: ARS):
    # client_position_all_swipe:<owner_id>:<remover>
    parts = call.data.split(":")
    try:
        remover = int(parts[-1])  # берём всегда последний элемент как номер страницы
    except Exception:
        remover = 0

    owner_id = call.from_user.id  # <-- критично: не доверяем числу из data

    # проверим, что у юзера реально есть заказы
    positions = Positionx.gets(worker_id=owner_id) or []
    if not positions:
        await call.message.answer("<b>❌ У вас нет заказов.</b>")
        await call.answer()
        return

    try:
        await call.message.edit_text(
            "<b>📁 Ваши заказы (все категории):</b>",
            reply_markup=client_position_all_swipe_fp(remover, owner_id),
        )
    except Exception:
        # на случай "message is not modified" и пр.
        await call.message.answer(
            "<b>📁 Ваши заказы (все категории):</b>",
            reply_markup=client_position_all_swipe_fp(remover, owner_id),
        )
    await call.answer()


# 🔧 helper: клавиатура и страница со списком
def _my_orders_inline_kb(
    items_unix: list[int], orders_map: dict, page: int, per_page: int, total: int
) -> InlineKeyboardMarkup:
    rows = []
    for punix in items_unix:
        p = orders_map.get(str(punix), {})
        # короткая инфа
        name = (p.get("position_name") or "Заказ").strip()
        if len(name) > 30:
            name = name[:29] + "…"
        budget = p.get("position_price") or 0

        # статус по простому: 0 — активен, 1 — в работе, 2 — выполнен (если используешь другое — подправь)
        st = p.get("position_status", 0)
        status_text = "активен" if st == 0 else ("в работе" if st == 1 else "выполнен")

        btn_text = f"{name} • {budget}₽ • {status_text}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"myorders:view:{p['position_id']}:{p['position_unix']}",
                )
            ]
        )

    # навигация
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"myorders:list_page:{page-1}"
            )
        )
    if (page + 1) * per_page < total:
        nav.append(
            InlineKeyboardButton(
                text="Вперёд ➡️", callback_data=f"myorders:list_page:{page+1}"
            )
        )
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _show_my_orders_page(
    msg_or_call_message, page: int, state: FSM, per_page: int = 6
):
    data = await state.get_data()
    orders_map = json.loads(data.get("my_orders_map", "{}"))
    order_unix_ids = data.get("my_orders_list", [])
    total = len(order_unix_ids)

    start = page * per_page
    items_unix = order_unix_ids[start : start + per_page]
    if not items_unix:
        try:
            await msg_or_call_message.edit_text("Заказов на этой странице нет.")
        except Exception:
            await msg_or_call_message.answer("Заказов на этой странице нет.")
        return

    kb = _my_orders_inline_kb(items_unix, orders_map, page, per_page, total)

    # обновим или отправим
    try:
        await msg_or_call_message.edit_text("<b>📁 Ваши заказы:</b>", reply_markup=kb)
    except Exception:
        await msg_or_call_message.answer("<b>📁 Ваши заказы:</b>", reply_markup=kb)


from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
import json


@router.callback_query(StateFilter("my_orders_list"), F.data.startswith("myord:del:"))
async def my_order_delete(call: CallbackQuery, state: FSMContext):
    # data format: myord:del:{position_unix}
    punix_str = call.data.split(":")[-1]
    try:
        punix = int(punix_str)
    except Exception:
        await call.answer("Некорректный идентификатор заказа.", show_alert=True)
        return

    data = await state.get_data()
    my_list = data.get("my_orders_list") or []
    mp_json = data.get("my_orders_map") or "{}"
    try:
        mp = json.loads(mp_json)
    except Exception:
        mp = {}

    item = mp.get(str(punix))
    if not item:
        await call.answer("Заказ не найден в списке.", show_alert=True)
        return

    # Доп. проверка: что заказ принадлежит пользователю
    if int(item.get("position_id", 0) or 0) != call.from_user.id:
        await call.answer("Это не ваш заказ.", show_alert=True)
        return

    # ❗️ КЛЮЧЕВОЕ: удаляем ТОЛЬКО по position_unix
    try:
        # Вариант 1: если есть именно такой метод
        ok = Positionx.delete(position_unix=punix)
    except AttributeError:
        # Вариант 2: если у тебя метод называется remove()
        ok = Positionx.remove(position_unix=punix)
    except Exception as e:
        await call.answer(f"Ошибка удаления: {e}", show_alert=True)
        return

    # Обновляем state локально, чтобы не перечитывать БД заново
    if punix in my_list:
        my_list = [k for k in my_list if k != punix]
    if str(punix) in mp:
        mp.pop(str(punix), None)

    await state.update_data(
        my_orders_list=my_list,
        my_orders_map=json.dumps(mp, ensure_ascii=False),
    )

    # Если ничего не осталось — сообщаем и сбрасываем стейт
    if not my_list:
        await call.message.edit_text("<b>❌ У вас пока нет заказов.</b>")
        await state.clear()
        await call.answer()
        return

    # Иначе — перерисовываем текущую страницу корректно
    page = int(data.get("my_orders_page", 0) or 0)
    per_page = int(data.get("my_orders_per_page", 6) or 6)
    last_page = max((len(my_list) - 1) // per_page, 0)
    page = min(page, last_page)

    await _show_my_orders_page(call.message, page=page, state=state)
    await call.answer("Заказ удалён.")


# 👁 открыть заказ (карточка) — переиспользуем твой position_open_admin
# 👁 открыть заказ (карточка) — переиспользуем твой position_open_admin
@router.callback_query(F.data.startswith("myorders:view:"))
async def my_orders_view(call: CallbackQuery, bot: Bot, state: FSM):
    parts = call.data.split(":")
    # ожидаем формат: myorders:view:{position_id}:{position_unix}
    if len(parts) < 4:
        await call.answer("Некорректные данные кнопки.", show_alert=True)
        return

    _, _, pid_str, punix_str = parts[:4]
    try:
        position_id = int(pid_str)
        position_unix = int(punix_str)
    except ValueError:
        await call.answer("Некорректные параметры заказа.", show_alert=True)
        return

    await state.clear()  # чтобы не мешало редактирование
    try:
        await position_open_admin(bot, call.from_user.id, position_id, position_unix)
    except Exception as e:
        # если что-то пошло не так — не падаем, покажем сообщение
        await call.message.answer("Не удалось открыть заказ. Попробуйте позже.")
        # можно залогировать e
    await call.answer()


# Перемещение по страницам позиций для редактирования позиции
@router.callback_query(F.data.startswith("position_edit_swipe:"))
async def prod_position_edit_swipe(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    category_id = call.data.split(":")[1]
    remover = int(call.data.split(":")[2])

    await del_message(call.message)

    await call.message.answer(
        "<b>📁 Выберите заказ для изменения 🖍</b>",
        reply_markup=position_edit_swipe_fp(remover, category_id, call),
    )


# Выбор позиции для редактирования
@router.callback_query(F.data.startswith("client_position_edit_open:"))
async def prod_position_edit_open(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    parts = call.data.split(":")
    # ожидаем: client_position_edit_open:{position_unix}:{position_id}:{remover}
    if len(parts) < 4:
        await call.answer("Некорректные данные кнопки.", show_alert=True)
        return

    _, position_unix, position_id, remover_str = parts[:4]
    # remover не используется дальше – можно не парсить int, но если нужен:
    # remover = int(remover_str)

    await state.clear()
    await del_message(call.message)
    await position_open_admin(bot, call.from_user.id, position_id, position_unix)


from aiogram import F
from aiogram.types import CallbackQuery


@router.callback_query(F.data.startswith("position_edit_open:"))
async def prod_position_edit_open(call: CallbackQuery, state: FSMContext):
    # Поддерживаем оба варианта:
    # 1) position_edit_open:{position_id}:{category_id}:{remover}
    # 2) position_edit_open:{position_id}:{category_id}:{remover}:{position_unix}
    parts = call.data.split(":")
    if len(parts) < 4:
        await call.answer("Ошибка данных (формат callback).", show_alert=True)
        return

    try:
        _, pos_id_s, cat_id_s, remover_s, *tail = parts
        position_id = int(pos_id_s)
        category_id = int(cat_id_s)
        # remover бывает строкой — не насилуем в int без нужды
        remover = remover_s
        position_unix = int(tail[0]) if tail and tail[0].isdigit() else 0
    except Exception:
        await call.answer("Ошибка данных (парсинг).", show_alert=True)
        return

    # Если punix не пришёл (старые кнопки) — можно попробовать подтянуть его,
    # но это опционально. Безопасный вариант: оставляем 0.
    # pos = Positionx.get(position_id=position_id)  # ⚠️ Если это id клиента — может быть несколько заказов.
    # position_unix = getattr(pos, "position_unix", 0) if pos and not position_unix else position_unix

    # Рисуем меню редактирования (твоя функция уже ожидает punix)
    try:
        await call.message.edit_text(
            "<b>Изменение заказа</b>",
            reply_markup=position_edit_open_finl(
                position_id, category_id, remover, position_unix
            ),
        )
    except Exception:
        await call.message.answer(
            "<b>Изменение заказа</b>",
            reply_markup=position_edit_open_finl(
                position_id, category_id, remover, position_unix
            ),
        )
    await call.answer()


# Выбор позиции для редактирования
@router.callback_query(F.data.startswith("user_position_edit_open:"))
async def prod_position_edit_open(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    data = call.data.split(":")
    position_id = int(data[1])  # ID позиции
    position_unix = int(data[2])  # ID категории
    remover = int(data[4])  # Параметр пагинации

    # Очистка состояния
    await state.clear()

    # Удаление старого сообщения
    await del_message(call.message)

    # Открытие информации по позиции
    await position_open_not_admin_user(
        bot, call.from_user.id, position_id, position_unix
    )


############################ САМО ИЗМЕНЕНИЕ ПОЗИЦИИ ############################
# Изменение названия позиции
@router.callback_query(F.data.startswith("position_edit_name:"))
async def prod_position_edit_name(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    position_id = call.data.split(":")[1]
    category_id = call.data.split(":")[2]
    remover = int(call.data.split(":")[3])

    await state.update_data(here_position_id=position_id)
    await state.update_data(here_category_id=category_id)
    await state.update_data(here_remover=remover)
    await state.set_state("here_position_edit_name")

    await del_message(call.message)

    await call.message.answer(
        "<b>📁 Введите новое название для заказа</b>",
        reply_markup=position_edit_cancel_finl(position_id, category_id, remover),
    )


# Принятие названия позиции для её изменения
@router.message(F.text, StateFilter("here_position_edit_name"))
async def prod_position_edit_name_get(
    message: Message, bot: Bot, state: FSM, arSession: ARS
):
    state_data = await state.get_data()

    position_id = state_data["here_position_id"]
    category_id = state_data["here_category_id"]
    remover = state_data["here_remover"]

    if len(message.text) > 50:
        return await message.answer(
            "<b>❌ Название не может превышать 50 символов.</b>\n"
            "📁 Введите новое название для заказа",
            reply_markup=position_edit_cancel_finl(position_id, category_id, remover),
        )

    await state.clear()
    get_position = Positionx.get(position_id=position_id)
    position_unix = get_position.position_unix
    Positionx.update_unix(position_id, position_name=clear_html(message.text))
    await position_open_admin(bot, message.from_user.id, position_id, position_unix)


# Изменение цены позиции
@router.callback_query(F.data.startswith("position_edit_price:"))
async def prod_position_edit_price(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    position_id = call.data.split(":")[1]
    category_id = call.data.split(":")[2]
    remover = int(call.data.split(":")[3])

    await state.update_data(here_position_id=position_id)
    await state.update_data(here_category_id=category_id)
    await state.update_data(here_remover=remover)
    await state.set_state("here_position_edit_price")

    await del_message(call.message)

    await call.message.answer(
        "<b>📁 Введите новую цену для заказа</b>",
        reply_markup=position_edit_cancel_finl(position_id, category_id, remover),
    )


# Принятие цены позиции для её изменения
@router.message(F.text, StateFilter("here_position_edit_price"))
async def prod_position_edit_price_get(
    message: Message, bot: Bot, state: FSM, arSession: ARS
):
    state_data = await state.get_data()

    position_id = state_data["here_position_id"]
    category_id = state_data["here_category_id"]
    remover = state_data["here_remover"]

    if not is_number(message.text):
        await message.answer(
            "<b>❌ Данные были введены неверно. Введите число</b>\n"
            "📁 Введите цену для заказа",
            reply_markup=position_edit_cancel_finl(position_id, category_id, remover),
        )

    if to_number(message.text) > 10_000_000 or to_number(message.text) < 0:
        await message.answer(
            "<b>❌ Цена не может быть меньше 0₽ или больше 10 000 000₽.</b>\n"
            "📁 Введите цену для заказа",
            reply_markup=position_edit_cancel_finl(position_id, category_id, remover),
        )

    await state.clear()
    get_position = Positionx.get(position_id=position_id)
    position_unix = get_position.position_unix
    Positionx.update_unix(position_id, position_price=to_number(message.text))
    await position_open_admin(bot, message.from_user.id, position_id, position_unix)


# Изменение описания позиции
@router.callback_query(F.data.startswith("position_edit_desc:"))
async def prod_position_edit_desc(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    position_id = call.data.split(":")[1]
    category_id = call.data.split(":")[2]
    remover = int(call.data.split(":")[3])

    await state.update_data(here_position_id=position_id)
    await state.update_data(here_category_id=category_id)
    await state.update_data(here_remover=remover)
    await state.set_state("here_position_edit_desc")

    await del_message(call.message)

    await call.message.answer(
        "<b>📁 Введите новое описание для заказа</b>\n"
        "❕ Отправьте <code>0</code> чтобы пропустить.",
        reply_markup=position_edit_cancel_finl(position_id, category_id, remover),
    )


# Принятие описания позиции для её изменения
@router.message(F.text, StateFilter("here_position_edit_desc"))
async def prod_position_edit_desc_get(
    message: Message, bot: Bot, state: FSM, arSession: ARS
):
    state_data = await state.get_data()

    category_id = state_data["here_category_id"]
    position_id = state_data["here_position_id"]
    remover = state_data["here_remover"]

    if len(message.text) > 400:
        return await message.answer(
            "<b>❌ Описание не может превышать 400 символов.</b>\n"
            "📁 Введите новое описание для заказа\n"
            "❕ Отправьте <code>0</code> чтобы пропустить.",
            reply_markup=position_edit_cancel_finl(position_id, category_id, remover),
        )

    try:
        if message.text != "0":
            await (await message.answer(message.text)).delete()

            position_desc = message.text
        else:
            position_desc = "None"
    except:
        return await message.answer(
            "<b>❌ Ошибка синтаксиса HTML.</b>\n"
            "📁 Введите новое описание для заказа\n"
            "❕ Отправьте <code>0</code> чтобы пропустить.",
            reply_markup=position_edit_cancel_finl(position_id, category_id, remover),
        )

    await state.clear()
    get_position = Positionx.get(position_id=position_id)
    position_unix = get_position.position_unix
    Positionx.update_unix(position_id, position_desc=position_desc)
    await position_open_admin(bot, message.from_user.id, position_id, position_unix)


@router.message(F.text.in_(("➕ Создать заказ",)))
async def start_order(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("<b>🏙 Выберите город:</b>", reply_markup=cities_swipe(0))
    await state.set_state("order_city")


# пагинация городов
@router.callback_query(StateFilter("order_city"), F.data.startswith("order:city_page:"))
async def city_page(call: CallbackQuery):
    page = int(call.data.split(":")[2])
    await call.message.edit_reply_markup(reply_markup=cities_swipe(page))
    await call.answer()


# выбор города
@router.callback_query(StateFilter("order_city"), F.data.startswith("order:city:"))
async def city_choose(call: CallbackQuery, state: FSMContext):
    city = call.data.split(":")[2]
    await state.update_data(city=city)
    await call.message.edit_text(
        f"🏙 Город: <b>{city}</b>\n\n📍 Введите адрес объекта (улица, дом, кв/офис):",
        reply_markup=cancel_order_button(),
    )
    await state.set_state("order_address")
    await call.answer()


# ────────────────────────── Адрес ──────────────────────────


@router.message(StateFilter("order_address"))
async def get_address(message: Message, state: FSMContext):
    address = clear_html(message.text or "").strip()
    if not address or len(address) < 5:
        await message.answer(
            "❌ Слишком короткий адрес. Введите адрес подробнее:",
            reply_markup=cancel_order_button(),
        )
        return
    await state.update_data(address=address)

    # категории — мультивыбор
    await message.answer(
        "🧰 Выберите категории работ (можно несколько), затем нажмите «Готово».",
        reply_markup=categories_multiselect_kb(selected_ids=set(), page=0),
    )
    await state.set_state("order_categories")


# пагинация категорий
@router.callback_query(
    StateFilter("order_categories"), F.data.startswith("order:cat_page:")
)
async def cats_page(call: CallbackQuery, state: FSMContext):
    page = int(call.data.split(":")[2])
    data = await state.get_data()
    selected = set(data.get("cats", []))
    await call.message.edit_reply_markup(
        reply_markup=categories_multiselect_kb(selected, page)
    )
    await call.answer()


# переключение категории
@router.callback_query(
    StateFilter("order_categories"), F.data.startswith("order:cat_toggle:")
)
async def cats_toggle(call: CallbackQuery, state: FSMContext):
    _, _, cat_id_str, page_str = call.data.split(":")
    cat_id = int(cat_id_str)
    page = int(page_str)
    data = await state.get_data()
    selected = set(data.get("cats", []))
    if cat_id in selected:
        selected.remove(cat_id)
    else:
        selected.add(cat_id)
    await state.update_data(cats=list(selected))
    await call.message.edit_reply_markup(
        reply_markup=categories_multiselect_kb(selected, page)
    )
    await call.answer()


# завершили выбор категорий
@router.callback_query(StateFilter("order_categories"), F.data == "order:cat_done")
async def cats_done(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = list(data.get("cats", []))
    if not selected:
        await call.answer("Выберите хотя бы одну категорию.", show_alert=True)
        return
    await call.message.edit_text(
        "📝 Опишите задачу (что нужно сделать):", reply_markup=cancel_order_button()
    )
    await state.set_state("order_desc")
    await call.answer()


# ────────────────────────── Описание ──────────────────────────


@router.message(StateFilter("order_desc"))
async def get_desc(message: Message, state: FSMContext):
    desc = clear_html(message.text or "").strip()
    if not desc or len(desc) < 10:
        await message.answer(
            "❌ Слишком короткое описание. Добавьте деталей:",
            reply_markup=cancel_order_button(),
        )
        return
    await state.update_data(desc=desc)
    await message.answer(
        "💰 Укажите бюджет в рублях (число).\nИли нажмите «Пропустить» — будет «договорная».",
        reply_markup=skip_button("order:budget_skip"),
    )
    await state.set_state("order_budget")


# пропуск бюджета
@router.callback_query(StateFilter("order_budget"), F.data == "order:budget_skip")
async def budget_skip(call: CallbackQuery, state: FSMContext):
    await state.update_data(budget="договорная")
    await call.message.edit_text(
        "📅 Укажите сроки выполнения.\nФормат: <code>дд.мм.гггг — дд.мм.гггг</code>\nИли напишите: <code>пока не определился</code>",
        reply_markup=cancel_order_button(),
    )
    await state.set_state("order_dates")
    await call.answer()


# бюджет числом
@router.message(StateFilter("order_budget"))
async def get_budget(message: Message, state: FSMContext):
    txt = (message.text or "").replace(" ", "")
    if not txt.isdigit():
        await message.answer(
            "❌ Введите число (без пробелов), либо нажмите «Пропустить».",
            reply_markup=skip_button("order:budget_skip"),
        )
        return
    val = int(txt)
    if not (0 <= val <= 10_000_000):
        await message.answer(
            "❌ Бюджет должен быть от 0 до 10 000 000.",
            reply_markup=skip_button("order:budget_skip"),
        )
        return
    await state.update_data(budget=val)
    await message.answer(
        "📅 Укажите сроки выполнения.\nФормат: <code>дд.мм.гггг — дд.мм.гггг</code>\nИли напишите: <code>пока не определился</code>",
        reply_markup=cancel_order_button(),
    )
    await state.set_state("order_dates")


# ────────────────────────── Сроки ──────────────────────────


@router.message(StateFilter("order_dates"))
async def get_dates(message: Message, state: FSMContext):
    raw = (message.text or "").strip().lower()
    if raw in ("пока не определился", "не определился", "не знаю"):
        await state.update_data(dates="пока не определился")
    else:
        parts = [p.strip() for p in raw.replace("—", "-").split("-")]
        if len(parts) != 2:
            await message.answer(
                "❌ Формат неверный. Пример: 10.08.2025 - 20.08.2025\nИли напишите: пока не определился",
                reply_markup=cancel_order_button(),
            )
            return
        d1 = _parse_date(parts[0])
        d2 = _parse_date(parts[1])
        if not d1 or not d2 or d2 < d1:
            await message.answer(
                "❌ Даты неверные или окончание раньше начала.",
                reply_markup=cancel_order_button(),
            )
            return
        await state.update_data(
            dates=f"{d1.strftime('%d.%m.%Y')} – {d2.strftime('%d.%m.%Y')}"
        )

    await message.answer(
        "📸 Пришлите до 5 фото (по желанию), или нажмите «Пропустить».",
        reply_markup=skip_button("order:photos_skip"),
    )
    await state.set_state("order_photos")


# ────────────────────────── Фото (опционально) ──────────────────────────


# ---------- Клавиатура для шага с фото ----------
def photos_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="order:photos_done")],
            [
                InlineKeyboardButton(
                    text="⏭ Пропустить", callback_data="order:photos_skip"
                )
            ],
        ]
    )


# Если у тебя уже есть skip_button/cancel_order_button — можешь оставить их.
# Тут отдельная клавиатура именно для шага с фото.


# ---------- Вспомогательно: переход на следующий шаг ----------
async def proceed_to_next_step(state: FSMContext, message_or_cb):
    await state.set_state("order_comment")
    text = "✍️ Добавьте комментарий к заказу (по желанию) или напишите «нет»."
    if isinstance(message_or_cb, Message):
        await message_or_cb.answer(text)
    else:
        await message_or_cb.message.answer(text)


# ────────────────────────── Фото (до 5 шт) ──────────────────────────


@router.message(StateFilter("order_photos"), F.photo, flags={"rate": 0})
async def add_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = list(data.get("photos", []))

    # Берём самое большое превью (последний элемент)
    file_id = message.photo[-1].file_id

    if file_id in photos:
        await message.answer(
            f"⚠️ Это фото уже добавлено. Сейчас сохранено: {len(photos)}/5.",
            reply_markup=photos_kb(),
        )
        return

    if len(photos) >= 5:
        await message.answer(
            "⚠️ Лимит 5 фото уже достигнут. Нажмите «Готово» или «Пропустить».",
            reply_markup=photos_kb(),
        )
        return

    photos.append(file_id)
    await state.update_data(photos=photos)

    if len(photos) < 5:
        await message.answer(
            f"✅ Фото сохранено ({len(photos)}/5). "
            f"Можете отправить ещё или нажмите «Готово».",
            reply_markup=photos_kb(),
        )
    else:
        await message.answer(
            "✅ Добавлено 5/5 фото. Нажмите «Готово» для перехода дальше.",
            reply_markup=photos_kb(),
        )


@router.message(StateFilter("order_photos"))
async def non_photo_in_photos_step(message: Message, state: FSMContext):
    # Разрешаем текст «пропустить» в любом регистре
    txt = (message.text or "").strip().lower()
    if txt in {"пропустить", "skip"}:
        # Если фото уже есть — не теряем их, идём как «Готово»
        data = await state.get_data()
        if data.get("photos"):
            await message.answer("➡️ Переходим дальше с уже добавленными фото.")
            await proceed_to_next_step(state, message)
        else:
            await message.answer("➡️ Пропускаем фото и идём дальше.")
            await state.update_data(photos=[])
            await proceed_to_next_step(state, message)
        return

    await message.answer(
        "🖼 Пришлите фото (до 5 шт). "
        "После загрузки нажмите «Готово» или «Пропустить».",
        reply_markup=photos_kb(),
    )


@router.callback_query(
    StateFilter("order_photos"), F.data == "order:photos_done", flags={"rate": 0}
)
async def photos_done(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])

    if not photos:
        # Ничего не добавили, предложим либо прислать, либо пропустить
        await cq.message.answer(
            "Пока нет фото. Пришлите хотя бы одно или нажмите «Пропустить».",
            reply_markup=photos_kb(),
        )
        await cq.answer()
        return

    await cq.message.answer(f"✅ Фото сохранены ({len(photos)}/5). Переходим дальше.")
    await cq.answer()
    await proceed_to_next_step(state, cq)


@router.callback_query(
    StateFilter("order_photos"), F.data == "order:photos_skip", flags={"rate": 0}
)
async def photos_skip(cq: CallbackQuery, state: FSMContext):
    # ВАЖНО: если фото уже есть — не удаляем их, идём дальше как «Готово»
    data = await state.get_data()
    if data.get("photos"):
        await cq.message.answer("➡️ Переходим дальше с уже добавленными фото.")
    else:
        await state.update_data(photos=[])
        await cq.message.answer("➡️ Пропускаем фото и идём дальше.")
    await cq.answer()
    await proceed_to_next_step(state, cq)


# ────────────────────────── Комментарий → Подтверждение ──────────────────────────
@router.message(StateFilter("order_comment"))
async def get_comment(message: Message, state: FSMContext):
    raw = (message.text or "").strip()
    comment = (
        "" if raw.lower() in {"нет", "не", "без комментария", "-", "—"} else raw[:1000]
    )
    await state.update_data(comment=comment)

    # показать подтверждение
    await _show_confirmation(message, state)
    await state.set_state("order_confirm")


# ────────────────────────── Обработка «Подтвердить / Изменить» ──────────────────────────


@router.callback_query(StateFilter("order_confirm"), F.data == "order:edit")
async def edit_order(cq: CallbackQuery, state: FSMContext):
    # Верни пользователя на нужный шаг (например, к описанию или категориям)
    # Пример: вернуться в описание
    await state.set_state("order_desc")
    await cq.message.answer("✏️ Измените описание заказа и отправьте новое сообщение.")
    await cq.answer()


@router.callback_query(StateFilter("order_confirm"), F.data == "order:confirm_edit")
async def confirm_edit(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "Введите новое ОПИСАНИЕ задачи:", reply_markup=cancel_order_button()
    )
    await state.set_state("order_desc")
    await call.answer()


# ────────────────────────── Отмена из любого шага ──────────────────────────


@router.callback_query(F.data == "order:cancel")
async def order_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("<b>Создание заказа отменено.</b>")
    await call.message.answer(
        "Главное меню:", reply_markup=menu_second_start_clients(call.from_user.id)
    )
    await call.answer()


################################################################################
############################### СОЗДАНИЕ ЗАКАЗОВ #############################
# Принятие названия категории для её создания
@router.message(F.text, StateFilter("here_category_name"))
async def prod_category_add_name_get(
    message: Message, bot: Bot, state: FSM, arSession: ARS
):
    if len(message.text) > 50:
        return await message.answer(
            "<b>❌ Название не может превышать 50 символов.</b>\n"
            "🗃 Введите название для заказа",
        )

    await state.clear()

    category_id = get_unix()
    Categoryx.add(category_id, clear_html(message.text))

    await category_open_admin(bot, message.from_user.id, category_id, 0)


# Открытие категории админом
async def category_open_admin(
    bot: Bot, user_id: int, category_id: Union[str, int], remover: int
):
    get_category = Categoryx.get(category_id=category_id)
    get_positions = Positionx.gets(category_id=category_id)

    send_text = ded(
        f"""
        <b>🗃️ Редактирование категории</b>
        ➖➖➖➖➖➖➖➖➖➖➖➖➖➖
        ▪️ Заказ: <code>{get_category.category_name}</code>
        ▪️ Дата создания: <code>{convert_date(get_category.category_unix)}</code>
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
        reply_markup=category_edit_open_finl(category_id, remover),
    )


# Выбор позиции для редактирования
@router.message(F.text == "🖍 Изменить заказ")
async def prod_position_edit(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    get_categories = Categoryx.get_all()

    if len(get_categories) >= 1:
        await message.answer(
            "<b>🖍 Выберите заказ для изменения </b>",
            reply_markup=position_edit_category_swipe_fp(0),
        )
    else:
        await message.answer("<b>❌ Отсутствуют категории для изменения позиций</b>")


# Открытие профиля
@router.message(F.text == "👤 Профиль")
async def profile_entry(message: Message):
    await open_profile_user(message.bot, message.from_user.id)


# Открытие профиля
@router.message(F.text == "👤 Мой профиль")
async def user_profile(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await open_profile_client(bot, message.from_user.id)


@router.message(F.text.in_(("📍 Помощь")))
async def client_help(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await message.answer(
        "<b>☎️ Не нашли, что искали? Мы поможем! Здесь вы можете найти FAQ или связаться с поддержкой?</b>",
        reply_markup=menu_help_clients(message.from_user.id),
    )


@router.message(F.text.in_(("➕ Помощь")))
async def user_help(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await message.answer(
        "<b>☎️ Не нашли, что искали? Мы поможем! Здесь вы можете найти FAQ или связаться с поддержкой?</b>",
        reply_markup=menu_help_users(message.from_user.id),
    )


@router.message(F.text.in_(("🔙 Назад")))
async def user_help(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await message.answer(
        "<b>Мы в главном меню</b>",
        reply_markup=menu_second_start_clients(message.from_user.id),
    )


@router.message(F.text.in_(("◀️ Назад")))
async def user_help(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await message.answer(
        "<b>Мы в главном меню</b>",
        reply_markup=menu_second_start(message.from_user.id),
    )


@router.message(F.text.in_(("📖 Правовая информация")))
async def user_help(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await message.answer(
        "<b>Что вас интересует?</b>",
        reply_markup=client_functions_codexk(message.from_user.id),
    )


@router.message(F.text.in_(("📗 Правовая информация")))
async def user_help(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await message.answer(
        "<b>Что вас интересует?</b>",
        reply_markup=user_functions_codexk(message.from_user.id),
    )


# Открытие FAQ
@router.message(F.text.in_(("❓ FAQ", "/faq")))
async def user_faq(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    get_settings = Settingsx.get()
    send_message = get_settings.misc_faq

    if send_message == "None":
        send_message = ded(
            f"""
            ❔ Информация. Измените её в настройках бота.
            ➖➖➖➖➖➖➖➖➖➖
            {get_desc()}
        """
        )

    await message.answer(
        insert_tags(message.from_user.id, send_message),
        disable_web_page_preview=True,
    )


# Открытие сообщения с ссылкой на поддержку
@router.message(F.text.in_(("🛎 Поддержка", "/support")))
async def user_support(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    get_settings = Settingsx.get()

    if get_settings.misc_support == "None":
        return await message.answer(
            ded(
                f"""
                🛎 Поддержка. Измените её в настройках бота.
                ➖➖➖➖➖➖➖➖➖➖
                {get_desc()}
            """
            ),
            disable_web_page_preview=True,
        )

    await message.answer(
        "<b>☎️ Нажмите кнопку ниже для связи с Администратором.</b>",
        reply_markup=user_support_finl(get_settings.misc_support),
    )


# Получение версии бота
@router.message(Command(commands=["version"]))
async def admin_version(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(f"<b>❇️ Текущая версия бота: <code>{BOT_VERSION}</code></b>")


# Получение информации о боте
@router.message(Command(commands=["dj_desc"]))
async def admin_desc(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer(get_desc(), disable_web_page_preview=True)


################################################################################
# Возвращение к профилю
@router.callback_query(F.data == "user_profile")
async def user_profile_return(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    await state.clear()

    await del_message(call.message)
    await open_profile_user(bot, call.from_user.id)


# Просмотр истории покупок
@router.callback_query(F.data == "user_purchases")
async def user_purchases(call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS):
    get_purchases = Purchasesx.gets(user_id=call.from_user.id)
    get_purchases = get_purchases[-5:]

    if len(get_purchases) >= 1:
        await call.answer("✅ Последние 5 заказов")
        await del_message(call.message)

        for purchase in get_purchases:
            link_items = await upload_text(arSession, purchase.purchase_data)

            await call.message.answer(
                ded(
                    f"""
                    <b>🧾 Чек: <code>#{purchase.purchase_receipt}</code></b>
                    ▪️ Заказ: <code>{purchase.purchase_position_name} | {purchase.purchase_price}₽</code>
                    ▪️ Дата выполнения: <code>{convert_date(purchase.purchase_unix)}</code>
                    ▪️ Заказ: <a href='{link_items}'>кликабельно</a>
                """
                )
            )

            await asyncio.sleep(0.2)

        await open_profile_user(bot, call.from_user.id)
    else:
        await call.answer("❗ У вас отсутствуют выполненные заказы", True)


# Страницы наличия заказов
@router.callback_query(F.data.startswith("user_available_swipe:"))
async def user_available_swipe(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    remover = int(call.data.split(":")[1])

    items_available = get_items_available()

    if remover >= len(items_available):
        remover = len(items_available) - 1
    if remover < 0:
        remover = 0

    await call.message.edit_text(
        items_available[remover],
        reply_markup=prod_available_swipe_fp(remover, len(items_available)),
    )
