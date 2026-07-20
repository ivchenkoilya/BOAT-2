from __future__ import annotations

import html
from typing import Any

from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message

import reality_events_v96 as events


VERSION = "Reality 110 · Единая карточка события"


def _value(row: Any, key: str) -> int:
    try:
        return int(row[key] or 0)
    except (TypeError, ValueError, KeyError, IndexError):
        return 0


async def _personal_status(core: Any, event: Any, user_id: int) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT * FROM reality_event_participants_v96
        WHERE event_id=? AND user_id=?
        """,
        (str(event["event_id"]), int(user_id)),
    )
    row = await cursor.fetchone()
    info = events._event_info(str(event["event_key"]))
    title = html.escape(str(info.get("title") or "Событие реальности"))
    lines = [f"👤 <b>ТВОЙ ПРОГРЕСС · {title.upper()}</b>"]

    if row is None:
        lines.append("Твой вклад пока не зафиксирован.")
        return "\n\n".join(lines)

    key = str(event["event_key"])
    if key == "collective":
        contribution = _value(row, "contribution")
        lines.extend(
            [
                f"⭐ Личный вклад: <b>{contribution}</b>",
                "🏆 От 100 — +200 влияния · от 500 — ещё +1 очко Древа.",
            ]
        )
    elif key == "game_night":
        lines.append(f"🎮 Засчитано забегов: <b>{_value(row, 'game_runs')}/5</b>")
    elif key == "boss_fall":
        lines.extend(
            [
                f"⚔️ Ударов: <b>{_value(row, 'boss_attacks')}</b>",
                f"💢 Урон: <b>{_value(row, 'boss_damage')}</b>",
            ]
        )
    elif key == "tree_awakening":
        action_done = _value(row, "game_runs") > 0 or _value(row, "boss_attacks") >= 5
        lines.extend(
            [
                f"{'✅' if _value(row, 'influence_done') else '⬜'} Получить влияние",
                f"{'✅' if _value(row, 'task_done') else '⬜'} Выполнить задание",
                f"{'✅' if action_done else '⬜'} Завершить игру или нанести 5 ударов",
                f"🌳 Награда получена: <b>{'да' if _value(row, 'completed') else 'нет'}</b>",
            ]
        )
    elif key == "ego_tax":
        tax = _value(row, "tax_amount")
        refunded = bool(_value(row, "tax_refunded"))
        lines.extend(
            [
                f"🧾 Твой налог: <b>{tax}</b>",
                f"{'✅ Возвращён' if refunded else '⏳ Ещё можно вернуть'}",
            ]
        )
    elif key == "influence_day":
        lines.append(f"🔥 Получено бонусом события: <b>+{_value(row, 'event_bonus')}/500</b>")
    elif key == "popularity":
        lines.append(f"🌟 Получено от события: <b>+{_value(row, 'reward_influence')}</b>")
    else:
        lines.append("Участие зафиксировано.")

    lines.append("🔄 Общая карточка события обновлена в беседе.")
    return "\n".join(lines)


async def _refresh_shared_card(core: Any, bot: Any, event: Any) -> Any:
    chat_id = int(event["chat_id"])
    event_id = str(event["event_id"])

    # Сначала собираем все новые источники: влияние, игры, задания и рейд.
    await events._process_event(core, bot, event)
    refreshed = await events._event_by_id(core, event_id)
    if refreshed is None:
        return event

    if str(refreshed["status"]) != "active":
        return refreshed

    text = await events._event_text(core, refreshed, None)
    message_id = _value(refreshed, "message_id")
    if message_id > 0:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
            )
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).casefold():
                raise
    else:
        sent = await bot.send_message(chat_id, text)
        conn = core.db._require_connection()
        async with core.db.lock:
            await conn.execute(
                "UPDATE reality_events_v96 SET message_id=? WHERE event_id=?",
                (int(sent.message_id), event_id),
            )
            await conn.commit()
        refreshed = await events._event_by_id(core, event_id) or refreshed

    return refreshed


def install_reality_event_view_v110(core: Any) -> None:
    if getattr(core, "_reality_event_view_v110_installed", False):
        return
    core._reality_event_view_v110_installed = True
    core.REALITY_EVENT_VIEW_VERSION = VERSION

    @core.router.message(Command("event", "events", "reality_event"))
    async def cmd_event_view_v110(message: Message, bot: Any) -> None:
        if not message.from_user or not core.is_group(message):
            return

        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        event = await events._active_event(core, chat_id)

        if event is None:
            # Старый обработчик Reality 97, стоящий следом, опубликует голосование.
            return

        await events._ensure_participant(
            core,
            str(event["event_id"]),
            int(message.from_user.id),
        )
        refreshed = await _refresh_shared_card(core, bot, event)
        await message.answer(
            await _personal_status(core, refreshed, int(message.from_user.id))
        )

    # Ставим новый обработчик раньше старого /event Reality 97.
    handlers = core.router.message.handlers
    own = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_event_view_v110"
    ]
    handlers[:] = own + [handler for handler in handlers if handler not in own]
