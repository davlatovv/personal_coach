from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings
from bot.database.queries import (
    get_all_schedule_items,
    get_schedule_item,
    toggle_schedule_item,
    update_schedule_item_time,
    update_schedule_item_description,
    delete_custom_schedule_item,
)
from bot.states.add_event import EditItemStates
from bot.utils.emoji import CATEGORY_EMOJI, DAY_TYPE_LABEL, DAY_TYPE_EMOJI
from bot.utils.validators import validate_time, normalize_time

router = Router()

DAY_TYPE_CODES = ("boxing", "boxing_fri", "gym", "weekend_sat", "weekend_sun")


def _args(message: Message) -> str:
    parts = (message.text or "").strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _day_type_help() -> str:
    lines = ["Используй /edit <day_type>.", "", "Доступные типы:"]
    for code in DAY_TYPE_CODES:
        emoji = DAY_TYPE_EMOJI.get(code, "")
        label = DAY_TYPE_LABEL.get(code, code)
        lines.append(f"{code} — {emoji} {label}")
    return "\n".join(lines)


def _format_items(items: list[dict], day_type: str) -> str:
    label = DAY_TYPE_LABEL.get(day_type, day_type)
    emoji = DAY_TYPE_EMOJI.get(day_type, "")
    lines = [f"📋 События для дня «{emoji} {label}»", ""]

    for item in items:
        category_emoji = CATEGORY_EMOJI.get(item["category"], "📌")
        active_mark = "активно" if item["is_active"] else "отключено"
        custom_mark = ", custom" if item.get("is_custom") else ""
        lines.append(
            f"{item['id']}: {category_emoji} {item['time']} — {item['title']} "
            f"({active_mark}{custom_mark})"
        )

    lines.append("")
    lines.append("Открыть событие: /edit_item <id>")
    return "\n".join(lines)


async def _reschedule_if_today(message: Message, day_type: str) -> None:
    from bot.scheduler.scheduler import reschedule_today
    from bot.scheduler.day_resolver import resolve_day_type

    today_type = await resolve_day_type(date.today())
    if today_type == day_type:
        await reschedule_today(message.bot)


@router.message(Command("edit"))
async def cmd_edit(message: Message) -> None:
    day_type = _args(message).lower()
    if not day_type:
        await message.answer(_day_type_help())
        return
    if day_type not in DAY_TYPE_CODES:
        await message.answer("❗ Неизвестный тип дня.\n\n" + _day_type_help())
        return

    items = await get_all_schedule_items(settings.admin_id, day_type)
    if not items:
        label = DAY_TYPE_LABEL.get(day_type, day_type)
        emoji = DAY_TYPE_EMOJI.get(day_type, "")
        await message.answer(f"Нет событий для типа дня: {emoji} {label}")
        return

    await message.answer(_format_items(items, day_type))


@router.message(Command("edit_item"))
async def cmd_edit_item(message: Message) -> None:
    raw_id = _args(message)
    if not raw_id.isdigit():
        await message.answer("Используй /edit_item <id>")
        return

    item = await get_schedule_item(int(raw_id))
    if not item:
        await message.answer("Событие не найдено.")
        return

    emoji = CATEGORY_EMOJI.get(item["category"], "📌")
    status = "активно" if item["is_active"] else "отключено"
    custom_mark = " (пользовательское)" if item["is_custom"] else ""
    actions = [
        f"/disable {item['id']} — отключить",
        f"/enable {item['id']} — включить",
        f"/edit_time {item['id']} HH:MM — изменить время",
        f"/edit_desc {item['id']} — изменить описание",
    ]
    if item.get("is_custom"):
        actions.append(f"/delete {item['id']} — удалить")

    text = (
        f"{emoji} <b>{item['title']}</b>{custom_mark}\n"
        f"ID: {item['id']}\n"
        f"⏰ Время: {item['time']}\n"
        f"📂 Категория: {item['category']}\n"
        f"Статус: {status}\n"
    )
    if item["description"]:
        desc_preview = item["description"][:300] + ("..." if len(item["description"]) > 300 else "")
        text += f"\n📝 {desc_preview}\n"
    text += "\nКоманды:\n" + "\n".join(actions)

    await message.answer(text, parse_mode="HTML")


@router.message(Command("disable"))
async def cmd_disable(message: Message) -> None:
    raw_id = _args(message)
    if not raw_id.isdigit():
        await message.answer("Используй /disable <id>")
        return

    item = await get_schedule_item(int(raw_id))
    if not item:
        await message.answer("Событие не найдено.")
        return

    await toggle_schedule_item(item["id"], False)
    await _reschedule_if_today(message, item["day_type"])
    await message.answer(f"🔕 Событие отключено: {item['title']}")


@router.message(Command("enable"))
async def cmd_enable(message: Message) -> None:
    raw_id = _args(message)
    if not raw_id.isdigit():
        await message.answer("Используй /enable <id>")
        return

    item = await get_schedule_item(int(raw_id))
    if not item:
        await message.answer("Событие не найдено.")
        return

    await toggle_schedule_item(item["id"], True)
    await _reschedule_if_today(message, item["day_type"])
    await message.answer(f"🔔 Событие включено: {item['title']}")


@router.message(Command("edit_time"))
async def cmd_edit_time(message: Message) -> None:
    parts = _args(message).split(maxsplit=1)
    if len(parts) != 2 or not parts[0].isdigit():
        await message.answer("Используй /edit_time <id> <HH:MM>")
        return

    item = await get_schedule_item(int(parts[0]))
    if not item:
        await message.answer("Событие не найдено.")
        return

    normalized = normalize_time(parts[1])
    if not validate_time(normalized):
        await message.answer("❗ Неверный формат времени. Используй /edit_time <id> <HH:MM>")
        return

    await update_schedule_item_time(item["id"], normalized)
    await _reschedule_if_today(message, item["day_type"])
    await message.answer(f"✅ Время обновлено: {normalized}")


@router.message(Command("edit_desc"))
async def cmd_edit_desc(message: Message, state: FSMContext) -> None:
    raw_id = _args(message)
    if not raw_id.isdigit():
        await message.answer("Используй /edit_desc <id>")
        return

    item = await get_schedule_item(int(raw_id))
    if not item:
        await message.answer("Событие не найдено.")
        return

    await state.set_state(EditItemStates.waiting_new_description)
    await state.update_data(edit_item_id=item["id"])
    await message.answer(f"✏️ Введи новое описание для «{item['title']}» или /cancel:")


@router.message(EditItemStates.waiting_new_description, Command("cancel"))
async def fsm_edit_desc_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Редактирование описания отменено.")


@router.message(EditItemStates.waiting_new_description)
async def fsm_edit_desc(message: Message, state: FSMContext) -> None:
    if (message.text or "").startswith("/"):
        await message.answer("Введи новое описание текстом или /cancel.")
        return

    data = await state.get_data()
    item_id = data["edit_item_id"]

    await update_schedule_item_description(item_id, message.text.strip())
    await state.clear()

    await message.answer("✅ Описание обновлено!")


@router.message(Command("delete"))
async def cmd_delete(message: Message) -> None:
    raw_id = _args(message)
    if not raw_id.isdigit():
        await message.answer("Используй /delete <id>")
        return

    item = await get_schedule_item(int(raw_id))
    if not item:
        await message.answer("Событие не найдено.")
        return
    if not item["is_custom"]:
        await message.answer("❗ Системные события нельзя удалять.")
        return

    await delete_custom_schedule_item(item["id"])
    await _reschedule_if_today(message, item["day_type"])
    await message.answer(f"🗑 Событие удалено: {item['title']}")
