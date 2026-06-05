from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings
from bot.database.queries import insert_reminder
from bot.states.add_event import ReminderStates
from bot.utils.validators import normalize_time, validate_time

router = Router()


def _parse_date(date_str: str):
    return datetime.strptime(date_str, "%Y-%m-%d").date()


@router.message(Command("reminder"))
async def cmd_reminder(message: Message, state: FSMContext) -> None:
    await state.set_state(ReminderStates.waiting_title)
    await message.answer("🔔 Введи название напоминалки:")


@router.message(ReminderStates.waiting_title, Command("cancel"))
@router.message(ReminderStates.waiting_description, Command("cancel"))
@router.message(ReminderStates.waiting_time, Command("cancel"))
@router.message(ReminderStates.waiting_start_date, Command("cancel"))
@router.message(ReminderStates.waiting_end_date, Command("cancel"))
@router.message(ReminderStates.confirm, Command("cancel"))
async def fsm_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Добавление напоминалки отменено.")


@router.message(ReminderStates.waiting_title)
async def fsm_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title:
        await message.answer("❗ Название не может быть пустым. Введи название:")
        return

    await state.update_data(title=title)
    await state.set_state(ReminderStates.waiting_description)
    await message.answer(
        "📄 Введи описание или отправь /skip, чтобы пропустить:",
    )


@router.message(ReminderStates.waiting_description, Command("skip"))
async def fsm_skip_desc(message: Message, state: FSMContext) -> None:
    await state.update_data(description="")
    await state.set_state(ReminderStates.waiting_time)
    await message.answer("⏰ Введи время в формате HH:MM (например 14:30):")


@router.message(ReminderStates.waiting_description)
async def fsm_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(ReminderStates.waiting_time)
    await message.answer("⏰ Введи время в формате HH:MM (например 14:30):")


@router.message(ReminderStates.waiting_time)
async def fsm_time(message: Message, state: FSMContext) -> None:
    normalized = normalize_time(message.text.strip())

    if not validate_time(normalized):
        await message.answer(
            "❗ Неверный формат. Введи время в формате HH:MM (например 14:30):"
        )
        return

    await state.update_data(time=normalized)
    await state.set_state(ReminderStates.waiting_start_date)
    await message.answer("📆 Введи дату начала в формате YYYY-MM-DD:")


@router.message(ReminderStates.waiting_start_date)
async def fsm_start_date(message: Message, state: FSMContext) -> None:
    date_str = message.text.strip()
    try:
        _parse_date(date_str)
    except ValueError:
        await message.answer("❗ Неверный формат. Введи дату начала как YYYY-MM-DD:")
        return

    await state.update_data(start_date=date_str)
    await state.set_state(ReminderStates.waiting_end_date)
    await message.answer("📆 Введи дату окончания в формате YYYY-MM-DD:")


@router.message(ReminderStates.waiting_end_date)
async def fsm_end_date(message: Message, state: FSMContext) -> None:
    end_date_str = message.text.strip()
    try:
        end_date = _parse_date(end_date_str)
    except ValueError:
        await message.answer("❗ Неверный формат. Введи дату окончания как YYYY-MM-DD:")
        return

    data = await state.get_data()
    start_date = _parse_date(data["start_date"])
    if end_date < start_date:
        await message.answer(
            "❗ Дата окончания не может быть раньше даты начала. Введи дату окончания:"
        )
        return

    await state.update_data(end_date=end_date_str)
    await _show_confirm(message, state)


async def _show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    text = (
        "<b>Превью напоминалки:</b>\n\n"
        f"🔔 <b>{data['title']}</b>\n"
        f"⏰ {data['time']}\n"
        f"📆 {data['start_date']} — {data['end_date']}\n"
    )
    if data.get("description"):
        text += f"\n📝 {data['description']}"

    await state.set_state(ReminderStates.confirm)
    await message.answer(
        text + "\n\nОтправь /confirm, чтобы сохранить, или /cancel, чтобы отменить.",
        parse_mode="HTML",
    )


@router.message(ReminderStates.confirm, Command("confirm"))
async def fsm_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await insert_reminder(
        user_id=settings.admin_id,
        title=data["title"],
        description=data.get("description", ""),
        time=data["time"],
        start_date=data["start_date"],
        end_date=data["end_date"],
    )
    await state.clear()

    from bot.scheduler.scheduler import reschedule_today

    await reschedule_today(message.bot)

    await message.answer("✅ Напоминалка добавлена!")


@router.message(ReminderStates.confirm)
async def fsm_confirm_unknown(message: Message) -> None:
    await message.answer("Отправь /confirm, чтобы сохранить, или /cancel, чтобы отменить.")
