from __future__ import annotations

from typing import Any

import government_reform_v129 as reform


VERSION = "Reality 129 · Полный налог на игровой выигрыш"


def _is_game_win(reason: str) -> bool:
    clean = str(reason or "").casefold().strip()
    if reform._is_win_reason(clean):
        return True
    tokens = (
        "game", "roulette", "casino", "wager", "gambling", "bet_",
        "heist", "hunter", "roof", "vault", "coin", "dice",
    )
    return any(token in clean for token in tokens)


def install_government_win_tax_hotfix_v129(core: Any) -> None:
    if getattr(core, "_government_win_tax_hotfix_v129_installed", False):
        return
    core._government_win_tax_hotfix_v129_installed = True

    original_add_points_with_balance = core.Database.add_points_with_balance

    async def add_points_with_balance_and_tax(
        self: Any,
        chat_id: int,
        user_id: int,
        delta: int,
        reason: str,
        *,
        update_reward_time: bool = False,
    ) -> tuple[int, Any]:
        before, player = await original_add_points_with_balance(
            self,
            chat_id,
            user_id,
            delta,
            reason,
            update_reward_time=update_reward_time,
        )
        gross_win = max(0, int(player.points) - int(before))
        if gross_win > 0 and _is_game_win(reason):
            await reform._collect_win_tax(
                core,
                self,
                int(chat_id),
                int(user_id),
                gross_win,
                str(reason),
            )
            refreshed = await self.get_player(int(chat_id), int(user_id))
            if refreshed is not None:
                player = refreshed
        return int(before), player

    core.Database.add_points_with_balance = add_points_with_balance_and_tax
