import asyncio
import logging
from datetime import date, datetime
from typing import Optional

import pytz
from aiogram import Bot

from bot.config import settings
from bot.database.queries import get_active_reminders_for_date, get_schedule_items
from bot.scheduler.day_resolver import resolve_day_type
from bot.scheduler.jobs import send_notification, send_reminder_notification

logger = logging.getLogger(__name__)
TZ = pytz.timezone(settings.timezone)

_runner_task: Optional[asyncio.Task] = None
_runner_stop = asyncio.Event()
_scheduler_lock = asyncio.Lock()

# List of (time_str "HH:MM", async callable) registered for today.
_jobs: list[tuple[str, object]] = []
_jobs_fired: set[str] = set()  # keys already fired today: "HH:MM|job_index"


def _today_in_tz() -> date:
    return datetime.now(TZ).date()


def _now_hhmm() -> str:
    return datetime.now(TZ).strftime("%H:%M")


async def _build_jobs_for_date(bot: Bot, target_date: date) -> None:
    global _jobs, _jobs_fired
    _jobs = []
    _jobs_fired = set()

    day_type = await resolve_day_type(target_date)
    items = await get_schedule_items(settings.admin_id, day_type)
    reminders = await get_active_reminders_for_date(
        settings.admin_id,
        target_date.isoformat(),
    )

    for item in items:
        time_str = item["time"][:5]  # "HH:MM"
        _jobs.append(
            (time_str, lambda b=bot, i=item: send_notification(b, i, _today_in_tz()))
        )

    for reminder in reminders:
        time_str = reminder["time"][:5]
        _jobs.append(
            (
                time_str,
                lambda b=bot, r=reminder: send_reminder_notification(
                    b,
                    r,
                    _today_in_tz(),
                ),
            )
        )

    logger.info(
        "Scheduler rebuilt for %s (%s): %s schedule jobs, %s reminder jobs",
        target_date.isoformat(),
        day_type,
        len(items),
        len(reminders),
    )


async def setup_daily_jobs(bot: Bot, target_date: Optional[date] = None) -> None:
    if target_date is None:
        target_date = _today_in_tz()
    async with _scheduler_lock:
        await _build_jobs_for_date(bot, target_date)


async def _run_scheduler_loop(bot: Bot) -> None:
    last_rebuild_date: Optional[date] = None

    while not _runner_stop.is_set():
        now = datetime.now(TZ)
        today = now.date()

        # Rebuild at midnight for the new day.
        if last_rebuild_date != today:
            async with _scheduler_lock:
                await _build_jobs_for_date(bot, today)
            last_rebuild_date = today

        current_hhmm = now.strftime("%H:%M")

        async with _scheduler_lock:
            for idx, (time_str, coro_factory) in enumerate(_jobs):
                key = f"{time_str}|{idx}"
                if time_str == current_hhmm and key not in _jobs_fired:
                    _jobs_fired.add(key)
                    asyncio.create_task(coro_factory())

        await asyncio.sleep(1)


async def start_scheduler(bot: Bot) -> None:
    global _runner_task
    if _runner_task and not _runner_task.done():
        return

    _runner_stop.clear()
    await setup_daily_jobs(bot)
    _runner_task = asyncio.create_task(_run_scheduler_loop(bot))
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
    logger.info("Scheduler stopped")


async def reschedule_today(bot: Bot) -> None:
    await setup_daily_jobs(bot, _today_in_tz())
