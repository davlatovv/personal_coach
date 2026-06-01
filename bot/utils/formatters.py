from datetime import date
from typing import List, Dict, Any

from bot.utils.emoji import (
    CATEGORY_EMOJI,
    DAY_TYPE_EMOJI,
    DAY_TYPE_LABEL,
    WEEKDAY_NAMES,
)


def format_notification(item: Dict[str, Any]) -> str:
    """Format a schedule item as a notification message."""
    emoji = CATEGORY_EMOJI.get(item["category"], "📌")
    category_name = {
        "food": "ЕДА",
        "supplement": "ДОБАВКИ",
        "sport": "СПОРТ",
        "sleep": "СОН",
        "water": "ВОДА",
        "work": "РАБОТА",
    }.get(item["category"], item["category"].upper())

    lines = [
        f"{emoji} {category_name} — {item['time']}",
        "",
        item["title"],
    ]
    if item.get("description"):
        lines.append("")
        lines.append(item["description"])

    return "\n".join(lines)


def format_schedule_list(items: List[Dict[str, Any]], day_type: str, target_date: date) -> str:
    """Format a full day schedule for /today or /tomorrow."""
    weekday = target_date.weekday()
    weekday_name = WEEKDAY_NAMES.get(weekday, "")
    day_emoji = DAY_TYPE_EMOJI.get(day_type, "📅")
    day_label = DAY_TYPE_LABEL.get(day_type, day_type)

    lines = [f"📅 {weekday_name} — {day_label} {day_emoji}", ""]

    for item in items:
        emoji = CATEGORY_EMOJI.get(item["category"], "📌")
        lines.append(f"{emoji} {item['time']} — {item['title']}")

    return "\n".join(lines)


def format_week_schedule(week_data: List[Dict[str, Any]]) -> str:
    """Format week schedule for /week command."""
    lines = ["📅 Расписание на неделю", ""]

    for day_info in week_data:
        day_emoji = DAY_TYPE_EMOJI.get(day_info["day_type"], "📅")
        day_label = DAY_TYPE_LABEL.get(day_info["day_type"], day_info["day_type"])
        weekday_name = WEEKDAY_NAMES.get(day_info["weekday"], "")

        lines.append(f"── {weekday_name} ({day_label} {day_emoji}) ──")
        for item in day_info["items"]:
            emoji = CATEGORY_EMOJI.get(item["category"], "📌")
            lines.append(f"  {emoji} {item['time']} — {item['title']}")
        lines.append("")

    return "\n".join(lines).rstrip()


_CAT_NAMES = {
    "food": "Еда",
    "supplement": "Добавки",
    "sport": "Спорт",
    "sleep": "Сон",
    "water": "Вода",
    "work": "Работа",
}


def format_stats(stats_data: Dict[str, Any]) -> str:
    """Format statistics for /stats command."""
    lines = ["📊 Статистика за неделю", ""]

    for day in stats_data["days"]:
        weekday_name = WEEKDAY_NAMES.get(day["weekday"], "")
        day_emoji = DAY_TYPE_EMOJI.get(day["day_type"], "📅")
        status = day["status"]

        if status == "done":
            lines.append(f"{weekday_name} {day_emoji} — {day['count']} отправлено")
        elif status == "today":
            lines.append(f"{weekday_name} {day_emoji} — в процессе ({day['count']} отправлено)")
        elif status == "future":
            lines.append(f"{weekday_name} {day_emoji} — ещё впереди")
        else:
            lines.append(f"{weekday_name} {day_emoji} — нет данных")

    # Overall completion block
    comp = stats_data.get("completion", {})
    total = comp.get("total", 0)
    done = comp.get("done_count", 0)
    skipped = comp.get("skipped_count", 0)
    pending = comp.get("pending_count", 0)

    lines.append("")
    lines.append("Выполнение за неделю:")
    if total > 0:
        pct = round(done / total * 100)
        lines.append(f"✅ Выполнено: {done} / {total} ({pct}%)")
        if skipped:
            lines.append(f"❌ Пропущено: {skipped}")
        if pending:
            lines.append(f"⏳ Ожидает ответа: {pending}")
    else:
        lines.append("Нет данных")

    # Per-category breakdown
    cat_stats = stats_data.get("cat_stats", [])
    if cat_stats:
        lines.append("")
        lines.append("По категориям:")
        for row in cat_stats:
            cat = row["category"]
            emoji = CATEGORY_EMOJI.get(cat, "📌")
            cat_name = _CAT_NAMES.get(cat, cat)
            cat_total = row["total"]
            cat_done = row["done_count"]
            cat_skipped = row["skipped_count"]
            cat_pct = round(cat_done / cat_total * 100) if cat_total else 0
            lines.append(f"{emoji} {cat_name}: {cat_done}/{cat_total} ({cat_pct}%)" + (f" — {cat_skipped} пропущено" if cat_skipped else ""))

    lines.append("")
    streak = stats_data.get("streak", 0)
    lines.append(f"🔥 Streak: {streak} {'день' if streak == 1 else 'дня' if 2 <= streak <= 4 else 'дней'} подряд")

    return "\n".join(lines)
