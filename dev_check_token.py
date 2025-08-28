"""Quick check that telegram_bot.bot reads TELEGRAM_BOT_TOKEN from env.

Run: python dev_check_token.py
"""

import os
import importlib


def main() -> None:
    os.environ["TELEGRAM_BOT_TOKEN"] = "123456:ABCDEF"
    bot = importlib.import_module("telegram_bot.bot")
    ok = isinstance(getattr(bot, "TOKEN", None), str) and bot.TOKEN.startswith("123456:")
    print("TOKEN_OK", ok)


if __name__ == "__main__":
    main()

