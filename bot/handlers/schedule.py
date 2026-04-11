from datetime import date, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.database.queries import get_schedule_items
from bot.scheduler.day_resolver import resolve_day_type
from bot.utils.formatters import format_schedule_list, format_week_schedule
from bot.utils.emoji import DEFAULT_WEEK_PATTERN

router = Router()


async def _today_text() -> str:
    today = date.today()
    day_type = await resolve_day_type(today)
    items = await get_schedule_items(settings.admin_id, day_type)
    return format_schedule_list(items, day_type, today)


async def _tomorrow_text() -> str:
    tomorrow = date.today() + timedelta(days=1)
    day_type = await resolve_day_type(tomorrow)
    items = await get_schedule_items(settings.admin_id, day_type)
    return format_schedule_list(items, day_type, tomorrow)


@router.message(Command("today"))
@router.message(F.text == "📅 Сегодня")
async def cmd_today(message: Message) -> None:
    text = await _today_text()
    await message.answer(text)


@router.message(Command("tomorrow"))
async def cmd_tomorrow(message: Message) -> None:
    text = await _tomorrow_text()
    await message.answer(text)


@router.message(Command("week"))
async def cmd_week(message: Message) -> None:
    today = date.today()
    # Start from Monday of current week
    start_of_week = today - timedelta(days=today.weekday())

    week_data = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_type = await resolve_day_type(day)
        items = await get_schedule_items(settings.admin_id, day_type)
        week_data.append({
            "weekday": day.weekday(),
            "day_type": day_type,
            "date": day,
            "items": items,
        })

    text = format_week_schedule(week_data)
    # Split if too long
    if len(text) > 4096:
        parts = []
        current = ""
        for line in text.split("\n"):
            if len(current) + len(line) + 1 > 4000:
                parts.append(current)
                current = line
            else:
                current += ("\n" if current else "") + line
        if current:
            parts.append(current)
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(text)
