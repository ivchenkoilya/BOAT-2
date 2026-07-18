from __future__ import annotations

import logging
from typing import Any


LOGGER = logging.getLogger(__name__)
BOSS_HP = 100_000
PRESSURE_MAX = 150
PRESSURE_HIT_GAIN = 2
PRESSURE_CRIT_BONUS = 1
PRESSURE_ABILITY_GAIN = 4
PRESSURE_DECAY_SECONDS = 9


def install_raid_v65_balance(core: Any) -> None:
    """Reality 65: 100k HP и немного более тяжёлая шкала давления."""
    if getattr(core, "_raid_v65_balance_installed", False):
        return

    core._raid_v65_balance_installed = True
    core.BOSS_MAX_HP = BOSS_HP

    try:
        import raid_v60

        raid_v60.PRESSURE_MAX = PRESSURE_MAX
        raid_v60.PRESSURE_HIT_GAIN = PRESSURE_HIT_GAIN
        raid_v60.PRESSURE_CRIT_BONUS = PRESSURE_CRIT_BONUS
        raid_v60.PRESSURE_ABILITY_GAIN = PRESSURE_ABILITY_GAIN
        raid_v60.PRESSURE_DECAY_SECONDS = PRESSURE_DECAY_SECONDS
    except Exception:
        LOGGER.exception("Не удалось применить баланс давления Reality 65")

    original_connect = core.Database.connect

    async def connect_with_v65_balance(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()

        async with self.lock:
            try:
                # Нулевой активный босс уже побеждён. Сначала переводим его в
                # resolving, чтобы увеличение максимального HP не воскресило бой.
                await conn.execute(
                    """
                    UPDATE boss_battles
                    SET hp = 0, status = 'resolving'
                    WHERE status = 'active' AND hp <= 0
                    """
                )

                # Для текущего активного боя сохраняем уже нанесённый урон:
                # например, 60 000 / 75 000 превращается в 85 000 / 100 000.
                await conn.execute(
                    """
                    UPDATE boss_battles
                    SET hp = MIN(?, MAX(1, hp + (? - max_hp))),
                        max_hp = ?
                    WHERE status = 'active'
                      AND hp > 0
                      AND max_hp <> ?
                    """,
                    (BOSS_HP, BOSS_HP, BOSS_HP, BOSS_HP),
                )

                # Завершающийся рейд всегда должен оставаться на нулевом HP.
                await conn.execute(
                    "UPDATE boss_battles SET hp = 0 WHERE status = 'resolving'"
                )
                await conn.commit()
            except Exception:
                await conn.rollback()
                LOGGER.exception("Не удалось мигрировать рейд на 100 000 HP")
                raise

    core.Database.connect = connect_with_v65_balance
