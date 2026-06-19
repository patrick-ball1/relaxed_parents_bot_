"""
Аналитика событий.
Пишет в SQLite и синхронно обновляет Excel-файл.
"""

import json
from typing import Optional
from database import Database
from excel_report import append_event_to_excel, refresh_excel_user

_db = Database()


async def log_event(user_id: int, event: str, data: Optional[dict] = None):
    """Записывает событие в БД и обновляет Excel."""
    await _db.log_event(user_id, event, data)

    name = await _db.get_user_name(user_id)
    data_str = json.dumps(data or {}, ensure_ascii=False) if data else ""

    # Дописываем строку события в лист «События»
    await append_event_to_excel(user_id, name, event, data_str)

    # Обновляем строку пользователя в листе «Пользователи»
    await refresh_excel_user(user_id)
