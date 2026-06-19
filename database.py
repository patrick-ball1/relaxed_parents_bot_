"""
Модуль работы с базой данных.
Хранит состояние пользователей: имя, сегмент, дата старта, стадия воронки.
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    name        TEXT,
    segment     TEXT,
    stage       TEXT DEFAULT 'new',
    start_time  TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS analytics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    event       TEXT,
    data        TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""


class Database:
    async def init(self):
        async with engine.begin() as conn:
            for stmt in CREATE_TABLE_SQL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    await conn.execute(text(stmt))

    async def ensure_user(self, user_id: int):
        async with SessionLocal() as s:
            await s.execute(
                text("INSERT OR IGNORE INTO users (user_id) VALUES (:uid)"),
                {"uid": user_id},
            )
            await s.commit()

    async def set_user_name(self, user_id: int, name: str):
        async with SessionLocal() as s:
            await s.execute(
                text("UPDATE users SET name=:name WHERE user_id=:uid"),
                {"name": name, "uid": user_id},
            )
            await s.commit()

    async def get_user_name(self, user_id: int) -> str:
        async with SessionLocal() as s:
            row = await s.execute(
                text("SELECT name FROM users WHERE user_id=:uid"), {"uid": user_id}
            )
            result = row.fetchone()
            return result[0] if result and result[0] else "дорогая мама"

    async def set_user_segment(self, user_id: int, segment: str):
        async with SessionLocal() as s:
            await s.execute(
                text("UPDATE users SET segment=:seg WHERE user_id=:uid"),
                {"seg": segment, "uid": user_id},
            )
            await s.commit()

    async def set_start_time(self, user_id: int, dt: datetime):
        async with SessionLocal() as s:
            await s.execute(
                text("UPDATE users SET start_time=:st WHERE user_id=:uid"),
                {"st": dt.isoformat(), "uid": user_id},
            )
            await s.commit()

    async def get_start_time(self, user_id: int) -> datetime:
        async with SessionLocal() as s:
            row = await s.execute(
                text("SELECT start_time FROM users WHERE user_id=:uid"), {"uid": user_id}
            )
            result = row.fetchone()
            if result and result[0]:
                return datetime.fromisoformat(result[0])
            return datetime.utcnow()

    async def set_user_stage(self, user_id: int, stage: str):
        async with SessionLocal() as s:
            await s.execute(
                text("UPDATE users SET stage=:stage WHERE user_id=:uid"),
                {"stage": stage, "uid": user_id},
            )
            await s.commit()

    async def log_event(self, user_id: int, event: str, data: Optional[dict] = None):
        async with SessionLocal() as s:
            await s.execute(
                text(
                    "INSERT INTO analytics (user_id, event, data) VALUES (:uid, :ev, :d)"
                ),
                {"uid": user_id, "ev": event, "d": json.dumps(data or {}, ensure_ascii=False)},
            )
            await s.commit()
