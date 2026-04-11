from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

HELP_TEXT = """
📋 <b>Список команд</b>

/today — расписание на сегодня
/tomorrow — расписание на завтра
/week — расписание на неделю
/stats — статистика уведомлений за неделю
/edit — редактировать расписание
/add — добавить своё событие
/daytype — изменить тип текущего дня
/pause [часы] — поставить уведомления на паузу
/resume — возобновить уведомления

<b>Кнопки клавиатуры:</b>
📅 Сегодня — расписание на сегодня
📊 Статистика — статистика за неделю
➕ Добавить — добавить событие
⚙️ Настройки — редактировать расписание
""".strip()


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(F.text == "⚙️ Настройки")
async def btn_settings(message: Message) -> None:
    from bot.keyboards.inline import edit_day_type_keyboard
    await message.answer(
        "⚙️ Выбери тип дня для редактирования:",
        reply_markup=edit_day_type_keyboard(),
    )
