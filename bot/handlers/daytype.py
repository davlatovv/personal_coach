from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.database.queries import set_day_type
from bot.keyboards.inline import day_type_keyboard
from bot.utils.emoji import DAY_TYPE_LABEL, DAY_TYPE_EMOJI

router = Router()


@router.message(Command("daytype"))
async def cmd_daytype(message: Message) -> None:
    await message.answer(
        "Выбери тип сегодняшнего дня:",
        reply_markup=day_type_keyboard(),
    )


@router.callback_query(F.data.startswith("daytype:"))
async def cb_daytype(callback: CallbackQuery) -> None:
    day_type = callback.data.split(":")[1]
    today_str = date.today().isoformat()

    await set_day_type(today_str, day_type)

    # Reschedule jobs
    from bot.scheduler.scheduler import reschedule_today
    await reschedule_today(callback.bot)

    label = DAY_TYPE_LABEL.get(day_type, day_type)
    emoji = DAY_TYPE_EMOJI.get(day_type, "")

    await callback.message.edit_text(
        f"✅ Тип дня изменён на: {emoji} {label}\n"
        "Расписание уведомлений обновлено."
    )
    await callback.answer()
