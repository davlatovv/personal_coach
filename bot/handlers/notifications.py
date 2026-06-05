from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.database.queries import update_notification_status

router = Router()

STATUS_TEXT = {
    "done": "✅ Выполнено",
    "skipped": "❌ Пропущено",
}


def _log_id_arg(message: Message, command: str) -> int | None:
    parts = (message.text or "").strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        return None
    return int(parts[1].strip())


async def _set_status(message: Message, action: str) -> None:
    log_id = _log_id_arg(message, action)
    if log_id is None:
        await message.answer(f"Используй /{action} <notification_id>")
        return

    status = "skipped" if action == "skip" else action
    await update_notification_status(log_id, status)
    await message.answer(f"{STATUS_TEXT.get(status, status)}: notification_id={log_id}")


@router.message(Command("done"))
async def cmd_done(message: Message) -> None:
    await _set_status(message, "done")


@router.message(Command("skip"))
async def cmd_skip(message: Message) -> None:
    await _set_status(message, "skip")
