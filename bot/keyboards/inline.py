from typing import List, Dict, Any

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.emoji import DAY_TYPE_EMOJI, DAY_TYPE_LABEL, CATEGORY_EMOJI


_DAY_TYPE_OPTIONS = [
    ("boxing", "🥊 Бокс (Пн/Ср)"),
    ("boxing_fri", "🥊 Бокс (Пт)"),
    ("gym", "🏋️ Зал"),
    ("weekend_sat", "🏃 Суббота"),
    ("weekend_sun", "😴 Воскресенье"),
]


def day_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for dt, label in _DAY_TYPE_OPTIONS:
        builder.button(text=label, callback_data=f"daytype:{dt}")
    builder.adjust(2)
    return builder.as_markup()


def edit_day_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for dt, label in _DAY_TYPE_OPTIONS:
        builder.button(text=label, callback_data=f"edit_daytype:{dt}")
    builder.adjust(2)
    return builder.as_markup()


def edit_items_keyboard(items: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        emoji = CATEGORY_EMOJI.get(item["category"], "📌")
        active_mark = "" if item["is_active"] else " ✗"
        label = f"{emoji} {item['time']} — {item['title']}{active_mark}"
        builder.button(text=label, callback_data=f"edit_item:{item['id']}")
    builder.button(text="◀️ Назад", callback_data="edit_back")
    builder.adjust(1)
    return builder.as_markup()


def edit_item_actions_keyboard(item: Dict[str, Any]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if item["is_active"]:
        builder.button(text="🔕 Отключить", callback_data=f"edit_action:disable:{item['id']}")
    else:
        builder.button(text="🔔 Включить", callback_data=f"edit_action:enable:{item['id']}")
    builder.button(text="⏰ Изменить время", callback_data=f"edit_action:time:{item['id']}")
    builder.button(text="✏️ Изменить описание", callback_data=f"edit_action:desc:{item['id']}")
    if item.get("is_custom"):
        builder.button(text="🗑 Удалить", callback_data=f"edit_action:delete:{item['id']}")
    builder.button(text="◀️ Назад", callback_data=f"edit_back_items:{item['day_type']}")
    builder.adjust(1)
    return builder.as_markup()


def category_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    categories = [
        ("food", "🥗 Еда"),
        ("supplement", "💊 Добавки"),
        ("sport", "🥊 Спорт"),
        ("sleep", "💤 Сон"),
        ("water", "💧 Вода"),
        ("work", "💼 Работа"),
    ]
    for cat, label in categories:
        builder.button(text=label, callback_data=f"add_cat:{cat}")
    builder.adjust(2)
    return builder.as_markup()


def add_day_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    options = [
        ("all", "📅 Все типы дней"),
        ("boxing", "🥊 Бокс (Пн/Ср)"),
        ("boxing_fri", "🥊 Бокс (Пт)"),
        ("gym", "🏋️ Зал"),
        ("weekend_sat", "🏃 Суббота"),
        ("weekend_sun", "😴 Воскресенье"),
        ("specific_date", "📆 Конкретная дата"),
    ]
    for val, label in options:
        builder.button(text=label, callback_data=f"add_dtype:{val}")
    builder.adjust(2)
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Сохранить", callback_data="add_confirm:yes")
    builder.button(text="❌ Отмена", callback_data="add_confirm:no")
    builder.adjust(2)
    return builder.as_markup()


def notification_action_keyboard(log_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выполнено", callback_data=f"notif:done:{log_id}")
    builder.button(text="❌ Пропустить", callback_data=f"notif:skip:{log_id}")
    builder.adjust(2)
    return builder.as_markup()


def skip_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Пропустить", callback_data="add_skip_desc")
    return builder.as_markup()
