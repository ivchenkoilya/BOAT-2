from __future__ import annotations

import hashlib
import html
from datetime import datetime, timezone
from typing import Any

from aiogram.filters import Command
from aiogram.types import BotCommand, Message

from career_model_v120 import (
    CAREER_CENTER,
    CAREER_HERO,
    career_value,
    fmt,
    progress,
    progress_bar,
)


async def career_rank(core: Any, chat_id: int, user_id: int) -> tuple[int, int]:
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT COUNT(*) amount FROM players WHERE chat_id=?", (chat_id,))
    total_row = await cursor.fetchone()
    cursor = await conn.execute(
        "SELECT career_points FROM players WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    )
    own = await cursor.fetchone()
    points = int(own["career_points"] or 0) if own else 0
    cursor = await conn.execute(
        "SELECT COUNT(*) amount FROM players WHERE chat_id=? AND "
        "(career_points>? OR (career_points=? AND user_id<?))",
        (chat_id, points, points, user_id),
    )
    above = await cursor.fetchone()
    return int(above["amount"] or 0) + 1 if above else 1, int(total_row["amount"] or 0) if total_row else 0


async def career_board(core: Any, chat_id: int, limit: int = 10) -> list[Any]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM players WHERE chat_id=? ORDER BY career_points DESC,user_id ASC LIMIT ?",
        (chat_id, limit),
    )
    return [core.Database._row_to_player(row) for row in await cursor.fetchall()]


async def target_player(core: Any, message: Message) -> Any | None:
    replied = message.reply_to_message.from_user if message.reply_to_message else None
    if replied is not None and not replied.is_bot:
        return await core.db.upsert_player(int(message.chat.id), replied)
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 2 and parts[1].strip():
        return await core.db.admin_find_player(parts[1].strip(), int(message.chat.id))
    if message.from_user:
        return await core.db.upsert_player(int(message.chat.id), message.from_user)
    return None


async def career_text(core: Any, chat_id: int, player: Any) -> str:
    fresh = await core.db.get_player(chat_id, player.user_id) or player
    career = career_value(fresh.points)
    role = core.role_by_points(fresh.points, False)
    rank, total = await career_rank(core, chat_id, fresh.user_id)
    start, target, target_name = progress(career)
    remaining = max(0, target - career)
    progress_line = "Высшая карьерная роль достигнута." if target <= start else f"До {target_name}: <b>{fmt(remaining)}</b>"
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT delta,reason FROM career_log_v120 WHERE chat_id=? AND user_id=? ORDER BY id DESC LIMIT 3",
        (chat_id, fresh.user_id),
    )
    rows = list(await cursor.fetchall())
    recent = "\n".join(
        f"• +{fmt(int(row['delta']))} · {html.escape(str(row['reason']))}"
        for row in rows
    ) or "• Новых карьерных начислений пока нет."
    return (
        "🌌 <b>КАРЬЕРНОЕ ВЛИЯНИЕ</b>\n\n"
        f"Участник: {core.player_link(fresh)}\n"
        f"💰 Обычное влияние: <b>{fmt(int(fresh.points))}</b>\n"
        f"⭐ Карьерное влияние: <b>{fmt(career)}</b>\n"
        f"{role.emoji} Роль: <b>{html.escape(role.title)}</b>\n"
        f"🏆 Карьерное место: <b>{rank} из {total}</b>\n\n"
        f"<code>{progress_bar(career)}</code>\n"
        f"{progress_line}\n\n"
        f"<b>Последние начисления:</b>\n{recent}\n\n"
        "Ставки, переводы и займы карьерное влияние не дают."
    )


def install_career_ui_v120(core: Any) -> None:
    if getattr(core, "_career_ui_v120_installed", False):
        return
    core._career_ui_v120_installed = True

    async def build_profile_v120(chat_id: int, player: Any, *, addressed: bool = False) -> str:
        fresh = await core.db.get_player(chat_id, player.user_id) or player
        career = career_value(fresh.points)
        role = core.role_by_points(fresh.points, False)
        career_place, career_total = await career_rank(core, chat_id, fresh.user_id)
        hero_day_state = await core.db.get_hero_day_state(chat_id)
        is_hero_day = bool(hero_day_state is not None and int(hero_day_state["user_id"]) == fresh.user_id)
        sabotage = await core.db.get_active_sabotage_for_usurper(chat_id, fresh.user_id)
        if career >= CAREER_CENTER:
            title, emoji = "Центр Вселенной", "🌌"
        elif is_hero_day and role.key == "hero":
            title, emoji = "Временный Главный герой", "🌟👑"
        elif sabotage is not None and role.key == "hero":
            title, emoji = "Саботажный Главный герой", "💣👑"
        else:
            title, emoji = role.title, role.emoji
        today_type_state = await core.active_today_type(chat_id, fresh.user_id)
        if today_type_state is None:
            today_type_line = "🎭 <b>Типаж дня:</b> ещё не определён"
        else:
            type_info, remaining = today_type_state
            today_type_line = (
                f"🎭 <b>Типаж дня:</b> {type_info['emoji']} {html.escape(type_info['title'])} "
                f"(ещё {core.human_duration(remaining)})"
            )
        intro = (
            f"Я знаю, кто такой {core.player_link(fresh)}.\n{emoji} <b>Роль — {html.escape(title)}</b>"
            if addressed
            else f"{emoji} <b>Твоя роль — {html.escape(title)}</b>"
        )
        lore_index = await core.db.next_rotation_index(
            fresh.user_id, f"profile:{chat_id}:{role.key}:lore", len(core.ROLE_LORE[role.key])
        )
        trait_index = await core.db.next_rotation_index(
            fresh.user_id, f"profile:{chat_id}:{role.key}:trait", len(core.ROLE_TRAITS[role.key])
        )
        return "\n".join([
            intro,
            *(["🌟 <b>Звание:</b> Главный герой дня"] if is_hero_day and career < CAREER_CENTER else []),
            "",
            core.ROLE_LORE[role.key][lore_index],
            "",
            f"🧠 <b>Подтип:</b> {html.escape(core.ROLE_TRAITS[role.key][trait_index])}",
            today_type_line,
            f"💰 <b>Обычное влияние:</b> {fmt(int(fresh.points))}",
            f"⭐ <b>Карьерное влияние:</b> {fmt(career)}",
            f"🌌 <b>Карьерное место:</b> {career_place} из {career_total}",
            f"💬 <b>Сообщений учтено:</b> {fresh.message_count}",
            f"➡️ {core.next_role_text(fresh.points, False)}",
        ])

    core.build_profile = build_profile_v120

    async def build_top_text_v120(chat_id: int, heading: str = "Карьерная иерархия") -> str:
        board = await career_board(core, chat_id, 10)
        if not board:
            return "Здесь пока нет людей. Только декорации."
        temporary_id = await core.temporary_hero_day_user_id(chat_id)
        sabotage_ids = set(await core.db.active_sabotage_usurper_ids(chat_id))
        lines = [f"🌌 <b>{html.escape(heading)}</b>", ""]
        for index, player in enumerate(board, start=1):
            career = career_value(player.points)
            role = core.role_by_points(player.points, index == 1)
            title, marker = role.title, "🌌" if career >= CAREER_CENTER else ("👑" if role.key == "hero" else f"{index}.")
            if career < CAREER_CENTER and role.key == "hero" and player.user_id == temporary_id:
                title, marker = "Временный Главный герой", "🌟"
            elif career < CAREER_CENTER and role.key == "hero" and player.user_id in sabotage_ids:
                title, marker = "Саботажный Главный герой", "💣"
            lines.append(
                f"{marker} {core.player_link(player)} — <b>{fmt(career)}</b> карьерного "
                f"· <b>{fmt(int(player.points))}</b> на балансе ({html.escape(title)})"
            )
        lines.extend(["", "Рейтинг ролей строится по карьерному влиянию. Ставки на него не влияют."])
        return "\n".join(lines)

    core.build_top_text = build_top_text_v120

    async def build_stats_text_v120(chat_id: int, player: Any) -> str:
        fresh = await core.db.get_player(chat_id, player.user_id) or player
        career = career_value(fresh.points)
        career_place, career_total = await career_rank(core, chat_id, fresh.user_id)
        wallet_place, wallet_total = await core.db.rank_of(chat_id, fresh.user_id)
        role = core.role_by_points(fresh.points, False)
        hero_day_state = await core.db.get_hero_day_state(chat_id)
        is_hero_day = bool(hero_day_state is not None and int(hero_day_state["user_id"]) == fresh.user_id)
        sabotage = await core.db.get_active_sabotage_for_usurper(chat_id, fresh.user_id)
        if career >= CAREER_CENTER:
            role_title, role_emoji = "Центр Вселенной", "🌌"
        elif is_hero_day and role.key == "hero":
            role_title, role_emoji = "Временный Главный герой", "🌟👑"
        elif sabotage is not None and role.key == "hero":
            role_title, role_emoji = "Саботажный Главный герой", "💣👑"
        else:
            role_title, role_emoji = role.title, role.emoji
        stats = await core.db.get_behavior(chat_id, fresh.user_id)
        return (
            f"📊 <b>Статистика {core.player_link(fresh)}</b>\n\n"
            f"💰 Баланс влияния: <b>{fmt(int(fresh.points))}</b>\n"
            f"⭐ Карьерное влияние: <b>{fmt(career)}</b>\n"
            f"{role_emoji} Роль: <b>{html.escape(role_title)}</b>\n"
            f"🌌 Карьерное место: <b>{career_place} из {career_total}</b>\n"
            f"🏦 Место по балансу: <b>{wallet_place} из {wallet_total}</b>\n"
            f"{core.next_role_text(fresh.points, False)}\n\n"
            f"💬 Сообщений: <b>{int(stats.get('messages', 0))}</b>\n"
            f"🎙 Голосовых: <b>{int(stats.get('voice_messages', 0))}</b> ({int(stats.get('voice_seconds', 0))} сек.)\n"
            f"↩️ Ответов другим: <b>{int(stats.get('replies_sent', 0))}</b>\n"
            f"📨 Ответов тебе: <b>{int(stats.get('replies_received', 0))}</b>\n"
            f"❤️ Реакций получено: <b>{int(stats.get('reactions_received', 0))}</b>"
        )

    core.build_stats_text = build_stats_text_v120

    async def build_hero_chance_text_v120(chat_id: int, player: Any) -> str:
        fresh = await core.db.get_player(chat_id, player.user_id) or player
        career = career_value(fresh.points)
        base = min(90, max(0, int(career / CAREER_HERO * 90)))
        bonus = core.dated_number(chat_id, fresh.user_id, "hero_chance", 10)
        return (
            "👑 <b>Шанс стать Главным героем</b>\n\n"
            f"{core.player_link(fresh)} — <b>{min(100, base + bonus)}%</b>.\n"
            f"Карьерное влияние: <b>{fmt(career)} / {fmt(CAREER_HERO)}</b>."
        )

    core.build_hero_chance_text = build_hero_chance_text_v120

    async def build_hero_of_day_text_v120(chat_id: int) -> str:
        board = await career_board(core, chat_id, 10_000)
        eligible = [player for player in board if career_value(player.points) >= CAREER_HERO]
        if not eligible:
            return (
                "👑 <b>Главный герой дня пока не выбран.</b>\n\n"
                f"Ни один участник ещё не набрал <b>{fmt(CAREER_HERO)}</b> карьерного влияния."
            )
        date_key = datetime.now(timezone.utc).date().isoformat()
        digest = hashlib.sha256(date_key.encode("utf-8")).digest()
        winner = eligible[int.from_bytes(digest[:4], "big") % len(eligible)]
        return (
            "👑 <b>Избрание Главного героя дня</b>\n\n"
            f"Сегодня реальность выбрала {core.player_link(winner)}.\n"
            f"Карьерное влияние: <b>{fmt(career_value(winner.points))}</b>."
        )

    core.build_hero_of_day_text = build_hero_of_day_text_v120

    if hasattr(core, "about_bot_text"):
        original_about = core.about_bot_text

        def about_with_career() -> str:
            return (
                original_about()
                + "\n\n🌌 <b>Карьерное влияние</b> определяет постоянную роль и не тратится."
                + "\nСтавки, переводы и займы меняют только обычный баланс."
                + f"\nГлавный герой: {fmt(CAREER_HERO)} · Центр Вселенной: {fmt(CAREER_CENTER)}."
            )

        core.about_bot_text = about_with_career

    @core.router.message(Command("career", "career_influence", "career_points"))
    async def cmd_career_v120(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        target = await target_player(core, message)
        if target is None:
            await message.answer("Участник не найден. Используй команду ответом на его сообщение.")
            return
        await message.answer(await career_text(core, int(message.chat.id), target))

    @core.router.message(Command("career_roles", "new_roles"))
    async def cmd_career_roles_v120(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        await message.answer(
            "🌌 <b>КАРЬЕРНАЯ ИЕРАРХИЯ</b>\n\n"
            "🪑 Декорация: <b>0–49 999</b>\n"
            "🌫 Пыль: <b>50 000–199 999</b>\n"
            "👥 Массовка: <b>200 000–499 999</b>\n"
            "🎭 Второстепенная роль: <b>500 000–899 999</b>\n"
            "👑 Главный герой: <b>900 000–1 499 999</b>\n"
            "🌌 Центр Вселенной: <b>1 500 000+</b>\n\n"
            "Карьерное влияние нельзя проиграть, потратить, перевести или взять в долг."
        )

    original_commands = core.group_bot_commands

    def commands_with_career() -> list[BotCommand]:
        commands = original_commands()
        existing = {item.command for item in commands}
        if "career" not in existing:
            commands.append(BotCommand(command="career", description="Карьерное влияние и постоянная роль"))
        if "career_roles" not in existing:
            commands.append(BotCommand(command="career_roles", description="Новые пороги карьерных ролей"))
        return commands

    core.group_bot_commands = commands_with_career
    handlers = core.router.message.handlers
    preferred = [
        handler for handler in handlers
        if getattr(handler.callback, "__name__", "") in {"cmd_career_v120", "cmd_career_roles_v120"}
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
