from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import NetworkError, TelegramError, TimedOut
from telegram.request import HTTPXRequest

from config import (
    TELEGRAM_CONNECT_TIMEOUT,
    TELEGRAM_GET_UPDATES_READ_TIMEOUT,
    TELEGRAM_POOL_TIMEOUT,
    TELEGRAM_PROXY_URL,
    TELEGRAM_READ_TIMEOUT,
    TELEGRAM_WRITE_TIMEOUT,
)


def build_request(read_timeout: float) -> HTTPXRequest:
    request_kwargs = {}
    if TELEGRAM_PROXY_URL:
        request_kwargs["proxy"] = TELEGRAM_PROXY_URL

    return HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=read_timeout,
        write_timeout=TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
        **request_kwargs,
    )


async def main() -> int:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN не задан. Добавь его в .env")
        return 1

    print("Проверяю подключение к Telegram API...")
    if TELEGRAM_PROXY_URL:
        print(f"Прокси: {TELEGRAM_PROXY_URL}")

    bot = Bot(token, request=build_request(TELEGRAM_READ_TIMEOUT))
    try:
        me = await bot.get_me()
        print(f"OK: бот @{me.username} (id={me.id})")
    except TimedOut:
        print("Ошибка: TimedOut при getMe().")
        print("Интернет до api.telegram.org есть, но Python не дождался ответа.")
        print("Попробуй: git pull, перезапуск, VPN/прокси, TELEGRAM_PROXY_URL в .env")
        return 2
    except NetworkError as error:
        print(f"Ошибка сети: {error}")
        return 2
    except TelegramError as error:
        print(f"Ошибка Telegram API: {error}")
        return 3
    finally:
        await bot.shutdown()

    updates_bot = Bot(token, request=build_request(TELEGRAM_GET_UPDATES_READ_TIMEOUT))
    try:
        await updates_bot.get_updates(timeout=5, limit=1)
        print("OK: getUpdates тоже отвечает.")
    except TimedOut:
        print("getMe прошёл, но getUpdates дал TimedOut.")
        print("Это похоже на нестабильный long polling. Перезапусти bot.py после git pull.")
        return 2
    except TelegramError as error:
        print(f"getUpdates: {error}")
        return 3
    finally:
        await updates_bot.shutdown()

    print("Можно запускать: python bot.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
