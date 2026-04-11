from datetime import date, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.database.queries import get_week_day_counts, get_category_counts
from bot.scheduler.day_resolver import resolve_day_type
from bot.utils.formatters import format_stats
from bot.utils.emoji import DAY_TYPE_EMOJI, DAY_TYPE_LABEL, WEEKDAY_NAMES

router = Router()


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message) -> None:
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    week_start_str = start_of_week.isoformat()
    week_end_str = end_of_week.isoformat()

    day_counts = await get_week_day_counts(
        settings.admin_id, week_start_str, week_end_str
    )
    counts_by_date = {row["date"]: row for row in day_counts}

    cat_counts = await get_category_counts(
        settings.admin_id, week_start_str, week_end_str
    )
    by_category = {row["category"]: row["count"] for row in cat_counts}

    days_info = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_str = day.isoformat()
        day_type = await resolve_day_type(day)

        if day_str in counts_by_date:
            count = counts_by_date[day_str]["count"]
            status = "today" if day == today else "done"
        elif day < today:
            count = 0
            status = "done"
        elif day == today:
            count = 0
            status = "today"
        else:
            count = 0
            status = "future"

        days_info.append({
            "weekday": i,
            "day_type": day_type,
            "count": count,
            "status": status,
        })

    # Calculate streak: consecutive days with at least 1 notification, going backwards from today
    streak = 0
    check_day = today
    while True:
        check_str = check_day.isoformat()
        if check_str in counts_by_date and counts_by_date[check_str]["count"] > 0:
            streak += 1
            check_day -= timedelta(days=1)
        else:
            break

    stats_data = {
        "days": days_info,
        "by_category": by_category,
        "streak": streak,
    }

    text = format_stats(stats_data)
    await message.answer(text)
