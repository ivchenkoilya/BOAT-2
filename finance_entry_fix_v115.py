from __future__ import annotations

import time
from typing import Any

from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from admin_career_v123 import install_admin_career_v123
from admin_election_action_fix_v140 import install_admin_election_action_fix_v140
from admin_election_button_hotfix_v134 import install_admin_election_button_hotfix_v134
from admin_election_force_voting_v141 import install_admin_election_force_voting_v141
from admin_election_now_v133 import install_admin_election_now_v133
from admin_finance_compat_v123 import install_admin_finance_compat_v123
from admin_fresh_v142 import install_admin_fresh_v142
from admin_full_v124 import install_admin_full_v124
from admin_government_market_v132 import install_admin_government_market_v132
from admin_market_lock_hotfix_v132 import install_admin_market_lock_hotfix_v132
from bot_game_stake_limit_v136 import install_bot_game_stake_limit_v136
from bunker_game_v144 import install_bunker_game_v144
from career_interactions_v122 import install_career_interactions_v122
from career_system_v120 import install_career_system_v120
from central_bank_wager_limit_v137 import install_central_bank_wager_limit_v137
from command_hub_v121 import install_command_hub_v121
from command_hub_compat_v121 import install_command_hub_compat_v121
from finance_investments_v127 import install_finance_investments_v127
from finance_loan_requests_v118 import install_finance_loan_requests_v118
from finance_products_v129 import install_finance_products_v129
from finance_route_fix_v116 import install_finance_route_fix_v116
from finance_transfer_limit_v133 import install_finance_transfer_limit_v133
from government_command_v129 import install_government_command_v129
from government_crisis_hotfix_v131 import install_government_crisis_hotfix_v131
from government_crisis_v131 import install_government_crisis_v131
from government_economy_hotfix_v128 import install_government_economy_hotfix_v128
from government_entry_v143 import install_government_entry_v143
from government_institutions_v128 import install_government_institutions_v128
from government_mandates_integrity_v143 import install_government_mandates_integrity_v143
from government_mandates_v143 import install_government_mandates_v143
from government_reform_assets_v129 import install_government_reform_assets_v129
from government_reform_v129 import install_government_reform_v129
from government_small_group_v130 import install_government_small_group_v130
from government_v127 import install_government_v127
from government_win_tax_hotfix_v129 import install_government_win_tax_hotfix_v129
from hierarchy_activity_hotfix_v130 import install_hierarchy_activity_hotfix_v130
from hierarchy_v130 import install_hierarchy_v130
from sanctions_hotfix_v126 import install_sanctions_hotfix_v126
from sanctions_v126 import install_sanctions_v126
from talent_career_v135 import install_talent_career_v135
from telegram_network_resilience_v139 import install_telegram_network_resilience_v139


VERSION = "Reality 146 · Бункер в Игровом центре"
FINANCE_PREFIX = "finance_"


def _finance_link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_SHORT_NAME and core.BOT_PUBLIC_USERNAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/"
            f"{core.WEBAPP_SHORT_NAME}?startapp={FINANCE_PREFIX}{int(chat_id)}"
        )
    if core.WEBAPP_PUBLIC_URL:
        return (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/finance-v127/"
            f"?chat_id={int(chat_id)}&build=146-{int(time.time())}"
        )
    return ""


def install_finance_entry_fix_v115(core: Any) -> None:
    if getattr(core, "_finance_entry_fix_v115_installed", False):
        return
    core._finance_entry_fix_v115_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    install_finance_route_fix_v116(core)
    install_finance_loan_requests_v118(core)
    install_finance_investments_v127(core)
    install_finance_products_v129(core)

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
            "💸 <b>ФИНАНСОВЫЙ ЦЕНТР · REALITY 146</b>\n\n"
            "Переводы и ставки до 1 000 000 обычного влияния, займы, вклады, "
            "биржа и инвестиционный портфель. Центральный банк может удерживать "
            "комиссию, а администратор управляет курсами и остановкой торгов.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="💸 ОТКРЫТЬ ФИНАНСОВЫЙ ЦЕНТР",
                        url=link,
                    )
                ]]
            ),
        )

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_finance_app_v115"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]

    install_career_system_v120(core)
    install_command_hub_v121(core)
    install_command_hub_compat_v121(core)
    install_career_interactions_v122(core)
    install_admin_finance_compat_v123(core)
    install_admin_career_v123(core)
    install_admin_full_v124(core)
    install_sanctions_v126(core)
    install_sanctions_hotfix_v126(core)
    install_government_v127(core)
    install_government_institutions_v128(core)
    install_government_economy_hotfix_v128(core)
    install_government_reform_v129(core)
    install_government_win_tax_hotfix_v129(core)
    install_government_small_group_v130(core)
    install_government_reform_assets_v129(core)
    install_government_command_v129(core)
    install_hierarchy_v130(core)
    install_hierarchy_activity_hotfix_v130(core)
    install_government_crisis_v131(core)
    install_government_crisis_hotfix_v131(core)
    install_admin_government_market_v132(core)
    install_admin_market_lock_hotfix_v132(core)
    install_finance_transfer_limit_v133(core)
    install_admin_election_now_v133(core)
    install_admin_election_button_hotfix_v134(core)
    install_talent_career_v135(core)
    install_bot_game_stake_limit_v136(core)
    install_central_bank_wager_limit_v137(core)
    install_telegram_network_resilience_v139(core)
    install_admin_election_action_fix_v140(core)
    install_admin_election_force_voting_v141(core)
    install_admin_fresh_v142(core)
    install_government_mandates_v143(core)
    install_government_mandates_integrity_v143(core)
    install_government_entry_v143(core)
    install_bunker_game_v144(core)
