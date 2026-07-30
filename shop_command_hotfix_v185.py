from __future__ import annotations

import time
from typing import Any

from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


VERSION = "Reality 185 · Shop command hotfix"
SHOP_PREFIX = "shop_"


def _shop_link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_SHORT_NAME and core.BOT_PUBLIC_USERNAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/"
            f"{core.WEBAPP_SHORT_NAME}?startapp={SHOP_PREFIX}{int(chat_id)}"
        )
    if core.WEBAPP_PUBLIC_URL:
        return (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/influence-shop-v184/"
            f"?chat_id={int(chat_id)}&build=185-{int(time.time())}"
        )
    return ""


def install_shop_command_hotfix_v185(core: Any) -> None:
    """Registers /shop before the old catch-all F.text handler.

    The project has a large monolithic router where a generic text handler was
    registered before extension modules. Merely decorating a new command at the
    end of the router can therefore leave /shop silently consumed. This layer
    deliberately moves the command handler to the first position.
    """
    if getattr(core, "_shop_command_hotfix_v185_installed", False):
        return
    core._shop_command_hotfix_v185_installed = True
    core.INFLUENCE_SHOP_VERSION = VERSION

    @core.router.message(Command("shop"))
    async def cmd_shop_v185(message: Message) -> None:
        if not message.from_user:
            return
        chat_id = int(message.chat.id)
        if chat_id >= 0:
            await message.answer(
                "🛍 Магазин влияния открывается из групповой беседы, "
                "потому что баланс и покупки разделены по чатам."
            )
            return

        await core.db.upsert_player(chat_id, message.from_user)
        link = _shop_link(core, chat_id)
        if not link:
            await message.answer(
                "⚠️ Магазин пока не может открыться: не настроен публичный адрес Mini App."
            )
            return

        await message.answer(
            "🛍 <b>МАГАЗИН ВЛИЯНИЯ</b>\n\n"
            "Здесь влияние превращается во власть. Покупки и баланс "
            "привязаны именно к этой беседе.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🛍 ОТКРЫТЬ МАГАЗИН ВЛИЯНИЯ",
                        url=link,
                    )
                ]]
            ),
        )

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_shop_v185"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
