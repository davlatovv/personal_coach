from datetime import date
from typing import Optional

import pytz

from bot.config import settings
from bot.database.queries import get_day_type
from bot.utils.emoji import DEFAULT_WEEK_PATTERN


def get_today_local() -> date:
    tz = pytz.timezone(settings.timezone)
    return date.today()  # APScheduler already uses TZ-aware jobs, but date.today() is fine locally


async def resolve_day_type(target_date: Optional[date] = None) -> str:
    """
    Resolve day type for a given date.
    Priority: explicit override in day_types table > default week pattern.
    """
    if target_date is None:
        target_date = date.today()

    date_str = target_date.isoformat()
    override = await get_day_type(date_str)
    if override:
        return override

    weekday = target_date.weekday()
    return DEFAULT_WEEK_PATTERN[weekday]
