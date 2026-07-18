from __future__ import annotations

import logging
import time
from typing import Any


LOGGER = logging.getLogger(__name__)


def install_raid_v60_guard(core: Any) -> None:
    """Не даёт запланированной одиночной атаке сломаться, если отряд выбит."""
    if getattr(core, "_raid_v60_guard_installed", False):
        return
    core._raid_v60_guard_installed = True

    original_perform_action = core.Database.boss_perform_action

    async def guarded_perform_action(self: Any, boss_id: str) -> dict[str, Any]:
        conn = self._require_connection()
        now = int(time.time())
        try:
            async with self.lock:
                cursor = await conn.execute(
                    "SELECT next_action_at, status FROM boss_battles WHERE boss_id = ?",
                    (boss_id,),
                )
                battle = await cursor.fetchone()
                if (
                    battle is not None
                    and str(battle["status"]) == "active"
                    and int(battle["next_action_at"]) <= now
                ):
                    cursor = await conn.execute(
                        "SELECT COUNT(*) AS amount FROM boss_fighters WHERE boss_id = ? AND player_hp > 0",
                        (boss_id,),
                    )
                    alive = await cursor.fetchone()
                    if alive is None or int(alive["amount"]) <= 0:
                        await conn.execute(
                            """
                            UPDATE boss_runtime_v60
                            SET planned_action = 'shield', planned_for = ?
                            WHERE boss_id = ?
                            """,
                            (int(battle["next_action_at"]), boss_id),
                        )
                        await conn.commit()
        except Exception:
            LOGGER.exception("Не удалось проверить отряд перед атакой босса")

        try:
            return await original_perform_action(self, boss_id)
        except IndexError:
            LOGGER.exception("Запланированная атака осталась без цели; заменяем её щитом")
            async with self.lock:
                cursor = await conn.execute(
                    "SELECT next_action_at FROM boss_battles WHERE boss_id = ?",
                    (boss_id,),
                )
                battle = await cursor.fetchone()
                if battle is not None:
                    await conn.execute(
                        """
                        UPDATE boss_runtime_v60
                        SET planned_action = 'shield', planned_for = ?
                        WHERE boss_id = ?
                        """,
                        (int(battle["next_action_at"]), boss_id),
                    )
                    await conn.commit()
            return await original_perform_action(self, boss_id)

    core.Database.boss_perform_action = guarded_perform_action
