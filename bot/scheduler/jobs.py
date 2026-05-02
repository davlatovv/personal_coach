import logging
import random
import asyncio
from datetime import date
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramNetworkError, TelegramServerError

from bot.config import settings
from bot.database.queries import log_notification
from bot.keyboards.inline import notification_action_keyboard
from bot.utils.emoji import CATEGORY_EMOJI, SPORT_PHRASES
from bot.utils.formatters import format_notification

logger = logging.getLogger(__name__)


# In-memory pause state (reset on restart)
_pause_state: dict = {
    "paused": False,
    "resume_at": None,  # datetime or None
}


def is_paused() -> bool:
    if not _pause_state["paused"]:
        return False
    if _pause_state["resume_at"] is not None:
        from datetime import datetime
        import pytz
        from bot.config import settings as s
        tz = pytz.timezone(s.timezone)
        now = datetime.now(tz)
        if now >= _pause_state["resume_at"]:
            _pause_state["paused"] = False
            _pause_state["resume_at"] = None
            return False
    return True


def set_pause(resume_at=None) -> None:
    _pause_state["paused"] = True
    _pause_state["resume_at"] = resume_at


def clear_pause() -> None:
    _pause_state["paused"] = False
    _pause_state["resume_at"] = None


async def send_notification(bot: Bot, item: dict, target_date: date) -> None:
    """Send a single scheduled notification and log it."""
    if is_paused():
        return

    text = format_notification(item)

    if item["category"] == "sport":
        phrase = random.choice(SPORT_PHRASES)
        text += f"\n\n💪 {phrase}"

    try:
        log_id = await log_notification(
            user_id=settings.admin_id,
            schedule_item_id=item["id"],
            target_date=target_date.isoformat(),
            day_type=item["day_type"],
            category=item["category"],
        )
        keyboard = notification_action_keyboard(log_id)
    except Exception as e:
        logger.error(f"[NOTIFICATION PREP ERROR] item_id={item['id']}: {e}")
        return

    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            await bot.send_message(chat_id=settings.admin_id, text=text, reply_markup=keyboard)
            return
        except TelegramRetryAfter as e:
            wait_for = max(float(e.retry_after), 1.0)
            logger.warning(
                f"[NOTIFICATION RETRY_AFTER] item_id={item['id']} attempt={attempt}/{max_attempts}, "
                f"sleep={wait_for:.2f}s"
            )
            await asyncio.sleep(wait_for)
        except (TelegramNetworkError, TelegramServerError) as e:
            # Exponential backoff for temporary Telegram-side/network failures.
            wait_for = min(2 ** attempt, 30)
            logger.warning(
                f"[NOTIFICATION TRANSIENT ERROR] item_id={item['id']} attempt={attempt}/{max_attempts}: {e}. "
                f"sleep={wait_for}s"
            )
            await asyncio.sleep(wait_for)
        except Exception as e:
            logger.error(f"[NOTIFICATION ERROR] item_id={item['id']}: {e}")
            return

    logger.error(f"[NOTIFICATION GIVEUP] item_id={item['id']} exhausted {max_attempts} attempts")
