from typing import List, Dict, Any, Optional
from datetime import date, datetime
import aiosqlite

from bot.database.db import get_db


# ── Users ─────────────────────────────────────────────────────────────────────

async def upsert_user(user_id: int, username: Optional[str]) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username
            """,
            (user_id, username),
        )
        await db.commit()


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


# ── Day types ─────────────────────────────────────────────────────────────────

async def set_day_type(target_date: str, day_type: str) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO day_types (date, day_type)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET day_type=excluded.day_type
            """,
            (target_date, day_type),
        )
        await db.commit()


async def get_day_type(target_date: str) -> Optional[str]:
    async with get_db() as db:
        async with db.execute(
            "SELECT day_type FROM day_types WHERE date = ?", (target_date,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["day_type"] if row else None


# ── Schedule items ────────────────────────────────────────────────────────────

async def get_schedule_items(user_id: int, day_type: str) -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT * FROM schedule_items
            WHERE user_id = ? AND day_type = ? AND is_active = 1
            ORDER BY time ASC
            """,
            (user_id, day_type),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_all_schedule_items(user_id: int, day_type: str) -> List[Dict[str, Any]]:
    """Get all items including inactive ones (for /edit)."""
    async with get_db() as db:
        async with db.execute(
            """
            SELECT * FROM schedule_items
            WHERE user_id = ? AND day_type = ?
            ORDER BY time ASC
            """,
            (user_id, day_type),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_schedule_item(item_id: int) -> Optional[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM schedule_items WHERE id = ?", (item_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def toggle_schedule_item(item_id: int, is_active: bool) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE schedule_items SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, item_id),
        )
        await db.commit()


async def update_schedule_item_time(item_id: int, new_time: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE schedule_items SET time = ? WHERE id = ?",
            (new_time, item_id),
        )
        await db.commit()


async def update_schedule_item_description(item_id: int, new_description: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE schedule_items SET description = ? WHERE id = ?",
            (new_description, item_id),
        )
        await db.commit()


async def delete_custom_schedule_item(item_id: int) -> None:
    async with get_db() as db:
        await db.execute(
            "DELETE FROM schedule_items WHERE id = ? AND is_custom = 1",
            (item_id,),
        )
        await db.commit()


async def insert_schedule_item(
    user_id: int,
    day_type: str,
    time: str,
    category: str,
    title: str,
    description: str,
    is_custom: int = 1,
) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO schedule_items
                (user_id, day_type, time, category, title, description, is_active, is_custom)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (user_id, day_type, time, category, title, description, is_custom),
        )
        await db.commit()
        return cursor.lastrowid


async def check_seed_done(user_id: int) -> bool:
    async with get_db() as db:
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM schedule_items WHERE user_id = ? AND is_custom = 0",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] > 0


# ── Notifications log ─────────────────────────────────────────────────────────

async def log_notification(
    user_id: int,
    schedule_item_id: int,
    target_date: str,
    day_type: str,
    category: str,
) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO notifications_log
                (user_id, schedule_item_id, date, day_type, category, status)
            VALUES (?, ?, ?, ?, ?, 'sent')
            """,
            (user_id, schedule_item_id, target_date, day_type, category),
        )
        await db.commit()
        return cursor.lastrowid


async def update_notification_status(log_id: int, status: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE notifications_log SET status = ? WHERE id = ?",
            (status, log_id),
        )
        await db.commit()


async def get_completion_stats(user_id: int, week_start: str, week_end: str) -> Dict[str, Any]:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done_count,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_count,
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as pending_count
            FROM notifications_log
            WHERE user_id = ? AND date >= ? AND date <= ?
            """,
            (user_id, week_start, week_end),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else {"total": 0, "done_count": 0, "skipped_count": 0, "pending_count": 0}


async def get_category_completion_stats(user_id: int, week_start: str, week_end: str) -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT
                category,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as done_count,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_count
            FROM notifications_log
            WHERE user_id = ? AND date >= ? AND date <= ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (user_id, week_start, week_end),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_week_stats(user_id: int, week_start: str, week_end: str) -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT date, day_type, category, COUNT(*) as count
            FROM notifications_log
            WHERE user_id = ? AND date >= ? AND date <= ?
            GROUP BY date, category
            ORDER BY date ASC
            """,
            (user_id, week_start, week_end),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_week_day_counts(user_id: int, week_start: str, week_end: str) -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT date, day_type, COUNT(*) as count
            FROM notifications_log
            WHERE user_id = ? AND date >= ? AND date <= ?
            GROUP BY date
            ORDER BY date ASC
            """,
            (user_id, week_start, week_end),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_category_counts(user_id: int, week_start: str, week_end: str) -> List[Dict[str, Any]]:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT category, COUNT(*) as count
            FROM notifications_log
            WHERE user_id = ? AND date >= ? AND date <= ?
            GROUP BY category
            ORDER BY count DESC
            """,
            (user_id, week_start, week_end),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
