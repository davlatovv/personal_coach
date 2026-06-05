from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings
from bot.database.queries import insert_schedule_item
from bot.states.add_event import AddEventStates
from bot.utils.emoji import CATEGORY_EMOJI, DAY_TYPE_LABEL, DAY_TYPE_EMOJI
from bot.utils.validators import validate_time, normalize_time

router = Router()

DAY_TYPE_CODES = ("boxing", "boxing_fri", "gym", "weekend_sat", "weekend_sun")
CATEGORY_CODES = ("food", "supplement", "sport", "sleep", "water", "work")


def _category_help() -> str:
    return (
        "📂 Введи категорию одним из кодов:\n"
        "food, supplement, sport, sleep, water, work"
    )


def _day_type_help() -> str:
    return (
        "📅 Введи тип дня одним из кодов:\n"
        "all, boxing, boxing_fri, gym, weekend_sat, weekend_sun, specific_date"
    )


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddEventStates.waiting_title)
    await message.answer("📝 Введи название события:")


@router.message(AddEventStates.waiting_title, Command("cancel"))
@router.message(AddEventStates.waiting_description, Command("cancel"))
@router.message(AddEventStates.waiting_time, Command("cancel"))
@router.message(AddEventStates.waiting_category, Command("cancel"))
@router.message(AddEventStates.waiting_day_type, Command("cancel"))
@router.message(AddEventStates.waiting_specific_date, Command("cancel"))
@router.message(AddEventStates.confirm, Command("cancel"))
async def fsm_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Добавление отменено.")


@router.message(AddEventStates.waiting_title)
async def fsm_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title:
        await message.answer("❗ Название не может быть пустым. Введи название:")
        return

    await state.update_data(title=title)
    await state.set_state(AddEventStates.waiting_description)
    await message.answer(
        "📄 Введи описание или отправь /skip, чтобы пропустить:",
    )


@router.message(AddEventStates.waiting_description, Command("skip"))
async def fsm_skip_desc(message: Message, state: FSMContext) -> None:
    await state.update_data(description="")
    await state.set_state(AddEventStates.waiting_time)
    await message.answer("⏰ Введи время в формате HH:MM (например 14:30):")


@router.message(AddEventStates.waiting_description)
async def fsm_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(AddEventStates.waiting_time)
    await message.answer("⏰ Введи время в формате HH:MM (например 14:30):")


@router.message(AddEventStates.waiting_time)
async def fsm_time(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    normalized = normalize_time(raw)

    if not validate_time(normalized):
        await message.answer("❗ Неверный формат. Введи время в формате HH:MM (например 14:30):")
        return

    await state.update_data(time=normalized)
    await state.set_state(AddEventStates.waiting_category)
    await message.answer(_category_help())


@router.message(AddEventStates.waiting_category)
async def fsm_category(message: Message, state: FSMContext) -> None:
    category = message.text.strip().lower()
    if category not in CATEGORY_CODES:
        await message.answer("❗ Неизвестная категория.\n" + _category_help())
        return

    await state.update_data(category=category)
    await state.set_state(AddEventStates.waiting_day_type)
    await message.answer(_day_type_help())


@router.message(AddEventStates.waiting_day_type)
async def fsm_day_type(message: Message, state: FSMContext) -> None:
    dtype = message.text.strip().lower()
    valid_codes = {"all", "specific_date", *DAY_TYPE_CODES}
    if dtype not in valid_codes:
        await message.answer("❗ Неизвестный тип дня.\n" + _day_type_help())
        return

    if dtype == "specific_date":
        await state.update_data(day_type=None)
        await state.set_state(AddEventStates.waiting_specific_date)
        await message.answer("📆 Введи дату в формате YYYY-MM-DD (например 2025-01-15):")
        return

    day_type = None if dtype == "all" else dtype
    await state.update_data(day_type=day_type, specific_date=None)
    await _show_confirm(message, state)


@router.message(AddEventStates.waiting_specific_date)
async def fsm_specific_date(message: Message, state: FSMContext) -> None:
    import re
    date_str = message.text.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        await message.answer("❗ Неверный формат. Введи дату как YYYY-MM-DD:")
        return

    await state.update_data(specific_date=date_str)
    await _show_confirm(message, state)


async def _show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    emoji = CATEGORY_EMOJI.get(data["category"], "📌")
    day_type = data.get("day_type")
    specific_date = data.get("specific_date")

    if specific_date:
        scope = f"📆 Дата: {specific_date}"
    elif day_type is None:
        scope = "📅 Все типы дней"
    else:
        label = DAY_TYPE_LABEL.get(day_type, day_type)
        dt_emoji = DAY_TYPE_EMOJI.get(day_type, "")
        scope = f"{dt_emoji} {label}"

    text = (
        f"<b>Превью события:</b>\n\n"
        f"{emoji} <b>{data['title']}</b>\n"
        f"⏰ {data['time']}\n"
        f"📂 {data['category']}\n"
        f"{scope}\n"
    )
    if data.get("description"):
        text += f"\n📝 {data['description']}"

    await state.set_state(AddEventStates.confirm)
    await message.answer(
        text + "\n\nОтправь /confirm, чтобы сохранить, или /cancel, чтобы отменить.",
        parse_mode="HTML",
    )


@router.message(AddEventStates.confirm, Command("confirm"))
async def fsm_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    day_type = data.get("day_type")
    specific_date = data.get("specific_date")

    # Determine which day types to insert into
    if specific_date:
        # For specific date: insert as custom_event-like schedule item with a marker
        # We store it as a schedule_item with day_type=None and date in description prefix
        await insert_schedule_item(
            user_id=settings.admin_id,
            day_type="specific",
            time=data["time"],
            category=data["category"],
            title=data["title"],
            description=f"[date:{specific_date}] {data.get('description', '')}".strip(),
            is_custom=1,
        )
    elif day_type is None:
        # All day types
        for dt in DAY_TYPE_CODES:
            await insert_schedule_item(
                user_id=settings.admin_id,
                day_type=dt,
                time=data["time"],
                category=data["category"],
                title=data["title"],
                description=data.get("description", ""),
                is_custom=1,
            )
    else:
        await insert_schedule_item(
            user_id=settings.admin_id,
            day_type=day_type,
            time=data["time"],
            category=data["category"],
            title=data["title"],
            description=data.get("description", ""),
            is_custom=1,
        )

    await state.clear()

    # Reschedule today's jobs if relevant
    from bot.scheduler.scheduler import reschedule_today
    await reschedule_today(message.bot)

    await message.answer("✅ Событие добавлено!")


@router.message(AddEventStates.confirm)
async def fsm_confirm_unknown(message: Message) -> None:
    await message.answer("Отправь /confirm, чтобы сохранить, или /cancel, чтобы отменить.")
