# - *- coding: utf- 8 - *-
import sqlite3
from pydantic import BaseModel

from tgbot.data.config import PATH_DATABASE
from tgbot.database.db_helper import dict_factory, update_format_where, update_format
from tgbot.utils.const_functions import ded, get_unix


# Модель таблицы
class CategoryModel(BaseModel):
    increment: int
    category_id: int
    category_name: str
    category_unix: int


# Работа с категориями
class Categoryx:
    storage_name = "storage_category"

    # 🔹 Дефолтные категории (будут добавлены автоматически, если таблица пуста)
    DEFAULT_CATEGORIES = [
        "Отделочные работы",
        "Плиточные работы",
        "Стяжка пола",
        "Бетонные полы",
        "Бетонные работы",
        "Монолитные работы",
        "Штукатурка стен",
        "Шпаклевка стен",
        "Малярные работы",
        "Покраска",
        "Обои",
        "Электрика",
        "Сантехника",
        "Кровельные работы",
        "Фасадные работы",
        "Фундамент",
        "Демонтаж",
        "Сварка",
        "Окна",
        "Установка дверей",
        "Полы",
        "Каркас",
        "Вентиляция",
        "Отопление",
        "Благоустройство",
        "Проектирование",
        "Смета",
        "Утепление",
        "Перегородки",
        "Вывоз мусора",
        "Подсобные работы",
        "Кладка",
        "Дом с нуля",
        "Дизайн проект",
        "Декор",
        "Халтура",
    ]

    # Добавление записи
    @staticmethod
    def add(category_id: int, category_name: str):
        category_unix = get_unix()
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            con.execute(
                ded(
                    f"""
                    INSERT INTO {Categoryx.storage_name} (
                        category_id,
                        category_name,
                        category_unix
                    ) VALUES (?, ?, ?)
                """
                ),
                [category_id, category_name, category_unix],
            )

    # ✅ Сидинг дефолтных категорий (без дублей по названию)
    @staticmethod
    def ensure_defaults():
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            # что уже есть
            existing = con.execute(
                f"SELECT category_name FROM {Categoryx.storage_name}"
            ).fetchall()
            have = {
                (row.get("category_name") or "").strip().lower()
                for row in (existing or [])
            }

            to_add = []
            base_id = get_unix()
            for idx, name in enumerate(Categoryx.DEFAULT_CATEGORIES):
                name_clean = (name or "").strip()
                if not name_clean:
                    continue
                if name_clean.lower() in have:
                    continue
                cat_id = base_id + idx  # гарантируем уникальность id
                cat_unix = base_id + idx
                to_add.append((cat_id, name_clean, cat_unix))

            if to_add:
                con.executemany(
                    f"""
                    INSERT INTO {Categoryx.storage_name} (
                        category_id, category_name, category_unix
                    ) VALUES (?, ?, ?)
                    """,
                    to_add,
                )

    # Получение записи
    @staticmethod
    def get(**kwargs) -> CategoryModel:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Categoryx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)
            response = con.execute(sql, parameters).fetchone()
            if response is not None:
                response = CategoryModel(**response)
            return response

    # Получение записей
    @staticmethod
    def gets(**kwargs) -> list[CategoryModel]:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Categoryx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)
            rows = con.execute(sql, parameters).fetchall()
            if rows:
                return [CategoryModel(**r) for r in rows]
            return []

    # Получение всех записей (с автосидингом при пустой таблице)
    @staticmethod
    def get_all() -> list[CategoryModel]:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Categoryx.storage_name}"
            rows = con.execute(sql).fetchall()

            # если пусто — досыпаем дефолт и читаем снова
            if not rows:
                Categoryx.ensure_defaults()
                rows = con.execute(sql).fetchall()

            if rows:
                return [CategoryModel(**r) for r in rows]
            return []

    # Редактирование записи
    @staticmethod
    def update(category_id, **kwargs):
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"UPDATE {Categoryx.storage_name} SET"
            sql, parameters = update_format(sql, kwargs)
            parameters.append(category_id)
            con.execute(sql + "WHERE category_id = ?", parameters)

    # Удаление записи
    @staticmethod
    def delete(**kwargs):
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"DELETE FROM {Categoryx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)
            con.execute(sql, parameters)

    # Очистка всех записей
    @staticmethod
    def clear():
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            con.execute(f"DELETE FROM {Categoryx.storage_name}")
