from __future__ import annotations

from typing import Any

import reality_events_v96 as events


def install_reality_events_runtime_fix_v96(core: Any) -> None:
    if getattr(core, "_reality_events_runtime_fix_v96_installed", False):
        return
    core._reality_events_runtime_fix_v96_installed = True

    async def award_influence_once(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        amount: int,
        event_id: str,
        reward_key: str,
    ) -> int:
        base = max(0, int(amount))
        if base <= 0:
            return 0
        reason = f"reality_event_{event_id}_{reward_key}"
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT delta FROM score_log WHERE chat_id=? AND user_id=? AND reason=? LIMIT 1",
            (chat_id, user_id, reason),
        )
        row = await cursor.fetchone()
        if row is not None:
            return max(0, int(row["delta"]))
        player = await core_arg.db.get_player(chat_id, user_id)
        if player is None:
            return 0

        method = getattr(core_arg.db, "add_points_with_balance", None)
        if method is not None:
            before, after = await method(chat_id, user_id, base, reason)
            before_points = int(before.points) if hasattr(before, "points") else int(before)
            actual = max(0, int(after.points) - before_points)
        else:
            before_points = int(player.points)
            after = await core_arg.db.add_points(chat_id, user_id, base, reason)
            actual = max(0, int(after.points) - before_points)

        async with core_arg.db.lock:
            await conn.execute(
                """
                UPDATE reality_event_participants_v96
                SET reward_influence=reward_influence+?
                WHERE event_id=? AND user_id=?
                """,
                (actual, event_id, user_id),
            )
            await conn.commit()
        return actual

    events._award_influence_once = award_influence_once
