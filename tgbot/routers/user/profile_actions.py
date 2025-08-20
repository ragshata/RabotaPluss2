# -*- coding: utf-8 -*-
import json
from aiogram import Router, F, types
from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from tgbot.database.db_users import Userx
from tgbot.keyboards.inline_user import user_profile_finl
from tgbot.keyboards.inline_register import cities_kb, specs_kb, SPECS

router = Router()


# ───────── helpers ─────────
def _photos_to_list(raw: str | list) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    try:
        data = json.loads(raw or "[]")
        if isinstance(data, list):
            return [str(x) for x in data]
    except Exception:
        pass
    return []


def _list_to_json(lst: list[str]) -> str:
    return json.dumps(lst, ensure_ascii=False)


def _titles_from_slugs(slugs: list[str]) -> list[str]:
    slug_to_title = {slug: title for slug, title in SPECS}
    return [slug_to_title.get(s, s) for s in slugs]


def _slugs_from_titles(titles: list[str]) -> list[str]:
    title_to_slug = {title: slug for slug, title in SPECS}
    return [title_to_slug.get(t, t) for t in titles]


# ───────── states ─────────
class ProfileStates(StatesGroup):
    edit_name = State()
    edit_surname = State()
    edit_phone = State()
    edit_experience = State()
    edit_city = State()
    edit_specs = State()
    add_photos = State()


# ───────── edit menu ─────────
@router.callback_query(F.data == "profile:edit")
async def profile_edit_menu(c: CallbackQuery):
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
    await c.message.answer("Что редактируем?", reply_markup=kb)
    await c.answer()


# Имя
@router.callback_query(F.data == "profile:edit_name")
async def ask_name(c: CallbackQuery, state: FSMContext):
    await c.message.answer("Введите новое имя:")
    await state.set_state(ProfileStates.edit_name)
    await c.answer()


@router.message(ProfileStates.edit_name)
async def save_name(m: types.Message, state: FSMContext):
    name = m.text.strip()
    Userx.update(m.from_user.id, user_rlname=name)
    await state.clear()
    await m.answer("Имя обновлено ✅")


# Фамилия
@router.callback_query(F.data == "profile:edit_surname")
async def ask_surname(c: CallbackQuery, state: FSMContext):
    await c.message.answer("Введите новую фамилию:")
    await state.set_state(ProfileStates.edit_surname)
    await c.answer()


@router.message(ProfileStates.edit_surname)
async def save_surname(m: types.Message, state: FSMContext):
    surname = m.text.strip()
    Userx.update(m.from_user.id, user_surname=surname)
    await state.clear()
    await m.answer("Фамилия обновлена ✅")


# Телефон
@router.callback_query(F.data == "profile:edit_phone")
async def ask_phone(c: CallbackQuery, state: FSMContext):
    await c.message.answer("Введите телефон в формате +79991234567:")
    await state.set_state(ProfileStates.edit_phone)
    await c.answer()


@router.message(ProfileStates.edit_phone)
async def save_phone(m: types.Message, state: FSMContext):
    phone = m.text.strip()
    if not phone.startswith("+") or not phone[1:].isdigit() or len(phone) < 10:
        await m.answer("❌ Некорректно. Пример: +79991234567")
        return
    Userx.update(m.from_user.id, user_number=phone)
    await state.clear()
    await m.answer("Телефон обновлён ✅")


# Опыт
@router.callback_query(F.data == "profile:edit_experience")
async def ask_experience(c: CallbackQuery, state: FSMContext):
    await c.message.answer("Сколько лет опыта? Введите число от 0 до 60:")
    await state.set_state(ProfileStates.edit_experience)
    await c.answer()


@router.message(ProfileStates.edit_experience)
async def save_experience(m: types.Message, state: FSMContext):
    t = m.text.strip()
    if not t.isdigit():
        await m.answer("❌ Введите число лет (0..60).")
        return
    years = int(t)
    if not (0 <= years <= 60):
        await m.answer("❌ Диапазон 0..60.")
        return
    Userx.update(m.from_user.id, experience_years=years)
    await state.clear()
    await m.answer("Опыт обновлён ✅")


# Город
@router.callback_query(F.data == "profile:edit_city")
async def choose_city(c: CallbackQuery, state: FSMContext):
    await c.message.answer(
        "Выберите город:", reply_markup=cities_kb(prefix="edit_city")
    )
    await state.set_state(ProfileStates.edit_city)
    await c.answer()


@router.callback_query(ProfileStates.edit_city, F.data.startswith("edit_city:"))
async def save_city(c: CallbackQuery, state: FSMContext):
    _, city = c.data.split(":", 1)
    Userx.update(c.from_user.id, city=city)
    await state.clear()
    await c.message.edit_text(f"Город обновлён ✅: {city}")
    await c.answer()


# Специализации
@router.callback_query(F.data == "profile:edit_specs")
async def edit_specs(c: CallbackQuery, state: FSMContext):
    user = Userx.get(user_id=c.from_user.id)
    current_titles = [
        t.strip() for t in (user.specializations or "").split(",") if t.strip()
    ]
    current_slugs = _slugs_from_titles(current_titles)
    await state.update_data(edit_specs_selected=current_slugs)
    await c.message.answer(
        "Выберите специализации и нажмите «Готово».",
        reply_markup=specs_kb(
            current_slugs, prefix="edit_spec", done_id="edit_spec_done"
        ),
    )
    await state.set_state(ProfileStates.edit_specs)
    await c.answer()


@router.callback_query(ProfileStates.edit_specs, F.data.startswith("edit_spec:"))
async def toggle_edit_spec(c: CallbackQuery, state: FSMContext):
    _, slug = c.data.split(":", 1)
    data = await state.get_data()
    selected = list(data.get("edit_specs_selected", []))
    if slug in selected:
        selected.remove(slug)
    else:
        selected.append(slug)
    await state.update_data(edit_specs_selected=selected)
    await c.message.edit_reply_markup(
        reply_markup=specs_kb(selected, prefix="edit_spec", done_id="edit_spec_done")
    )
    await c.answer()


@router.callback_query(ProfileStates.edit_specs, F.data == "edit_spec_done")
async def save_edit_specs(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    slugs = list(data.get("edit_specs_selected", []))
    if not slugs:
        await c.answer("Выберите хотя бы одну специализацию.", show_alert=True)
        return
    titles = _titles_from_slugs(slugs)
    titles_str = ",".join(titles)
    Userx.update(c.from_user.id, specializations=titles_str)
    await state.clear()
    await c.message.edit_text(f"Специализации обновлены ✅: {titles_str}")
    await c.answer()


# ───────── photos / portfolio ─────────
@router.callback_query(F.data == "profile:add_photos")
async def add_photos(c: CallbackQuery, state: FSMContext):
    await c.message.answer(
        "Отправьте 1–5 фото ваших работ. Можно несколькими сообщениями."
    )
    await state.set_state(ProfileStates.add_photos)
    await c.answer()


@router.message(ProfileStates.add_photos, F.photo)
async def receive_portfolio_photo(m: types.Message, state: FSMContext):
    user = Userx.get(user_id=m.from_user.id)
    photos = _photos_to_list(user.work_photos)
    if len(photos) >= 50:
        await m.answer("Достигнут лимит 50 фото.")
        return
    file_id = m.photo[-1].file_id
    photos.append(file_id)
    Userx.update(m.from_user.id, work_photos=_list_to_json(photos))
    await m.answer(f"Фото добавлено ✅ (всего: {len(photos)}).")


@router.callback_query(F.data == "profile:clear_photos")
async def clear_photos(c: CallbackQuery):
    Userx.update(c.from_user.id, work_photos="[]")
    await c.message.answer("Все фото портфолио удалены 🗑")
    await c.answer()


@router.callback_query(F.data.startswith("profile:view_photos:"))
async def view_photos(c: CallbackQuery):
    _, _, page_str = c.data.split(":")
    page = int(page_str)
    user = Userx.get(user_id=c.from_user.id)
    photos = _photos_to_list(user.work_photos)
    if not photos:
        await c.message.answer("Портфолио пусто.")
        await c.answer()
        return

    per_page = 10
    start = page * per_page
    chunk = photos[start : start + per_page]
    media = [InputMediaPhoto(media=fid) for fid in chunk]

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

    try:
        await c.message.answer_media_group(media=media)
    except Exception:
        # если альбом не прошёл — отправим по одному
        for m in media:
            await c.message.answer_photo(m.media)

    if nav:
        total_pages = (len(photos) - 1) // per_page + 1
        await c.message.answer(f"Стр. {page+1}/{total_pages}", reply_markup=kb)

    await c.answer()
