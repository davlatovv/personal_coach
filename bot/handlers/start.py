from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardRemove

from bot.database.queries import upsert_user
from bot.database.seed import seed_schedule

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    username = message.from_user.username

    await upsert_user(user_id, username)
    await seed_schedule(user_id)

    text = (
        "👋 Привет! Я твой персональный планировщик дня.\n\n"
        "Я буду присылать уведомления по расписанию:\n"
        "— что делать и когда\n"
        "— что есть\n"
        "— какие добавки пить\n\n"
        "📋 Команды:\n"
        "/today — расписание на сегодня\n"
        "/tomorrow — расписание на завтра\n"
        "/week — расписание на неделю\n"
        "/stats — статистика уведомлений\n"
        "/edit — редактировать расписание\n"
        "/add — добавить событие\n"
        "/reminder — добавить напоминалку\n"
        "/daytype — изменить тип дня\n"
        "/pause — пауза уведомлений\n"
        "/resume — возобновить уведомления\n"
        "/help — помощь"
    )

    await message.answer(text, reply_markup=ReplyKeyboardRemove())
