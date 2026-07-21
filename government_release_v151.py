from __future__ import annotations

import time
from typing import Any

from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import government_v127 as gov
from government_creator_control_v151 import install_government_creator_control_v151
from government_creator_intervention_v151 import install_government_creator_intervention_v151
from government_release_v150 import install_government_release_v150


VERSION = "Reality 151 · Контроль создателя"


def _government_link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_SHORT_NAME and core.BOT_PUBLIC_USERNAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/{core.WEBAPP_SHORT_NAME}"
            f"?startapp={gov.GOV_PREFIX}{int(chat_id)}"
        )
    if core.WEBAPP_PUBLIC_URL:
        return (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/government-v127/"
            f"?chat_id={int(chat_id)}&build=151-{int(time.time())}"
        )
    return ""


def install_government_release_v151(core: Any) -> None:
    if getattr(core, "_government_release_v151_installed", False):
        return
    core._government_release_v151_installed = True

    install_government_release_v150(core)
    install_government_creator_control_v151(core)
    install_government_creator_intervention_v151(core)
    core.GOVERNMENT_VERSION = VERSION

    handlers = core.router.message.handlers
    obsolete = {
        "cmd_government_v127",
        "cmd_government_v128",
        "cmd_government_v129",
        "cmd_government_v143",
        "cmd_government_v150",
        "cmd_government_v151",
    }
    handlers[:] = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") not in obsolete
    ]

    @core.router.message(Command("government", "state", "gov"))
    async def cmd_government_v151(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = _government_link(core, chat_id)
        if not link:
            await message.answer("⚠️ Адрес государственного Mini App не настроен.")
            return

        await message.answer(
            "🏛 <b>ГОСУДАРСТВО РЕАЛЬНОСТИ</b>\n\n"
            "Это политическая и экономическая система, привязанная к этой беседе. "
            "Участники избирают президента и депутатов, занимают государственные должности, "
            "принимают законы, управляют налогами и казной, получают мандаты, проводят "
            "расследования и участвуют в государственных конфликтах.\n\n"
            "Все решения, операции и действия должностных лиц сохраняются в государственном "
            "реестре. Создатель системы осуществляет технический надзор и может вмешиваться "
            "в работу государственных структур.",
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
        if getattr(handler.callback, "__name__", "") == "cmd_government_v151"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
