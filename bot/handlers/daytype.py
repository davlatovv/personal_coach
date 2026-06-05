from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.database.queries import set_day_type
from bot.utils.emoji import DAY_TYPE_LABEL, DAY_TYPE_EMOJI

router = Router()

DAY_TYPE_CODES = ("boxing", "boxing_fri", "gym", "weekend_sat", "weekend_sun")


def _day_type_help() -> str:
    lines = ["Используй /daytype <type>.", "", "Доступные типы:"]
    for code in DAY_TYPE_CODES:
        emoji = DAY_TYPE_EMOJI.get(code, "")
        label = DAY_TYPE_LABEL.get(code, code)
        lines.append(f"{code} — {emoji} {label}")
    return "\n".join(lines)


@router.message(Command("daytype"))
async def cmd_daytype(message: Message) -> None:
    args = message.text.strip().split(maxsplit=1)
    if len(args) == 1:
        await message.answer(_day_type_help())
        return

    day_type = args[1].strip().lower()
    if day_type not in DAY_TYPE_CODES:
        await message.answer("❗ Неизвестный тип дня.\n\n" + _day_type_help())
        return

    today_str = date.today().isoformat()

    await set_day_type(today_str, day_type)

    # Reschedule jobs
    from bot.scheduler.scheduler import reschedule_today
    await reschedule_today(message.bot)

    label = DAY_TYPE_LABEL.get(day_type, day_type)
    emoji = DAY_TYPE_EMOJI.get(day_type, "")

    await message.answer(
        f"✅ Тип дня изменён на: {emoji} {label}\n"
        "Расписание уведомлений обновлено."
    )
