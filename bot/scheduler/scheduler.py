from datetime import date, datetime, timedelta
from typing import Optional

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from bot.config import settings
from bot.database.queries import get_schedule_items
from bot.scheduler.day_resolver import resolve_day_type
from bot.scheduler.jobs import send_notification

_scheduler: Optional[AsyncIOScheduler] = None
TZ = pytz.timezone(settings.timezone)


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=TZ)
    return _scheduler


async def setup_daily_jobs(bot: Bot, target_date: Optional[date] = None) -> None:
    """
    Schedule all notifications for target_date (default: today).
    Removes existing daily jobs before adding new ones.
    """
    scheduler = get_scheduler()
    if target_date is None:
        target_date = date.today()

    day_type = await resolve_day_type(target_date)
    items = await get_schedule_items(settings.admin_id, day_type)

    # Remove all existing "daily_notif_*" jobs
    for job in scheduler.get_jobs():
        if job.id.startswith("daily_notif_"):
            job.remove()

    # Also schedule the midnight re-scheduler
    _ensure_midnight_job(bot, scheduler)

    for item in items:
        time_parts = item["time"].split(":")
        hour, minute = int(time_parts[0]), int(time_parts[1])

        job_id = f"daily_notif_{item['id']}_{target_date.isoformat()}"

        # Build a run_date: today at that H:M in TZ
        run_dt = TZ.localize(datetime(
            target_date.year, target_date.month, target_date.day,
            hour, minute, 0
        ))

        # Skip if time already passed
        now = datetime.now(TZ)
        if run_dt <= now:
            continue

        scheduler.add_job(
            send_notification,
            trigger="date",
            run_date=run_dt,
            args=[bot, item, target_date],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=120,
        )


def _ensure_midnight_job(bot: Bot, scheduler: AsyncIOScheduler) -> None:
    """Add/replace midnight job that reloads schedule for the new day."""
    job_id = "midnight_reschedule"
    existing = scheduler.get_job(job_id)
    if existing:
        return

    async def _reschedule():
        await setup_daily_jobs(bot)

    scheduler.add_job(
        _reschedule,
        trigger=CronTrigger(hour=0, minute=0, second=5, timezone=TZ),
        id=job_id,
        replace_existing=True,
    )


async def reschedule_today(bot: Bot) -> None:
    """Force re-schedule jobs for today (called after /daytype change)."""
    await setup_daily_jobs(bot, date.today())
