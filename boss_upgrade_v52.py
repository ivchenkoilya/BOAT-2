from __future__ import annotations

from typing import Any


PLAYER_MAX_HP = 300


def install_boss_upgrade_v52(core: Any) -> None:
    """Поднимает здоровье всех боевых ролей до 300 и обновляет старые бои."""
    if getattr(core, "_boss_upgrade_v52_installed", False):
        return

    core._boss_upgrade_v52_installed = True

    for profile in core.BOSS_COMBAT_ROLES.values():
        profile["max_hp"] = PLAYER_MAX_HP

    original_schema = core.ensure_reality49_boss_schema

    async def ensure_schema_with_300_hp() -> None:
        await original_schema()
        conn = core.db._require_connection()
        async with core.db.lock:
            await conn.execute(
                """
                UPDATE boss_fighters
                SET player_hp = CASE
                        WHEN player_max_hp < ?
                            THEN MIN(?, player_hp + (? - player_max_hp))
                        ELSE MIN(player_hp, ?)
                    END,
                    player_max_hp = ?
                WHERE player_max_hp <> ?
                """,
                (
                    PLAYER_MAX_HP,
                    PLAYER_MAX_HP,
                    PLAYER_MAX_HP,
                    PLAYER_MAX_HP,
                    PLAYER_MAX_HP,
                    PLAYER_MAX_HP,
                ),
            )
            await conn.commit()

    core.ensure_reality49_boss_schema = ensure_schema_with_300_hp
