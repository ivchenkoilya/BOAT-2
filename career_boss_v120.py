from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from career_model_v120 import CAREER_CENTER, CAREER_HERO, CareerAwareInt

_ROLE_OVERRIDE: ContextVar[int | None] = ContextVar("career_role_override_v120", default=None)


def install_career_boss_v120(core: Any) -> None:
    if getattr(core, "_career_boss_v120_installed", False):
        return
    core._career_boss_v120_installed = True
    core.CAREER_ROLE_CONTEXT_V120 = _ROLE_OVERRIDE

    career_role_by_points = core.role_by_points

    def role_by_points_with_context(points: int, is_leader: bool):
        override = _ROLE_OVERRIDE.get()
        if override is None:
            return career_role_by_points(points, is_leader)
        return career_role_by_points(
            CareerAwareInt(int(points), int(override)),
            is_leader,
        )

    core.role_by_points = role_by_points_with_context

    original_boss_ability = core.Database.boss_apply_ability

    async def boss_apply_ability_with_career(
        self: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        conn = self._require_connection()
        cursor = await conn.execute(
            "SELECT career_points FROM players WHERE chat_id=? AND user_id=?",
            (int(chat_id), int(user_id)),
        )
        row = await cursor.fetchone()
        if row is None:
            return await original_boss_ability(self, boss_id, chat_id, user_id)
        effective_career = int(row["career_points"] or 0)
        if effective_career < CAREER_CENTER:
            cursor = await conn.execute(
                "SELECT 1 FROM hero_day_state WHERE chat_id=? AND user_id=? LIMIT 1",
                (int(chat_id), int(user_id)),
            )
            temporary_hero = await cursor.fetchone() is not None
            cursor = await conn.execute(
                "SELECT 1 FROM sabotages WHERE chat_id=? AND usurper_id=? "
                "AND status='active' LIMIT 1",
                (int(chat_id), int(user_id)),
            )
            sabotage_hero = await cursor.fetchone() is not None
            if temporary_hero or sabotage_hero:
                effective_career = max(effective_career, CAREER_HERO)
        token = _ROLE_OVERRIDE.set(effective_career)
        try:
            return await original_boss_ability(self, boss_id, chat_id, user_id)
        finally:
            _ROLE_OVERRIDE.reset(token)

    core.Database.boss_apply_ability = boss_apply_ability_with_career
