# - *- coding: utf- 8 - *-
from aiogram import Router, Bot, F, types
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.filters.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from tgbot.database.db_users import Clientx, Userx
from tgbot.database.db_settings import Settingsx
from tgbot.database.db_users import UserModel
from tgbot.keyboards.inline_register import cities_kb, skip_kb, specs_kb
from tgbot.keyboards.inline_user import user_support_finl
from tgbot.keyboards.reply_main import (
    menu_frep,
    menu_second_start,
    menu_second_start_clients,
)
from tgbot.utils.const_functions import ded
from tgbot.utils.misc.bot_filters import IsBuy, IsRefill, IsWork
from tgbot.utils.misc.bot_models import FSM, ARS


import json

router = Router()

# Игнор-колбэки покупок
prohibit_buy = [
    "buy_category_swipe",
    "buy_category_open",
    "buy_position_swipe",
    "buy_position_open",
    "buy_item_open",
    "buy_item_confirm",
]

# Игнор-колбэки пополнений
prohibit_refill = [
    "user_refill",
    "user_refill_method",
    "Pay:",
    "Pay:Yoomoney",
]

router = Router(name=__name__)


################################################################################
########################### СТАТУС ТЕХНИЧЕСКИХ РАБОТ ###########################
# Фильтр на технические работы - сообщение
@router.message(IsWork())
async def filter_work_message(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    get_settings = Settingsx.get()

    if get_settings.misc_support != "None":
        return await message.answer(
            "<b>⛔ Бот находится на технических работах.</b>",
            reply_markup=user_support_finl(get_settings.misc_support),
        )

    await message.answer("<b>⛔ Бот находится на технических работах.</b>")


# Фильтр на технические работы - колбэк
@router.callback_query(IsWork())
async def filter_work_callback(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    await state.clear()

    await call.answer("⛔ Бот находится на технических работах.", True)


################################################################################
################################# СТАТУС ПОКУПОК ###############################
# Фильтр на доступность покупок - сообщение
@router.message(IsBuy(), F.text == "🧑🏻‍💻 Выполнить заказ")
@router.message(IsBuy(), StateFilter("here_item_count"))
async def filter_buy_message(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer("<b>⛔ Заказы временно отключены.</b>")


# Фильтр на доступность покупок - колбэк
@router.callback_query(IsBuy(), F.text.startswith(prohibit_buy))
async def filter_buy_callback(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    await state.clear()

    await call.answer("⛔ Заказы временно отключены.", True)


################################################################################
############################### СТАТУС ПОПОЛНЕНИЙ ##############################
# Фильтр на доступность пополнения - сообщение
@router.message(IsRefill(), StateFilter("here_pay_amount"))
async def filter_refill_message(message: Message, bot: Bot, state: FSM, arSession: ARS):
    await state.clear()

    await message.answer("<b>⛔ Пополнение временно отключено.</b>")


# Фильтр на доступность пополнения - колбэк
@router.callback_query(IsRefill(), F.text.startswith(prohibit_refill))
async def filter_refill_callback(
    call: CallbackQuery, bot: Bot, state: FSM, arSession: ARS
):
    await state.clear()

    await call.answer("⛔ Пополнение временно отключено.", True)


################################################################################
#################################### ПРОЧЕЕ ####################################
# Открытие главного меню
@router.message(F.text.in_(("🔙 Главное меню", "/start")))
async def main_start(message: Message, bot: Bot, state: FSM, arSession: ARS):
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


# добавьте новые состояния
class RegisterStates(StatesGroup):
    user_rlname = State()
    user_surname = State()
    user_number = State()
    experience_years = State()  # NEW
    city = State()  # NEW
    specs = State()  # NEW (мультивыбор)
    photos = State()  # NEW (опционально)


@router.message(F.text.in_(("👷 Я исполнитель",)))
async def enter_registr(message: Message, state: FSMContext):
    user = Userx.get(user_id=message.from_user.id)

    def is_empty(value) -> bool:
        return value is None or str(value).strip() in ("", "0")

    if not user or any(
        [
            is_empty(user.user_rlname),
            is_empty(user.user_surname),
            is_empty(user.user_number),
        ]
    ):
        # Старт регистрации
        await message.answer(
            "📝 Введите свое имя:", reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(RegisterStates.user_rlname)
    else:
        # Уже зарегистрирован
        await message.answer(
            f"Добро пожаловать обратно, {user.user_rlname}!",
            reply_markup=menu_second_start(message.from_user.id),
        )


@router.message(RegisterStates.user_rlname)
async def set_name(message: Message, state: FSMContext):
    await state.update_data(user_rlname=message.text.strip())
    await message.answer(
        "📝 Введите свою фамилию:", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(RegisterStates.user_surname)


@router.message(RegisterStates.user_surname)
async def set_surname(message: Message, state: FSMContext):
    await state.update_data(user_surname=message.text.strip())
    await message.answer(
        "📞 Введите свой номер телефона в формате +79991234567:",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    await state.set_state(RegisterStates.user_number)


@router.message(RegisterStates.user_number)
async def set_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not phone.startswith("+") or not phone[1:].isdigit() or len(phone) < 10:
        await message.answer(
            "❌ Введите корректный номер телефона в формате +79991234567."
        )
        return
    await state.update_data(user_number=phone)
    await message.answer("⏳ Сколько лет опыта работы? Введите число (например, 3):")
    await state.set_state(RegisterStates.experience_years)


@router.message(RegisterStates.experience_years)
async def set_experience(message: Message, state: FSMContext):
    txt = message.text.strip()
    if not txt.isdigit():
        await message.answer("❌ Введите только число лет (например, 5).")
        return
    years = int(txt)
    if years < 0 or years > 60:
        await message.answer("❌ Нереалистичное значение. Введите число от 0 до 60.")
        return
    await state.update_data(experience_years=years)
    await message.answer("🏙 Выберите город:", reply_markup=cities_kb())
    await state.set_state(RegisterStates.city)


@router.callback_query(RegisterStates.city, F.data.startswith("city:"))
async def choose_city(call: CallbackQuery, state: FSMContext):
    _, city = call.data.split(":", 1)
    await state.update_data(city=city)
    # Переходим к выбору специализаций
    await call.message.edit_text(
        "🧰 Выберите основные специализации (можно несколько), затем нажмите «Готово»."
    )
    await call.message.edit_reply_markup(reply_markup=specs_kb(selected=[]))
    await state.update_data(specs_selected=[])  # список вместо set
    await state.set_state(RegisterStates.specs)  # ВАЖНО!
    await call.answer()


@router.callback_query(RegisterStates.specs, F.data.startswith("spec:"))
async def toggle_spec(call: CallbackQuery, state: FSMContext):
    _, slug = call.data.split(":", 1)
    data = await state.get_data()
    selected: list[str] = list(data.get("specs_selected", []))
    if slug in selected:
        selected.remove(slug)
    else:
        selected.append(slug)
    await state.update_data(specs_selected=selected)
    await call.message.edit_reply_markup(reply_markup=specs_kb(selected))
    await call.answer()


# --- импорты рядом с остальными ---
from aiogram import F, Router, Bot
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from tgbot.database.db_position import Positionx

router = Router(name=__name__)


# ========= клавиатура подтверждения/добавления/отмены =========
def handoff_kb(punix: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data=f"handoff:confirm:{punix}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Добавить ещё", callback_data=f"handoff:add:{punix}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data=f"handoff:cancel:{punix}"
                )
            ],
        ]
    )


# ========= состояния, как в регистрации =========
class HandoffStates(StatesGroup):
    photos = State()  # ждём фото от исполнителя


# ========= старт «Сдать работу» =========
# вызывaется по твоей кнопке: myresp:handoff:{punix}
@router.callback_query(F.data.startswith("myresp:handoff:"))
async def handoff_start(call: CallbackQuery, state: FSMContext):
    punix = int(call.data.split(":")[2])
    await state.update_data(handoff_punix=punix, handoff_photos=[])
    await call.message.edit_text(
        "📸 Загрузите 1–5 фото выполненной работы.\n"
        "Можно отправлять несколько сообщений с фото.\n"
        "Когда будете готовы — нажмите «✅ Подтвердить».",
        reply_markup=handoff_kb(punix),
    )
    await state.set_state(HandoffStates.photos)
    await call.answer()


# ========= приём фото (1..5), как в твоей регистрации =========
@router.message(HandoffStates.photos, F.photo)
async def handoff_receive_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    punix: int = int(data.get("handoff_punix", 0))
    files: list[str] = list(data.get("handoff_photos", []))

    if len(files) >= 5:
        await message.answer(
            "Максимум 5 фото. Нажмите «✅ Подтвердить» или «❌ Отмена»."
        )
        return

    file_id = message.photo[-1].file_id  # берём самое большое
    files.append(file_id)
    await state.update_data(handoff_photos=files)

    await message.answer(
        f"Фото добавлено ({len(files)}/5). Можете отправить ещё или нажмите «✅ Подтвердить».",
        reply_markup=handoff_kb(punix),
    )


# ========= подтвердить отправку =========
@router.callback_query(HandoffStates.photos, F.data.startswith("handoff:confirm:"))
async def handoff_confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
    punix = int(call.data.split(":")[-1])
    data = await state.get_data()
    photos: list[str] = list(data.get("handoff_photos", []))[:5]

    pos = Positionx.get(position_unix=punix)
    if not pos:
        await call.answer("Заказ не найден.", show_alert=True)
        return

    client_id = int(getattr(pos, "position_id", 0) or 0)
    title = getattr(pos, "position_name", "Заказ")

    # если фото нет — попросим добавить хотя бы одно
    if not photos:
        await call.answer(
            "Добавьте хотя бы одно фото или нажмите «❌ Отмена».", show_alert=True
        )
        return

    # 1) отправим медиагруппу заказчику
    media = [InputMediaPhoto(type="photo", media=fid) for fid in photos]
    try:
        await bot.send_media_group(chat_id=client_id, media=media)
    except Exception:
        # fallback: по одному
        for fid in photos:
            try:
                await bot.send_photo(chat_id=client_id, photo=fid)
            except Exception:
                pass

    # 2) уведомление заказчику
    try:
        await bot.send_message(
            chat_id=client_id,
            text=(
                "🚚 <b>Исполнитель сдал работу</b>\n\n"
                f"📦 Заказ: <code>{title}</code>\n\n"
                "Проверьте материалы и подтвердите выполнение заказа."
            ),
            disable_web_page_preview=True,
        )
    except Exception:
        pass

    # (опционально) поменять статус на «на проверке» = 2
    try:
        Positionx.update_unix(punix, position_status=2)
    except Exception:
        pass

    # 3) ответ исполнителю
    try:
        await call.message.edit_text("✅ Отправлено заказчику. Ожидайте подтверждения.")
    except Exception:
        await call.message.answer("✅ Отправлено заказчику. Ожидайте подтверждения.")

    await state.clear()
    await call.answer()


# ========= добавить ещё (просто подсказка, остаёмся в state) =========
@router.callback_query(HandoffStates.photos, F.data.startswith("handoff:add:"))
async def handoff_add_more(call: CallbackQuery, state: FSMContext):
    await call.answer("Пришлите ещё фото одним или несколькими сообщениями.")


# ========= отмена =========
@router.callback_query(HandoffStates.photos, F.data.startswith("handoff:cancel:"))
async def handoff_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.edit_text("❌ Отменено.")
    except Exception:
        await call.message.answer("❌ Отменено.")
    await call.answer()


# ─── Состояния ───
class RegisterStatesClients(StatesGroup):
    client_rlname = State()
    client_surname = State()
    client_number = State()


# ─── Хелперы ───
def _is_empty(v) -> bool:
    return v is None or str(v).strip() in ("", "0")


def _valid_phone(phone: str) -> bool:
    p = phone.strip()
    return p.startswith("+") and len(p) >= 10 and p[1:].isdigit()


# ─── Запуск регистрации / вход для заказчика ───
@router.message(F.text.in_(("🔎 Я заказчик",)))
async def enter_registr_client(message: Message, state: FSMContext):
    client = Clientx.get(client_id=message.from_user.id)

    if (client is None) or any(
        [
            _is_empty(getattr(client, "client_rlname", None)),
            _is_empty(getattr(client, "client_surname", None)),
            _is_empty(getattr(client, "client_number", None)),
        ]
    ):
        await message.answer(
            "📝 Введите своё имя:", reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(RegisterStatesClients.client_rlname)
        return

    # Уже зарегистрирован
    await message.answer(
        f"Добро пожаловать обратно, {client.client_rlname}!",
        reply_markup=menu_second_start_clients(message.from_user.id),
    )


# ─── Имя ───
@router.message(RegisterStatesClients.client_rlname)
async def set_client_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Имя не может быть пустым. Введите имя ещё раз:")
        return
    await state.update_data(client_rlname=name)
    await message.answer("📝 Введите свою фамилию:")
    await state.set_state(RegisterStatesClients.client_surname)


# ─── Фамилия ───
@router.message(RegisterStatesClients.client_surname)
async def set_client_surname(message: Message, state: FSMContext):
    surname = (message.text or "").strip()
    if not surname:
        await message.answer(
            "❌ Фамилия не может быть пустой. Введите фамилию ещё раз:"
        )
        return
    await state.update_data(client_surname=surname)
    await message.answer("📞 Введите свой номер телефона в формате +79991234567:")
    await state.set_state(RegisterStatesClients.client_number)


# ─── Телефон ───
@router.message(RegisterStatesClients.client_number)
async def set_client_phone(message: Message, state: FSMContext):
    phone = (message.text or "").strip()

    if not _valid_phone(phone):
        await message.answer(
            "❌ Пожалуйста, введите корректный номер телефона в формате +79991234567:"
        )
        return

    await state.update_data(client_number=phone)

    # Сохраняем в БД
    data = await state.get_data()
    client_rlname = data["client_rlname"]
    client_surname = data["client_surname"]
    client_number = data["client_number"]

    Clientx.update(
        message.from_user.id,
        client_login=(message.from_user.username or "unknown").lower(),
        client_name=message.from_user.first_name or "unknown",
        client_rlname=client_rlname,
        client_surname=client_surname,
        client_number=client_number,
    )

    await state.clear()

    # Сообщения после регистрации
    await message.answer(
        ded(
            f"""
        ✅ Регистрация завершена!
        Ваше имя: {client_rlname}
        Ваша фамилия: {client_surname}
        Ваш номер телефона: {client_number}
        """
        )
    )
    await message.answer(
        f"Добро пожаловать, {client_rlname}!\nВы можете создать новый заказ."
    )
    await message.answer(
        "Главное меню:",
        reply_markup=menu_second_start_clients(message.from_user.id),
    )
