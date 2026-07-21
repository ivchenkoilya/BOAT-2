from __future__ import annotations

import time
from typing import Any

from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from admin_career_v123 import install_admin_career_v123
from career_interactions_v122 import install_career_interactions_v122
from career_system_v120 import install_career_system_v120
from command_hub_v121 import install_command_hub_v121
from command_hub_compat_v121 import install_command_hub_compat_v121
from finance_route_fix_v116 import install_finance_route_fix_v116
from finance_loan_requests_v118 import install_finance_loan_requests_v118


VERSION = "Reality 123 · Карьерный админ-центр"
FINANCE_PREFIX = "finance_"


def _finance_link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_SHORT_NAME and core.BOT_PUBLIC_USERNAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/"
            f"{core.WEBAPP_SHORT_NAME}?startapp={FINANCE_PREFIX}{int(chat_id)}"
        )
    if core.WEBAPP_PUBLIC_URL:
        return (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/finance-v118/"
            f"?chat_id={int(chat_id)}&build=123-{int(time.time())}"
        )
    return ""


def install_finance_entry_fix_v115(core: Any) -> None:
    if getattr(core, "_finance_entry_fix_v115_installed", False):
        return
    core._finance_entry_fix_v115_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    # Reality 117 подключает стабильные маршруты состояния, действий и истории.
    install_finance_route_fix_v116(core)
    # Reality 118 добавляет заявки на заём и адресные кнопки решения.
    install_finance_loan_requests_v118(core)

    # Старые /finance-обработчики удаляются полностью, чтобы текстовое меню
    # Reality 112 больше не могло перехватить команду раньше Mini App.
    handlers = core.router.message.handlers
    obsolete_names = {"cmd_finance_v112", "cmd_finance_app_v114", "cmd_finance_app_v115"}
    handlers[:] = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") not in obsolete_names
    ]

    @core.router.message(Command("finance", "money", "bank"))
    async def cmd_finance_app_v115(message: Message) -> None:
        if not await core.require_group_command(message, "Финансовый центр"):
            return
        if not message.from_user:
            return
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = _finance_link(core, chat_id)
        if not link:
            await message.answer(
                "⚠️ Финансовый центр не настроен: отсутствует адрес Mini App."
            )
            return
        await message.answer(
            "💸 <b>ФИНАНСОВЫЙ ЦЕНТР · REALITY 123</b>\n\n"
            "Переводи обычное влияние, выдавай займы или публикуй заявку. "
            "Карьерное влияние не тратится и определяет постоянную роль.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="💸 ОТКРЫТЬ ФИНАНСОВЫЙ ЦЕНТР",
                        url=link,
                    )
                ]]
            ),
        )

    # Только новый обработчик остаётся первым среди команд сообщений.
    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_finance_app_v115"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]

    # Карьерная модель ставится первой, затем центры команд и мгновенные награды.
    # Reality 123 устанавливается последней: добавляет отдельный защищённый
    # админ-центр и заменяет вход /admin, не удаляя старую панель Reality 76.
    install_career_system_v120(core)
    install_command_hub_v121(core)
    install_command_hub_compat_v121(core)
    install_career_interactions_v122(core)
    install_admin_career_v123(core)
