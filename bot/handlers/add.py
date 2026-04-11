from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import settings
from bot.database.queries import insert_schedule_item
from bot.keyboards.inline import (
    category_keyboard,
    add_day_type_keyboard,
    confirm_keyboard,
    skip_keyboard,
)
from bot.states.add_event import AddEventStates
from bot.utils.emoji import CATEGORY_EMOJI, DAY_TYPE_LABEL, DAY_TYPE_EMOJI
from bot.utils.validators import validate_time, normalize_time

router = Router()


@router.message(Command("add"))
@router.message(F.text == "➕ Добавить")
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddEventStates.waiting_title)
    await message.answer("📝 Введи название события:")


@router.message(AddEventStates.waiting_title)
async def fsm_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title:
        await message.answer("❗ Название не может быть пустым. Введи название:")
        return

    await state.update_data(title=title)
    await state.set_state(AddEventStates.waiting_description)
    await message.answer(
        "📄 Введи описание (или нажми «Пропустить»):",
        reply_markup=skip_keyboard(),
    )


@router.callback_query(AddEventStates.waiting_description, F.data == "add_skip_desc")
async def fsm_skip_desc(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(description="")
    await state.set_state(AddEventStates.waiting_time)
    await callback.message.answer("⏰ Введи время в формате HH:MM (например 14:30):")
    await callback.answer()


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
    await message.answer("📂 Выбери категорию:", reply_markup=category_keyboard())


@router.callback_query(AddEventStates.waiting_category, F.data.startswith("add_cat:"))
async def fsm_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(AddEventStates.waiting_day_type)
    await callback.message.answer(
        "📅 Для какого типа дня?",
        reply_markup=add_day_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(AddEventStates.waiting_day_type, F.data.startswith("add_dtype:"))
async def fsm_day_type(callback: CallbackQuery, state: FSMContext) -> None:
    dtype = callback.data.split(":")[1]

    if dtype == "specific_date":
        await state.update_data(day_type=None)
        await state.set_state(AddEventStates.waiting_specific_date)
        await callback.message.answer("📆 Введи дату в формате YYYY-MM-DD (например 2025-01-15):")
        await callback.answer()
        return

    day_type = None if dtype == "all" else dtype
    await state.update_data(day_type=day_type, specific_date=None)
    await _show_confirm(callback.message, state)
    await callback.answer()


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
    await message.answer(text, reply_markup=confirm_keyboard(), parse_mode="HTML")


@router.callback_query(AddEventStates.confirm, F.data.startswith("add_confirm:"))
async def fsm_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    choice = callback.data.split(":")[1]

    if choice == "no":
        await state.clear()
        await callback.message.edit_text("❌ Добавление отменено.")
        await callback.answer()
        return

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
        for dt in ["boxing", "gym", "weekend_sat", "weekend_sun"]:
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
    await reschedule_today(callback.bot)

    await callback.message.edit_text("✅ Событие добавлено!")
    await callback.answer()
