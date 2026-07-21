from __future__ import annotations

import time
from typing import Any

import boss_combat_v149 as combat_v149
import hero_loadouts_v103 as loadouts


ATTACK_COOLDOWN_SECONDS = 3
ABILITY_COOLDOWN_SECONDS = 5 * 60
MAX_BOSS_SHIELDS = 3


def install_boss_balance_v151(core: Any) -> None:
    """Финальный баланс Центра Вселенной поверх всех старых боевых слоёв."""
    if getattr(core, "_boss_balance_v151_installed", False):
        return
    core._boss_balance_v151_installed = True

    # Обычный ответ босса: 50–100 базового урона. Экипировка, уклонение и
    # защитные эффекты по-прежнему могут уменьшить итоговое значение.
    combat_v149.NORMAL_DAMAGE_MIN = 50
    combat_v149.NORMAL_DAMAGE_MAX = 100

    # Более мягкие дебафы: реже, только на один обычный удар и без полного
    # уничтожения критического урона.
    combat_v149.DEBUFF_CHANCE = 0.25
    combat_v149.DEBUFF_HITS = 1
    combat_v149.WEAKEN_MULTIPLIER = 0.85
    combat_v149.CRIT_BLOCK_MULTIPLIER = 0.75

    core.BOSS_ATTACK_COOLDOWN_SECONDS = ATTACK_COOLDOWN_SECONDS
    core.ROLE_ABILITY_COOLDOWN_SECONDS = ABILITY_COOLDOWN_SECONDS
    for role_key in list(getattr(core, "BOSS_ABILITY_COOLDOWNS", {})):
        core.BOSS_ABILITY_COOLDOWNS[role_key] = ABILITY_COOLDOWN_SECONDS

    # Все герои получают не более пяти минут перезарядки. Былогерий больше не
    # ограничен одним применением за бой — «Возвращение в сюжет» доступно снова
    # после обычного пятиминутного кулдауна.
    for hero in loadouts.HEROES.values():
        hero["cooldown"] = ABILITY_COOLDOWN_SECONDS
    if 7 in loadouts.HEROES:
        loadouts.HEROES[7]["once"] = False
        loadouts.HEROES[7]["cooldown"] = ABILITY_COOLDOWN_SECONDS

    original_connect = core.Database.connect

    async def connect_with_v151(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.execute(
                "UPDATE boss_battles SET shield_hits = MIN(shield_hits, ?) WHERE shield_hits > ?",
                (MAX_BOSS_SHIELDS, MAX_BOSS_SHIELDS),
            )
            await conn.commit()

    core.Database.connect = connect_with_v151

    original_action = core.Database.boss_perform_action

    async def boss_action_v151(self: Any, boss_id: str) -> dict[str, Any]:
        started_at = int(time.time()) - 2
        result = await original_action(self, boss_id)
        if not result.get("ok"):
            return result

        conn = self._require_connection()
        async with self.lock:
            await conn.execute(
                "UPDATE boss_battles SET shield_hits = MIN(shield_hits, ?) WHERE boss_id = ?",
                (MAX_BOSS_SHIELDS, str(boss_id)),
            )
            await conn.execute(
                """
                UPDATE boss_logs
                SET log_text = REPLACE(
                    REPLACE(
                        log_text,
                        'Подавленное эго: −30% урона на 2 обычные атаки',
                        'Подавленное эго: −15% урона на 1 обычную атаку'
                    ),
                    'Сломленная уверенность: крит отключён на 2 обычные атаки',
                    'Сломленная уверенность: крит ослаблен на 25% на 1 обычную атаку'
                )
                WHERE boss_id = ? AND created_at >= ?
                """,
                (str(boss_id), started_at),
            )
            if result.get("action") == "shield":
                cursor = await conn.execute(
                    "SELECT shield_hits FROM boss_battles WHERE boss_id = ?",
                    (str(boss_id),),
                )
                row = await cursor.fetchone()
                shields = min(MAX_BOSS_SHIELDS, int(row["shield_hits"]) if row else 0)
                corrected = (
                    f"🪞 «Все мне завидуют»: Щит ЧСВ усилен до {shields}/"
                    f"{MAX_BOSS_SHIELDS}. Больше трёх зарядов накопить нельзя."
                )
                await conn.execute(
                    "INSERT INTO boss_logs (boss_id, log_text, created_at) VALUES (?, ?, ?)",
                    (str(boss_id), corrected, int(time.time())),
                )
                result = dict(result)
                result["log"] = corrected
                result["shield_hits"] = shields
            await conn.commit()

        if result.get("log"):
            result = dict(result)
            result["log"] = (
                str(result["log"])
                .replace(
                    "Подавленное эго: −30% урона на 2 обычные атаки",
                    "Подавленное эго: −15% урона на 1 обычную атаку",
                )
                .replace(
                    "Сломленная уверенность: крит отключён на 2 обычные атаки",
                    "Сломленная уверенность: крит ослаблен на 25% на 1 обычную атаку",
                )
            )
        return result

    core.Database.boss_perform_action = boss_action_v151

    original_hit = core.Database.boss_apply_hit

    async def hit_v151(
        self: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        started_at = int(time.time()) - 2
        result = await original_hit(self, boss_id, chat_id, user_id)
        if not result.get("ok"):
            return result

        notes = [
            str(note)
            .replace("критический урон отключён", "критический урон ослаблен на 25%")
            .replace("урон снижен на 30%", "урон снижен на 15%")
            for note in list(result.get("debuff_notes") or [])
        ]
        if notes:
            result = dict(result)
            result["debuff_notes"] = notes

        conn = self._require_connection()
        async with self.lock:
            await conn.execute(
                """
                UPDATE boss_logs
                SET log_text = REPLACE(
                    REPLACE(
                        log_text,
                        'критический урон отключён',
                        'критический урон ослаблен на 25%'
                    ),
                    'урон снижен на 30%',
                    'урон снижен на 15%'
                )
                WHERE boss_id = ? AND created_at >= ?
                """,
                (str(boss_id), started_at),
            )
            await conn.commit()
        return result

    core.Database.boss_apply_hit = hit_v151
    core.Database.r49_boss_apply_hit = hit_v151

    original_ability = core.Database.boss_apply_ability

    async def ability_v151(
        self: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        conn = self._require_connection()
        try:
            cursor = await conn.execute(
                "SELECT skin_id FROM hero_skin_choices_v101 WHERE user_id = ?",
                (int(user_id),),
            )
            skin_row = await cursor.fetchone()
            hero_id = int(skin_row["skin_id"]) if skin_row else 0
        except Exception:
            hero_id = 0

        if hero_id == 7:
            now = int(time.time())
            cursor = await conn.execute(
                "SELECT ability_used_at FROM boss_fighters WHERE boss_id = ? AND user_id = ?",
                (str(boss_id), int(user_id)),
            )
            fighter = await cursor.fetchone()
            if fighter is not None:
                remaining = ABILITY_COOLDOWN_SECONDS - (
                    now - int(fighter["ability_used_at"] or 0)
                )
                if remaining > 0:
                    return {
                        "ok": False,
                        "reason": (
                            "«Возвращение в сюжет» снова будет доступно через "
                            f"{core.human_duration(remaining)}."
                        ),
                    }

            async with self.lock:
                await conn.execute(
                    """
                    DELETE FROM hero_runtime_v103
                    WHERE boss_id = ? AND user_id = ? AND effect_key = 'bylo_used'
                    """,
                    (str(boss_id), int(user_id)),
                )
                await conn.commit()

        return await original_ability(self, boss_id, chat_id, user_id)

    core.Database.boss_apply_ability = ability_v151
