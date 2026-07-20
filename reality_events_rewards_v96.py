from __future__ import annotations

import json
from typing import Any

import reality_events_v96 as events


MIN_MULTIPLIER = 0.0
MAX_MULTIPLIER = 5.0


def _clamp_multiplier(value: Any, default: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(MIN_MULTIPLIER, min(MAX_MULTIPLIER, number))


def install_reality_events_rewards_v96(core: Any) -> None:
    if getattr(core, "_reality_events_rewards_v96_installed", False):
        return
    core._reality_events_rewards_v96_installed = True

    original_connect = core.Database.connect

    async def connect_with_reward_overrides(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reality_event_reward_overrides_v96(
                    event_id TEXT PRIMARY KEY,
                    influence_multiplier REAL NOT NULL DEFAULT 1.0,
                    tree_multiplier REAL NOT NULL DEFAULT 1.0,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_reward_overrides

    async def multipliers(core_arg: Any, event_id: str) -> tuple[float, float]:
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT influence_multiplier,tree_multiplier
            FROM reality_event_reward_overrides_v96 WHERE event_id=?
            """,
            (event_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return 1.0, 1.0
        return (
            _clamp_multiplier(row["influence_multiplier"]),
            _clamp_multiplier(row["tree_multiplier"]),
        )

    base_award_influence = events._award_influence_once

    async def award_with_multiplier(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        amount: int,
        event_id: str,
        reward_key: str,
    ) -> int:
        influence_multiplier, _ = await multipliers(core_arg, event_id)
        adjusted = max(0, int(round(int(amount) * influence_multiplier)))
        return await base_award_influence(
            core_arg,
            chat_id,
            user_id,
            adjusted,
            event_id,
            reward_key,
        )

    base_grant_tree = events._grant_tree_once

    async def tree_with_multiplier(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        points: int,
        event_id: str,
        reward_key: str,
    ) -> int:
        _, tree_multiplier = await multipliers(core_arg, event_id)
        adjusted = max(0, int(round(int(points) * tree_multiplier)))
        return await base_grant_tree(
            core_arg,
            chat_id,
            user_id,
            adjusted,
            event_id,
            reward_key,
        )

    events._award_influence_once = award_with_multiplier
    events._grant_tree_once = tree_with_multiplier

    base_admin_state = events._admin_state

    async def admin_state_with_rewards(core_arg: Any, request: Any):
        response = await base_admin_state(core_arg, request)
        if not getattr(response, "body", None):
            return response
        try:
            data = json.loads(response.body.decode("utf-8"))
        except Exception:
            return response
        event = data.get("event") or {}
        event_id = str(event.get("event_id") or "")
        influence_multiplier = 1.0
        tree_multiplier = 1.0
        if event_id:
            influence_multiplier, tree_multiplier = await multipliers(core_arg, event_id)
        data["reward_override"] = {
            "influence_multiplier": influence_multiplier,
            "tree_multiplier": tree_multiplier,
        }
        return core_arg.web.json_response(data, status=response.status)

    events._admin_state = admin_state_with_rewards

    base_admin_action = events._admin_action

    async def admin_action_with_rewards(core_arg: Any, bot: Any, request: Any):
        try:
            data = await request.json()
        except Exception:
            data = {}
        if str(data.get("action") or "") != "event_reward_settings":
            return await base_admin_action(core_arg, bot, request)

        user, reason = core_arg._webapp_auth(request)
        if user is None or int(user.id) != int(core_arg.DEVELOPER_ID):
            return core_arg.web.json_response(
                {"ok": False, "reason": reason or "Нет доступа."},
                status=403,
            )
        try:
            chat_id = int(data.get("chat_id") or 0)
        except (TypeError, ValueError):
            chat_id = 0
        event = await events._active_event(core_arg, chat_id) if chat_id else None
        if event is None:
            return core_arg.web.json_response(
                {"ok": False, "reason": "Сначала запусти событие."},
                status=400,
            )
        influence_multiplier = _clamp_multiplier(data.get("influence_multiplier"))
        tree_multiplier = _clamp_multiplier(data.get("tree_multiplier"))
        conn = core_arg.db._require_connection()
        async with core_arg.db.lock:
            await conn.execute(
                """
                INSERT INTO reality_event_reward_overrides_v96(
                    event_id,influence_multiplier,tree_multiplier,updated_at
                ) VALUES(?,?,?,?)
                ON CONFLICT(event_id) DO UPDATE SET
                    influence_multiplier=excluded.influence_multiplier,
                    tree_multiplier=excluded.tree_multiplier,
                    updated_at=excluded.updated_at
                """,
                (
                    str(event["event_id"]),
                    influence_multiplier,
                    tree_multiplier,
                    events._now(),
                ),
            )
            await conn.commit()
        return core_arg.web.json_response(
            {
                "ok": True,
                "message": (
                    f"Множители сохранены: влияние ×{influence_multiplier:g}, "
                    f"Древо ×{tree_multiplier:g}."
                ),
            }
        )

    events._admin_action = admin_action_with_rewards
