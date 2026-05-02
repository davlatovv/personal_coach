import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

from bot.config import settings
from bot.database.db import create_tables
from bot.database.seed import seed_schedule
from bot.database.queries import upsert_user
from bot.scheduler.scheduler import start_scheduler, stop_scheduler

from bot.handlers import start, schedule, stats, daytype, pause, edit, add, help as help_handler
from bot.handlers import notifications

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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
    await seed_schedule(settings.admin_id)

    session = AiohttpSession(timeout=60.0)
    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

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
    dp.include_router(help_handler.router)
    dp.include_router(notifications.router)

    # Scheduler
    await start_scheduler(bot)

    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await stop_scheduler()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
