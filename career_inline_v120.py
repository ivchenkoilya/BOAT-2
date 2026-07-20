from __future__ import annotations

import html
import time
from typing import Any

from aiogram.filters import Command
from aiogram.types import Message

from career_model_v120 import (
    CAREER_CENTER,
    CAREER_DUST,
    CAREER_EXTRAS,
    CAREER_HERO,
    CAREER_SECONDARY,
    career_value,
    fmt,
)


def roles_text_v120() -> str:
    return (
        "🌌 <b>КАРЬЕРНАЯ ИЕРАРХИЯ РЕАЛЬНОСТИ</b>\n\n"
        f"🪑 <b>Декорация</b> · 0–{fmt(CAREER_DUST - 1)}\n"
        "Пока остаётся фоном беседы.\n\n"
        f"🌫 <b>Пыль</b> · {fmt(CAREER_DUST)}–{fmt(CAREER_EXTRAS - 1)}\n"
        "Уже заметен, но легко растворяется в общем шуме.\n\n"
        f"👥 <b>Массовка</b> · {fmt(CAREER_EXTRAS)}–{fmt(CAREER_SECONDARY - 1)}\n"
        "Полноценный участник коллективного сюжета.\n\n"
        f"🎭 <b>Второстепенная роль</b> · {fmt(CAREER_SECONDARY)}–{fmt(CAREER_HERO - 1)}\n"
        "Заметный человек, способный менять ход беседы.\n\n"
        f"👑 <b>Главный герой</b> · {fmt(CAREER_HERO)}–{fmt(CAREER_CENTER - 1)}\n"
        "Постоянная высокая роль, заработанная карьерными действиями.\n\n"
        f"🌌 <b>Центр Вселенной</b> · от {fmt(CAREER_CENTER)}\n"
        "Высшая постоянная роль. Его присутствие само становится событием.\n\n"
        "⭐ Роль определяется карьерным влиянием.\n"
        "💰 Ставки, переводы, займы и траты меняют только обычный баланс."
    )


def install_career_inline_v120(core: Any) -> None:
    if getattr(core, "_career_inline_v120_installed", False):
        return
    core._career_inline_v120_installed = True
    core.roles_text = roles_text_v120

    original_inline_menu_specs = core.inline_menu_specs

    def inline_menu_specs_v120(user: Any) -> list[dict[str, Any]]:
        items = original_inline_menu_specs(user)
        for item in items:
            if str(item.get("result_id") or "") == "roles":
                item["title"] = "🌌 Все карьерные роли 🌌"
                item["description"] = "От Декорации до Центра Вселенной"
                item["message_text"] = roles_text_v120()
            if str(item.get("action") or "") == "score:influence":
                item["description"] = (
                    "Обычное влияние + 1 500–3 000 карьерного · кулдаун 6 часов"
                )
        return items

    core.inline_menu_specs = inline_menu_specs_v120

    original_role_ability_info = core.role_ability_info_text

    def role_ability_info_v120() -> str:
        return (
            original_role_ability_info()
            + "\n\n🌌 <b>Центр Вселенной</b> использует усиленную боевую роль "
            "Главного героя, но остаётся отдельным высшим карьерным званием."
        )

    core.role_ability_info_text = role_ability_info_v120

    @core.router.message(Command("career_set"))
    async def cmd_career_set_v120(message: Message) -> None:
        if (
            not message.from_user
            or int(message.from_user.id) != int(core.DEVELOPER_ID)
            or not core.is_group(message)
        ):
            return
        parts = (message.text or "").split()
        target = None
        amount_token = ""
        if message.reply_to_message and message.reply_to_message.from_user:
            target = await core.db.upsert_player(
                int(message.chat.id), message.reply_to_message.from_user
            )
            amount_token = parts[1] if len(parts) >= 2 else ""
        elif len(parts) >= 3:
            target = await core.db.admin_find_player(parts[1], int(message.chat.id))
            amount_token = parts[2]
        elif len(parts) >= 2:
            target = await core.db.upsert_player(int(message.chat.id), message.from_user)
            amount_token = parts[1]
        try:
            amount = max(0, min(100_000_000, int(amount_token)))
        except (TypeError, ValueError):
            amount = -1
        if target is None or amount < 0:
            await message.answer(
                "Использование: ответом <code>/career_set 1500000</code> "
                "или <code>/career_set @username 1500000</code>."
            )
            return
        conn = core.db._require_connection()
        cursor = await conn.execute(
            "SELECT career_points FROM players WHERE chat_id=? AND user_id=?",
            (int(message.chat.id), int(target.user_id)),
        )
        row = await cursor.fetchone()
        before = int(row["career_points"] or 0) if row else 0
        now = int(time.time())
        async with core.db.lock:
            await conn.execute(
                "UPDATE players SET career_points=?,career_initialized=1,updated_at=? "
                "WHERE chat_id=? AND user_id=?",
                (amount, now, int(message.chat.id), int(target.user_id)),
            )
            await conn.execute(
                "INSERT INTO career_log_v120(chat_id,user_id,delta,reason,source_type,source_id,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    int(message.chat.id), int(target.user_id), amount - before,
                    "Установлено администратором", "admin", f"admin:{now}", now,
                ),
            )
            await conn.commit()
        fresh = await core.db.get_player(int(message.chat.id), int(target.user_id))
        role = core.role_by_points(fresh.points, False) if fresh else core.DECORATION
        await message.answer(
            f"✅ Карьерное влияние {core.player_link(fresh or target)}: "
            f"<b>{fmt(before)} → {fmt(amount)}</b>.\n"
            f"Новая постоянная роль: {role.emoji} <b>{html.escape(role.title)}</b>."
        )

    handlers = core.router.message.handlers
    preferred = [
        handler for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_career_set_v120"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
