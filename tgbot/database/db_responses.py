# -*- coding: utf-8 -*-
import sqlite3
from typing import Optional

from pydantic import BaseModel

from tgbot.data.config import PATH_DATABASE
from tgbot.database.db_helper import dict_factory, update_format_where, update_format
from tgbot.utils.const_functions import get_unix, ded, clear_html, gen_id


# Модель таблицы
class ResponseModel(BaseModel):
    increment: int
    response_id: int  # уникальный ID отклика (gen_id)
    worker_id: int  # кто откликнулся (user_id исполнителя)
    position_unix: int  # какой заказ (у тебя это идентификатор позиции)
    comment: str  # комментарий исполнителя
    offer: str  # предложение (число в строке или "договорная")
    status: int  # 0 - ожидание, 1 - одобрен, 2 - отклонён
    response_unix: int  # время создания (unix)


# Работа с откликами
class Responsesx:
    storage_name = "storage_responses"

    # Добавление записи
    @staticmethod
    def add(
        worker_id: int,
        position_unix: int,
        comment: str,
        offer: int | str,
        status: int = 0,
    ) -> int:
        response_id = gen_id()
        response_unix = get_unix()
        comment = clear_html((comment or "").strip())
        offer_text = str(offer) if offer is not None else "договорная"

        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            con.execute(
                ded(
                    f"""
                    INSERT INTO {Responsesx.storage_name} (
                        response_id,
                        worker_id,
                        position_unix,
                        comment,
                        offer,
                        status,
                        response_unix
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                ),
                [
                    response_id,
                    worker_id,
                    position_unix,
                    comment,
                    offer_text,
                    status,
                    response_unix,
                ],
            )

        return response_id

    # Получение записи (одной)
    @staticmethod
    def get(**kwargs) -> Optional[ResponseModel]:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Responsesx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)
            response = con.execute(sql, parameters).fetchone()
            if response is not None:
                response = ResponseModel(**response)
            return response

    # Получение записей (множество)
    @staticmethod
    def gets(**kwargs) -> list[ResponseModel]:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Responsesx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)
            rows = con.execute(sql, parameters).fetchall()
            if len(rows) >= 1:
                rows = [ResponseModel(**r) for r in rows]
            return rows

    # Получение всех записей
    @staticmethod
    def get_all() -> list[ResponseModel]:
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"SELECT * FROM {Responsesx.storage_name}"
            rows = con.execute(sql).fetchall()
            if len(rows) >= 1:
                rows = [ResponseModel(**r) for r in rows]
            return rows

    # Обновление записи по response_id
    @staticmethod
    def update(response_id: int, **kwargs):
        if not kwargs:
            return
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"UPDATE {Responsesx.storage_name} SET"
            sql, parameters = update_format(sql, kwargs)
            parameters.append(response_id)
            con.execute(sql + " WHERE response_id = ?", parameters)

    # Удаление записей по условиям
    @staticmethod
    def delete(**kwargs):
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            sql = f"DELETE FROM {Responsesx.storage_name}"
            sql, parameters = update_format_where(sql, kwargs)
            con.execute(sql, parameters)

    # Полная очистка
    @staticmethod
    def clear():
        with sqlite3.connect(PATH_DATABASE) as con:
            con.row_factory = dict_factory
            con.execute(f"DELETE FROM {Responsesx.storage_name}")

    # Утилита: получить отклик по (worker_id, position_unix)
    @staticmethod
    def get_by_worker_and_punix(
        worker_id: int, position_unix: int
    ) -> Optional[ResponseModel]:
        return Responsesx.get(worker_id=worker_id, position_unix=position_unix)
