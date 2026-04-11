from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Settings:
    bot_token: str
    admin_id: int
    db_path: str
    timezone: str


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN")
    admin_id = os.getenv("ADMIN_ID")
    db_path = os.getenv("DB_PATH", "data/schedule.db")
    timezone = os.getenv("TIMEZONE", "Asia/Tashkent")

    if not bot_token:
        raise ValueError("BOT_TOKEN не задан в .env")
    if not admin_id:
        raise ValueError("ADMIN_ID не задан в .env")

    # Ensure data directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        bot_token=bot_token,
        admin_id=int(admin_id),
        db_path=db_path,
        timezone=timezone,
    )


settings = get_settings()
