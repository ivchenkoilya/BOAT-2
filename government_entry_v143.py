from __future__ import annotations

from typing import Any

from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import government_v127 as gov


VERSION = "Reality 143 · Мандаты и основные законы"


def install_government_entry_v143(core: Any) -> None:
    if getattr(core, "_government_entry_v143_installed", False):
        return
    core._government_entry_v143_installed = True
    core.GOVERNMENT_VERSION = VERSION

    handlers = core.router.message.handlers
    obsolete = {
        "cmd_government_v127",
        "cmd_government_v128",
        "cmd_government_v129",
        "cmd_government_v143",
    }
    handlers[:] = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") not in obsolete
    ]

    @core.router.message(Command("government", "state", "gov"))
    async def cmd_government_v143(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = gov._government_link(core, chat_id)
        if not link:
            await message.answer("⚠️ Адрес государственного Mini App не настроен.")
            return
        await message.answer(
            "🏛 <b>ГОСУДАРСТВО РЕАЛЬНОСТИ · REALITY 143</b>\n\n"
            "Выборы, Госдума, президент, казна, налоги и государственные структуры.\n\n"
            "📜 Добавлены официальные мандаты с электронной подписью, Telegram ID, "
            "сроком полномочий и кодом проверки.\n\n"
            "⚖️ В Кодексе действуют десять основных законов государства, а новые "
            "законы Госдумы получают номера начиная с №11.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🏛 ОТКРЫТЬ ГОСУДАРСТВО REALITY 143",
                        url=link,
                    )
                ]]
            ),
        )

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_government_v143"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
