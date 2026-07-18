from __future__ import annotations

import logging
from typing import Any


LOGGER = logging.getLogger(__name__)


def install_raid_v61_safety(core: Any) -> None:
    """Не позволяет увеличению HP воскресить уже поверженного босса."""
    if getattr(core, "_raid_v61_safety_installed", False):
        return
    core._raid_v61_safety_installed = True

    original_connect = core.Database.connect

    async def connect_with_zero_hp_safety(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            # status=resolving используется только после достижения нулевого HP.
            await conn.execute(
                "UPDATE boss_battles SET hp = 0 WHERE status = 'resolving'"
            )
            # Старый активный босс с 0/50000 после миграции превращался в
            # 25000/75000 и сохранял четвёртую фазу. Возвращаем его в очередь
            # надёжного завершения, которую обработает raid_v59_recovery.
            await conn.execute(
                """
                UPDATE boss_battles
                SET hp = 0, status = 'resolving'
                WHERE status = 'active'
                  AND max_hp = 75000
                  AND hp = 25000
                  AND phase = 4
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_zero_hp_safety
