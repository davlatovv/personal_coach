from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.config import settings
from bot.database.queries import (
    get_all_schedule_items,
    get_schedule_item,
    toggle_schedule_item,
    update_schedule_item_time,
    update_schedule_item_description,
    delete_custom_schedule_item,
)
from bot.keyboards.inline import edit_day_type_keyboard, edit_items_keyboard, edit_item_actions_keyboard
from bot.states.add_event import EditItemStates
from bot.utils.validators import validate_time, normalize_time
from bot.utils.emoji import DAY_TYPE_LABEL, DAY_TYPE_EMOJI

router = Router()


@router.message(Command("edit"))
async def cmd_edit(message: Message) -> None:
    await message.answer(
        "✏️ Выбери тип дня для редактирования:",
        reply_markup=edit_day_type_keyboard(),
    )


@router.callback_query(F.data.startswith("edit_daytype:"))
async def cb_edit_daytype(callback: CallbackQuery) -> None:
    day_type = callback.data.split(":")[1]
    items = await get_all_schedule_items(settings.admin_id, day_type)

    label = DAY_TYPE_LABEL.get(day_type, day_type)
    emoji = DAY_TYPE_EMOJI.get(day_type, "")

    if not items:
        await callback.message.edit_text(f"Нет событий для типа дня: {emoji} {label}")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📋 События для дня «{emoji} {label}»\n"
        "Нажми на событие для редактирования:",
        reply_markup=edit_items_keyboard(items),
    )
    await callback.answer()


@router.callback_query(F.data == "edit_back")
async def cb_edit_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "✏️ Выбери тип дня для редактирования:",
        reply_markup=edit_day_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_back_items:"))
async def cb_edit_back_items(callback: CallbackQuery) -> None:
    day_type = callback.data.split(":")[1]
    items = await get_all_schedule_items(settings.admin_id, day_type)
    label = DAY_TYPE_LABEL.get(day_type, day_type)
    emoji = DAY_TYPE_EMOJI.get(day_type, "")

    await callback.message.edit_text(
        f"📋 События для дня «{emoji} {label}»\n"
        "Нажми на событие для редактирования:",
        reply_markup=edit_items_keyboard(items),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_item:"))
async def cb_edit_item(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[1])
    item = await get_schedule_item(item_id)

    if not item:
        await callback.answer("Событие не найдено", show_alert=True)
        return

    from bot.utils.emoji import CATEGORY_EMOJI
    emoji = CATEGORY_EMOJI.get(item["category"], "📌")
    status = "✅ активно" if item["is_active"] else "❌ отключено"
    custom_mark = " (пользовательское)" if item["is_custom"] else ""

    text = (
        f"{emoji} <b>{item['title']}</b>{custom_mark}\n"
        f"⏰ Время: {item['time']}\n"
        f"📂 Категория: {item['category']}\n"
        f"Статус: {status}\n"
    )
    if item["description"]:
        desc_preview = item["description"][:100] + ("..." if len(item["description"]) > 100 else "")
        text += f"\n📝 {desc_preview}"

    await callback.message.edit_text(
        text,
        reply_markup=edit_item_actions_keyboard(item),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_action:"))
async def cb_edit_action(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    item_id = int(parts[2])

    item = await get_schedule_item(item_id)
    if not item:
        await callback.answer("Событие не найдено", show_alert=True)
        return

    if action == "disable":
        await toggle_schedule_item(item_id, False)
        await callback.answer("🔕 Событие отключено")
        # Refresh item view
        updated = await get_schedule_item(item_id)
        await callback.message.edit_reply_markup(
            reply_markup=edit_item_actions_keyboard(updated)
        )

    elif action == "enable":
        await toggle_schedule_item(item_id, True)
        await callback.answer("🔔 Событие включено")
        updated = await get_schedule_item(item_id)
        await callback.message.edit_reply_markup(
            reply_markup=edit_item_actions_keyboard(updated)
        )

    elif action == "time":
        await state.set_state(EditItemStates.waiting_new_time)
        await state.update_data(edit_item_id=item_id, edit_day_type=item["day_type"])
        await callback.message.answer(
            f"⏰ Введи новое время для «{item['title']}» (формат HH:MM):"
        )
        await callback.answer()

    elif action == "desc":
        await state.set_state(EditItemStates.waiting_new_description)
        await state.update_data(edit_item_id=item_id, edit_day_type=item["day_type"])
        await callback.message.answer(
            f"✏️ Введи новое описание для «{item['title']}»:"
        )
        await callback.answer()

    elif action == "delete":
        if not item["is_custom"]:
            await callback.answer("❗ Системные события нельзя удалять", show_alert=True)
            return
        await delete_custom_schedule_item(item_id)
        await callback.answer("🗑 Событие удалено")
        items = await get_all_schedule_items(settings.admin_id, item["day_type"])
        label = DAY_TYPE_LABEL.get(item["day_type"], item["day_type"])
        emoji = DAY_TYPE_EMOJI.get(item["day_type"], "")
        await callback.message.edit_text(
            f"📋 События для дня «{emoji} {label}»\n"
            "Нажми на событие для редактирования:",
            reply_markup=edit_items_keyboard(items),
        )


@router.message(EditItemStates.waiting_new_time)
async def fsm_edit_time(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    normalized = normalize_time(raw)

    if not validate_time(normalized):
        await message.answer("❗ Неверный формат времени. Введи в формате HH:MM (например 07:30):")
        return

    data = await state.get_data()
    item_id = data["edit_item_id"]
    day_type = data["edit_day_type"]

    await update_schedule_item_time(item_id, normalized)
    await state.clear()

    # Reschedule
    from bot.scheduler.scheduler import reschedule_today
    from datetime import date
    from bot.scheduler.day_resolver import resolve_day_type
    today_type = await resolve_day_type(date.today())
    if today_type == day_type:
        await reschedule_today(message.bot)

    await message.answer(f"✅ Время обновлено: {normalized}")


@router.message(EditItemStates.waiting_new_description)
async def fsm_edit_desc(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    item_id = data["edit_item_id"]

    await update_schedule_item_description(item_id, message.text.strip())
    await state.clear()

    await message.answer("✅ Описание обновлено!")
