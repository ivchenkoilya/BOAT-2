from __future__ import annotations

from typing import Any

import hierarchy_v130 as hierarchy


VERSION = "Reality 130 · Реальная активность участников"


async def _activity_map(core: Any, chat_id: int) -> dict[int, dict[str, int | bool]]:
    conn = core.db._require_connection()
    cutoff = hierarchy._now() - hierarchy.ACTIVE_WINDOW_SECONDS
    cursor = await conn.execute(
        """
        SELECT p.user_id,p.updated_at,p.message_count,
               COALESCE(b.updated_at,0) behavior_updated_at,
               COALESCE(b.messages,0) messages,
               COALESCE(b.inline_uses,0) inline_uses,
               COALESCE(b.reactions_given,0) reactions_given,
               COALESCE(b.positive_actions,0) positive_actions,
               COALESCE(b.negative_actions,0) negative_actions
        FROM players p
        LEFT JOIN user_behavior b
          ON b.chat_id=p.chat_id AND b.user_id=p.user_id
        WHERE p.chat_id=?
        """,
        (int(chat_id),),
    )
    result: dict[int, dict[str, int | bool]] = {}
    for row in await cursor.fetchall():
        behavior_at = int(row["behavior_updated_at"] or 0)
        behavior_actions = (
            int(row["messages"] or 0)
            + int(row["inline_uses"] or 0)
            + int(row["reactions_given"] or 0)
            + int(row["positive_actions"] or 0)
            + int(row["negative_actions"] or 0)
        )
        if behavior_at > 0:
            last_activity = behavior_at
            active = behavior_at >= cutoff and behavior_actions > 0
        else:
            last_activity = int(row["updated_at"] or 0)
            active = (
                last_activity >= cutoff
                and int(row["message_count"] or 0) > 0
            )
        result[int(row["user_id"])] = {
            "active": bool(active),
            "last_activity": int(last_activity),
        }
    return result


async def active_user_count_v130(core: Any, chat_id: int) -> int:
    activity = await _activity_map(core, chat_id)
    count = sum(1 for item in activity.values() if bool(item["active"]))
    if count:
        return count
    return 1 if activity else 0


def install_hierarchy_activity_hotfix_v130(core: Any) -> None:
    if getattr(core, "_hierarchy_activity_hotfix_v130_installed", False):
        return
    core._hierarchy_activity_hotfix_v130_installed = True

    hierarchy.active_user_count = active_user_count_v130
    original_state = hierarchy._state

    async def state_with_real_activity(
        core_value: Any,
        bot: Any,
        chat_id: int,
        viewer_id: int,
    ) -> dict[str, Any]:
        state = await original_state(
            core_value,
            bot,
            chat_id,
            viewer_id,
        )
        activity = await _activity_map(core_value, chat_id)
        for participant in state.get("participants", []):
            item = activity.get(int(participant.get("user_id", 0)))
            if item is None:
                participant["active"] = False
                continue
            participant["active"] = bool(item["active"])
            participant["last_activity"] = int(item["last_activity"])
        active = sum(
            1
            for participant in state.get("participants", [])
            if participant.get("active")
        )
        if not active and state.get("participants"):
            active = 1
        state.setdefault("summary", {})["active"] = int(active)
        state["summary"]["deputy_seats"] = hierarchy.recommended_deputy_seats(active)
        state["summary"]["activity_window_days"] = 14
        return state

    hierarchy._state = state_with_real_activity
