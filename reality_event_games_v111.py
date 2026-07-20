from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import reality_events_v96 as events


LOGGER = logging.getLogger(__name__)
VERSION = "Reality 111 · Игровой вклад событий"
GAME_SHARE = 0.20

_WAGER_REASONS = (
    "bot_game_coin",
    "bot_game_dice",
)
_MINI_APP_MARKERS = (
    "game_influence_hunt_rooftop",
    "game_influence_hunt_heist",
    "game_influence_hunt_night-hunter",
    "game_influence_hunt_night_hunter",
)
_REFRESH_TASKS: dict[int, asyncio.Task[Any]] = {}


def _now() -> int:
    return events._now()


def _is_wager_win(reason: str) -> bool:
    value = str(reason or "").casefold()
    return any(marker in value for marker in _WAGER_REASONS)


def _is_mini_app_reward(reason: str) -> bool:
    value = str(reason or "").casefold()
    return any(marker in value for marker in _MINI_APP_MARKERS)


def _is_supported_game_reward(reason: str) -> bool:
    return _is_wager_win(reason) or _is_mini_app_reward(reason)


def _share(delta: int) -> int:
    value = max(0, int(delta))
    if value <= 0:
        return 0
    return max(1, int(round(value * GAME_SHARE)))


async def _repair_game_contributions(core: Any, event: Any) -> int:
    """Adds ignored wagers and rounding corrections for Mini App rewards."""
    if str(event["event_key"]) != "collective":
        return 0

    event_id = str(event["event_id"])
    chat_id = int(event["chat_id"])
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT id,user_id,delta,reason
        FROM score_log
        WHERE chat_id=? AND created_at>=? AND created_at<=? AND delta>0
        ORDER BY id ASC
        """,
        (chat_id, int(event["starts_at"]), min(_now(), int(event["ends_at"]))),
    )
    added_total = 0
    for row in await cursor.fetchall():
        reason = str(row["reason"] or "")
        is_wager = _is_wager_win(reason)
        is_mini_app = _is_mini_app_reward(reason)
        if not is_wager and not is_mini_app:
            continue

        delta = int(row["delta"])
        desired = _share(delta)
        # Старый слой уже начислял Mini App через int(delta * 0.20), но ставки
        # полностью исключал. Добавляем только недостающую разницу.
        already_counted = max(0, int(delta * GAME_SHARE)) if is_mini_app else 0
        contribution = max(0, desired - already_counted)
        source_id = str(row["id"])

        async with core.db.lock:
            inserted = await conn.execute(
                """
                INSERT OR IGNORE INTO reality_event_sources_v96(
                    event_id,source_type,source_id,created_at
                ) VALUES(?,?,?,?)
                """,
                (event_id, "collective_game_v111", source_id, _now()),
            )
            if inserted.rowcount <= 0:
                await conn.commit()
                continue
            if contribution <= 0:
                await conn.commit()
                continue

            user_id = int(row["user_id"])
            await conn.execute(
                """
                INSERT OR IGNORE INTO reality_event_participants_v96(event_id,user_id)
                VALUES(?,?)
                """,
                (event_id, user_id),
            )
            await conn.execute(
                """
                UPDATE reality_event_participants_v96
                SET contribution=contribution+?
                WHERE event_id=? AND user_id=?
                """,
                (contribution, event_id, user_id),
            )
            await conn.execute(
                "UPDATE reality_events_v96 SET progress=progress+? WHERE event_id=?",
                (contribution, event_id),
            )
            await conn.commit()
            added_total += contribution
    return added_total


async def _edit_shared_card(core: Any, bot: Any, event: Any) -> None:
    if event is None or str(event["status"]) != "active":
        return
    message_id = int(event["message_id"] or 0)
    if message_id <= 0:
        return
    try:
        await bot.edit_message_text(
            chat_id=int(event["chat_id"]),
            message_id=message_id,
            text=await events._event_text(core, event, None),
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).casefold():
            LOGGER.warning("Не удалось обновить игровую карточку события: %s", exc)
    except TelegramForbiddenError:
        LOGGER.warning("Бот не может редактировать карточку события в чате %s", event["chat_id"])
    except Exception:
        LOGGER.exception("Ошибка обновления карточки события после игровой награды")


async def _refresh_chat(core: Any, bot: Any, chat_id: int) -> None:
    try:
        # Небольшая пауза позволяет игровому обработчику завершить транзакцию.
        await asyncio.sleep(0.25)
        event = await events._active_event(core, int(chat_id))
        if event is None:
            return
        await events._process_event(core, bot, event)
        refreshed = await events._event_by_id(core, str(event["event_id"]))
        await _edit_shared_card(core, bot, refreshed)
    except Exception:
        LOGGER.exception("Не удалось обновить событие после игры в чате %s", chat_id)
    finally:
        _REFRESH_TASKS.pop(int(chat_id), None)


def _queue_refresh(core: Any, bot: Any, chat_id: int) -> None:
    chat = int(chat_id)
    if chat >= 0:
        return
    current = _REFRESH_TASKS.get(chat)
    if current is not None and not current.done():
        return
    _REFRESH_TASKS[chat] = core.spawn_background_task(_refresh_chat(core, bot, chat))


def install_reality_event_games_v111(core: Any) -> None:
    if getattr(core, "_reality_event_games_v111_installed", False):
        return
    core._reality_event_games_v111_installed = True
    core.REALITY_EVENT_GAMES_VERSION = VERSION

    original_score_sources = events._process_score_sources

    async def process_score_sources_with_games(core_arg: Any, event: Any) -> None:
        await original_score_sources(core_arg, event)
        await _repair_game_contributions(core_arg, event)

    events._process_score_sources = process_score_sources_with_games

    original_event_text = events._event_text

    async def event_text_with_game_rule(
        core_arg: Any,
        event: Any,
        user_id: int | None,
    ) -> str:
        text = await original_event_text(core_arg, event, user_id)
        if str(event["event_key"]) != "collective" or str(event["status"]) != "active":
            return text
        rule = (
            "🎲 Игровой вклад: <b>20%</b> от положительного выигрыша в кубике, "
            "монетке и Mini App. Проигрыш общий прогресс не уменьшает."
        )
        if rule in text:
            return text
        return f"{text}\n\n{rule}"[:4096]

    events._event_text = event_text_with_game_rule

    runtime_bot: dict[str, Any] = {"bot": None}
    original_balance = core.Database.add_points_with_balance

    async def add_points_with_game_event_refresh(
        self: Any,
        chat_id: int,
        user_id: int,
        delta: int,
        reason: str,
        *args: Any,
        **kwargs: Any,
    ):
        result = await original_balance(
            self,
            chat_id,
            user_id,
            delta,
            reason,
            *args,
            **kwargs,
        )
        bot = runtime_bot["bot"]
        if (
            bot is not None
            and int(chat_id) < 0
            and int(delta) > 0
            and _is_supported_game_reward(reason)
        ):
            _queue_refresh(core, bot, int(chat_id))
        return result

    core.Database.add_points_with_balance = add_points_with_game_event_refresh

    original_start_server = core.start_webapp_server

    async def start_server_with_game_event_refresh(bot: Any):
        runtime_bot["bot"] = bot
        runner = await original_start_server(bot)
        LOGGER.info("%s активирован", VERSION)
        return runner

    core.start_webapp_server = start_server_with_game_event_refresh
    core.refresh_reality_event_after_game = lambda bot, chat_id: _queue_refresh(
        core, bot, int(chat_id)
    )
