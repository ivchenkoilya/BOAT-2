from __future__ import annotations

import asyncio
import html
import logging
from typing import Any

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

import reality_events_v96 as events


LOGGER = logging.getLogger(__name__)
VERSION = "Reality 109 · Живые события"
LIVE_PROCESS_INTERVAL = 2
EDIT_DEBOUNCE_SECONDS = 1.2

_LAST_FINGERPRINTS: dict[str, tuple[Any, ...]] = {}
_PENDING_EDITS: dict[str, asyncio.Task[Any]] = {}
_SYNC_TASKS: dict[int, asyncio.Task[Any]] = {}


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


async def _event_fingerprint(core: Any, event: Any) -> tuple[Any, ...]:
    event_id = str(event["event_id"])
    rows = await _participant_rows(core, event_id)
    participant_state = tuple(
        (
            _safe_int(row["user_id"]),
            _safe_int(row["contribution"]),
            _safe_int(row["game_runs"]),
            _safe_int(row["task_done"]),
            _safe_int(row["influence_done"]),
            _safe_int(row["boss_attacks"]),
            _safe_int(row["boss_damage"]),
            _safe_int(row["event_bonus"]),
            _safe_int(row["tax_amount"]),
            _safe_int(row["tax_refunded"]),
            _safe_int(row["reward_influence"]),
            _safe_int(row["reward_tree"]),
            _safe_int(row["completed"]),
        )
        for row in rows
    )
    return (
        str(event["status"]),
        _safe_int(event["progress"]),
        _safe_int(event["target"]),
        str(event["meta_json"] or ""),
        str(event["result_text"] or ""),
        participant_state,
    )


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


async def _edit_event_message_now(core: Any, bot: Any, event_id: str) -> None:
    event = await events._event_by_id(core, event_id)
    if event is None or str(event["status"]) != "active":
        return
    message_id = _safe_int(event["message_id"])
    if message_id <= 0:
        return
    try:
        await bot.edit_message_text(
            chat_id=_safe_int(event["chat_id"]),
            message_id=message_id,
            text=await events._event_text(core, event, None),
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).casefold():
            LOGGER.warning("Не удалось обновить карточку события %s: %s", event_id, exc)
    except TelegramForbiddenError:
        LOGGER.warning("Бот больше не может редактировать событие %s", event_id)
    except Exception:
        LOGGER.exception("Ошибка живого обновления события %s", event_id)


async def _delayed_edit(core: Any, bot: Any, event_id: str) -> None:
    try:
        await asyncio.sleep(EDIT_DEBOUNCE_SECONDS)
        await _edit_event_message_now(core, bot, event_id)
    finally:
        _PENDING_EDITS.pop(event_id, None)


def _schedule_edit(core: Any, bot: Any, event_id: str) -> None:
    current = _PENDING_EDITS.get(event_id)
    if current is not None and not current.done():
        return
    task = core.spawn_background_task(_delayed_edit(core, bot, event_id))
    _PENDING_EDITS[event_id] = task


async def _sync_chat(core: Any, bot: Any, chat_id: int) -> None:
    try:
        event = await events._active_event(core, chat_id)
        if event is not None:
            await events._process_event(core, bot, event)
    except Exception:
        LOGGER.exception("Не удалось синхронизировать живое событие в чате %s", chat_id)
    finally:
        _SYNC_TASKS.pop(chat_id, None)


def _schedule_chat_sync(core: Any, bot: Any, chat_id: int) -> None:
    if int(chat_id) >= 0:
        return
    current = _SYNC_TASKS.get(int(chat_id))
    if current is not None and not current.done():
        return
    task = core.spawn_background_task(_sync_chat(core, bot, int(chat_id)))
    _SYNC_TASKS[int(chat_id)] = task


def install_reality_event_live_v109(core: Any) -> None:
    if getattr(core, "_reality_event_live_v109_installed", False):
        return
    core._reality_event_live_v109_installed = True
    core.REALITY_EVENT_LIVE_VERSION = VERSION
    events.PROCESS_INTERVAL = LIVE_PROCESS_INTERVAL

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
            LOGGER.exception("Не удалось построить живую сводку события %s", event["event_id"])
            return base
        return f"{base}\n\n{summary}"[:4096]

    events._event_text = event_text_with_live_summary

    original_update_message = events._update_message

    async def update_message_live(core_arg: Any, bot: Any, event: Any) -> None:
        if str(event["status"]) != "active" or _safe_int(event["message_id"]) <= 0:
            return
        _schedule_edit(core_arg, bot, str(event["event_id"]))

    events._update_message = update_message_live

    original_process_event = events._process_event

    async def process_event_live(core_arg: Any, bot: Any, event: Any) -> None:
        event_id = str(event["event_id"])
        await original_process_event(core_arg, bot, event)
        refreshed = await events._event_by_id(core_arg, event_id)
        if refreshed is None:
            _LAST_FINGERPRINTS.pop(event_id, None)
            return
        fingerprint = await _event_fingerprint(core_arg, refreshed)
        previous = _LAST_FINGERPRINTS.get(event_id)
        _LAST_FINGERPRINTS[event_id] = fingerprint
        if str(refreshed["status"]) == "active" and fingerprint != previous:
            _schedule_edit(core_arg, bot, event_id)

    events._process_event = process_event_live

    # В Reality 97 начисления через add_points уже запускают быструю синхронизацию.
    # Здесь дополнительно охватываем add_points_with_balance, которым пользуются
    # команды, задания и многие награды новых модулей.
    runtime_bot: dict[str, Any] = {"bot": None}
    balance_method = getattr(core.Database, "add_points_with_balance", None)
    if balance_method is not None:
        async def add_points_with_live_refresh(
            self: Any,
            chat_id: int,
            user_id: int,
            delta: int,
            reason: str,
            *args: Any,
            **kwargs: Any,
        ):
            result = await balance_method(
                self,
                chat_id,
                user_id,
                delta,
                reason,
                *args,
                **kwargs,
            )
            bot = runtime_bot["bot"]
            if bot is not None and int(chat_id) < 0 and not str(reason or "").startswith("reality_event_"):
                _schedule_chat_sync(core, bot, int(chat_id))
            return result

        core.Database.add_points_with_balance = add_points_with_live_refresh

    original_start_server = core.start_webapp_server

    async def start_server_with_live_event_updates(bot: Any):
        runtime_bot["bot"] = bot
        runner = await original_start_server(bot)
        LOGGER.info("%s активирован", VERSION)
        return runner

    core.start_webapp_server = start_server_with_live_event_updates
    core.refresh_reality_event_message = lambda bot, chat_id: _schedule_chat_sync(
        core, bot, int(chat_id)
    )
