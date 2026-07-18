from __future__ import annotations

import logging
from typing import Any


LOGGER = logging.getLogger(__name__)


def install_raid_v59_recovery(core: Any) -> None:
    """Завершает рейды, которые зависли в status=resolving до обновления."""
    if getattr(core, "_raid_v59_recovery_installed", False):
        return
    core._raid_v59_recovery_installed = True

    original_start_webapp_server = core.start_webapp_server

    async def start_webapp_server_with_recovery(bot: Any):
        runner = await original_start_webapp_server(bot)

        async def recover_stuck_victories() -> None:
            try:
                conn = core.db._require_connection()
                cursor = await conn.execute(
                    """
                    SELECT boss_id
                    FROM boss_battles
                    WHERE status = 'resolving' AND hp <= 0
                    ORDER BY created_at ASC
                    """
                )
                rows = await cursor.fetchall()
                for row in rows:
                    await core.resolve_boss_victory(str(row["boss_id"]), bot)
            except Exception:
                LOGGER.exception("Не удалось восстановить зависшее завершение рейда")

        core.spawn_background_task(recover_stuck_victories())
        return runner

    core.start_webapp_server = start_webapp_server_with_recovery
