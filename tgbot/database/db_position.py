# -*- coding: utf-8 -*-
import sqlite3
from typing import Union

from pydantic import BaseModel, field_validator

from tgbot.data.config import PATH_DATABASE
from tgbot.database.db_helper import dict_factory, update_format, update_format_where
from tgbot.utils.const_functions import ded, get_unix


# Модель таблицы с мягкой нормализацией входных данных
class PositionModel(BaseModel):
    increment: int = 0
    category_id: int = 0
    position_id: int = 0
    position_name: str = ""
    position_price: float = 0
    position_desc: str = ""
    position_time: float = 0
    worker_id: int = 0
    position_status: int = 0
    position_unix: int = 0

    # пустые строки/None/«—» → 0, поддержка "1 000,50"
    @field_validator("position_price", "position_time", mode="before")
    @classmethod
    def _to_float(cls, v):
        if v is None:
            return 0
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            s = v.strip()
            if s in ("", "—", "-", "–"):
                return 0
            s = s.replace(" ", "").replace(",", ".")
            try:
                return float(s)
            except Exception:
                return 0
        return v

    @field_validator(
        "increment",
        "category_id",
        "position_id",
        "worker_id",
        "position_status",
        "position_unix",
        mode="before",
    )
    @classmethod
    def _to_int(cls, v):
        if v is None:
            return 0
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        if isinstance(v, str):
            s = v.strip()
            if s in ("", "—", "-", "–"):
                return 0
            try:
                # поддержка "001", "1 000", "10.0"
                return int(float(s.replace(" ", "").replace(",", ".")))
            except Exception:
                return 0
        return v

    @field_validator("position_name", "position_desc", mode="before")
    @classmethod
    def _str_or_empty(cls, v):
        return "" if v is None else str(v)


class Positionx:
    storage_name = "storage_position"

    # Добавление записи
    @staticmethod
    def add(
        category_id: int,
        position_id: int,
        position_name: str,
        position_price: float,
        position_desc: str,
        position_time: float,
        worker_id: int,
        position_status: int,
    ):
        position_unix = get_unix()

        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            con.execute(
                ded(
                    f"""
                    INSERT INTO {Positionx.storage_name} (
                        position_id,
                        position_name,
                        position_price,
                        position_desc,
                        position_time,
                        worker_id,
                        position_status,
                        position_unix,
                        category_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                ),
                [
                    position_id,
                    position_name,
                    position_price,
                    position_desc,
                    position_time,
                    worker_id,
                    position_status,
                    position_unix,
                    category_id,
                ],
            )
        return position_unix

    # Получение записи
    @staticmethod
    def get(**kwargs) -> PositionModel:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Positionx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)

            response = con.execute(sql, parameters).fetchone()
            if response is not None:
                response = PositionModel(**response)
            return response

    # Получение worker_id
    @staticmethod
    def get_worker_id(**kwargs) -> Union[int, None]:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT worker_id FROM {Positionx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)

            response = con.execute(sql, parameters).fetchone()
            if response is not None:
                return response.get("worker_id")
            return None

    @staticmethod
    def count_by_category(category_id: int) -> int:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT COUNT(*) as count FROM {Positionx.storage_name} WHERE category_id = ?"
            result = con.execute(sql, (category_id,)).fetchone()
            return result["count"] if result else 0

    @staticmethod
    def update_unix(position_unix: int, **kwargs):
        """Обновление по position_unix."""
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"UPDATE {Positionx.storage_name} SET"
            sql, parameters = update_format(sql, kwargs)
            parameters.append(position_unix)
            con.execute(sql + " WHERE position_unix = ?", parameters)

    @staticmethod
    def gets(**kwargs) -> list[PositionModel]:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory

            sql = f"SELECT * FROM {Positionx.storage_name}"
            if "position_id" in kwargs:
                sql += " WHERE position_id = :position_id"
                parameters = {"position_id": kwargs["position_id"]}
            else:
                sql, parameters = update_format_where(sql, kwargs)

            response = con.execute(sql, parameters).fetchall()
            if len(response) >= 1:
                response = [PositionModel(**cache_object) for cache_object in response]
            return response

    @staticmethod
    def get_by_id_and_status(
        position_id: int, position_status: int
    ) -> list[PositionModel]:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"""
                SELECT * FROM {Positionx.storage_name}
                WHERE position_id = ? AND position_status = ?
            """
            response = con.execute(sql, (position_id, position_status)).fetchall()
            if len(response) >= 1:
                response = [PositionModel(**cache_object) for cache_object in response]
            return response

    # Получение всех записей
    @staticmethod
    def get_all() -> list[PositionModel]:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Positionx.storage_name}"
            response = con.execute(sql).fetchall()
            if len(response) >= 1:
                response = [PositionModel(**cache_object) for cache_object in response]
            return response

    @staticmethod
    def get_position_ids(**kwargs) -> Union[int, None]:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = lambda cursor, row: row[0]  # (position_id)
            sql = f"SELECT position_id FROM {Positionx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)
            response = con.execute(sql, parameters).fetchone()
            return response if response is not None else None

    # Редактирование записи
    @staticmethod
    def update(position_id, **kwargs):
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"UPDATE {Positionx.storage_name} SET"
            sql, parameters = update_format(sql, kwargs)
            parameters.append(position_id)
            con.execute(sql + " WHERE position_id = ?", parameters)

    @staticmethod
    def update_gpt(field_name: str, field_value, **kwargs):
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"UPDATE {Positionx.storage_name} SET"
            sql, parameters = update_format(sql, kwargs)
            parameters.append(field_value)
            con.execute(sql + f" WHERE {field_name} = ?", parameters)

    # Удаление записи
    @staticmethod
    def delete(**kwargs):
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"DELETE FROM {Positionx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)
            con.execute(sql, parameters)

    # Очистка всех записей
    @staticmethod
    def clear():
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"DELETE FROM {Positionx.storage_name}"
            con.execute(sql)
