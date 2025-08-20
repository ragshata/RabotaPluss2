# -*- coding: utf-8 -*-
from aiogram import BaseMiddleware
from aiogram.types import User

from tgbot.database.db_users import Userx
from tgbot.utils.const_functions import clear_html


class ExistsUserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        u: User | None = data.get("event_from_user")
        if not u or u.is_bot:
            return await handler(event, data)

        user_id = u.id
        user_login = (u.username or "unknown").lower()
        user_name = clear_html(u.full_name) or "unknown"

        # Предпочтительно: безопасное создание без затирания профиля
        try:
            # Если реализовал Userx.ensure (см. мой предыдущий ответ) — используем его
            Userx.ensure(user_id=user_id, user_login=user_login, user_name=user_name)
        except AttributeError:
            # Фолбэк: эмулируем ensure через get/add/update
            existing = Userx.get(user_id=user_id)
            if existing is None:
                # Создаём запись с безопасными дефолтами и НЕ трогаем профиль потом
                Userx.add(
                    user_id=user_id,
                    user_login=user_login,
                    user_name=user_name,
                    user_rlname="0",
                    user_surname="0",
                    user_number=0,
                    experience_years=0,
                    city="",
                    specializations="",
                    work_photos="[]",
                )
            else:
                # Обновляем только login/name при изменении
                updates = {}
                if user_name != existing.user_name:
                    updates["user_name"] = user_name
                if user_login != existing.user_login:
                    updates["user_login"] = user_login
                if updates:
                    Userx.update(user_id, **updates)

        return await handler(event, data)
