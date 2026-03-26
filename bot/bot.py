from __future__ import annotations

import argparse
import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from config import Config
from handlers import handle_command, route_natural_language
from services import BackendClient, LLMClient
from ui.keyboards import build_main_keyboard


async def resolve_text(text: str, llm: LLMClient, backend: BackendClient) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("/"):
        return await handle_command(cleaned, backend)
    return await route_natural_language(cleaned, llm, backend)


async def run_test_mode(command_text: str) -> int:
    config = Config.load()

    backend = BackendClient(
        base_url=config.lms_api_base_url,
        api_key=config.lms_api_key,
    )
    llm = LLMClient(
        base_url=config.llm_api_base_url,
        api_key=config.llm_api_key,
        model=config.llm_api_model,
    )

    response = await resolve_text(command_text or "", llm, backend)
    print(response)
    return 0


async def run_telegram_mode() -> int:
    config = Config.load()

    if not config.bot_token:
        print("BOT_TOKEN is missing.", file=sys.stderr)
        return 1

    backend = BackendClient(
        base_url=config.lms_api_base_url,
        api_key=config.lms_api_key,
    )
    llm = LLMClient(
        base_url=config.llm_api_base_url,
        api_key=config.llm_api_key,
        model=config.llm_api_model,
    )

    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start_handler(message: Message) -> None:
        text = await handle_command("/start", backend)
        await message.answer(text, reply_markup=build_main_keyboard())

    @dp.callback_query()
    async def callback_handler(callback: CallbackQuery) -> None:
        data = (callback.data or "").strip()
        if data.startswith("cmd:"):
            prompt = data.removeprefix("cmd:")
        elif data.startswith("ask:"):
            prompt = data.removeprefix("ask:")
        else:
            prompt = "what labs are available"

        response = await resolve_text(prompt, llm, backend)
        await callback.answer()
        if callback.message is not None:
            await callback.message.answer(response, reply_markup=build_main_keyboard())

    @dp.message()
    async def fallback_handler(message: Message) -> None:
        response = await resolve_text(message.text or "", llm, backend)
        await message.answer(response, reply_markup=build_main_keyboard())

    await dp.start_polling(bot)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", dest="test_command", help="Run bot in offline test mode")
    args = parser.parse_args()

    if args.test_command is not None:
        return asyncio.run(run_test_mode(args.test_command))

    return asyncio.run(run_telegram_mode())


if __name__ == "__main__":
    raise SystemExit(main())
