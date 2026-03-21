# Development Plan

The goal of this bot is to provide a clean, testable architecture before implementing full functionality. I will keep the Telegram transport layer separate from business logic so that every command can be tested offline from the command line. The first step is scaffolding: create an entry point, configuration loading, handler modules, and a CLI `--test` mode. This allows the same handler functions to be used later by Telegram updates and now by the autochecker.

For backend integration, I will add a small service layer that can call the LMS backend using values from `.env.bot.secret`, especially `LMS_API_BASE_URL` and `LMS_API_KEY`. The `/health` command will be the first backend-aware command because it is simple and useful for diagnostics. The `/start` and `/help` commands will remain static at first.

For intent routing, I will begin with explicit slash commands and later add plain-text intent recognition for user questions such as asking about labs, scores, or deadlines. This routing should stay independent from Telegram-specific code.

For deployment, I will verify locally with `uv run bot.py --test`, then run the bot on the VM with `nohup`. After each task, I will first validate test mode, then verify the Telegram bot, and only then continue with new functionality.
