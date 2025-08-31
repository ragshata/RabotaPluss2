# - *- coding: utf- 8 - *-
from typing import Union

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tgbot.database.db_category import Categoryx
from tgbot.database.db_position import Positionx
from tgbot.database.db_settings import Settingsx
from tgbot.utils.const_functions import ikb


from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

# ВМЕСТО твоих _position_edit_cat_kb / position_edit_category_* / position_edit_category_page /
# position_edit_category_pick — вставь этот блок

import json
from aiogram import F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder as IKB
from tgbot.database.db_category import Categoryx
from tgbot.database.db_position import Positionx
from tgbot.utils.const_functions import ikb

router = Router(name=__name__)

# -*- coding: utf-8 -*-
from tgbot.database.db_position import Positionx


# --- helper для безопасного апдейта по position_unix ---
def _safe_update_by_unix(punix: int, **fields):
    """
    Пытаемся обновить запись по position_unix.
    Сначала через update_unix(...), если не получится — через update_gpt(...).
    """
    try:
        # твой новый метод в Positionx — обновляет по position_unix
        Positionx.update_unix(punix, **fields)
        return True
    except Exception:
        # запасной путь: обновление по произвольному полю
        Positionx.update_gpt("position_unix", punix, **fields)
        return True


def update_position_by_unix(punix: int, **changes):
    pos = Positionx.get(position_unix=punix)
    if not pos:
        raise RuntimeError("position not found")

    fields = {}
    for name in (
        "category_id",
        "position_id",
        "position_name",
        "position_price",
        "position_desc",
        "worker_id",
        "position_status",
        "time",
        "position_time",
    ):
        if hasattr(pos, name):
            val = getattr(pos, name)
            fields[name] = (
                int(val or 0) if isinstance(val, (int, bool)) else (val or "")
            )
    fields.update(changes)

    last_err = None
    if hasattr(Positionx, "update"):
        try:
            return Positionx.update_unix(position_unix=punix, **fields)
        except Exception as e:
            last_err = e
        try:
            return Positionx.update_unix(position_unix=punix, data=fields)
        except Exception as e:
            last_err = e
    if hasattr(Positionx, "set"):
        try:
            return Positionx.set(position_unix=punix, data=fields)
        except Exception as e:
            last_err = e
    if hasattr(Positionx, "edit"):
        try:
            return Positionx.edit(position_unix=punix, **fields)
        except Exception as e:
            last_err = e

    try:
        for k, v in fields.items():
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


################################### КАТЕГОРИИ ##################################
# Изменение категории
def category_edit_open_finl(category_id, remover) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb("▪️ Изм. Название", data=f"category_edit_name:{category_id}:{remover}"),
        ikb("▪️ Добавить заказ", data=f"position_add_open:{category_id}"),
    ).row(
        ikb("🔙 Вернуться", data=f"category_edit_swipe:{remover}"),
        ikb("▪️ Удалить", data=f"category_edit_delete:{category_id}:{remover}"),
    )

    return keyboard.as_markup()


# Подтверждение удаления категории
def category_edit_delete_finl(category_id, remover) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(
            "✅ Да, удалить",
            data=f"category_edit_delete_confirm:{category_id}:{remover}",
        ),
        ikb("❌ Нет, отменить", data=f"category_edit_open:{category_id}:{remover}"),
    )

    return keyboard.as_markup()


# Отмена изменения категории и возвращение
def category_edit_cancel_finl(category_id, remover) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb("❌ Отменить", data=f"category_edit_open:{category_id}:{remover}"),
    )

    return keyboard.as_markup()


#################################### ПОЗИЦИИ ###################################
# Кнопки при открытии позиции для изменения
# -*- coding: utf-8 -*-
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder as IKB
from tgbot.utils.const_functions import ikb


def position_edit_open_finl_all(
    position_id: int, remover: int, position_unix: int
) -> InlineKeyboardMarkup:
    kb = IKB()
    kb.row(
        ikb(
            "▪️ Изм. Название",
            data=f"position_edit_name:{position_id}:{remover}:{position_unix}",
        ),
        ikb(
            "▪️ Изм. цену",
            data=f"position_edit_price:{position_id}:{remover}:{position_unix}",
        ),
    ).row(
        ikb(
            "▪️ Изм. Описание",
            data=f"position_edit_desc:{position_id}:{remover}:{position_unix}",
        ),
    ).row(
        ikb(
            "▪️ Изм. Категории",
            data=f"position_edit_cats:{position_id}:{remover}:{position_unix}",
        ),
    ).row(
        ikb(
            "✅ Завершить Заказ",
            data=f"position_edit_confirm:{position_id}:{remover}:{position_unix}",
        ),
    ).row(
        ikb(
            "▪️ Удалить Заказ",
            data=f"position_edit_delete:{position_id}:{remover}:{position_unix}",
        ),
    ).row(
        ikb("🔙 Вернуться", data=f"position_edit_swipe:{remover}"),
    )
    return kb.as_markup()


def position_edit_open_finl_dindon(
    position_id, category_id, remover, position_unix
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(
            "✅ Завершить Заказ",
            data=f"position_edit_confirm:{position_id}:{category_id}:{remover}:{position_unix}",
        )
    )
    return keyboard.as_markup()


# Кнопки при открытии позиции для изменения
def position_edit_open_finl(
    position_id, category_id, remover, position_unix
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(
            "▪️ Изм. Название",
            data=f"position_edit_name:{position_id}:{category_id}:{remover}",
        ),
        ikb(
            "▪️ Изм. цену",
            data=f"position_edit_price:{position_id}:{category_id}:{remover}",
        ),
    ).row(
        ikb(
            "▪️ Изм. Описание",
            data=f"position_edit_desc:{position_id}:{category_id}:{remover}",
        ),
    ).row(
        ikb(
            "▪️ Изм. Категорию",
            # передадим punix, чтобы потом обновить позицию
            data=f"position_edit_category:{position_id}:{category_id}:{remover}:{position_unix}",
        ),
    ).row(
        ikb(
            "✅ Завершить Заказ",
            data=f"position_edit_confirm:{position_id}:{category_id}:{remover}:{position_unix}",
        ),
    ).row(
        ikb(
            "▪️ Удалить Заказ",
            data=f"position_edit_delete:{position_id}:{category_id}:{remover}:{position_unix}",
        )
    ).row(
        ikb("🔙 Вернуться", data=f"position_edit_swipe:{category_id}:{remover}"),
    )

    return keyboard.as_markup()


# --- helper для безопасного апдейта по position_unix ---
def _safe_update_by_unix(punix: int, **fields):
    """
    Обновляет запись по position_unix.
    Сначала через update_unix(...), если нет — через update_gpt(...).
    """
    try:
        Positionx.update_unix(punix, **fields)
        return True
    except Exception:
        Positionx.update_gpt("position_unix", punix, **fields)
        return True


# --- helpers ---
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


def _compose_desc(ext: dict, fallback: str = "") -> str:
    try:
        return "[ORDER]\n" + json.dumps(ext, ensure_ascii=False, indent=2)
    except Exception:
        return fallback or "[ORDER]\n{}"


def _cats_edit_kb(
    selected: set[int],
    all_cats: list,
    position_id: int,
    remover: str,
    punix: int,
    page: int = 0,
    per_page: int = 8,
) -> InlineKeyboardMarkup:
    cats = sorted(all_cats, key=lambda c: int(getattr(c, "category_id", 0) or 0))
    total = len(cats)
    last_page = max((total - 1) // per_page, 0)
    page = max(0, min(page, last_page))
    start = page * per_page
    chunk = cats[start : start + per_page]

    kb = IKB()
    row = []
    for c in chunk:
        cid = int(getattr(c, "category_id", 0) or 0)
        title = str(getattr(c, "category_name", cid))
        mark = "✅" if cid in selected else "⬜"
        row.append(ikb(f"{mark} {title}", data=f"poscat:toggle:{punix}:{cid}:{page}"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)

    kb.row(
        InlineKeyboardButton(
            text="«",
            callback_data=f"poscat:page:{position_id}:{remover}:{punix}:{max(page-1,0)}",
        ),
        InlineKeyboardButton(text=f"{page+1}/{last_page+1}", callback_data="noop"),
        InlineKeyboardButton(
            text="»",
            callback_data=f"poscat:page:{position_id}:{remover}:{punix}:{min(page+1,last_page)}",
        ),
    )
    kb.row(
        ikb("💾 Сохранить", data=f"poscat:save:{position_id}:{remover}:{punix}"),
        ikb("🔙 Назад", data=f"poscat:back:{position_id}:{remover}:{punix}"),
    )
    return kb.as_markup()


# --- ОТКРЫТЬ мультивыбор (заменяет position_edit_category_open) ---
@router.callback_query(F.data.startswith("position_edit_category:"))
async def position_edit_category_open(call: CallbackQuery, state: FSMContext):
    try:
        _, pos_id_s, cat_id_s, remover, punix_s = call.data.split(":")
        position_id = int(pos_id_s)
        current_cat = int(cat_id_s)
        punix = int(punix_s)
    except Exception:
        await call.answer("Ошибка данных", show_alert=True)
        return

    pos = Positionx.get(position_unix=punix) or Positionx.get(position_id=position_id)
    if not pos:
        await call.answer("Заказ не найден", show_alert=True)
        return

    ext = _ext_from_desc(getattr(pos, "position_desc", "") or "")
    selected = set(int(x) for x in (ext.get("categories") or []) if str(x).isdigit())
    if not selected and current_cat:
        selected = {current_cat}

    # сохраняем выбор в FSM под ключ punix
    await state.update_data(**{f"edit_cats_{punix}": list(selected)})

    all_cats = Categoryx.get_all() or []
    kb = _cats_edit_kb(selected, all_cats, position_id, remover, punix, page=0)
    try:
        await call.message.edit_text(
            "<b>Выберите категории (мультивыбор)</b>\n"
            "Нажимайте, чтобы переключать. Затем «💾 Сохранить».",
            reply_markup=kb,
        )
    except Exception:
        await call.message.answer(
            "<b>Выберите категории (мультивыбор)</b>\n"
            "Нажимайте, чтобы переключать. Затем «💾 Сохранить».",
            reply_markup=kb,
        )
    await call.answer()


# --- TOGGLE чекбокса ---
@router.callback_query(F.data.startswith("poscat:toggle:"))
async def poscat_toggle(call: CallbackQuery, state: FSMContext):
    # poscat:toggle:{punix}:{cat_id}:{page}
    try:
        _, _, punix_s, cat_s, page_s = call.data.split(":")
        punix = int(punix_s)
        cid = int(cat_s)
        page = int(page_s)
    except Exception:
        await call.answer()
        return

    data = await state.get_data()
    key = f"edit_cats_{punix}"
    selected = set(int(x) for x in (data.get(key) or []) if str(x).isdigit())
    if cid in selected:
        selected.remove(cid)
    else:
        selected.add(cid)
    await state.update_data(**{key: list(selected)})

    all_cats = Categoryx.get_all() or []
    # pid/remover для toggle не нужны — просто перерисуем текущую страницу
    kb = _cats_edit_kb(
        selected, all_cats, position_id=0, remover="r", punix=punix, page=page
    )
    try:
        await call.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await call.answer()


# --- ПАГИНАЦИЯ списка категорий ---
@router.callback_query(F.data.startswith("poscat:page:"))
async def poscat_page(call: CallbackQuery, state: FSMContext):
    # poscat:page:{position_id}:{remover}:{punix}:{page}
    try:
        _, _, pos_id_s, remover, punix_s, page_s = call.data.split(":")
        position_id = int(pos_id_s)
        punix = int(punix_s)
        page = int(page_s)
    except Exception:
        await call.answer()
        return

    data = await state.get_data()
    selected = set(
        int(x) for x in (data.get(f"edit_cats_{punix}") or []) if str(x).isdigit()
    )
    all_cats = Categoryx.get_all() or []
    kb = _cats_edit_kb(selected, all_cats, position_id, remover, punix, page=page)
    try:
        await call.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        try:
            await call.message.edit_text(
                "<b>Выберите категории (мультивыбор)</b>", reply_markup=kb
            )
        except Exception:
            await call.message.answer(
                "<b>Выберите категории (мультивыбор)</b>", reply_markup=kb
            )
    await call.answer()


@router.callback_query(F.data.startswith("poscat:save:"))
async def poscat_save(call: CallbackQuery, state: FSMContext):
    # data: poscat:save:{position_id}:{remover}:{punix}
    try:
        punix = int(call.data.split(":")[-1])  # берём последний элемент – punix
    except Exception:
        await call.answer("Ошибка данных", show_alert=True)
        return

    data = await state.get_data()
    # В НОВОЙ версии мы храним выбор по ключу edit_cats_{punix}
    selected = [
        int(x) for x in (data.get(f"edit_cats_{punix}") or []) if str(x).isdigit()
    ]

    pos = Positionx.get(position_unix=punix)
    if not pos:
        await call.answer("Заказ не найден", show_alert=True)
        return

    ext = _ext_from_desc(getattr(pos, "position_desc", "") or "")
    ext["categories"] = selected
    main_cat_id = selected[0] if selected else 0
    new_desc = _compose_desc(ext, getattr(pos, "position_desc", "") or "")

    # ✅ корректный апдейт по position_unix
    _safe_update_by_unix(punix, category_id=main_cat_id, position_desc=new_desc)

    await call.answer("Категории обновлены")
    await call.message.delete()


# --- НАЗАД без сохранения ---
@router.callback_query(F.data.startswith("poscat:back:"))
async def poscat_back(call: CallbackQuery, state: FSMContext):
    # poscat:back:{position_id}:{remover}:{punix}
    try:
        _, _, pos_id_s, remover, punix_s = call.data.split(":")
        position_id = int(pos_id_s)
        punix = int(punix_s)
    except Exception:
        await call.answer()
        return

    pos = Positionx.get(position_unix=punix)
    cur_cat = int(getattr(pos, "category_id", 0) or 0) if pos else 0

    from tgbot.keyboards.inline_admin_prod import position_edit_open_finl

    try:
        await call.message.edit_text(
            "<b>Изменение заказа</b>",
            reply_markup=position_edit_open_finl(position_id, cur_cat, remover, punix),
        )
    except Exception:
        await call.message.answer(
            "<b>Изменение заказа</b>",
            reply_markup=position_edit_open_finl(position_id, cur_cat, remover, punix),
        )
    await call.answer()


# Кнопки при открытии позиции для изменения
def user_position_edit_open_finl(
    position_id, category_id, remover, position_unix
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    get_settings = Settingsx.get()
    keyboard.row(
        ikb(
            "✅ Отправить на проверку",
            data=f"position_done_dindon:{position_id}:{category_id}:{remover}:{position_unix}",
        ),
    ).row(
        ikb(
            "▪️ Написать в арбитраж",
            url=f"https://t.me/{get_settings.misc_support}",
        ),
    )

    return keyboard.as_markup()


# Подтверждение удаления позиции
def position_edit_delete_finl(
    position_id, category_id, remover, position_unix
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(
            "✅ Да, удалить",
            data=f"position_edit_delete_confirm:{position_id}:{category_id}:{remover}:{position_unix}",
        ),
        ikb(
            "❌ Нет, отменить",
            data=f"position_edit_open:{position_id}:{category_id}:{remover}",
        ),
    )

    return keyboard.as_markup()


def position_edit_done_finl(
    position_id, category_id, remover, position_unix
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(
            "✅ Да, подтвердить",
            data=f"position_edit_done_confirm:{position_id}:{category_id}:{remover}:{position_unix}",
        ),
        ikb(
            "❌ Нет",
            data=f"position_edit_open:{position_id}:{category_id}:{remover}:{position_unix}",
        ),
    )

    return keyboard.as_markup()


# Подтверждение очистики позиции
def position_edit_clear_finl(position_id, category_id, remover) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(
            "✅ Да, очистить",
            data=f"position_edit_clear_confirm:{position_id}:{category_id}:{remover}",
        ),
        ikb(
            "❌ Нет, отменить",
            data=f"position_edit_open:{position_id}:{category_id}:{remover}",
        ),
    )

    return keyboard.as_markup()


# Отмена изменения позиции и возвращение
def position_edit_cancel_finl(
    position_id, category_id, remover
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(
            "❌ Отменить",
            data=f"position_edit_open:{position_id}:{category_id}:{remover}",
        ),
    )

    return keyboard.as_markup()


##################################### ЗАКАЗЫ ###################################
# Отмена изменения позиции и возвращение
def item_add_finish_finl(position_id: Union[int, str]) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb("✅ Завершить загрузку", data=f"item_add_position_finish:{position_id}"),
    )

    return keyboard.as_markup()


# Удаление заказа
def item_delete_finl(item_id, position_id, category_id) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb("▪️ Удалить заказ", data=f"item_delete_confirm:{item_id}"),
    ).row(
        ikb("🔙 Вернуться", data=f"item_delete_swipe:{position_id}:{category_id}:0"),
    )

    return keyboard.as_markup()


############################### УДАЛЕНИЕ РАЗДЕЛОВ ##############################
# Выбор раздела для удаления
def products_removes_finl() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb("🗃 Удалить все категории", data=f"prod_removes_categories"),
    ).row(
        ikb("📁 Удалить все заказы", data=f"prod_removes_positions"),
    )

    return keyboard.as_markup()


def users_admire() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(" ✉️ ", url="https://telegra.ph/POLZOVATELSKOE-SOGLASHENIE-01-10-9"),
    )

    return keyboard.as_markup()


def privacy_policy() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(" ✉️ ", url="https://telegra.ph/POLITIKA-KONFIDENCIALNOSTI-01-10-10"),
    )

    return keyboard.as_markup()


def baza_znanii() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(" ✉️ ", url="https://telegra.ph/Baza-znanij-08-20"),
    )

    return keyboard.as_markup()


def knowledge_base() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb(" ✉️ ", url="https://telegra.ph/Pomoshch-01-10-3"),
    )

    return keyboard.as_markup()


# Удаление всех категорий
def products_removes_categories_finl() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb("✅ Да, удалить все", data="prod_removes_categories_confirm"),
        ikb("❌ Нет, отменить", data="prod_removes_return"),
    )

    return keyboard.as_markup()


# Удаление всех позиций
def products_removes_positions_finl() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb("✅ Да, удалить все", data="prod_removes_positions_confirm"),
        ikb("❌ Нет, отменить", data="prod_removes_return"),
    )

    return keyboard.as_markup()


# Удаление всех заказов
def products_removes_items_finl() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    keyboard.row(
        ikb("✅ Да, удалить все", data="prod_removes_items_confirm"),
        ikb("❌ Нет, отменить", data="prod_removes_return"),
    )

    return keyboard.as_markup()
