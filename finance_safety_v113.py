from __future__ import annotations

from typing import Any

import finance_system_v112 as finance


VERSION = "Reality 113 · Финансовая защита"


def install_finance_safety_v113(core: Any) -> None:
    if getattr(core, "_finance_safety_v113_installed", False):
        return
    core._finance_safety_v113_installed = True
    core.FINANCE_SAFETY_VERSION = VERSION

    original_add = core.Database.add_points

    async def add_points_with_debt_collection(
        self: Any,
        chat_id: int,
        user_id: int,
        delta: int,
        reason: str,
        *args: Any,
        **kwargs: Any,
    ):
        before = await self.get_player(int(chat_id), int(user_id))
        result = await original_add(
            self,
            chat_id,
            user_id,
            delta,
            reason,
            *args,
            **kwargs,
        )
        before_points = int(before.points) if before is not None else 0
        actual = int(result.points) - before_points
        if int(chat_id) < 0 and actual > 0 and finance._eligible_earning(reason):
            withheld = await finance._withhold_overdue(
                core,
                int(chat_id),
                int(user_id),
                actual,
            )
            if withheld > 0:
                bot = finance._RUNTIME_BOT.get("bot")
                if bot is not None:
                    finance._queue_notice(
                        core,
                        bot,
                        int(chat_id),
                        int(user_id),
                        withheld,
                    )
                fresh = await self.get_player(int(chat_id), int(user_id))
                if fresh is not None:
                    return fresh
        return result

    core.Database.add_points = add_points_with_debt_collection

    # В основном боте есть старые общие callback-обработчики. Финансовые кнопки
    # должны проверяться первыми, иначе подтверждение перевода или займа может
    # быть перехвачено другим игровым действием.
    callback_names = {
        "confirm_transfer_v112",
        "cancel_transfer_v112",
        "accept_loan_v112",
        "reject_loan_v112",
        "finance_menu_callback_v112",
    }
    handlers = core.router.callback_query.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") in callback_names
    ]
    handlers[:] = preferred + [
        handler for handler in handlers if handler not in preferred
    ]
