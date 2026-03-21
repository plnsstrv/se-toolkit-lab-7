from __future__ import annotations

import argparse
import sys

from config import Config
from handlers import handle_command


def run_test_mode(command_text: str) -> int:
    _ = Config.load()
    response = handle_command(command_text)
    print(response)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test",
        dest="test_command",
        help='Run bot in offline test mode, e.g. --test "/start"',
    )
    args = parser.parse_args()

    if args.test_command is not None:
        return run_test_mode(args.test_command)

    config = Config.load()
    if not config.bot_token:
        print(
            "BOT_TOKEN is missing. Use --test mode or configure .env.bot.secret.",
            file=sys.stderr,
        )
        return 1

    print("Telegram mode is not implemented yet. Use --test for Task 1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
