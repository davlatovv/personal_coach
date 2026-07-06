import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import settings
from bot.database.db import create_tables
from bot.database.queries import upsert_user
from bot.scheduler.scheduler import start_scheduler, stop_scheduler

from bot.handlers import (
    start,
    schedule,
    stats,
    daytype,
    pause,
    edit,
    add,
    reminder,
    help as help_handler,
)
from bot.handlers import notifications

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


BOT_COMMANDS = [
    BotCommand(command="today", description="Расписание на сегодня"),
    BotCommand(command="tomorrow", description="Расписание на завтра"),
    BotCommand(command="week", description="Расписание на неделю"),
    BotCommand(command="stats", description="Статистика уведомлений"),
    BotCommand(command="edit", description="Редактировать расписание"),
    BotCommand(command="edit_item", description="Показать событие по ID"),
    BotCommand(command="enable", description="Включить событие"),
    BotCommand(command="disable", description="Отключить событие"),
    BotCommand(command="edit_time", description="Изменить время события"),
    BotCommand(command="edit_desc", description="Изменить описание события"),
    BotCommand(command="delete", description="Удалить пользовательское событие"),
    BotCommand(command="add", description="Добавить событие"),
    BotCommand(command="reminder", description="Добавить напоминалку"),
    BotCommand(command="daytype", description="Изменить тип дня"),
    BotCommand(command="done", description="Отметить уведомление выполненным"),
    BotCommand(command="skip", description="Пропустить описание или уведомление"),
    BotCommand(command="confirm", description="Подтвердить действие"),
    BotCommand(command="cancel", description="Отменить действие"),
    BotCommand(command="pause", description="Пауза уведомлений"),
    BotCommand(command="resume", description="Возобновить уведомления"),
    BotCommand(command="help", description="Помощь"),
]


async def admin_only_middleware(handler, event, data):
    """Block all updates from non-admin users."""
    user = None
    if hasattr(event, "from_user"):
        user = event.from_user
    elif hasattr(event, "message") and event.message:
        user = event.message.from_user

    if user and user.id != settings.admin_id:
        logger.warning(f"Blocked update from user_id={user.id}")
        return

    return await handler(event, data)


async def main() -> None:
    # Init DB
    await create_tables()
    await upsert_user(settings.admin_id, None)

    session = AiohttpSession(timeout=60.0)
    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    await bot.set_my_commands(BOT_COMMANDS)

    # Middleware
    dp.update.outer_middleware(admin_only_middleware)

    # Routers
    dp.include_router(start.router)
    dp.include_router(schedule.router)
    dp.include_router(stats.router)
    dp.include_router(daytype.router)
    dp.include_router(pause.router)
    dp.include_router(edit.router)
    dp.include_router(add.router)
    dp.include_router(reminder.router)
    dp.include_router(help_handler.router)
    dp.include_router(notifications.router)

    # Scheduler
    await start_scheduler(bot)

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        await stop_scheduler()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
