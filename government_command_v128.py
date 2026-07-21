from __future__ import annotations

from typing import Any

from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import government_v127 as government


VERSION = "Reality 128 · Госструктуры и полномочия"


def install_government_command_v128(core: Any) -> None:
    if getattr(core, "_government_command_v128_installed", False):
        return
    core._government_command_v128_installed = True

    handlers = core.router.message.handlers
    obsolete = {"cmd_government_v127", "cmd_government_v128"}
    handlers[:] = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") not in obsolete
    ]

    @core.router.message(Command("government", "state", "gov"))
    async def cmd_government_v128(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = government._government_link(core, chat_id)
        if not link:
            await message.answer("⚠️ Адрес государственного Mini App не настроен.")
            return
        await message.answer(
            "🏛 <b>ГОСУДАРСТВО РЕАЛЬНОСТИ · REALITY 128</b>\n\n"
            "Президент, Госдума, выборы, законы, казна и Надзор дополнены "
            "Верховным судом, прокуратурой, Центральным банком, Счётной палатой, "
            "ЦИК, омбудсменом, Советом безопасности и государственной пресс-службой.\n\n"
            "У каждого чиновника внутри приложения есть собственные кнопки полномочий.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="🏛 ОТКРЫТЬ ГОСУДАРСТВО", url=link)
                ]]
            ),
        )

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_government_v128"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
