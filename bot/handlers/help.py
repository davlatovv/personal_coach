from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

HELP_TEXT = """
📋 <b>Список команд</b>

/today — расписание на сегодня
/tomorrow — расписание на завтра
/week — расписание на неделю
/stats — статистика уведомлений за неделю
/edit [type] — список событий для типа дня
/edit_item [id] — показать событие
/enable [id] — включить событие
/disable [id] — отключить событие
/edit_time [id] [HH:MM] — изменить время события
/edit_desc [id] — изменить описание события
/delete [id] — удалить пользовательское событие
/add — добавить своё событие
/reminder — добавить напоминалку
/daytype [type] — изменить тип текущего дня
/done [id] — отметить уведомление выполненным
/skip [id] — пропустить уведомление; в формах пропускает описание
/confirm — подтвердить добавление
/cancel — отменить текущее действие
/pause [часы] — поставить уведомления на паузу
/resume — возобновить уведомления
""".strip()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")
