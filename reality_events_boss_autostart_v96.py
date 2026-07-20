from __future__ import annotations

import logging
from typing import Any

from aiogram.types import User

import reality_events_v96 as events
from reality_events_runtime_fix_v96 import install_reality_events_runtime_fix_v96


LOGGER = logging.getLogger(__name__)


def install_reality_events_boss_autostart_v96(core: Any) -> None:
    if getattr(core, "_reality_events_boss_autostart_v96_installed", False):
        return
    core._reality_events_boss_autostart_v96_installed = True

    # Сначала исправляем совместимость начислений со старым API баланса.
    install_reality_events_runtime_fix_v96(core)
    original_start_event = events._start_event

    async def start_event_with_boss(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        event_key: str | None = None,
        *,
        forced: bool = False,
    ):
        event = await original_start_event(
            core_arg,
            bot,
            chat_id,
            event_key,
            forced=forced,
        )
        if str(event["event_key"]) != "boss_fall":
            return event

        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT 1 FROM boss_battles
            WHERE chat_id=? AND status IN ('active','resolving')
            LIMIT 1
            """,
            (chat_id,),
        )
        if await cursor.fetchone() is not None:
            return event

        starter = User(
            id=int(core_arg.DEVELOPER_ID),
            is_bot=False,
            first_name="Событие реальности",
            username=str(getattr(core_arg, "DEVELOPER_USERNAME", "") or "RealityEvent"),
        )
        try:
            started, result = await core_arg.start_boss_battle(chat_id, starter, bot)
            if not started:
                LOGGER.warning(
                    "Падение Центра запущено, но автобосс не создан в %s: %s",
                    chat_id,
                    result,
                )
        except Exception:
            LOGGER.exception("Не удалось автоматически вызвать Центр Вселенной в %s", chat_id)
        return event

    events._start_event = start_event_with_boss
