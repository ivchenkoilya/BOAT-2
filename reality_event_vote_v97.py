from __future__ import annotations

import asyncio
import html
import random
import time
from datetime import datetime, timezone
from typing import Any

from aiogram import F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import reality_events_v96 as events


VERSION = "Reality 97 · Голосование событий"
ACTIVE_WINDOW = 7 * 24 * 60 * 60
LIVE_INTERVAL = 5
_LIVE_LOCK = asyncio.Lock()
_RUNTIME_BOT: Any | None = None


def _now() -> int:
    return int(time.time())


def _date_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _vote_keyboard(date_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🌌 Поддержать запуск",
                callback_data=f"eventv97:{date_key}",
            )
        ]]
    )


async def _active_players(core: Any, chat_id: int) -> list[Any]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT user_id,full_name,username,points,message_count
        FROM players
        WHERE chat_id=? AND updated_at>=?
        ORDER BY message_count DESC,points DESC
        """,
        (chat_id, _now() - ACTIVE_WINDOW),
    )
    return list(await cursor.fetchall())


async def _launch_row(core: Any, chat_id: int, date_key: str | None = None) -> Any | None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM reality_event_launches_v97 WHERE chat_id=? AND date_key=?",
        (chat_id, date_key or _date_key()),
    )
    return await cursor.fetchone()


async def _vote_rows(core: Any, chat_id: int, date_key: str | None = None) -> list[Any]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT v.user_id,COALESCE(p.full_name,'Участник') full_name
        FROM reality_event_votes_v97 v
        LEFT JOIN players p ON p.chat_id=v.chat_id AND p.user_id=v.user_id
        WHERE v.chat_id=? AND v.date_key=?
        ORDER BY v.created_at ASC
        """,
        (chat_id, date_key or _date_key()),
    )
    return list(await cursor.fetchall())


async def _required_votes(core: Any, chat_id: int) -> int:
    amount = len(await _active_players(core, chat_id))
    return max(1, min(3, amount or 1))


async def _launch_text(core: Any, chat_id: int, date_key: str | None = None) -> str:
    day = date_key or _date_key()
    row = await _launch_row(core, chat_id, day)
    votes = await _vote_rows(core, chat_id, day)
    required = int(row["required_votes"]) if row else await _required_votes(core, chat_id)
    names = "\n".join(
        f"• <a href=\"tg://user?id={int(item['user_id'])}\">{html.escape(str(item['full_name']))}</a>"
        for item in votes
    ) or "• Пока никто"

    if row is not None and str(row["status"]) == "launched":
        chosen_id = int(row["chosen_user_id"] or 0)
        chosen = "случайный участник"
        if chosen_id:
            conn = core.db._require_connection()
            cursor = await conn.execute(
                "SELECT full_name FROM players WHERE chat_id=? AND user_id=?",
                (chat_id, chosen_id),
            )
            player = await cursor.fetchone()
            if player:
                chosen = (
                    f'<a href="tg://user?id={chosen_id}">'
                    f'{html.escape(str(player["full_name"]))}</a>'
                )
        return (
            "🌠 <b>РЕАЛЬНОСТЬ ПРОБУДИЛАСЬ</b>\n\n"
            f"Голосов собрано: <b>{len(votes)}/{required}</b>.\n"
            f"Сегодня реальность выбрала: {chosen}.\n\n"
            "Текущее событие уже опубликовано отдельным сообщением."
        )

    return (
        "🌠 <b>СОБЫТИЕ РЕАЛЬНОСТИ ДОСТУПНО</b>\n\n"
        "Участники сами решают, когда запустить сегодняшнее событие. "
        "После нужного количества голосов бот случайно выберет участника дня "
        "и одно из событий.\n\n"
        f"🗳 Голосов: <b>{len(votes)}/{required}</b>\n"
        f"Нажали:\n{names}"
    )


async def _ensure_launch(core: Any, bot: Any, chat_id: int, *, send_new: bool = False) -> Any:
    if await events._active_event(core, chat_id) is not None:
        return None
    day = _date_key()
    required = await _required_votes(core, chat_id)
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.execute(
            """
            INSERT INTO reality_event_launches_v97(
                chat_id,date_key,status,required_votes,created_at,updated_at
            ) VALUES(?,?,'voting',?,?,?)
            ON CONFLICT(chat_id,date_key) DO UPDATE SET
                required_votes=excluded.required_votes,
                updated_at=excluded.updated_at
            """,
            (chat_id, day, required, _now(), _now()),
        )
        await conn.commit()
    row = await _launch_row(core, chat_id, day)
    message_id = int(row["message_id"] or 0) if row else 0
    text = await _launch_text(core, chat_id, day)
    if send_new or not message_id:
        sent = await bot.send_message(chat_id, text, reply_markup=_vote_keyboard(day))
        async with core.db.lock:
            await conn.execute(
                "UPDATE reality_event_launches_v97 SET message_id=?,updated_at=? WHERE chat_id=? AND date_key=?",
                (int(sent.message_id), _now(), chat_id, day),
            )
            await conn.commit()
        return sent
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=_vote_keyboard(day),
        )
    except Exception:
        pass
    return row


async def _sync_event_now(core: Any, bot: Any, chat_id: int) -> None:
    event = await events._active_event(core, chat_id)
    if event is None:
        return
    async with _LIVE_LOCK:
        await events._process_event(core, bot, event)


def install_reality_event_vote_v97(core: Any) -> None:
    global _RUNTIME_BOT
    if getattr(core, "_reality_event_vote_v97_installed", False):
        return
    core._reality_event_vote_v97_installed = True
    core.BOT_VERSION = VERSION
    events.PROCESS_INTERVAL = LIVE_INTERVAL

    original_connect = core.Database.connect

    async def connect_with_votes(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS reality_event_launches_v97(
                    chat_id INTEGER NOT NULL,
                    date_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'voting',
                    required_votes INTEGER NOT NULL DEFAULT 3,
                    message_id INTEGER,
                    chosen_user_id INTEGER,
                    event_id TEXT,
                    created_at INTEGER NOT NULL,
                    launched_at INTEGER,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY(chat_id,date_key)
                );
                CREATE TABLE IF NOT EXISTS reality_event_votes_v97(
                    chat_id INTEGER NOT NULL,
                    date_key TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY(chat_id,date_key,user_id)
                );
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_votes

    original_add_points = core.Database.add_points

    async def add_points_with_live_event(
        self: Any,
        chat_id: int,
        user_id: int,
        delta: int,
        reason: str,
        *,
        update_reward_time: bool = False,
    ):
        result = await original_add_points(
            self,
            chat_id,
            user_id,
            delta,
            reason,
            update_reward_time=update_reward_time,
        )
        if (
            _RUNTIME_BOT is not None
            and int(chat_id) < 0
            and not str(reason or "").startswith("reality_event_")
        ):
            core.spawn_background_task(_sync_event_now(core, _RUNTIME_BOT, int(chat_id)))
        return result

    core.Database.add_points = add_points_with_live_event

    original_start_server = core.start_webapp_server

    async def start_server_with_live_events(bot: Any):
        global _RUNTIME_BOT
        _RUNTIME_BOT = bot
        return await original_start_server(bot)

    core.start_webapp_server = start_server_with_live_events

    async def participant_daily_launch(core_arg: Any, bot: Any) -> None:
        now = _now()
        current = datetime.fromtimestamp(now, timezone.utc)
        if current.hour < int(events.LAUNCH_HOUR_UTC):
            return
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT DISTINCT chat_id FROM players
            WHERE chat_id<0 AND updated_at>=?
            """,
            (now - ACTIVE_WINDOW,),
        )
        for row in await cursor.fetchall():
            chat_id = int(row["chat_id"])
            if await events._active_event(core_arg, chat_id) is not None:
                continue
            settings_cursor = await conn.execute(
                "SELECT enabled FROM reality_event_settings_v96 WHERE chat_id=?",
                (chat_id,),
            )
            settings = await settings_cursor.fetchone()
            if settings is not None and not int(settings["enabled"]):
                continue
            launch = await _launch_row(core_arg, chat_id)
            if launch is None:
                try:
                    await _ensure_launch(core_arg, bot, chat_id)
                except Exception:
                    pass

    events._daily_launch = participant_daily_launch

    @core.router.message(Command("event", "events", "reality_event"))
    async def cmd_event_vote_v97(message: Message, bot: Any) -> None:
        if not message.from_user or not core.is_group(message):
            return
        await core.db.upsert_player(message.chat.id, message.from_user)
        event = await events._active_event(core, message.chat.id)
        if event is not None:
            await _sync_event_now(core, bot, message.chat.id)
            refreshed = await events._active_event(core, message.chat.id)
            if refreshed is not None:
                await events._ensure_participant(
                    core,
                    str(refreshed["event_id"]),
                    message.from_user.id,
                )
                await message.answer(
                    await events._event_text(
                        core,
                        refreshed,
                        message.from_user.id,
                    )
                )
            return
        await _ensure_launch(core, bot, message.chat.id, send_new=True)

    @core.router.callback_query(F.data.startswith("eventv97:"))
    async def vote_event_v97(callback: CallbackQuery, bot: Any) -> None:
        if not callback.from_user or not callback.message:
            await callback.answer()
            return
        chat_id = int(callback.message.chat.id)
        if chat_id >= 0:
            await callback.answer("Голосование работает только в беседе.", show_alert=True)
            return
        day = str(callback.data or "").split(":", 1)[-1]
        if day != _date_key():
            await callback.answer("Это голосование уже закончилось.", show_alert=True)
            return
        if await events._active_event(core, chat_id) is not None:
            await callback.answer("Сегодняшнее событие уже запущено.", show_alert=True)
            return

        await core.db.upsert_player(chat_id, callback.from_user)
        conn = core.db._require_connection()
        required = await _required_votes(core, chat_id)
        async with core.db.lock:
            await conn.execute(
                """
                INSERT INTO reality_event_launches_v97(
                    chat_id,date_key,status,required_votes,created_at,updated_at
                ) VALUES(?,?,'voting',?,?,?)
                ON CONFLICT(chat_id,date_key) DO UPDATE SET
                    required_votes=excluded.required_votes,
                    updated_at=excluded.updated_at
                """,
                (chat_id, day, required, _now(), _now()),
            )
            cursor = await conn.execute(
                "INSERT OR IGNORE INTO reality_event_votes_v97(chat_id,date_key,user_id,created_at) VALUES(?,?,?,?)",
                (chat_id, day, int(callback.from_user.id), _now()),
            )
            inserted = cursor.rowcount > 0
            await conn.commit()

        votes = await _vote_rows(core, chat_id, day)
        if len(votes) < required:
            try:
                await callback.message.edit_text(
                    await _launch_text(core, chat_id, day),
                    reply_markup=_vote_keyboard(day),
                )
            except Exception:
                pass
            await callback.answer(
                "Голос принят." if inserted else "Ты уже голосовал.",
                show_alert=False,
            )
            return

        players = await _active_players(core, chat_id)
        chosen_id = int(random.choice(players)["user_id"]) if players else int(random.choice(votes)["user_id"])
        try:
            event = await events._start_event(core, bot, chat_id, forced=True)
        except ValueError as exc:
            await callback.answer(str(exc), show_alert=True)
            return

        async with core.db.lock:
            await conn.execute(
                """
                UPDATE reality_event_launches_v97
                SET status='launched',chosen_user_id=?,event_id=?,launched_at=?,updated_at=?
                WHERE chat_id=? AND date_key=?
                """,
                (
                    chosen_id,
                    str(event["event_id"]),
                    _now(),
                    _now(),
                    chat_id,
                    day,
                ),
            )
            await conn.commit()

        if str(event["event_key"]) == "ego_tax":
            cursor = await conn.execute(
                "SELECT tax_amount FROM reality_event_participants_v96 WHERE event_id=? AND user_id=?",
                (str(event["event_id"]), chosen_id),
            )
            tax_row = await cursor.fetchone()
            tax = int(tax_row["tax_amount"] or 0) if tax_row else 0
            relief = tax // 2
            if relief > 0:
                await core.db.add_points(
                    chat_id,
                    chosen_id,
                    relief,
                    f"reality_event_{event['event_id']}_chosen_tax_relief",
                )
                async with core.db.lock:
                    await conn.execute(
                        "UPDATE reality_event_participants_v96 SET tax_amount=tax_amount-? WHERE event_id=? AND user_id=?",
                        (relief, str(event["event_id"]), chosen_id),
                    )
                    await conn.commit()
        else:
            await events._award_influence_once(
                core,
                chat_id,
                chosen_id,
                100,
                str(event["event_id"]),
                "chosen_participant",
            )

        try:
            await callback.message.edit_text(await _launch_text(core, chat_id, day))
        except Exception:
            pass
        await callback.answer("Событие запущено!", show_alert=True)
