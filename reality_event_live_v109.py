from __future__ import annotations

import asyncio
import html
import logging
import time
from typing import Any

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import Message

import reality_events_v96 as events


LOGGER = logging.getLogger(__name__)
VERSION = "Reality 119 · Автообновление карточек событий"
WATCH_INTERVAL = 2.0
IMMEDIATE_DELAY = 0.18
HEARTBEAT_SECONDS = 45

_RUNTIME_BOT: Any | None = None
_WATCHER_STARTED = False
_LAST_TEXT: dict[str, str] = {}
_LAST_EDIT_AT: dict[str, float] = {}
_CHAT_LOCKS: dict[int, asyncio.Lock] = {}
_SYNC_TASKS: dict[int, asyncio.Task[Any]] = {}
_DIRTY_CHATS: set[int] = set()


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


async def _participant_rows(core: Any, event_id: str) -> list[Any]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT p.*,COALESCE(pl.full_name,'Участник') AS full_name
        FROM reality_event_participants_v96 p
        LEFT JOIN reality_events_v96 e ON e.event_id=p.event_id
        LEFT JOIN players pl ON pl.chat_id=e.chat_id AND pl.user_id=p.user_id
        WHERE p.event_id=?
        ORDER BY p.user_id ASC
        """,
        (event_id,),
    )
    return list(await cursor.fetchall())


def _top_lines(rows: list[Any], field: str, *, suffix: str = "") -> list[str]:
    leaders = sorted(
        (row for row in rows if _safe_int(row[field]) > 0),
        key=lambda row: (_safe_int(row[field]), -_safe_int(row["user_id"])),
        reverse=True,
    )[:3]
    medals = ("🥇", "🥈", "🥉")
    return [
        f"{medals[index]} {html.escape(str(row['full_name']))} — "
        f"<b>{_safe_int(row[field])}{suffix}</b>"
        for index, row in enumerate(leaders)
    ]


async def _live_summary(core: Any, event: Any) -> str:
    rows = await _participant_rows(core, str(event["event_id"]))
    key = str(event["event_key"])
    lines: list[str] = ["🔄 <b>ЖИВОЙ ПРОГРЕСС</b>"]

    if key == "collective":
        contributors = [row for row in rows if _safe_int(row["contribution"]) > 0]
        total = sum(_safe_int(row["contribution"]) for row in contributors)
        lines.append(f"👥 Внесли влияние: <b>{len(contributors)}</b>")
        lines.append(f"⭐ Общий вклад: <b>{total}</b>")
        lines.extend(_top_lines(rows, "contribution"))
    elif key == "game_night":
        players = [row for row in rows if _safe_int(row["game_runs"]) > 0]
        runs = sum(_safe_int(row["game_runs"]) for row in players)
        lines.append(f"👥 Уникальных игроков: <b>{len(players)}</b>")
        lines.append(f"🎮 Засчитано забегов: <b>{runs}</b>")
        lines.extend(_top_lines(rows, "game_runs", suffix=" заб."))
    elif key == "boss_fall":
        fighters = [row for row in rows if _safe_int(row["boss_attacks"]) > 0]
        attacks = sum(_safe_int(row["boss_attacks"]) for row in fighters)
        damage = sum(_safe_int(row["boss_damage"]) for row in fighters)
        lines.append(f"⚔️ Бойцов: <b>{len(fighters)}</b>")
        lines.append(f"💢 Ударов: <b>{attacks}</b> · урон: <b>{damage}</b>")
        lines.extend(_top_lines(rows, "boss_damage", suffix=" урона"))
    elif key == "tree_awakening":
        influence = sum(1 for row in rows if _safe_int(row["influence_done"]) > 0)
        tasks = sum(1 for row in rows if _safe_int(row["task_done"]) > 0)
        action = sum(
            1
            for row in rows
            if _safe_int(row["game_runs"]) > 0 or _safe_int(row["boss_attacks"]) >= 5
        )
        completed = sum(1 for row in rows if _safe_int(row["completed"]) > 0)
        lines.extend(
            [
                f"⭐ Получили влияние: <b>{influence}</b>",
                f"🎯 Выполнили задание: <b>{tasks}</b>",
                f"🎮 Игра или 5 ударов: <b>{action}</b>",
                f"🌳 Завершили всё: <b>{completed}</b>",
            ]
        )
    elif key == "ego_tax":
        taxed = [row for row in rows if _safe_int(row["tax_amount"]) > 0]
        refunded = [row for row in taxed if _safe_int(row["tax_refunded"]) > 0]
        total_tax = sum(_safe_int(row["tax_amount"]) for row in taxed)
        returned = sum(_safe_int(row["tax_amount"]) for row in refunded)
        lines.append(f"🧾 Налог получили: <b>{len(taxed)}</b> участников · <b>{total_tax}</b> влияния")
        lines.append(f"✅ Вернули налог: <b>{len(refunded)}</b> · возвращено <b>{returned}</b>")
    elif key == "influence_day":
        players = [row for row in rows if _safe_int(row["event_bonus"]) > 0]
        total = sum(_safe_int(row["event_bonus"]) for row in players)
        lines.append(f"👥 Получили усиление: <b>{len(players)}</b>")
        lines.append(f"🔥 Дополнительно начислено: <b>{total}</b> влияния")
        lines.extend(_top_lines(rows, "event_bonus", suffix=" бонуса"))
    elif key == "popularity":
        rewarded = [row for row in rows if _safe_int(row["reward_influence"]) > 0]
        total = sum(_safe_int(row["reward_influence"]) for row in rewarded)
        lines.append(f"🌟 Награждено участников: <b>{len(rewarded)}</b>")
        lines.append(f"⭐ Выдано влияния: <b>{total}</b>")
    else:
        lines.append(f"👥 Участников: <b>{len(rows)}</b>")

    return "\n".join(lines)


async def _save_message_id(core: Any, event_id: str, message_id: int) -> None:
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.execute(
            "UPDATE reality_events_v96 SET message_id=? WHERE event_id=?",
            (int(message_id), str(event_id)),
        )
        await conn.commit()


async def _send_replacement_card(core: Any, bot: Any, event: Any, text: str) -> None:
    sent = await bot.send_message(int(event["chat_id"]), text)
    event_id = str(event["event_id"])
    await _save_message_id(core, event_id, int(sent.message_id))
    _LAST_TEXT[event_id] = text
    _LAST_EDIT_AT[event_id] = time.monotonic()


async def _edit_shared_card(core: Any, bot: Any, event: Any, *, force: bool = False) -> None:
    if event is None or str(event["status"]) != "active":
        return
    event_id = str(event["event_id"])
    text = await events._event_text(core, event, None)
    now = time.monotonic()
    if (
        not force
        and _LAST_TEXT.get(event_id) == text
        and now - _LAST_EDIT_AT.get(event_id, 0.0) < HEARTBEAT_SECONDS
    ):
        return

    message_id = _safe_int(event["message_id"])
    if message_id <= 0:
        await _send_replacement_card(core, bot, event, text)
        return

    try:
        await bot.edit_message_text(
            chat_id=_safe_int(event["chat_id"]),
            message_id=message_id,
            text=text,
        )
        _LAST_TEXT[event_id] = text
        _LAST_EDIT_AT[event_id] = now
    except TelegramBadRequest as exc:
        error = str(exc).casefold()
        if "message is not modified" in error:
            _LAST_TEXT[event_id] = text
            _LAST_EDIT_AT[event_id] = now
            return
        if any(
            marker in error
            for marker in (
                "message to edit not found",
                "message can't be edited",
                "message can not be edited",
            )
        ):
            try:
                await _send_replacement_card(core, bot, event, text)
            except Exception:
                LOGGER.exception("Не удалось восстановить карточку события %s", event_id)
            return
        LOGGER.warning("Не удалось обновить карточку события %s: %s", event_id, exc)
    except TelegramForbiddenError:
        LOGGER.warning("Бот не может редактировать карточку события %s", event_id)
    except Exception:
        LOGGER.exception("Ошибка автообновления карточки события %s", event_id)


async def _sync_chat_now(core: Any, bot: Any, chat_id: int, *, force: bool = False) -> None:
    chat = int(chat_id)
    if chat >= 0:
        return
    lock = _CHAT_LOCKS.setdefault(chat, asyncio.Lock())
    async with lock:
        try:
            async with events._PROCESS_LOCK:
                event = await events._active_event(core, chat)
                if event is None:
                    return
                await events._process_event(core, bot, event)
            refreshed = await events._active_event(core, chat)
            if refreshed is not None:
                await _edit_shared_card(core, bot, refreshed, force=force)
        except Exception:
            LOGGER.exception("Не удалось синхронизировать событие в чате %s", chat)


async def _queued_sync(core: Any, bot: Any, chat_id: int) -> None:
    chat = int(chat_id)
    try:
        while chat in _DIRTY_CHATS:
            _DIRTY_CHATS.discard(chat)
            await asyncio.sleep(IMMEDIATE_DELAY)
            await _sync_chat_now(core, bot, chat, force=True)
    finally:
        _SYNC_TASKS.pop(chat, None)
        if chat in _DIRTY_CHATS:
            _schedule_chat_sync(core, bot, chat)


def _schedule_chat_sync(core: Any, bot: Any, chat_id: int) -> None:
    chat = int(chat_id)
    if chat >= 0:
        return
    _DIRTY_CHATS.add(chat)
    current = _SYNC_TASKS.get(chat)
    if current is not None and not current.done():
        return
    _SYNC_TASKS[chat] = core.spawn_background_task(_queued_sync(core, bot, chat))


async def _watch_loop(core: Any, bot: Any) -> None:
    await asyncio.sleep(3)
    while True:
        try:
            conn = core.db._require_connection()
            cursor = await conn.execute(
                "SELECT DISTINCT chat_id FROM reality_events_v96 WHERE status='active'"
            )
            chats = [int(row["chat_id"]) for row in await cursor.fetchall()]
            for chat_id in chats:
                await _sync_chat_now(core, bot, chat_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Ошибка сторожа ежедневных событий")
        await asyncio.sleep(WATCH_INTERVAL)


def _install_event_start_override(core: Any, bot: Any) -> None:
    if getattr(core, "_event_start_card_v119_installed", False):
        return
    handlers = core.router.message.handlers
    old_handler = next(
        (
            handler
            for handler in handlers
            if getattr(handler.callback, "__name__", "") == "cmd_event_start_v98"
        ),
        None,
    )
    if old_handler is None:
        return
    original_callback = old_handler.callback
    handlers[:] = [handler for handler in handlers if handler is not old_handler]

    @core.router.message(Command("event_start", "start_event", "event_vote"))
    async def cmd_event_start_card_v119(message: Message, bot: Any) -> None:
        if not message.from_user or not core.is_group(message):
            return
        chat_id = int(message.chat.id)
        active = await events._active_event(core, chat_id)
        if active is None:
            await original_callback(message, bot)
            return

        await core.db.upsert_player(chat_id, message.from_user)
        await events._ensure_participant(
            core,
            str(active["event_id"]),
            int(message.from_user.id),
        )
        await _sync_chat_now(core, bot, chat_id, force=True)
        notice = (
            "🌠 Событие уже запущено. Общая карточка обновлена и дальше "
            "обновляется автоматически — повторно запускать её не нужно."
        )
        ephemeral = getattr(core, "ephemeral_reply", None)
        if callable(ephemeral):
            try:
                await ephemeral(message, notice, delay_seconds=5)
                return
            except Exception:
                pass
        await message.answer(notice)

    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_event_start_card_v119"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
    core._event_start_card_v119_installed = True


def install_reality_event_live_v109(core: Any) -> None:
    if getattr(core, "_reality_event_live_v109_installed", False):
        return
    core._reality_event_live_v109_installed = True
    core.REALITY_EVENT_LIVE_VERSION = VERSION
    events.PROCESS_INTERVAL = min(_safe_int(getattr(events, "PROCESS_INTERVAL", 2)) or 2, 2)

    original_event_text = events._event_text

    async def event_text_with_live_summary(
        core_arg: Any,
        event: Any,
        user_id: int | None,
    ) -> str:
        base = await original_event_text(core_arg, event, user_id)
        if str(event["status"]) != "active":
            return base
        try:
            summary = await _live_summary(core_arg, event)
        except Exception:
            LOGGER.exception("Не удалось построить сводку события %s", event["event_id"])
            return base
        return f"{base}\n\n{summary}"[:4096]

    events._event_text = event_text_with_live_summary

    async def update_message_live(core_arg: Any, bot_arg: Any, event: Any) -> None:
        await _edit_shared_card(core_arg, bot_arg, event, force=True)

    events._update_message = update_message_live

    original_add_points = core.Database.add_points

    async def add_points_with_event_refresh(
        self: Any,
        chat_id: int,
        user_id: int,
        delta: int,
        reason: str,
        *args: Any,
        **kwargs: Any,
    ):
        result = await original_add_points(
            self,
            chat_id,
            user_id,
            delta,
            reason,
            *args,
            **kwargs,
        )
        if (
            _RUNTIME_BOT is not None
            and int(chat_id) < 0
            and not str(reason or "").startswith("reality_event_")
        ):
            _schedule_chat_sync(core, _RUNTIME_BOT, int(chat_id))
        return result

    core.Database.add_points = add_points_with_event_refresh

    original_balance = getattr(core.Database, "add_points_with_balance", None)
    if original_balance is not None:
        async def add_points_with_balance_event_refresh(
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
            if (
                _RUNTIME_BOT is not None
                and int(chat_id) < 0
                and not str(reason or "").startswith("reality_event_")
            ):
                _schedule_chat_sync(core, _RUNTIME_BOT, int(chat_id))
            return result

        core.Database.add_points_with_balance = add_points_with_balance_event_refresh

    original_start_server = core.start_webapp_server

    async def start_server_with_live_event_updates(bot_arg: Any):
        global _RUNTIME_BOT, _WATCHER_STARTED
        _RUNTIME_BOT = bot_arg
        _install_event_start_override(core, bot_arg)
        runner = await original_start_server(bot_arg)
        if not _WATCHER_STARTED:
            _WATCHER_STARTED = True
            core.spawn_background_task(_watch_loop(core, bot_arg))
        LOGGER.info("%s активирован", VERSION)
        return runner

    core.start_webapp_server = start_server_with_live_event_updates
    core.refresh_reality_event_message = lambda bot_arg, chat_id: _schedule_chat_sync(
        core,
        bot_arg,
        int(chat_id),
    )
