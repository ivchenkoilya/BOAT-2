from __future__ import annotations

from typing import Any

from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import government_v127 as government


VERSION = "Reality 130 · Компактное государство"


def install_government_command_v129(core: Any) -> None:
    if getattr(core, "_government_command_v129_installed", False):
        return
    core._government_command_v129_installed = True

    handlers = core.router.message.handlers
    obsolete = {"cmd_government_v127", "cmd_government_v128", "cmd_government_v129"}
    handlers[:] = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") not in obsolete
    ]

    @core.router.message(Command("government", "state", "gov"))
    async def cmd_government_v129(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = government._government_link(core, chat_id)
        if not link:
            await message.answer("⚠️ Адрес государственного Mini App не настроен.")
            return
        await message.answer(
            "🏛 <b>ГОСУДАРСТВО РЕАЛЬНОСТИ · REALITY 130</b>\n\n"
            "Выборные пороги: депутат — <b>50 000</b>, председатель Госдумы — "
            "<b>100 000</b>, президент — <b>200 000</b> карьерного влияния.\n\n"
            "Количество депутатов автоматически подстраивается под активность: "
            "<b>1, 3, 5 или 7 мест</b>. Для шести активных участников создаётся "
            "Госдума из <b>трёх депутатов</b>.\n\n"
            "Президент напрямую назначает чиновников, а депутаты согласовывают "
            "законы, включая налог от <b>0% до 100%</b> с игрового выигрыша.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🏛 ОТКРЫТЬ ГОСУДАРСТВО",
                        url=link,
                    )
                ]]
            ),
        )

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_government_v129"
    ]
    handlers[:] = preferred + [
        handler
        for handler in handlers
        if handler not in preferred
    ]
