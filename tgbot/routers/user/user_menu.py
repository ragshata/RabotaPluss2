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
                    text="✅ Подтвердить", callback_data="order:confirm_ok"
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


# ────────────────────────── Старт сценария ──────────────────────────


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


# ────────────────────────── Клавиатура подтверждения ──────────────────────────
def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data="order:confirm"
                )
            ],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data="order:edit")],
        ]
    )


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


@router.callback_query(StateFilter("order_confirm"), F.data == "order:confirm")
async def confirm_ok(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    city = data["city"]
    address = data["address"]
    desc = data["desc"]
    budget = data.get("budget", "договорная")
    dates = data.get("dates", "пока не определился")
    photos = data.get("photos", [])
    cats_ids = data.get("cats", [])

    main_cat_id = cats_ids[0] if cats_ids else 0
    position_name = (desc[:50] + "…") if len(desc) > 53 else desc

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
    price_val = budget if isinstance(budget, int) else 0

    Positionx.add(
        main_cat_id,  # category_id
        call.from_user.id,  # position_id → автоинкремент
        position_name,
        price_val,
        position_desc,
        0,  # time legacy
        0,  # worker_id (используем для владельца)
        0,  # st atus
    )

    await state.clear()

    cats_map = {c.category_id: c.category_name for c in Categoryx.get_all()}
    cats_titles = [cats_map.get(cid, str(cid)) for cid in cats_ids]
    cats_text = ", ".join(cats_titles) if cats_titles else "—"
    budget_text = f"{budget} руб." if isinstance(budget, int) else str(budget)

    await call.message.answer(
        ded(
            f"""
        ✅ <b>Ваш заказ создан!</b>
        Категория: [{cats_text}]
        Описание: [{desc}]
        Адрес: [{address}]
        Бюджет: [{budget_text}]
        Сроки: [{dates}]
    """
        )
    )
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


@router.callback_query(StateFilter("myresp_list"), F.data.startswith("myresp:view:"))
async def myresp_view(call: CallbackQuery, state: FSMContext):
    punix = int(call.data.split(":")[2])
    data = await state.get_data()
    dataset = data.get("myresp_data") or {}
    rec = (dataset.get("map") or {}).get(str(punix))

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

    budget = rec.get("position_price", 0)
    budget_text = f"{budget} руб." if budget else (ext.get("budget") or "договорная")
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

    wid = call.from_user.id
    assigned = rec.get("worker_id", 0) or 0
    pid = rec.get("position_id", 0) or 0

    buttons = []
    if assigned == wid:
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

router = Router()

# =============== Клавиатуры ===============


def _orders_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Все заказы", callback_data="orders:mode_all"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗂 По категориям", callback_data="orders:mode_cats"
                )
            ],
        ]
    )


def _orders_all_kb(
    keys, order_map, page: int, per_page: int, total: int
) -> InlineKeyboardMarkup:
    rows = []

    # Кнопки заказов (по одной в строке)
    for k in keys:
        d = order_map[str(k)]
        name = d.get("position_name") or d.get("name") or "Без названия"
        name = html.unescape(str(name))
        name = shorten(name, width=36, placeholder="…")
        price = d.get("position_price", 0)
        price_txt = (
            f"{price:,}".replace(",", " ") + " ₽"
            if isinstance(price, int) and price > 0
            else "договорная"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{name} · {price_txt}", callback_data=f"orders:open:{k}"
                )
            ]
        )

    # Пагинация
    last_page = max((total - 1) // per_page, 0)
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="« Назад", callback_data=f"orders:all:p:{page-1}")
        )
    nav.append(
        InlineKeyboardButton(
            text=f"{page+1}/{last_page+1}", callback_data="orders:noop"
        )
    )
    if page < last_page:
        nav.append(
            InlineKeyboardButton(
                text="Вперёд »", callback_data=f"orders:all:p:{page+1}"
            )
        )
    if nav:
        rows.append(nav)

    # Кнопка «← Режимы»
    rows.append(
        [
            InlineKeyboardButton(
                text="← Режимы просмотра", callback_data="orders:back_modes"
            )
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


async def _ensure_orders_all_dataset(state: FSMContext):
    data = await state.get_data()
    orders_map = data.get("orders_all_map")
    orders_list = data.get("orders_all_list")
    if orders_map is not None and orders_list is not None:
        return orders_list, orders_map

    mp = {}
    keys = []
    for pos in _iter_all_positions():
        d = _pos_to_public_dict(pos)

        # ✳️ Показываем только свободные заказы
        if _to_int(d.get("worker_id", 0)) != 0:
            continue

        # Активные (если у тебя другой финальный статус — поправь _pos_is_active)
        if not _pos_is_active(d):
            continue

        k = _order_key(d)
        if k == 0 or str(k) in mp:
            continue
        mp[str(k)] = d
        keys.append(k)

    def sort_val(k: int) -> int:
        dd = mp[str(k)]
        pu = _to_int(dd.get("position_unix", 0))
        return pu if pu > 0 else _to_int(dd.get("position_id", 0))

    keys.sort(key=sort_val, reverse=True)
    await state.update_data(orders_all_list=keys, orders_all_map=mp)
    return keys, mp


async def _show_orders_all_page(
    msg_or_cb, page: int, state: FSMContext, per_page: int = 6
):
    keys, mp = await _ensure_orders_all_dataset(state)
    total = len(keys)
    last_page = max((total - 1) // per_page, 0)
    page = max(0, min(page, last_page))
    slice_keys = keys[page * per_page : page * per_page + per_page]

    kb = _orders_all_kb(slice_keys, mp, page, per_page, total)
    text = "<b>🧾 Актуальные заказы (все)</b>\nВыберите заказ:"

    # выводим — если это коллбэк, пробуем edit_text
    try:
        if isinstance(msg_or_cb, CallbackQuery):
            await msg_or_cb.message.edit_text(text, reply_markup=kb)
            await msg_or_cb.answer()
        else:
            await msg_or_cb.answer(text, reply_markup=kb)
    except Exception:
        # на всякий случай fallback
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


@router.callback_query(F.data.startswith("orders:all:p:"))
async def orders_all_pagination(cq: CallbackQuery, state: FSMContext):
    try:
        page = int(cq.data.split(":")[-1])
    except Exception:
        page = 0
    await _show_orders_all_page(cq, page=page, state=state)


@router.callback_query(F.data.startswith("orders:open:"))
async def orders_open(cq: CallbackQuery, state: FSMContext):
    # Детальный просмотр выбранного заказа
    key = cq.data.split(":")[-1]
    data = await state.get_data()
    mp = data.get("orders_all_map") or {}
    item = mp.get(key)
    if not item:
        await cq.answer("Заказ не найден", show_alert=True)
        return

    # Красивый вывод деталей
    name = html.escape(str(item.get("position_name", "—")))
    price = item.get("position_price", 0)
    price_txt = (
        f"{price:,}".replace(",", " ") + " ₽"
        if isinstance(price, int) and price > 0
        else "договорная"
    )
    cat_id = item.get("category_id", 0)
    status = item.get("position_status", 0)

    text = (
        f"<b>📦 Заказ</b>\n\n"
        f"🧰 Категория: <code>{cat_id}</code>\n"
        f"💬 Название: <code>{name}</code>\n"
        f"💰 Бюджет: <code>{price_txt}</code>\n"
        f"📌 Статус: <code>{status}</code>\n"
        f"\nВыберите действие:"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← К списку", callback_data="orders:all:back")],
            # тут можешь добавить «Откликнуться»/«Подробно», если у тебя есть обработчики
        ]
    )

    try:
        await cq.message.edit_text(text, reply_markup=kb)
    except Exception:
        await cq.message.answer(text, reply_markup=kb)
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


@router.callback_query(F.data.startswith("orders:view:"))
async def orders_view(call: CallbackQuery, state: FSMContext):
    _, _, pid_str, punix_str = call.data.split(":")
    pid, punix = int(pid_str), int(punix_str)

    data = await state.get_data()
    rec = _find_by_pid_punix(data, pid, punix)
    if not rec:
        await call.answer("Заказ не найден. Обновите список.", show_alert=True)
        return

    ext = _pos_ext(rec.get("position_desc", ""))
    cats = Categoryx.get_all()
    cat_map = {c.category_id: c.category_name for c in cats}
    cat_ids = ext.get("categories") or (
        [rec.get("category_id")] if rec.get("category_id") is not None else []
    )
    cats_text = (
        ", ".join([cat_map.get(cid, str(cid)) for cid in cat_ids]) if cat_ids else "—"
    )

    budget = rec.get("position_price", 0)
    budget_text = f"{budget} руб." if budget else (ext.get("budget") or "договорная")
    city = ext.get("city", "—")
    address = ext.get("address", "—")
    dates = ext.get("dates", "—")
    desc = ext.get("raw_desc", "")

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

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Согласиться", callback_data=f"orders:respond:{pid}:{punix}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к списку", callback_data="orders:back_to_list"
                )
            ],
        ]
    )

    await call.message.edit_text(txt, reply_markup=kb)
    await state.set_state("orders_viewing")
    await call.answer()


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

    order_map = dataset["map"]
    current_list = dataset.get("current", []) or []
    done_list = dataset.get("done", []) or []

    total_cur, total_done = len(current_list), len(done_list)
    source = current_list if tab == "current" else done_list
    total = len(source)

    # Нормализация пагинации
    if per_page <= 0:
        per_page = 6
    last_page = max((total - 1) // per_page, 0)
    page = max(0, min(page, last_page))

    start = page * per_page
    items = source[start : start + per_page]

    # Клава: передаём tot_cur и tot_done
    kb = _list_kb(
        tab, items, order_map, page, per_page, total, worker_id, total_cur, total_done
    )
    # Первая строка клавиатуры — вкладки; обновим их счетчиками корректно
    kb.inline_keyboard[0] = _tabs_kb(total_cur, total_done, tab)[0]

    text = "<b>📋 Мои отклики</b>\nВыберите заказ:"
    try:
        await msg.edit_text(text, reply_markup=kb)
    except Exception:
        await msg.answer(text, reply_markup=kb)

    # Запомним активную вкладку/страницу — чтобы «Назад к списку» работал
    await state.update_data(myresp_tab=tab, myresp_page=page, myresp_per_page=per_page)


# ───────── entrypoint ─────────


@router.message(F.text == "📋 Мои отклики")
async def my_responses_root(message: Message, state: FSMContext):
    await state.clear()
    await _show_myresp_tab(
        message, tab="current", page=0, state=state, worker_id=message.from_user.id
    )
    await state.set_state("myresp_list")


# Переключение вкладок
@router.callback_query(StateFilter("myresp_list"), F.data.startswith("myresp:tab:"))
async def myresp_tab(call: CallbackQuery, state: FSMContext):
    tab = call.data.split(":")[2]
    await _show_myresp_tab(
        call.message, tab=tab, page=0, state=state, worker_id=call.from_user.id
    )
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


# Просмотр карточки отклика / заказа
@router.callback_query(StateFilter("myresp_list"), F.data.startswith("myresp:view:"))
async def myresp_view(call: CallbackQuery, state: FSMContext):
    punix = int(call.data.split(":")[2])
    data = await state.get_data()
    dataset = data.get("myresp_data") or {}
    mp = dataset.get("map", {})
    rec = mp.get(str(punix))

    # Если в карте нет — попробуем подтянуть напрямую
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

    budget = rec.get("position_price", 0)
    budget_text = f"{budget} руб." if budget else (ext.get("budget") or "договорная")
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

    # Кнопки
    worker_id = call.from_user.id
    assigned_id = rec.get("worker_id", 0) or 0
    pid = rec.get("position_id", 0) or 0

    buttons: List[List[InlineKeyboardButton]] = []
    # Если назначен именно этот worker — дать кнопку связи с заказчиком
    if assigned_id == worker_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📞 Связаться с заказчиком", url=f"tg://user?id={pid}"
                )
            ]
        )
    else:
        # иначе — просто напомнить, что ожидает подтверждения
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⏳ Ожидает подтверждения", callback_data="noop"
                )
            ]
        )

    # Назад к списку (в текущую вкладку и страницу)
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
    # ДОБАВЛЯЕМ отдельной строкой кнопку «Все категории»
    # await message.answer(
    #    "Или посмотреть сразу все ваши заказы:",
    #    reply_markup=client_myorders_all_button_kb(user_id),
    # )


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


# ◀️▶️ пагинация списка
@router.callback_query(
    StateFilter("my_orders_list"), F.data.startswith("myorders:list_page:")
)
async def my_orders_page(call: CallbackQuery, state: FSM):
    page = int(call.data.split(":")[2])
    await _show_my_orders_page(call.message, page=page, state=state)
    await call.answer()


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


# Выбор позиции для редактирования
@router.callback_query(F.data.startswith("position_edit_open:"))
async def prod_position_edit_open(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    position_id = call.data.split(":")[2]
    category_id = call.data.split(":")[3]
    remover = int(call.data.split(":")[4])
    position_unix = call.data.split(":")[1]

    await state.clear()

    await del_message(call.message)
    await position_open_admin(bot, call.from_user.id, position_id, position_unix)


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
    Positionx.update(position_id, position_name=clear_html(message.text))
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
    Positionx.update(position_id, position_price=to_number(message.text))
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
    Positionx.update(position_id, position_desc=position_desc)
    await position_open_admin(bot, message.from_user.id, position_id, position_unix)


@router.message(F.text == "📝 Управление заказами")
async def admin_products(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()
    await message.answer(
        "<b>🧑🏻‍💻 Создание и изменение заказов</b>",
        reply_markup=items_frep_client(),
    )


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
