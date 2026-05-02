import asyncio
import logging
from datetime import date, datetime
from typing import Optional

import aioschedule as schedule
import pytz
from aiogram import Bot

from bot.config import settings
from bot.database.queries import get_schedule_items
from bot.scheduler.day_resolver import resolve_day_type
from bot.scheduler.jobs import send_notification

logger = logging.getLogger(__name__)
TZ = pytz.timezone(settings.timezone)

_runner_task: Optional[asyncio.Task] = None
_runner_stop = asyncio.Event()
_scheduler_lock = asyncio.Lock()


def _today_in_tz() -> date:
    return datetime.now(TZ).date()


async def _build_jobs_for_date(bot: Bot, target_date: date) -> None:
    """Clear all jobs and register daily jobs for target_date and midnight rebuild."""
    schedule.clear()

    # Rebuild schedule every day after midnight for the new day type.
    schedule.every().day.at("00:00").do(_midnight_rebuild_job, bot)

    day_type = await resolve_day_type(target_date)
    items = await get_schedule_items(settings.admin_id, day_type)

    for item in items:
        schedule.every().day.at(item["time"]).do(_send_notification_job, bot, item)

    logger.info(
        "Scheduler rebuilt for %s (%s): %s jobs",
        target_date.isoformat(),
        day_type,
        len(items),
    )


async def _midnight_rebuild_job(bot: Bot) -> None:
    async with _scheduler_lock:
        await _build_jobs_for_date(bot, _today_in_tz())


async def _send_notification_job(bot: Bot, item: dict) -> None:
    await send_notification(bot, item, _today_in_tz())


async def setup_daily_jobs(bot: Bot, target_date: Optional[date] = None) -> None:
    """Public API: rebuild all daily jobs for target_date (default: today)."""
    if target_date is None:
        target_date = _today_in_tz()

    async with _scheduler_lock:
        await _build_jobs_for_date(bot, target_date)


async def _run_scheduler_loop() -> None:
    while not _runner_stop.is_set():
        try:
            await schedule.run_pending()
        except Exception as e:
            logger.exception("[SCHEDULER LOOP ERROR] %s", e)
        await asyncio.sleep(1)


async def start_scheduler(bot: Bot) -> None:
    global _runner_task
    if _runner_task and not _runner_task.done():
        return

    _runner_stop.clear()
    await setup_daily_jobs(bot)
    _runner_task = asyncio.create_task(_run_scheduler_loop())
    logger.info("Scheduler started")


async def stop_scheduler() -> None:
    global _runner_task
    _runner_stop.set()
    if _runner_task:
        _runner_task.cancel()
        try:
            await _runner_task
        except asyncio.CancelledError:
            pass
        _runner_task = None
    schedule.clear()
    logger.info("Scheduler stopped")


async def reschedule_today(bot: Bot) -> None:
    """Force re-schedule jobs for today (called after /daytype or schedule changes)."""
    await setup_daily_jobs(bot, _today_in_tz())
