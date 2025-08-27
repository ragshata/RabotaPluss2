# - *- coding: utf- 8 - *-
from __future__ import annotations

from typing import Union

from aiogram import Bot

import json

from aiogram import Router, F, types, Bot
from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from tgbot.database.db_users import Userx, UserModel
from tgbot.database.db_purchases import Purchasesx  # если есть, иначе убери
from tgbot.keyboards.inline_user import user_profile_finl
from tgbot.keyboards.inline_register import cities_kb, specs_kb, SPECS
from tgbot.utils.const_functions import get_unix, ded


router = Router()
from tgbot.database.db_category import Categoryx
from tgbot.database.db_item import Itemx
from tgbot.database.db_position import Positionx
from tgbot.database.db_purchases import Purchasesx, PurchasesModel
from tgbot.database.db_purchases_clients import Purchasesclientx
from tgbot.database.db_refill import Refillx, RefillModel
from tgbot.database.db_settings import Settingsx
from tgbot.database.db_users import ClientModel, Clientx, Userx, UserModel
from tgbot.keyboards.inline_admin import profile_search_finl, profile_search_finl_client
from tgbot.keyboards.inline_admin_prod import (
    position_edit_open_finl,
    category_edit_open_finl,
    item_delete_finl,
    user_position_edit_open_finl,
)
from tgbot.keyboards.inline_user import (
    client_profile_finl,
    products_open_finl,
    user_profile_finl,
)
from tgbot.utils.const_functions import ded, get_unix, convert_day, convert_date
from tgbot.utils.misc.bot_models import ARS


################################################################################
################################# ПОЛЬЗОВАТЕЛЬ #################################
# tgbot/routers/profile.py


def _pos_ext(desc: str) -> dict:
    if not desc:
        return {}
    try:
        s = desc
        if s.startswith("[ORDER]"):
            s = s.split("\n", 1)[1] if "\n" in s else ""
        return json.loads(s or "{}")
    except Exception:
        return {}


# ─────────────────── helpers ───────────────────


def _photos_to_list(photos_raw: str | list[str]) -> list[str]:
    if isinstance(photos_raw, list):
        return photos_raw
    try:
        data = json.loads(photos_raw or "[]")
        if isinstance(data, list):
            return [str(x) for x in data]
    except Exception:
        pass
    return []


def _list_to_json(lst: list[str]) -> str:
    return json.dumps(lst, ensure_ascii=False)


def _get_selected_slugs_from_titles(titles: list[str]) -> list[str]:
    title_to_slug = {title: slug for slug, title in SPECS}
    return [title_to_slug.get(t, t) for t in titles]


def _titles_from_slugs(slugs: list[str]) -> list[str]:
    slug_to_title = {slug: title for slug, title in SPECS}
    return [slug_to_title.get(s, s) for s in slugs]


# ─────────────────── states ───────────────────


class ProfileStates(StatesGroup):
    edit_name = State()
    edit_surname = State()
    edit_phone = State()
    edit_experience = State()
    edit_city = State()
    edit_specs = State()
    add_photos = State()


# ─────────────────── open profile ───────────────────


async def open_profile_user(bot: Bot, user_id: Union[int, str]):
    get_purchases = Purchasesx.gets(user_id=user_id)  # если не нужно — можно убрать
    get_user: UserModel = Userx.get(user_id=user_id)

    how_days = int(get_unix() - get_user.user_unix) // 60 // 60 // 24
    user_rating = (
        round(get_user.user_rating_avg, 2) if get_user.user_rating_avg else "Нет оценок"
    )

    # новые поля
    exp = get_user.experience_years or 0
    city = get_user.city or "—"
    specs_titles = (get_user.specializations or "").strip()
    specs_titles = specs_titles if specs_titles else "—"

    photos = _photos_to_list(get_user.work_photos)
    photos_count = len(photos)

    send_text = ded(
        f"""
        <b>👤 Ваш профиль:</b>
        ➖➖➖➖➖➖➖➖➖➖
        🆔 <code>{get_user.user_rlname}</code> <code>{get_user.user_surname}</code>
        📞 Телефон: <code>{get_user.user_number}</code>
        🏙 Город: <code>{city}</code>
        🔧 Опыт: <code>{exp} лет</code>
        🧰 Специализации: <code>{specs_titles}</code>
        🖼 Фото работ: <code>{photos_count}</code>
        💰 Баланс: <code>{get_user.user_balance}₽</code>
        ⭐ Средняя оценка: <code>{user_rating}</code>

        🕰 Регистрация: <code>{convert_date(get_user.user_unix, False, False)} ({convert_day(how_days)})</code>
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
        reply_markup=user_profile_finl(),
    )


# ─────────────────── edit menu ───────────────────


@router.callback_query(F.data == "profile:edit")
async def profile_edit_menu(call: CallbackQuery):
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Имя", callback_data="profile:edit_name")],
            [
                types.InlineKeyboardButton(
                    text="Фамилия", callback_data="profile:edit_surname"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Телефон", callback_data="profile:edit_phone"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Опыт (лет)", callback_data="profile:edit_experience"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Город", callback_data="profile:edit_city"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Специализации", callback_data="profile:edit_specs"
                )
            ],
        ]
    )
    await call.message.answer("Что редактируем?", reply_markup=kb)
    await call.answer()


# Имя
@router.callback_query(F.data == "profile:edit_name")
async def ask_name(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новое имя:")
    await state.set_state(ProfileStates.edit_name)
    await call.answer()


@router.message(ProfileStates.edit_name)
async def save_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    Userx.update(message.from_user.id, user_rlname=name)
    await state.clear()
    await message.answer("Имя обновлено ✅")
    await open_profile_user(message.bot, message.from_user.id)


# Фамилия
@router.callback_query(F.data == "profile:edit_surname")
async def ask_surname(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новую фамилию:")
    await state.set_state(ProfileStates.edit_surname)
    await call.answer()


@router.message(ProfileStates.edit_surname)
async def save_surname(message: types.Message, state: FSMContext):
    surname = message.text.strip()
    Userx.update(message.from_user.id, user_surname=surname)
    await state.clear()
    await message.answer("Фамилия обновлена ✅")
    await open_profile_user(message.bot, message.from_user.id)


# Телефон
@router.callback_query(F.data == "profile:edit_phone")
async def ask_phone(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите телефон в формате +79991234567:")
    await state.set_state(ProfileStates.edit_phone)
    await call.answer()


@router.message(ProfileStates.edit_phone)
async def save_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not phone.startswith("+") or not phone[1:].isdigit() or len(phone) < 10:
        await message.answer("❌ Некорректно. Пример: +79991234567")
        return
    Userx.update(message.from_user.id, user_number=phone)
    await state.clear()
    await message.answer("Телефон обновлён ✅")
    await open_profile_user(message.bot, message.from_user.id)


# Опыт
@router.callback_query(F.data == "profile:edit_experience")
async def ask_experience(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Сколько лет опыта? Введите число от 0 до 60:")
    await state.set_state(ProfileStates.edit_experience)
    await call.answer()


@router.message(ProfileStates.edit_experience)
async def save_experience(message: types.Message, state: FSMContext):
    txt = message.text.strip()
    if not txt.isdigit():
        await message.answer("❌ Введите число лет (0..60).")
        return
    years = int(txt)
    if years < 0 or years > 60:
        await message.answer("❌ Диапазон 0..60.")
        return
    Userx.update(message.from_user.id, experience_years=years)
    await state.clear()
    await message.answer("Опыт обновлён ✅")
    await open_profile_user(message.bot, message.from_user.id)


# Город
@router.callback_query(F.data == "profile:edit_city")
async def choose_city(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "Выберите город:", reply_markup=cities_kb(prefix="edit_city")
    )
    await state.set_state(ProfileStates.edit_city)
    await call.answer()


@router.callback_query(ProfileStates.edit_city, F.data.startswith("edit_city:"))
async def save_city(call: CallbackQuery, state: FSMContext):
    _, city = call.data.split(":", 1)
    Userx.update(call.from_user.id, city=city)
    await state.clear()
    await call.message.edit_text(f"Город обновлён ✅: {city}")
    await open_profile_user(call.message.bot, call.from_user.id)
    await call.answer()


# Специализации (мультивыбор)
@router.callback_query(F.data == "profile:edit_specs")
async def edit_specs(call: CallbackQuery, state: FSMContext):
    user = Userx.get(user_id=call.from_user.id)
    current_titles = [
        t.strip() for t in (user.specializations or "").split(",") if t.strip()
    ]
    current_slugs = _get_selected_slugs_from_titles(current_titles)
    await state.update_data(edit_specs_selected=current_slugs)
    await call.message.answer(
        "Выберите специализации и нажмите «Готово».",
        reply_markup=specs_kb(
            current_slugs, prefix="edit_spec", done_id="edit_spec_done"
        ),
    )
    await state.set_state(ProfileStates.edit_specs)
    await call.answer()


@router.callback_query(ProfileStates.edit_specs, F.data.startswith("edit_spec:"))
async def toggle_edit_spec(call: CallbackQuery, state: FSMContext):
    _, slug = call.data.split(":", 1)
    data = await state.get_data()
    selected = list(data.get("edit_specs_selected", []))
    if slug in selected:
        selected.remove(slug)
    else:
        selected.append(slug)
    await state.update_data(edit_specs_selected=selected)
    await call.message.edit_reply_markup(
        reply_markup=specs_kb(selected, prefix="edit_spec", done_id="edit_spec_done")
    )
    await call.answer()


@router.callback_query(ProfileStates.edit_specs, F.data == "edit_spec_done")
async def save_edit_specs(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    slugs = list(data.get("edit_specs_selected", []))
    if not slugs:
        await call.answer("Выберите хотя бы одну специализацию.", show_alert=True)
        return
    titles = _titles_from_slugs(slugs)
    titles_str = ",".join(titles)
    Userx.update(call.from_user.id, specializations=titles_str)
    await state.clear()
    await call.message.edit_text(f"Специализации обновлены ✅: {titles_str}")
    await open_profile_user(call.message.bot, call.from_user.id)
    await call.answer()


# ─────────────────── photos / portfolio ───────────────────


@router.callback_query(F.data == "profile:add_photos")
async def add_photos(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "Отправьте 1–5 фото ваших работ. Можно несколькими сообщениями."
    )
    await state.set_state(ProfileStates.add_photos)
    await call.answer()


@router.message(ProfileStates.add_photos, F.photo)
async def receive_portfolio_photo(message: types.Message, state: FSMContext):
    user = Userx.get(user_id=message.from_user.id)
    photos = _photos_to_list(user.work_photos)
    if len(photos) >= 50:
        await message.answer("Достигнут лимит 50 фото.")
        return
    file_id = message.photo[-1].file_id
    photos.append(file_id)
    Userx.update(message.from_user.id, work_photos=_list_to_json(photos))
    await message.answer(f"Фото добавлено ✅ (всего: {len(photos)}).")
    # остаёмся в состоянии, чтобы принять ещё фото


@router.callback_query(F.data == "profile:clear_photos")
async def clear_photos(call: CallbackQuery):
    Userx.update(call.from_user.id, work_photos="[]")
    await call.message.answer("Все фото портфолио удалены 🗑")
    await open_profile_user(call.message.bot, call.from_user.id)
    await call.answer()


@router.callback_query(F.data.startswith("profile:view_photos:"))
async def view_photos(call: CallbackQuery):
    _, _, page_str = call.data.split(":")
    page = int(page_str)
    user = Userx.get(user_id=call.from_user.id)
    photos = _photos_to_list(user.work_photos)
    if not photos:
        await call.message.answer("Портфолио пусто.")
        await call.answer()
        return

    per_page = 10
    start = page * per_page
    chunk = photos[start : start + per_page]
    media = [InputMediaPhoto(media=fid) for fid in chunk]

    # Навигация
    nav = []
    if page > 0:
        nav.append(
            types.InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"profile:view_photos:{page-1}"
            )
        )
    if start + per_page < len(photos):
        nav.append(
            types.InlineKeyboardButton(
                text="Вперёд ➡️", callback_data=f"profile:view_photos:{page+1}"
            )
        )
    kb = types.InlineKeyboardMarkup(inline_keyboard=[nav] if nav else [])

    # отправка альбома (макс 10)
    try:
        await call.message.answer_media_group(media=media)
        if nav:
            await call.message.answer(
                f"Стр. {page+1}/{(len(photos)-1)//per_page+1}", reply_markup=kb
            )
    except Exception:
        # если альбом не отправился (редкий случай) — отправим по одному
        for m in media:
            await call.message.answer_photo(m.media)
        if nav:
            await call.message.answer(
                f"Стр. {page+1}/{(len(photos)-1)//per_page+1}", reply_markup=kb
            )

    await call.answer()


from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder as IKB
from tgbot.database.db_users import Clientx
from tgbot.database.db_settings import Settingsx
from tgbot.keyboards.inline_user import user_support_finl
from tgbot.utils.const_functions import ikb, ded, get_unix, convert_date


def _client_sub_kb(active: bool) -> InlineKeyboardMarkup:
    kb = IKB()
    if active:
        kb.row(ikb("ℹ️ Что включено", data="sub:info"))
    else:
        kb.row(ikb("💳 Оплатить (написать администратору)", data="sub:pay"))
        kb.row(ikb("ℹ️ Что включено", data="sub:info"))
    kb.row(ikb("← В профиль", data="client:profile:back"))
    return kb.as_markup()


@router.callback_query(F.data == "client:subscription")
async def client_subscription(call: CallbackQuery):
    c = Clientx.get(client_id=call.from_user.id)
    if not c:
        await call.answer("Профиль не найден.", show_alert=True)
        return

    now = get_unix()
    paid_until = int(getattr(c, "sub_paid_until", 0) or 0)
    is_trial = bool(int(getattr(c, "sub_is_trial", 0) or 0))
    active = paid_until > now

    if active:
        txt = ded(
            f"""
            <b>Подписка активна</b>
            Действует до: <code>{convert_date(paid_until, False, False)}</code>
            Режим: <code>{'бесплатный месяц' if is_trial else 'платная'}</code>
        """
        )
    else:
        txt = ded(
            """
            <b>Подписка неактивна</b>
            Первый месяц — <b>бесплатно</b>.
            Далее — <b>100 ₽ в неделю</b>.
        """
        )

    await call.message.edit_text(txt, reply_markup=_client_sub_kb(active))
    await call.answer()


@router.callback_query(F.data == "client:profile:back")
async def client_profile_back(call: CallbackQuery):
    await call.answer()
    await open_profile_client(call.bot, call.from_user.id)


@router.callback_query(F.data == "sub:info")
async def sub_info(call: CallbackQuery):
    await call.answer()
    await call.message.answer(
        "Подписка открывает возможность создавать заказы.\n"
        "Первый месяц — бесплатно, затем 100 ₽ в неделю.\n"
        "Оплата производится через администратора."
    )


@router.callback_query(F.data == "sub:pay")
async def sub_pay(call: CallbackQuery):
    await call.answer()
    settings = Settingsx.get()
    await call.message.answer(
        "<b>☎️ Нажмите кнопку ниже для связи с Администратором для оплаты.</b>",
        reply_markup=user_support_finl(settings.misc_support),
    )


from tgbot.utils.const_functions import ikb  # если ещё не импортирован


# Открытие профиля клиентом
async def open_profile_client(bot: Bot, user_id: Union[int, str]):
    get_purchases = Purchasesclientx.gets(client_id=user_id)
    get_client = Clientx.get(client_id=user_id)

    how_days = int(get_unix() - get_client.client_unix) // 60 // 60 // 24
    send_text = ded(
        f"""
        <b>👤 Ваш профиль:</b>
        ➖➖➖➖➖➖➖➖➖➖
        🆔 <code>{get_client.client_rlname}</code> <code>{get_client.client_surname}</code>

        🕰 Регистрация: <code>{convert_date(get_client.client_unix, False, False)} ({convert_day(how_days)})</code>
    """
    )

    kb = client_profile_finl()


    await bot.send_message(chat_id=user_id, text=send_text, reply_markup=kb)


# Открытие позиции пользователем
async def position_open_user(
    bot: Bot, user_id: int, position_id: Union[str, int], position_unix
):
    get_items = Itemx.gets(position_id=position_id)
    get_position = Positionx.get(position_unix=position_unix)
    get_category = Categoryx.get(category_id=get_position.category_id)

    if get_position.position_desc != "None":
        text_desc = f"\n▪️ Описание: {get_position.position_desc}"
    else:
        text_desc = ""

    send_text = ded(
        f"""
        <b>🧑🏻‍💻 Выполнение заказа:</b>
        ➖➖➖➖➖➖➖➖➖➖
        ▪️ Название: <code>{get_position.position_name}</code>
        ▪️ Категория: <code>{get_category.category_name}</code>
        ▪️ Время на выполнение: <code>{get_position.position_time}ч</code>
        ▪️ Стоимость: <code>{get_position.position_price}₽</code>
        {text_desc}
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
        reply_markup=products_open_finl(
            position_id, get_position.category_id, get_position.position_unix
        ),
    )


################################################################################
#################################### АДМИН #####################################
# Открытие профиля админом
async def open_profile_admin(bot: Bot, user_id: int, get_user: UserModel):
    get_purchases = Purchasesx.gets(user_id=get_user.user_id)

    how_days = int(get_unix() - get_user.user_unix) // 60 // 60 // 24
    #!count_items = sum([purchase.purchase_count for purchase in get_purchases])
    #!▪️ Выполнено заказов: <code>{count_items}шт</code>

    send_text = ded(
        f"""
        <b>👤 Профиль пользователя: <a href='tg://user?id={get_user.user_id}'>{get_user.user_name}</a></b>
        ➖➖➖➖➖➖➖➖➖➖
        ▪️ ID: <code>{get_user.user_id}</code>
        ▪️ Логин: <b>@{get_user.user_login}</b>
        ▪️ Имя: <a href='tg://user?id={get_user.user_id}'>{get_user.user_name}</a>
        ▪️ Регистрация: <code>{convert_date(get_user.user_unix, False, False)} ({convert_day(how_days)})</code>

        ▪️ Баланс: <code>{get_user.user_balance}₽</code>
        ▪️ Всего выдано: <code>{get_user.user_give}₽</code>
        ▪️ Всего пополнено: <code>{get_user.user_refill}₽</code>
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
        reply_markup=profile_search_finl(get_user.user_id),
    )


async def open_profile_admin_client(bot: Bot, user_id: int, get_user: ClientModel):
    get_purchases = Purchasesclientx.gets(client_id=get_user.client_id)

    how_days = int(get_unix() - get_user.client_unix) // 60 // 60 // 24
    #!count_items = sum([purchase.purchase_count for purchase in get_purchases])
    #!▪️ Выполнено заказов: <code>{count_items}шт</code>

    send_text = ded(
        f"""
        <b>👤 Профиль пользователя: <a href='tg://user?id={get_user.client_id}'>{get_user.client_name}</a></b>
        ➖➖➖➖➖➖➖➖➖➖
        ▪️ ID: <code>{get_user.client_id}</code>
        ▪️ Логин: <b>@{get_user.client_login}</b>
        ▪️ Имя: <a href='tg://user?id={get_user.client_id}'>{get_user.client_name}</a>
        ▪️ Регистрация: <code>{convert_date(get_user.client_unix, False, False)} ({convert_day(how_days)})</code>

        ▪️ Баланс: <code>{get_user.client_balance}₽</code>
        ▪️ Всего выдано: <code>{get_user.client_give}₽</code>
        ▪️ Всего пополнено: <code>{get_user.client_refill}₽</code>
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
        reply_markup=profile_search_finl_client(get_user.client_id),
    )


# Открытие пополнения админом
async def refill_open_admin(bot: Bot, user_id: int, get_refill: RefillModel):
    get_user = Userx.get(user_id=get_refill.user_id)

    if get_refill.refill_method == "Yoomoney":
        pay_way = "Юkassa 🔮"
    else:
        pay_way = f"{get_refill.refill_method}"

    send_text = ded(
        f"""
        <b>🧾 Чек: <code>#{get_refill.refill_receipt}</code></b>
        ➖➖➖➖➖➖➖➖➖➖
        ▪️ Пользователь: <a href='tg://user?id={get_user.user_id}'>{get_user.user_name}</a> | <code>{get_user.user_id}</code>
        ▪️ Сумма пополнения: <code>{get_refill.refill_amount}₽</code>
        ▪️ Способ пополнения: <code>{pay_way}</code>
        ▪️ Комментарий: <code>{get_refill.refill_comment}</code>
        ▪️ Дата пополнения: <code>{convert_date(get_refill.refill_unix)}</code>
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
    )


# Открытие пополнения админом
async def refill_open_admin_client(bot: Bot, user_id: int, get_refill: RefillModel):
    get_user = Clientx.get(user_id=get_refill.user_id)

    if get_refill.refill_method == "Yoomoney":
        pay_way = "Юkassa 🔮"
    else:
        pay_way = f"{get_refill.refill_method}"

    send_text = ded(
        f"""
        <b>🧾 Чек: <code>#{get_refill.refill_receipt}</code></b>
        ➖➖➖➖➖➖➖➖➖➖
        ▪️ Пользователь: <a href='tg://user?id={get_user.client_id}'>{get_user.client_name}</a> | <code>{get_user.client_id}</code>
        ▪️ Сумма пополнения: <code>{get_refill.refill_amount}₽</code>
        ▪️ Способ пополнения: <code>{pay_way}</code>
        ▪️ Комментарий: <code>{get_refill.refill_comment}</code>
        ▪️ Дата пополнения: <code>{convert_date(get_refill.refill_unix)}</code>
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
    )


# Открытие Заказы админом
async def purchase_open_admin(
    bot: Bot, arSession: ARS, user_id: int, get_purchase: PurchasesModel
):
    from tgbot.utils.misc_functions import upload_text

    get_user = Userx.get(user_id=get_purchase.user_id)

    link_items = await upload_text(arSession, get_purchase.purchase_data)

    # ▪️ Выполнено заказов: <code>{get_purchase.purchase_count}шт</code>

    send_text = ded(
        f"""
        <b>🧾 Чек: <code>#{get_purchase.purchase_receipt}</code></b>
        ➖➖➖➖➖➖➖➖➖➖
        ▪️ Пользователь: <a href='tg://user?id={get_user.user_id}'>{get_user.user_name}</a> | <code>{get_user.user_id}</code>
        ▪️ Название заказа: <code>{get_purchase.purchase_position_name}</code>
        ▪️ Цена заказа: <code>{get_purchase.purchase_price_one}₽</code>
        ▪️ Баланс до Заказы: <code>{get_purchase.user_balance_before}₽</code>
        ▪️ Баланс после Заказы: <code>{get_purchase.user_balance_after}₽</code>
        ▪️ Дата Заказы: <code>{convert_date(get_purchase.purchase_unix)}</code>
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
    )


# Открытие Заказы админом
async def purchase_open_admin(
    bot: Bot, arSession: ARS, user_id: int, get_purchase: PurchasesModel
):
    from tgbot.utils.misc_functions import upload_text

    get_user = Userx.get(user_id=get_purchase.user_id)

    link_items = await upload_text(arSession, get_purchase.purchase_data)

    # ▪️ Выполнено заказов: <code>{get_purchase.purchase_count}шт</code>

    send_text = ded(
        f"""
        <b>🧾 Чек: <code>#{get_purchase.purchase_receipt}</code></b>
        ➖➖➖➖➖➖➖➖➖➖
        ▪️ Пользователь: <a href='tg://user?id={get_user.user_id}'>{get_user.user_name}</a> | <code>{get_user.user_id}</code>
        ▪️ Название заказа: <code>{get_purchase.purchase_position_name}</code>
        ▪️ Цена заказа: <code>{get_purchase.purchase_price_one}₽</code>
        ▪️ Баланс до Заказы: <code>{get_purchase.user_balance_before}₽</code>
        ▪️ Баланс после Заказы: <code>{get_purchase.user_balance_after}₽</code>
        ▪️ Дата Заказы: <code>{convert_date(get_purchase.purchase_unix)}</code>
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
    )


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


# Открытие позиции админом (и не только)
async def position_open_admin(
    bot: Bot, user_id: int, position_id: Union[str, int], position_unix
):
    # базовые выборки
    get_items = Itemx.gets(position_id=position_id)
    get_position = Positionx.get(position_unix=position_unix)
    if not get_position:
        await bot.send_message(user_id, "❌ Заказ не найден.")
        return

    get_category = None
    try:
        get_category = Categoryx.get(category_id=get_position.category_id)
    except Exception:
        pass

    get_purchases = Purchasesx.gets(purchase_position_id=position_id)
    get_settings = Settingsx.get()

    # агрегаты (если где-то используешь, оставим расчёт)
    profit_amount_all = profit_amount_day = profit_amount_week = profit_amount_month = 0
    for purchase in get_purchases:
        profit_amount_all += purchase.purchase_price
        if purchase.purchase_unix - get_settings.misc_profit_day >= 0:
            profit_amount_day += purchase.purchase_price
        if purchase.purchase_unix - get_settings.misc_profit_week >= 0:
            profit_amount_week += purchase.purchase_price
        if purchase.purchase_unix - get_settings.misc_profit_month >= 0:
            profit_amount_month += purchase.purchase_price

    # парсим расширенное описание
    ext = _pos_ext(get_position.position_desc)
    # карта категорий
    cats_map = {c.category_id: c.category_name for c in Categoryx.get_all()}

    # Категории
    if ext:
        cats_ids = ext.get("categories") or (
            [get_position.category_id]
            if getattr(get_position, "category_id", None)
            else []
        )
    else:
        cats_ids = (
            [get_position.category_id]
            if getattr(get_position, "category_id", None)
            else []
        )
    cats_text = (
        ", ".join([cats_map.get(cid, str(cid)) for cid in cats_ids])
        if cats_ids
        else (get_category.category_name if get_category else "—")
    )

    # Бюджет
    budget_val = (
        get_position.position_price
        if getattr(get_position, "position_price", 0)
        else ext.get("budget") if ext else None
    )
    if isinstance(budget_val, (int, float)):
        budget_text = f"{int(budget_val)}₽"
    else:
        budget_text = str(budget_val or "договорная")

    # Остальные поля
    city = ext.get("city", "—") if ext else "—"
    address = ext.get("address", "—") if ext else "—"
    dates = ext.get("dates", "—") if ext else "—"
    time_hours = getattr(get_position, "position_time", 0) or 0
    desc_text = (ext.get("raw_desc") if ext else None) or (
        get_position.position_name or "—"
    )

    # Формируем красивый текст
    send_text = ded(
        f"""
        <b>📁 Редактирование заказа</b>
        ➖➖➖➖➖➖➖➖➖➖
        ▪️ Заказ: <code>{desc_text}</code>
        ▪️ Категория: <code>{cats_text}</code>
        ▪️ Стоимость: <code>{budget_text}</code>
        ▪️ Город / адрес: <code>{city}</code>, <code>{address}</code>
        ▪️ Дата создания: <code>{convert_date(get_position.position_unix, False, False)}</code>
        ▪️ Сроки: <code>{dates}</code>
        ▪️ Норматив (часы): <code>{time_hours}</code>
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
        reply_markup=position_edit_open_finl(
            position_id, get_position.category_id, 0, position_unix
        ),
    )


# Открытие позиции userom
async def position_open_not_admin_user(
    bot: Bot, user_id: int, position_id: Union[str, int], position_unix
):
    get_items = Itemx.gets(position_id=position_id)
    get_position = Positionx.get(position_unix=position_unix)
    get_category = Categoryx.get(category_id=get_position.category_id)

    get_purchases = Purchasesx.gets(purchase_position_id=position_id)
    get_settings = Settingsx.get()

    profit_amount_all, profit_amount_day, profit_amount_week, profit_amount_month = (
        0,
        0,
        0,
        0,
    )
    profit_count_all, profit_count_day, profit_count_week, profit_count_month = (
        0,
        0,
        0,
        0,
    )

    position_desc = "<code>Отсутствует ❌</code>"

    if get_position.position_desc != "None":
        position_desc = f"{get_position.position_desc}"

    for purchase in get_purchases:
        profit_amount_all += purchase.purchase_price

        if purchase.purchase_unix - get_settings.misc_profit_day >= 0:
            profit_amount_day += purchase.purchase_price
        if purchase.purchase_unix - get_settings.misc_profit_week >= 0:
            profit_amount_week += purchase.purchase_price
        if purchase.purchase_unix - get_settings.misc_profit_month >= 0:
            profit_amount_month += purchase.purchase_price

    send_text = ded(
        f"""
        <b>📁 Заказ</b>
        ➖➖➖➖➖➖➖➖➖➖➖➖➖➖
        ▪️ Заказ: <code>{get_position.position_name}</code>
        ▪️ Категория: <code>{get_category.category_name}</code>
        ▪️ Стоимость: <code>{get_position.position_price}₽</code>
        ▪️ Дата создания: <code>{convert_date(get_category.category_unix)}</code>
        ▪️ Срок: {get_position.position_time} часов
        ▪️ Описание: {position_desc}
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
        reply_markup=user_position_edit_open_finl(
            position_id, get_position.category_id, 0, get_position.position_unix
        ),
    )


# Открытие товара админом
async def item_open_admin(
    bot: Bot, user_id: int, item_id: Union[str, int], remover: int
):
    get_item = Itemx.get(item_id=item_id)

    get_position = Positionx.get(position_id=get_item.position_id)
    get_category = Categoryx.get(category_id=get_item.category_id)

    send_text = ded(
        f"""
        <b>🧑🏻‍💻️ Редактирование заказа</b>
        ➖➖➖➖➖➖➖➖➖➖➖➖➖➖
        ▪️ Категория: <code>{get_category.category_name}</code>
        ▪️ Заказ: <code>{get_position.position_name}</code>
        ▪️ Дата добавления: <code>{convert_date(get_item.item_unix)}</code>
    """
    )

    await bot.send_message(
        chat_id=user_id,
        text=send_text,
        reply_markup=item_delete_finl(
            get_item.item_id, get_item.position_id, get_item.category_id
        ),
    )


# Статистика бота
def get_statistics() -> str:
    refill_amount_all, refill_amount_day, refill_amount_week, refill_amount_month = (
        0,
        0,
        0,
        0,
    )
    refill_count_all, refill_count_day, refill_count_week, refill_count_month = (
        0,
        0,
        0,
        0,
    )
    profit_amount_all, profit_amount_day, profit_amount_week, profit_amount_month = (
        0,
        0,
        0,
        0,
    )
    profit_count_all, profit_count_day, profit_count_week, profit_count_month = (
        0,
        0,
        0,
        0,
    )
    (
        users_all,
        users_day,
        users_week,
        users_month,
        users_money_have,
        users_money_give,
    ) = (0, 0, 0, 0, 0, 0)

    get_categories = Categoryx.get_all()
    get_positions = Positionx.get_all()
    get_purchases = Purchasesx.get_all()
    get_refill = Refillx.get_all()
    get_items = Itemx.get_all()
    get_users = Userx.get_all()

    get_settings = Settingsx.get()

    for purchase in get_purchases:
        profit_amount_all += purchase.purchase_price

        if purchase.purchase_unix - get_settings.misc_profit_day >= 0:
            profit_amount_day += purchase.purchase_price
        if purchase.purchase_unix - get_settings.misc_profit_week >= 0:
            profit_amount_week += purchase.purchase_price
        if purchase.purchase_unix - get_settings.misc_profit_month >= 0:
            profit_amount_month += purchase.purchase_price

    for refill in get_refill:
        refill_amount_all += refill.refill_amount
        refill_count_all += 1

        if refill.refill_unix - get_settings.misc_profit_day >= 0:
            refill_amount_day += refill.refill_amount
            refill_count_day += 1
        if refill.refill_unix - get_settings.misc_profit_week >= 0:
            refill_amount_week += refill.refill_amount
            refill_count_week += 1
        if refill.refill_unix - get_settings.misc_profit_month >= 0:
            refill_amount_month += refill.refill_amount
            refill_count_month += 1

    for user in get_users:
        users_money_have += user.user_balance
        users_money_give += user.user_give
        users_all += 1

        if user.user_unix - get_settings.misc_profit_day >= 0:
            users_day += 1
        if user.user_unix - get_settings.misc_profit_week >= 0:
            users_week += 1
        if user.user_unix - get_settings.misc_profit_month >= 0:
            users_month += 1

    return ded(
        f"""
        <b>📊 СТАТИСТИКА БОТА</b>
        ➖➖➖➖➖➖➖➖➖➖
        <b>👤 Пользователи</b>
        ┣ Юзеров за День: <code>{users_day}</code>
        ┣ Юзеров за Неделю: <code>{users_week}</code>
        ┣ Юзеров за Месяц: <code>{users_month}</code>
        ┗ Юзеров за Всё время: <code>{users_all}</code>

        <b>💰 Средства</b>
        ┣‒ Заказы (кол-во, сумма)
        ┣ За День: <code>{profit_count_day}шт</code> - <code>{profit_amount_day}₽</code>
        ┣ За Неделю: <code>{profit_count_week}шт</code> - <code>{profit_amount_week}₽</code>
        ┣ За Месяц: <code>{profit_count_month}шт</code> - <code>{profit_amount_month}₽</code>
        ┣ За Всё время: <code>{profit_count_all}шт</code> - <code>{profit_amount_all}₽</code>
        ┃
        ┣‒ Пополнения (кол-во, сумма)
        ┣ За День: <code>{refill_count_day}шт</code> - <code>{refill_amount_day}₽</code>
        ┣ За Неделю: <code>{refill_count_week}шт</code> - <code>{refill_amount_week}₽</code>
        ┣ За Месяц: <code>{refill_count_month}шт</code> - <code>{refill_amount_month}₽</code>
        ┣ За Всё время: <code>{refill_count_all}шт</code> - <code>{refill_amount_all}₽</code>
        ┃
        ┣‒ Прочее
        ┣ Средств выдано: <code>{users_money_give}₽</code>
        ┗ Средств в системе: <code>{users_money_have}₽</code>

        <b>📝 Доступные заказы</b>
        ┣ Позиций: <code>{len(get_positions)}шт</code>
        ┗ Категорий: <code>{len(get_categories)}шт</code>
   """
    )
