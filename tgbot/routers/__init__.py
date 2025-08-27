# - *- coding: utf- 8 - *-
from aiogram import Dispatcher, F

from tgbot.keyboards import inline_admin_prod
from tgbot.routers import main_errors, main_start, main_missed
from tgbot.routers.admin import admin_menu, admin_functions, admin_payment, admin_products, admin_settings
from tgbot.routers.user import profile_actions, user_menu, user_transactions, user_products
from tgbot.utils import text_functions
from tgbot.utils.misc.bot_filters import IsAdmin


# Регистрация всех роутеров
def register_all_routers(dp: Dispatcher):
    # Подключение фильтров
    dp.message.filter(F.chat.type == "private")  # Работа бота только в личке - сообщения
    dp.callback_query.filter(F.message.chat.type == "private")  # Работа бота только в личке - колбэки

    admin_menu.router.message.filter(IsAdmin())  # Работа роутера только для админов
    admin_functions.router.message.filter(IsAdmin())  # Работа роутера только для админов
    admin_payment.router.message.filter(IsAdmin())  # Работа роутера только для админов
    admin_settings.router.message.filter(IsAdmin())  # Работа роутера только для админов
    admin_products.router.message.filter(IsAdmin())  # Работа роутера только для админов

    # Подключение обязательных роутеров
    dp.include_router(main_errors.router)  # Роутер ошибки
    dp.include_router(main_start.router)  # Роутер основных команд

    # Подключение пользовательских роутеров (юзеров и админов)
    dp.include_router(profile_actions.router)
    dp.include_router(text_functions.router)
    dp.include_router(user_menu.router)  # Юзер роутер
    dp.include_router(inline_admin_prod.router) 
    dp.include_router(admin_menu.router)  # Админ роутер
    dp.include_router(user_products.router)  # Юзер роутер
    dp.include_router(user_transactions.router)  # Юзер роутер
    dp.include_router(admin_functions.router)  # Админ роутер
    dp.include_router(admin_payment.router)  # Админ роутер
    dp.include_router(admin_settings.router)  # Админ роутер
    dp.include_router(admin_products.router)  # Админ роутер

    # Подключение обязательных роутеров
    dp.include_router(main_missed.router)  # Роутер пропущенных апдейтов
