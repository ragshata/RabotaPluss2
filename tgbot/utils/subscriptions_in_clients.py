# subscriptions_in_clients.py (или рядом с Clientx)
import sqlite3, time
from tgbot.data.config import PATH_DATABASE

SUB_WEEK_PRICE_RUB = 100


def _now() -> int:
    return int(time.time())


def _days(n: int) -> int:
    return n * 24 * 60 * 60


def client_sub_ensure_columns():
    cols = set()
    with sqlite3.connect(PATH_DATABASE) as con:
        cur = con.execute("PRAGMA table_info(storage_clients)")
        for _, name, *_ in cur.fetchall():
            cols.add(name)

        def add(col_sql: str):
            try:
                con.execute(f"ALTER TABLE storage_clients ADD COLUMN {col_sql}")
            except Exception:
                pass

        if "sub_started_unix" not in cols:
            add("sub_started_unix INTEGER NOT NULL DEFAULT 0")
        if "sub_trial_until" not in cols:
            add("sub_trial_until INTEGER NOT NULL DEFAULT 0")
        if "sub_paid_until" not in cols:
            add("sub_paid_until INTEGER NOT NULL DEFAULT 0")
        if "sub_status" not in cols:
            add("sub_status TEXT NOT NULL DEFAULT 'inactive'")  # 'active'/'inactive'


# subscriptions_in_clients.py (продолжение)
from tgbot.database.db_users import ClientModel, Clientx  # или твой путь


def _human(ts: int) -> str:
    from datetime import datetime

    if not ts:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")


def client_sub_get(uid: int) -> ClientModel | None:
    return Clientx.get(client_id=uid)


def client_sub_is_active(uid: int) -> bool:
    c = client_sub_get(uid)
    if not c:
        return False
    if c.sub_status != "active":
        return False
    return c.sub_paid_until > _now()


def client_sub_start_free_month(uid: int):
    now = _now()
    trial_until = now + _days(30)
    # начинаем триал: paid_until = trial_until (чтобы «активно» до конца триала)
    Clientx.update(
        uid,
        sub_started_unix=now,
        sub_trial_until=trial_until,
        sub_paid_until=trial_until,
        sub_status="active",
    )
    return Clientx.get(client_id=uid)


def client_sub_extend_week(uid: int):
    c = Clientx.get(client_id=uid)
    now = _now()
    base = c.sub_paid_until if c and c.sub_paid_until > now else now
    new_paid_until = base + _days(7)
    Clientx.update(uid, sub_paid_until=new_paid_until, sub_status="active")
    return Clientx.get(client_id=uid)


# subscriptions_in_clients.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def paywall_text() -> str:
    return (
        "<b>Подписка нужна для создания заказов</b>\n\n"
        "Первый месяц — <b>бесплатно</b>.\n"
        "Далее — <b>100 ₽ в неделю</b>.\n\n"
        "Оформите подписку, чтобы продолжить."
    )


def subscribe_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Оплатить 100 ₽ за неделю", callback_data="sub:buy_week"
                )
            ],
            [InlineKeyboardButton(text="ℹ️ Что включено", callback_data="sub:info")],
        ]
    )


# subscriptions_in_clients.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime


def paywall_text() -> str:
    return (
        "<b>Подписка нужна для создания заказов</b>\n\n"
        "Первый месяц — <b>бесплатно</b>.\n"
        "Далее — <b>100 ₽ в неделю</b>.\n\n"
        "Оформите подписку, чтобы продолжить."
    )


def subscribe_kb_contact_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Оплатить (написать администратору)",
                    callback_data="sub:pay",
                )
            ],
            [InlineKeyboardButton(text="ℹ️ Что включено", callback_data="sub:info")],
        ]
    )


def _human(ts: int) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(ts)
