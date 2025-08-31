# -*- coding: utf-8 -*-
import asyncio
import os
import sys

import colorama
from aiogram import Dispatcher, Bot

from tgbot.data.config import get_admins, BOT_TOKEN, BOT_SCHEDULER
from tgbot.database.db_helper import create_dbx
from tgbot.middlewares import register_all_middlwares
from tgbot.routers import register_all_routers
from tgbot.services.api_session import AsyncRequestSession
from tgbot.utils.misc.bot_commands import set_commands
from tgbot.utils.misc.bot_logging import bot_logger
from tgbot.utils.misc.bot_models import ARS
from tgbot.utils.misc_functions import (
    check_update,
    check_bot_username,
    startup_notify,
    update_profit_day,
    update_profit_week,
    autobackup_admin,
    check_mail,
    update_profit_month,
)

colorama.init()


# Запуск шедулеров
async def scheduler_start(bot: Bot, arSession: ARS):
    # Планировщик может уже быть запущен при горячем рестарте — не упадём
    try:
        BOT_SCHEDULER.start()
    except Exception:
        pass

    BOT_SCHEDULER.add_job(
        update_profit_month, trigger="cron", day=1, hour=0, minute=0, second=5
    )
    BOT_SCHEDULER.add_job(
        update_profit_week,
        trigger="cron",
        day_of_week="mon",
        hour=0,
        minute=0,
        second=10,
    )
    BOT_SCHEDULER.add_job(
        update_profit_day, trigger="cron", hour=0, minute=0, second=15, args=(bot,)
    )
    BOT_SCHEDULER.add_job(autobackup_admin, trigger="cron", hour=0, args=(bot,))
    BOT_SCHEDULER.add_job(check_update, trigger="cron", hour=0, args=(bot, arSession))
    BOT_SCHEDULER.add_job(check_mail, trigger="cron", hour=12, args=(bot, arSession))


# Запуск бота и базовых функций
async def main():
    # Образы
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    arSession = AsyncRequestSession()  # пул асинхронных запросов

    # Регистрация
    register_all_middlwares(dp)
    register_all_routers(dp)

    try:
        # Команды и первичные проверки
        await set_commands(bot)
        await check_bot_username(bot)
        await check_update(bot, arSession)
        await check_mail(bot, arSession)
        await startup_notify(bot, arSession)

        # Планировщик
        await scheduler_start(bot, arSession)

        # Логи старта
        me = await bot.get_me()
        bot_logger.warning("BOT WAS STARTED")
        print(
            colorama.Fore.LIGHTYELLOW_EX
            + f"~~~~~ Bot was started - @{me.username} (pid={os.getpid()}) ~~~~~"
        )
        print(colorama.Fore.RESET)

        if len(get_admins()) == 0:
            print("***** ENTER ADMIN ID IN settings.ini *****")

        # ВАЖНО: сбрасываем вебхук и висящие апдейты.
        # НЕ вызываем get_updates(offset=-1) — это приводит к 409 при параллельном читателе.
        await bot.delete_webhook(drop_pending_updates=True)

        # Поллинг
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            arSession=arSession,
        )
    finally:
        # Корректные остановки
        try:
            if BOT_SCHEDULER.running:
                BOT_SCHEDULER.shutdown(wait=False)
        except Exception:
            pass

        await arSession.close()
        await bot.session.close()


if __name__ == "__main__":
    # Генерация БД и таблиц перед стартом
    create_dbx()

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        bot_logger.warning("Bot was stopped")
    finally:
        # Красивый клир консоли
        if sys.platform.startswith("win"):
            os.system("cls")
        else:
            os.system("clear")
