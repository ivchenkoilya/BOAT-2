from __future__ import annotations

from typing import Any

import career_rewards_v120 as rewards


GAMBLING_MARKERS = (
    "roulette",
    "influence_roulette",
    "fate",
    "wager",
    "stake",
    "ego_challenge",
    "duel",
)


def install_career_gambling_guard_v120(core: Any) -> None:
    if getattr(core, "_career_gambling_guard_v120_installed", False):
        return
    core._career_gambling_guard_v120_installed = True

    previous_score_award = rewards.score_award

    def score_award_without_gambling(row: Any):
        reason = str(row["reason"] or "").casefold()
        if any(marker in reason for marker in GAMBLING_MARKERS):
            return None
        return previous_score_award(row)

    rewards.score_award = score_award_without_gambling
