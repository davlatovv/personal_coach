from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite
from bot.config import settings

DB_PATH = settings.db_path


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db


async def create_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                timezone TEXT DEFAULT 'Asia/Tashkent',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS day_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE,
                day_type TEXT
            );

            CREATE TABLE IF NOT EXISTS schedule_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                day_type TEXT,
                time TEXT,
                category TEXT,
                title TEXT,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                is_custom INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS notifications_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                schedule_item_id INTEGER,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                date TEXT,
                day_type TEXT,
                category TEXT,
                status TEXT DEFAULT 'sent',
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS custom_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                description TEXT,
                time TEXT,
                date TEXT,
                day_type TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """)
        await db.commit()

    # Migrate existing DB: add status column if missing
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("PRAGMA table_info(notifications_log)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        if "status" not in columns:
            await db.execute(
                "ALTER TABLE notifications_log ADD COLUMN status TEXT DEFAULT 'sent'"
            )
            await db.commit()
