from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Сегодня"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="⚙️ Настройки")],
        ],
        resize_keyboard=True,
        persistent=True,
    )
