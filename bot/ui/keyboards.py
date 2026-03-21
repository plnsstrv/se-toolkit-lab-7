from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Labs", callback_data="labs"),
                InlineKeyboardButton(text="Health", callback_data="health"),
            ],
            [
                InlineKeyboardButton(text="Scores Lab 1", callback_data="scores:lab-01"),
                InlineKeyboardButton(text="Scores Lab 4", callback_data="scores:lab-04"),
            ],
            [
                InlineKeyboardButton(text="Enrollment", callback_data="enrollment"),
                InlineKeyboardButton(text="Lowest pass rate", callback_data="lowest-pass-rate"),
            ],
        ]
    )
