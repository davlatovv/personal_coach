from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.database.queries import update_notification_status

router = Router()

STATUS_TEXT = {
    "done": "✅ Выполнено",
    "skipped": "❌ Пропущено",
}


@router.callback_query(F.data.startswith("notif:"))
async def handle_notification_action(callback: CallbackQuery) -> None:
    _, action, log_id_str = callback.data.split(":")
    log_id = int(log_id_str)

    await update_notification_status(log_id, action)

    original_text = callback.message.text or ""
    status_label = STATUS_TEXT.get(action, action)
    new_text = f"{original_text}\n\n{status_label}"

    await callback.message.edit_text(new_text, reply_markup=None)
    await callback.answer()
