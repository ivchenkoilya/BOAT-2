from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from aiogram.exceptions import TelegramNetworkError


VERSION = "Reality 139 · Устойчивый запуск Telegram"
T = TypeVar("T")
_NETWORK_ERRORS = (TelegramNetworkError, asyncio.TimeoutError, OSError)


async def _retry_telegram(
    label: str,
    operation: Callable[[], Awaitable[T]],
) -> T:
    """Повторяет только сетевые запросы, не скрывая ошибки кода и токена."""
    delay = 2
    attempt = 0
    while True:
        try:
            return await operation()
        except _NETWORK_ERRORS as error:
            attempt += 1
            logging.warning(
                "Telegram API временно недоступен во время %s: %s. "
                "Повтор через %s сек. (попытка %s)",
                label,
                error,
                delay,
                attempt,
            )
            await asyncio.sleep(delay)
            delay = min(30, delay * 2)


def install_telegram_network_resilience_v139(core: Any) -> None:
    if getattr(core, "_telegram_network_resilience_v139_installed", False):
        return
    core._telegram_network_resilience_v139_installed = True
    core.TELEGRAM_NETWORK_VERSION = VERSION

    async def resilient_main() -> None:
        if not core.BOT_TOKEN:
            raise RuntimeError(
                "Не найден BOT_TOKEN. Создай файл .env по примеру .env.example."
            )

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )

        core.db = core.Database(core.DATABASE_PATH)
        await core.db.connect()
        await core.ensure_reality49_boss_schema()

        bot = core.Bot(
            token=core.BOT_TOKEN,
            default=core.DefaultBotProperties(parse_mode=core.ParseMode.HTML),
        )
        dispatcher = core.Dispatcher()
        dispatcher.include_router(core.router)
        web_runner = None

        try:
            # Веб-порт открывается до запросов к Telegram. Поэтому Amvera видит
            # живой контейнер, даже если Telegram API временно отвечает медленно.
            web_runner = await core.start_webapp_server(bot)

            await _retry_telegram(
                "установки списка команд",
                lambda: core.set_commands(bot),
            )
            await _retry_telegram(
                "восстановления активных боссов",
                lambda: core.resume_active_bosses(bot),
            )
            await _retry_telegram(
                "восстановления таймеров саботажа",
                lambda: core.resume_active_sabotage_expirations(bot),
            )
            await _retry_telegram(
                "удаления webhook перед polling",
                lambda: bot.delete_webhook(drop_pending_updates=True),
            )

            polling_delay = 2
            while True:
                try:
                    await dispatcher.start_polling(
                        bot,
                        allowed_updates=dispatcher.resolve_used_update_types(),
                    )
                    break
                except _NETWORK_ERRORS as error:
                    logging.warning(
                        "Polling потерял соединение с Telegram: %s. "
                        "Повтор через %s сек.",
                        error,
                        polling_delay,
                    )
                    await asyncio.sleep(polling_delay)
                    polling_delay = min(30, polling_delay * 2)
        finally:
            if web_runner is not None:
                await web_runner.cleanup()
            await core.db.close()
            await bot.session.close()

    core.main = resilient_main
