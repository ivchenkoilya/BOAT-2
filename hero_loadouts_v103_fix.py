from __future__ import annotations

import html
import time
from typing import Any


def install_hero_loadouts_v103_fix(core: Any) -> None:
    """Доводит провокацию и данные карточек героев до финального состояния."""
    if getattr(core, "_hero_loadouts_v103_fix_installed", False):
        return
    core._hero_loadouts_v103_fix_installed = True

    original_state = core.build_boss_web_state

    async def state_with_complete_catalog(
        boss_id: str,
        user_id: int,
    ) -> dict[str, Any]:
        result = await original_state(boss_id, user_id)
        for hero in result.get("hero_catalog") or []:
            hero["ability_hint"] = str(hero.get("hint") or "")
        return result

    core.build_boss_web_state = state_with_complete_catalog

    original_boss_action = core.Database.boss_perform_action

    async def boss_action_with_provoke(self: Any, boss_id: str) -> dict[str, Any]:
        result = await original_boss_action(self, boss_id)
        if not result.get("ok") or str(result.get("action")) != "single":
            return result

        affected = list(result.get("affected") or [])
        source = next(
            (
                item
                for item in affected
                if int(item.get("user_id", 0)) > 0
                and int(item.get("damage", 0)) > 0
            ),
            None,
        )
        if source is None:
            return result

        conn = self._require_connection()
        now = int(time.time())
        async with self.lock:
            cursor = await conn.execute(
                """
                SELECT runtime.user_id, players.full_name
                FROM hero_runtime_v103 runtime
                JOIN boss_battles battle ON battle.boss_id = runtime.boss_id
                LEFT JOIN players
                  ON players.chat_id = battle.chat_id
                 AND players.user_id = runtime.user_id
                WHERE runtime.boss_id = ?
                  AND runtime.effect_key = 'samoz_provoke'
                  AND (runtime.expires_at = 0 OR runtime.expires_at > ?)
                ORDER BY runtime.updated_at ASC
                LIMIT 1
                """,
                (str(boss_id), now),
            )
            provoke = await cursor.fetchone()
            if provoke is None:
                return result

            provocateur_id = int(provoke["user_id"])
            source_id = int(source["user_id"])
            damage = int(source["damage"])
            await conn.execute(
                """
                DELETE FROM hero_runtime_v103
                WHERE boss_id = ? AND user_id = ? AND effect_key = 'samoz_provoke'
                """,
                (str(boss_id), provocateur_id),
            )

            if provocateur_id == source_id:
                await conn.commit()
                return result

            cursor = await conn.execute(
                """
                SELECT player_hp, player_max_hp, protected, knocked_out_until
                FROM boss_fighters
                WHERE boss_id = ? AND user_id = ?
                """,
                (str(boss_id), provocateur_id),
            )
            target = await cursor.fetchone()
            if target is None or int(target["player_hp"]) <= 0:
                await conn.commit()
                return result

            # Возвращаем случайной цели уже применённый итоговый урон.
            await conn.execute(
                """
                UPDATE boss_fighters
                SET player_hp = MIN(player_max_hp, player_hp + ?),
                    damage_taken = MAX(0, damage_taken - ?),
                    knocked_out_until = CASE
                        WHEN player_hp + ? > 0 THEN 0
                        ELSE knocked_out_until
                    END
                WHERE boss_id = ? AND user_id = ?
                """,
                (damage, damage, damage, str(boss_id), source_id),
            )

            protected = bool(target["protected"])
            if protected:
                redirected_damage = 0
                hp_after = int(target["player_hp"])
                await conn.execute(
                    """
                    UPDATE boss_fighters SET protected = 0
                    WHERE boss_id = ? AND user_id = ?
                    """,
                    (str(boss_id), provocateur_id),
                )
            else:
                redirected_damage = damage
                hp_after = max(0, int(target["player_hp"]) - redirected_damage)
                knocked_until = (
                    now + core.BOSS_KNOCKOUT_SECONDS
                    if hp_after <= 0
                    else int(target["knocked_out_until"])
                )
                await conn.execute(
                    """
                    UPDATE boss_fighters
                    SET player_hp = ?,
                        damage_taken = damage_taken + ?,
                        knocked_out_until = ?
                    WHERE boss_id = ? AND user_id = ?
                    """,
                    (
                        hp_after,
                        redirected_damage,
                        knocked_until,
                        str(boss_id),
                        provocateur_id,
                    ),
                )

            name = html.escape(str(provoke["full_name"] or "Самозваний"))
            log = (
                f"👑 {name} крикнул «Я здесь главный» и забрал удар на себя"
                + (
                    ", но отразил его щитом."
                    if protected
                    else f": −{redirected_damage} HP."
                )
            )
            await conn.execute(
                "INSERT INTO boss_logs (boss_id, log_text, created_at) VALUES (?, ?, ?)",
                (str(boss_id), log, now),
            )
            await conn.commit()

        updated: list[dict[str, Any]] = []
        for entry in affected:
            copy = dict(entry)
            if int(copy.get("user_id", 0)) == source_id:
                copy.update(damage=0, knocked_out=False, redirected=True)
            updated.append(copy)
        updated.append(
            {
                "user_id": provocateur_id,
                "damage": redirected_damage,
                "hp": hp_after,
                "knocked_out": hp_after <= 0,
                "protected": protected,
                "provoked": True,
            }
        )
        output = dict(result)
        output["affected"] = updated
        output["provoked_by"] = provocateur_id
        output["loadout_notes"] = list(output.get("loadout_notes") or []) + [
            "Самозваний забрал следующую атаку босса"
        ]
        return output

    core.Database.boss_perform_action = boss_action_with_provoke
