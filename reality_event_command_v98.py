from __future__ import annotations

import random
from typing import Any

from aiogram.filters import Command
from aiogram.types import BotCommand, Message

import reality_event_vote_v97 as voting
import reality_events_v96 as events


VERSION = "Reality 98 · Команда запуска события"


async def _selected_participant_bonus(
    core: Any,
    chat_id: int,
    event: Any,
    chosen_id: int,
) -> None:
    event_id = str(event["event_id"])
    if str(event["event_key"]) == "ego_tax":
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT tax_amount FROM reality_event_participants_v96
            WHERE event_id=? AND user_id=?
            """,
            (event_id, chosen_id),
        )
        row = await cursor.fetchone()
        tax = int(row["tax_amount"] or 0) if row else 0
        relief = tax // 2
        if relief <= 0:
            return
        await core.db.add_points(
            chat_id,
            chosen_id,
            relief,
            f"reality_event_{event_id}_chosen_tax_relief",
        )
        async with core.db.lock:
            await conn.execute(
                """
                UPDATE reality_event_participants_v96
                SET tax_amount=MAX(0,tax_amount-?)
                WHERE event_id=? AND user_id=?
                """,
                (relief, event_id, chosen_id),
            )
            await conn.commit()
        return

    await events._award_influence_once(
        core,
        chat_id,
        chosen_id,
        100,
        event_id,
        "chosen_participant",
    )


async def _launch_after_command_votes(
    core: Any,
    bot: Any,
    chat_id: int,
    day: str,
    voters: list[Any],
) -> Any | None:
    conn = core.db._require_connection()

    # Один процесс получает право запуска. Остальные команды увидят уже
    # активное событие и не смогут создать дубликат.
    async with core.db.lock:
        cursor = await conn.execute(
            """
            UPDATE reality_event_launches_v97
            SET status='launching',updated_at=?
            WHERE chat_id=? AND date_key=? AND status='voting'
            """,
            (voting._now(), chat_id, day),
        )
        await conn.commit()
        if cursor.rowcount <= 0:
            return await events._active_event(core, chat_id)

    players = await voting._active_players(core, chat_id)
    pool = players or voters
    chosen_id = int(random.choice(pool)["user_id"])

    try:
        event = await events._start_event(core, bot, chat_id, forced=True)
    except Exception:
        async with core.db.lock:
            await conn.execute(
                """
                UPDATE reality_event_launches_v97
                SET status='voting',updated_at=?
                WHERE chat_id=? AND date_key=? AND status='launching'
                """,
                (voting._now(), chat_id, day),
            )
            await conn.commit()
        raise

    async with core.db.lock:
        await conn.execute(
            """
            UPDATE reality_event_launches_v97
            SET status='launched',chosen_user_id=?,event_id=?,
                launched_at=?,updated_at=?
            WHERE chat_id=? AND date_key=?
            """,
            (
                chosen_id,
                str(event["event_id"]),
                voting._now(),
                voting._now(),
                chat_id,
                day,
            ),
        )
        await conn.commit()

    await _selected_participant_bonus(core, chat_id, event, chosen_id)

    launch = await voting._launch_row(core, chat_id, day)
    message_id = int(launch["message_id"] or 0) if launch else 0
    text = await voting._launch_text(core, chat_id, day)
    try:
        if message_id:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
            )
        else:
            sent = await bot.send_message(chat_id, text)
            async with core.db.lock:
                await conn.execute(
                    """
                    UPDATE reality_event_launches_v97
                    SET message_id=?,updated_at=?
                    WHERE chat_id=? AND date_key=?
                    """,
                    (int(sent.message_id), voting._now(), chat_id, day),
                )
                await conn.commit()
    except Exception:
        pass

    return event


def install_reality_event_command_v98(core: Any) -> None:
    if getattr(core, "_reality_event_command_v98_installed", False):
        return
    core._reality_event_command_v98_installed = True
    core.BOT_VERSION = VERSION

    @core.router.message(Command("event_start", "start_event", "event_vote"))
    async def cmd_event_start_v98(message: Message, bot: Any) -> None:
        if not message.from_user or not core.is_group(message):
            return

        chat_id = int(message.chat.id)
        user_id = int(message.from_user.id)
        await core.db.upsert_player(chat_id, message.from_user)

        active = await events._active_event(core, chat_id)
        if active is not None:
            await voting._sync_event_now(core, bot, chat_id)
            refreshed = await events._active_event(core, chat_id)
            if refreshed is not None:
                await events._ensure_participant(
                    core,
                    str(refreshed["event_id"]),
                    user_id,
                )
                await message.answer(
                    "🌠 Сегодняшнее событие уже запущено.\n\n"
                    + await events._event_text(core, refreshed, user_id)
                )
            return

        day = voting._date_key()
        required = await voting._required_votes(core, chat_id)
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
                (chat_id, day, required, voting._now(), voting._now()),
            )
            cursor = await conn.execute(
                """
                INSERT OR IGNORE INTO reality_event_votes_v97(
                    chat_id,date_key,user_id,created_at
                ) VALUES(?,?,?,?)
                """,
                (chat_id, day, user_id, voting._now()),
            )
            inserted = cursor.rowcount > 0
            await conn.commit()

        voters = await voting._vote_rows(core, chat_id, day)
        if len(voters) < required:
            await voting._ensure_launch(core, bot, chat_id)
            left = required - len(voters)
            if inserted:
                await message.answer(
                    f"🗳 Твой голос за событие дня принят: "
                    f"<b>{len(voters)}/{required}</b>. Осталось: <b>{left}</b>."
                )
            else:
                await message.answer(
                    f"🗳 Ты уже голосовал сегодня. Сейчас: "
                    f"<b>{len(voters)}/{required}</b>."
                )
            return

        try:
            event = await _launch_after_command_votes(
                core,
                bot,
                chat_id,
                day,
                voters,
            )
        except Exception as exc:
            await message.answer(f"⚠️ Не удалось запустить событие: {exc}")
            return

        if event is None:
            await message.answer("🌠 Событие уже запускается другим участником.")
            return

        await message.answer(
            "🌌 <b>Голоса собраны — событие дня запущено!</b>\n"
            "Бот случайно выбрал участника и событие."
        )

    original_commands = core.group_bot_commands

    def commands_with_event_start() -> list[BotCommand]:
        commands = original_commands()
        if not any(command.command == "event_start" for command in commands):
            index = next(
                (
                    position + 1
                    for position, command in enumerate(commands)
                    if command.command == "event"
                ),
                len(commands),
            )
            commands.insert(
                index,
                BotCommand(
                    command="event_start",
                    description="Проголосовать за запуск события дня",
                ),
            )
        return commands

    core.group_bot_commands = commands_with_event_start

    # Общий обработчик текста в main.py зарегистрирован раньше расширений.
    # Поднимаем новую команду в начало списка, чтобы её не перехватили.
    handlers = core.router.message.handlers
    command_handlers = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_event_start_v98"
    ]
    handlers[:] = command_handlers + [
        handler for handler in handlers if handler not in command_handlers
    ]
