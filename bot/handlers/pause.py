from datetime import datetime, timedelta

import pytz
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.scheduler.jobs import set_pause, clear_pause, is_paused

router = Router()
TZ = pytz.timezone(settings.timezone)


@router.message(Command("pause"))
async def cmd_pause(message: Message) -> None:
    args = message.text.strip().split()

    if len(args) > 1:
        try:
            hours = float(args[1])
            resume_at = datetime.now(TZ) + timedelta(hours=hours)
            set_pause(resume_at=resume_at)
            await message.answer(
                f"⏸ Уведомления поставлены на паузу на {hours:.0f} ч.\n"
                f"Возобновятся в {resume_at.strftime('%H:%M')}.\n"
                f"Для досрочного снятия используй /resume"
            )
        except ValueError:
            await message.answer("❗ Укажи число часов: /pause 2")
    else:
        # Pause until end of day
        now = datetime.now(TZ)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)
        set_pause(resume_at=end_of_day)
        await message.answer(
            "⏸ Уведомления поставлены на паузу до конца дня.\n"
            "Для досрочного снятия используй /resume"
        )


@router.message(Command("resume"))
async def cmd_resume(message: Message) -> None:
    if not is_paused():
        await message.answer("▶️ Уведомления и так активны.")
        return

    clear_pause()
    await message.answer("▶️ Уведомления возобновлены!")
