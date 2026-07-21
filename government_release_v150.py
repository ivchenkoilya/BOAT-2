from __future__ import annotations

import time
from typing import Any

from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import government_v127 as gov
from government_treasury_contributions_v150 import install_government_treasury_contributions_v150


VERSION = "Reality 150 · Государственные фонды"


def _government_link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_SHORT_NAME and core.BOT_PUBLIC_USERNAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/{core.WEBAPP_SHORT_NAME}"
            f"?startapp={gov.GOV_PREFIX}{int(chat_id)}"
        )
    if core.WEBAPP_PUBLIC_URL:
        return (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/government-v127/"
            f"?chat_id={int(chat_id)}&build=150-{int(time.time())}"
        )
    return ""


def install_government_release_v150(core: Any) -> None:
    if getattr(core, "_government_release_v150_installed", False):
        return
    core._government_release_v150_installed = True
    core.GOVERNMENT_VERSION = VERSION

    install_government_treasury_contributions_v150(core)

    handlers = core.router.message.handlers
    obsolete = {
        "cmd_government_v127",
        "cmd_government_v128",
        "cmd_government_v129",
        "cmd_government_v143",
        "cmd_government_v150",
    }
    handlers[:] = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") not in obsolete
    ]

    @core.router.message(Command("government", "state", "gov"))
    async def cmd_government_v150(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = _government_link(core, chat_id)
        if not link:
            await message.answer("⚠️ Адрес государственного Mini App не настроен.")
            return
        await message.answer(
            "🏛 <b>ГОСУДАРСТВО РЕАЛЬНОСТИ · REALITY 150</b>\n\n"
            "🤝 Во вкладке «Казна» участники могут добровольно пополнять общий бюджет "
            "и целевые государственные фонды. Все вклады записываются в публичный реестр.\n\n"
            "🎰 Президент, депутат и министр финансов могут предложить закон о налоге "
            "на игровой выигрыш. Решение проходит Госдуму и подпись президента.\n\n"
            "🔐 Власть и специальные действия по-прежнему ограничены реальной должностью.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🏛 ОТКРЫТЬ ГОСУДАРСТВО REALITY 150",
                        url=link,
                    )
                ]]
            ),
        )

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_government_v150"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
