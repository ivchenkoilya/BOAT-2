from __future__ import annotations

import html
import logging
import random
import time
from typing import Any


LOGGER = logging.getLogger(__name__)
NORMAL_DAMAGE_MIN = 100
NORMAL_DAMAGE_MAX = 200
ULTIMATE_DAMAGE_MIN = 200
ULTIMATE_DAMAGE_MAX = 300
ULTIMATE_WARNING_SECONDS = 10
DEBUFF_CHANCE = 0.40
DEBUFF_HITS = 2
WEAKEN_MULTIPLIER = 0.70
CRIT_BLOCK_MULTIPLIER = 0.45
PASSIVE_HEAL_MIN = 100
PASSIVE_HEAL_MAX = 150
PASSIVE_HEAL_INTERVAL_SECONDS = 5 * 60


def install_boss_combat_v149(core: Any) -> None:
    """Final boss rebalance: stronger attacks, debuffs, ultimate and healing."""
    if getattr(core, "_boss_combat_v149_installed", False):
        return
    core._boss_combat_v149_installed = True

    # Старый runtime сохраняет своё расписание, но больше не лечит фиксированной
    # величиной: случайное восстановление 100–150 HP выполняет этот слой.
    core.BOSS_PASSIVE_HEAL_AMOUNT = 0

    original_connect = core.Database.connect

    async def connect_with_boss_combat_v149(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS boss_runtime_v149 (
                    boss_id TEXT PRIMARY KEY,
                    ultimate_state TEXT NOT NULL DEFAULT 'ready',
                    ultimate_at INTEGER NOT NULL DEFAULT 0,
                    last_heal_at INTEGER NOT NULL DEFAULT 0,
                    last_heal_amount INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS boss_debuffs_v149 (
                    boss_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    weaken_hits INTEGER NOT NULL DEFAULT 0,
                    crit_block_hits INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (boss_id, user_id)
                );

                CREATE INDEX IF NOT EXISTS idx_boss_debuffs_v149_boss
                ON boss_debuffs_v149 (boss_id, user_id);
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_boss_combat_v149

    async def ensure_runtime_locked(conn: Any, boss_id: str, now: int) -> Any:
        await conn.execute(
            """
            INSERT INTO boss_runtime_v149 (
                boss_id, ultimate_state, ultimate_at,
                last_heal_at, last_heal_amount, updated_at
            ) VALUES (?, 'ready', 0, ?, 0, ?)
            ON CONFLICT(boss_id) DO NOTHING
            """,
            (boss_id, now, now),
        )
        cursor = await conn.execute(
            "SELECT * FROM boss_runtime_v149 WHERE boss_id = ?",
            (boss_id,),
        )
        return await cursor.fetchone()

    async def maybe_passive_heal_locked(
        conn: Any,
        battle: Any,
        runtime: Any,
        now: int,
    ) -> tuple[Any, int]:
        if (
            str(battle["status"]) != "active"
            or int(battle["hp"]) <= 0
            or int(battle["hp"]) >= int(battle["max_hp"])
            or int(battle["heal_block_until"]) > now
            or now - int(runtime["last_heal_at"]) < PASSIVE_HEAL_INTERVAL_SECONDS
        ):
            return battle, 0

        requested = random.randint(PASSIVE_HEAL_MIN, PASSIVE_HEAL_MAX)
        healed = min(requested, int(battle["max_hp"]) - int(battle["hp"]))
        if healed <= 0:
            return battle, 0

        hp_after = int(battle["hp"]) + healed
        phase_after = core.boss_phase_for_hp(hp_after, int(battle["max_hp"]))
        await conn.execute(
            "UPDATE boss_battles SET hp = ?, phase = ? WHERE boss_id = ?",
            (hp_after, phase_after, str(battle["boss_id"])),
        )
        await conn.execute(
            """
            UPDATE boss_runtime_v149
            SET last_heal_at = ?, last_heal_amount = ?, updated_at = ?
            WHERE boss_id = ?
            """,
            (now, healed, now, str(battle["boss_id"])),
        )
        await conn.execute(
            "INSERT INTO boss_logs (boss_id, log_text, created_at) VALUES (?, ?, ?)",
            (
                str(battle["boss_id"]),
                f"💚 Центр Вселенной восстановил {healed} HP.",
                now,
            ),
        )
        cursor = await conn.execute(
            "SELECT * FROM boss_battles WHERE boss_id = ?",
            (str(battle["boss_id"]),),
        )
        return await cursor.fetchone(), healed

    async def arm_ultimate_locked(
        conn: Any,
        boss_id: str,
        now: int,
    ) -> dict[str, Any]:
        ultimate_at = now + ULTIMATE_WARNING_SECONDS
        await conn.execute(
            """
            UPDATE boss_runtime_v149
            SET ultimate_state = 'armed', ultimate_at = ?, updated_at = ?
            WHERE boss_id = ?
            """,
            (ultimate_at, now, boss_id),
        )
        await conn.execute(
            "UPDATE boss_battles SET next_action_at = ? WHERE boss_id = ?",
            (ultimate_at, boss_id),
        )
        log_text = (
            "⚠️ Центр Вселенной готовит ульту «Ты здесь никто». "
            "Через 10 секунд весь отряд получит 200–300 урона; защита не спасёт."
        )
        await conn.execute(
            "INSERT INTO boss_logs (boss_id, log_text, created_at) VALUES (?, ?, ?)",
            (boss_id, log_text, now),
        )
        await conn.commit()
        return {
            "ok": True,
            "action": "ultimate_warning",
            "log": log_text,
            "affected": [],
            "ultimate_at": ultimate_at,
        }

    async def execute_ultimate_locked(
        conn: Any,
        battle: Any,
        now: int,
    ) -> dict[str, Any]:
        boss_id = str(battle["boss_id"])
        cursor = await conn.execute(
            """
            SELECT bf.*, p.full_name
            FROM boss_fighters bf
            LEFT JOIN players p
              ON p.chat_id = ? AND p.user_id = bf.user_id
            WHERE bf.boss_id = ? AND bf.player_hp > 0
            ORDER BY bf.joined_at ASC
            """,
            (int(battle["chat_id"]), boss_id),
        )
        fighters = list(await cursor.fetchall())
        affected: list[dict[str, Any]] = []
        lines: list[str] = []

        for target in fighters:
            user_id = int(target["user_id"])
            name = html.escape(str(target["full_name"] or f"Участник {user_id}"))
            damage = random.randint(ULTIMATE_DAMAGE_MIN, ULTIMATE_DAMAGE_MAX)
            hp_after = max(0, int(target["player_hp"]) - damage)
            knocked_until = (
                now + core.BOSS_KNOCKOUT_SECONDS
                if hp_after <= 0
                else int(target["knocked_out_until"])
            )
            await conn.execute(
                """
                UPDATE boss_fighters
                SET player_hp = ?, damage_taken = damage_taken + ?,
                    knocked_out_until = ?
                WHERE boss_id = ? AND user_id = ?
                """,
                (hp_after, damage, knocked_until, boss_id, user_id),
            )
            lines.append(
                f"{name} −{damage} HP" + (" и выбит" if hp_after <= 0 else "")
            )
            affected.append(
                {
                    "user_id": user_id,
                    "damage": damage,
                    "hp": hp_after,
                    "knocked_out": hp_after <= 0,
                    "ultimate": True,
                    "ignored_defense": True,
                }
            )

        next_action_at = now + core.BOSS_ACTION_INTERVAL_SECONDS
        await conn.execute(
            "UPDATE boss_battles SET next_action_at = ? WHERE boss_id = ?",
            (next_action_at, boss_id),
        )
        await conn.execute(
            """
            UPDATE boss_runtime_v149
            SET ultimate_state = 'used', ultimate_at = 0, updated_at = ?
            WHERE boss_id = ?
            """,
            (now, boss_id),
        )
        log_text = "☄️ УЛЬТА «ТЫ ЗДЕСЬ НИКТО»: " + (
            "; ".join(lines) if lines else "в отряде не осталось целей"
        ) + "."
        await conn.execute(
            "INSERT INTO boss_logs (boss_id, log_text, created_at) VALUES (?, ?, ?)",
            (boss_id, log_text, now),
        )
        await conn.commit()
        return {
            "ok": True,
            "action": "ultimate",
            "log": log_text,
            "affected": affected,
            "next_action_at": next_action_at,
        }

    async def apply_debuff_locked(
        conn: Any,
        boss_id: str,
        user_id: int,
        now: int,
    ) -> tuple[str, str]:
        if random.random() >= DEBUFF_CHANCE:
            return "", ""

        if random.random() < 0.5:
            await conn.execute(
                """
                INSERT INTO boss_debuffs_v149 (
                    boss_id, user_id, weaken_hits, crit_block_hits, updated_at
                ) VALUES (?, ?, ?, 0, ?)
                ON CONFLICT(boss_id, user_id) DO UPDATE SET
                    weaken_hits = MAX(weaken_hits, excluded.weaken_hits),
                    updated_at = excluded.updated_at
                """,
                (boss_id, user_id, DEBUFF_HITS, now),
            )
            return "weaken", "Подавленное эго: −30% урона на 2 обычные атаки"

        await conn.execute(
            """
            INSERT INTO boss_debuffs_v149 (
                boss_id, user_id, weaken_hits, crit_block_hits, updated_at
            ) VALUES (?, ?, 0, ?, ?)
            ON CONFLICT(boss_id, user_id) DO UPDATE SET
                crit_block_hits = MAX(crit_block_hits, excluded.crit_block_hits),
                updated_at = excluded.updated_at
            """,
            (boss_id, user_id, DEBUFF_HITS, now),
        )
        return "crit_block", "Сломленная уверенность: крит отключён на 2 обычные атаки"

    original_boss_action = core.Database.boss_perform_action

    async def boss_perform_action_v149(self: Any, boss_id: str) -> dict[str, Any]:
        conn = self._require_connection()
        now = int(time.time())

        async with self.lock:
            cursor = await conn.execute(
                "SELECT * FROM boss_battles WHERE boss_id = ?",
                (boss_id,),
            )
            battle = await cursor.fetchone()
            if battle is None or str(battle["status"]) != "active":
                return {"ok": False, "reason": "inactive"}

            runtime = await ensure_runtime_locked(conn, boss_id, now)
            battle, healed = await maybe_passive_heal_locked(conn, battle, runtime, now)
            if healed:
                runtime = await ensure_runtime_locked(conn, boss_id, now)

            if int(battle["next_action_at"]) <= now:
                ultimate_state = str(runtime["ultimate_state"] or "ready")
                if ultimate_state == "armed" and int(runtime["ultimate_at"]) <= now:
                    return await execute_ultimate_locked(conn, battle, now)
                if (
                    ultimate_state == "ready"
                    and int(battle["hp"]) > 0
                    and int(battle["hp"]) * 2 <= int(battle["max_hp"])
                ):
                    return await arm_ultimate_locked(conn, boss_id, now)

            if healed:
                await conn.commit()

        result = await original_boss_action(self, boss_id)
        if not result.get("ok") or result.get("action") not in {"single", "mass"}:
            return result

        affected = list(result.get("affected") or [])
        if not affected:
            return result

        now = int(time.time())
        final_affected: list[dict[str, Any]] = []
        final_lines: list[str] = []
        debuff_lines: list[str] = []

        async with self.lock:
            cursor = await conn.execute(
                "SELECT chat_id FROM boss_battles WHERE boss_id = ?",
                (boss_id,),
            )
            battle_ref = await cursor.fetchone()
            if battle_ref is None:
                return result
            chat_id = int(battle_ref["chat_id"])

            for item in affected:
                entry = dict(item)
                user_id = int(entry.get("user_id", 0))
                current_damage = max(0, int(entry.get("damage", 0)))
                mitigated = max(0, int(entry.get("mitigated", 0)))

                cursor = await conn.execute(
                    """
                    SELECT bf.*, p.full_name
                    FROM boss_fighters bf
                    LEFT JOIN players p
                      ON p.chat_id = ? AND p.user_id = bf.user_id
                    WHERE bf.boss_id = ? AND bf.user_id = ?
                    """,
                    (chat_id, boss_id, user_id),
                )
                fighter = await cursor.fetchone()
                if fighter is None:
                    final_affected.append(entry)
                    continue

                name = html.escape(
                    str(fighter["full_name"] or f"Участник {user_id}")
                )
                if entry.get("protected") or (current_damage == 0 and mitigated > 0):
                    final_lines.append(f"{name} избежал урона")
                    final_affected.append(entry)
                    continue

                original_before_mitigation = max(1, current_damage + mitigated)
                survival_ratio = current_damage / original_before_mitigation
                requested_base = random.randint(NORMAL_DAMAGE_MIN, NORMAL_DAMAGE_MAX)
                target_damage = max(0, int(round(requested_base * survival_ratio)))
                extra = max(0, target_damage - current_damage)
                hp_now = int(fighter["player_hp"])
                hp_after = max(0, hp_now - extra)
                knocked_until = (
                    now + core.BOSS_KNOCKOUT_SECONDS
                    if hp_after <= 0
                    else int(fighter["knocked_out_until"])
                )
                if extra > 0:
                    await conn.execute(
                        """
                        UPDATE boss_fighters
                        SET player_hp = ?, damage_taken = damage_taken + ?,
                            knocked_out_until = ?
                        WHERE boss_id = ? AND user_id = ?
                        """,
                        (hp_after, extra, knocked_until, boss_id, user_id),
                    )

                entry.update(
                    damage=target_damage,
                    hp=hp_after,
                    knocked_out=hp_after <= 0,
                    boss_base_damage=requested_base,
                )
                final_affected.append(entry)
                final_lines.append(
                    f"{name} −{target_damage} HP"
                    + (" и выбит" if hp_after <= 0 else "")
                )

                if target_damage > 0:
                    _, debuff_text = await apply_debuff_locked(
                        conn, boss_id, user_id, now
                    )
                    if debuff_text:
                        debuff_lines.append(f"{name} — {debuff_text}")

            title = (
                "🌌 «Сокрушить самооценку»"
                if result.get("action") == "single"
                else "👥 «Вы всего лишь массовка»"
            )
            log_text = title + ": " + "; ".join(final_lines) + "."
            if debuff_lines:
                log_text += " 🕸 " + "; ".join(debuff_lines) + "."
            await conn.execute(
                "INSERT INTO boss_logs (boss_id, log_text, created_at) VALUES (?, ?, ?)",
                (boss_id, log_text, now),
            )
            await conn.commit()

        output = dict(result)
        output["affected"] = final_affected
        output["log"] = log_text
        output["debuffs_applied"] = debuff_lines
        return output

    core.Database.boss_perform_action = boss_perform_action_v149

    original_hit = core.Database.boss_apply_hit

    async def boss_apply_hit_v149(
        self: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        result = await original_hit(self, boss_id, chat_id, user_id)
        if not result.get("ok") or int(result.get("damage", 0)) <= 0:
            return result

        conn = self._require_connection()
        now = int(time.time())
        async with self.lock:
            cursor = await conn.execute(
                """
                SELECT weaken_hits, crit_block_hits
                FROM boss_debuffs_v149
                WHERE boss_id = ? AND user_id = ?
                """,
                (boss_id, user_id),
            )
            debuff = await cursor.fetchone()
            if debuff is None:
                return result

            weaken_hits = max(0, int(debuff["weaken_hits"]))
            crit_block_hits = max(0, int(debuff["crit_block_hits"]))
            if weaken_hits <= 0 and crit_block_hits <= 0:
                return result

            total_damage = max(0, int(result.get("damage", 0)))
            team_damage = max(0, int(result.get("team_strike_damage", 0)))
            personal_damage = max(0, total_damage - team_damage)
            adjusted_personal = personal_damage
            notes: list[str] = []
            blocked_critical = False

            if crit_block_hits > 0:
                crit_block_hits -= 1
                if result.get("critical"):
                    adjusted_personal = int(round(adjusted_personal * CRIT_BLOCK_MULTIPLIER))
                    blocked_critical = True
                notes.append("критический урон отключён")

            if weaken_hits > 0:
                weaken_hits -= 1
                adjusted_personal = int(round(adjusted_personal * WEAKEN_MULTIPLIER))
                notes.append("урон снижен на 30%")

            refund = max(0, personal_damage - adjusted_personal)
            if refund <= 0:
                await conn.execute(
                    """
                    UPDATE boss_debuffs_v149
                    SET weaken_hits = ?, crit_block_hits = ?, updated_at = ?
                    WHERE boss_id = ? AND user_id = ?
                    """,
                    (weaken_hits, crit_block_hits, now, boss_id, user_id),
                )
                await conn.commit()
                return result

            cursor = await conn.execute(
                "SELECT hp, max_hp, phase FROM boss_battles WHERE boss_id = ?",
                (boss_id,),
            )
            battle = await cursor.fetchone()
            if battle is None:
                return result

            hp_after = min(int(battle["max_hp"]), int(battle["hp"]) + refund)
            phase_after = core.boss_phase_for_hp(hp_after, int(battle["max_hp"]))
            await conn.execute(
                "UPDATE boss_battles SET hp = ?, phase = ? WHERE boss_id = ?",
                (hp_after, phase_after, boss_id),
            )
            await conn.execute(
                """
                UPDATE boss_fighters
                SET damage_done = MAX(0, damage_done - ?),
                    critical_hits = MAX(0, critical_hits - ?)
                WHERE boss_id = ? AND user_id = ?
                """,
                (refund, 1 if blocked_critical else 0, boss_id, user_id),
            )
            await conn.execute(
                """
                UPDATE boss_debuffs_v149
                SET weaken_hits = ?, crit_block_hits = ?, updated_at = ?
                WHERE boss_id = ? AND user_id = ?
                """,
                (weaken_hits, crit_block_hits, now, boss_id, user_id),
            )
            await conn.execute(
                "INSERT INTO boss_logs (boss_id, log_text, created_at) VALUES (?, ?, ?)",
                (
                    boss_id,
                    "🕸 Дебаф сработал: " + ", ".join(notes) + f"; −{refund} урона отменено.",
                    now,
                ),
            )
            await conn.commit()

        output = dict(result)
        output["damage"] = adjusted_personal + team_damage
        output["critical"] = False if blocked_critical else bool(result.get("critical"))
        output["debuff_reduction"] = refund
        output["debuff_notes"] = notes
        output["hp"] = hp_after
        output["phase"] = phase_after
        output["phase_changed"] = phase_after != int(result.get("phase", phase_after))
        output["defeated"] = hp_after <= 0
        return output

    core.Database.boss_apply_hit = boss_apply_hit_v149
    core.Database.r49_boss_apply_hit = boss_apply_hit_v149

    original_build_state = core.build_boss_web_state

    async def build_boss_state_v149(boss_id: str, user_id: int) -> dict[str, Any]:
        result = await original_build_state(boss_id, user_id)
        if not result.get("ok"):
            return result

        conn = core.db._require_connection()
        now = int(time.time())
        async with core.db.lock:
            runtime = await ensure_runtime_locked(conn, boss_id, now)
            await conn.commit()
            cursor = await conn.execute(
                """
                SELECT user_id, weaken_hits, crit_block_hits
                FROM boss_debuffs_v149
                WHERE boss_id = ?
                """,
                (boss_id,),
            )
            debuffs = {
                int(row["user_id"]): {
                    "weaken_hits": max(0, int(row["weaken_hits"])),
                    "crit_block_hits": max(0, int(row["crit_block_hits"])),
                }
                for row in await cursor.fetchall()
            }

        battle = result.setdefault("battle", {})
        ultimate_state = str(runtime["ultimate_state"] or "ready")
        ultimate_at = int(runtime["ultimate_at"] or 0)
        battle.update(
            {
                "ultimate_state": ultimate_state,
                "ultimate_armed": ultimate_state == "armed",
                "ultimate_used": ultimate_state == "used",
                "ultimate_at": ultimate_at,
                "last_passive_heal_amount": int(runtime["last_heal_amount"] or 0),
                "next_passive_heal_at": int(runtime["last_heal_at"] or now)
                + PASSIVE_HEAL_INTERVAL_SECONDS,
                "boss_damage_range": [NORMAL_DAMAGE_MIN, NORMAL_DAMAGE_MAX],
                "ultimate_damage_range": [ULTIMATE_DAMAGE_MIN, ULTIMATE_DAMAGE_MAX],
            }
        )
        if ultimate_state == "armed":
            battle.update(
                {
                    "next_action_at": ultimate_at,
                    "next_action_name": "Ты здесь никто",
                    "next_action_icon": "☄️",
                    "next_action_target": "весь отряд",
                    "next_action_hint": "УЛЬТА: 200–300 урона каждому, защита не спасёт",
                }
            )

        for fighter in result.get("fighters", []):
            values = debuffs.get(int(fighter.get("user_id", 0)), {})
            fighter["debuffs"] = values
        self_data = result.get("self")
        if isinstance(self_data, dict):
            self_data["debuffs"] = debuffs.get(user_id, {})
        return result

    core.build_boss_web_state = build_boss_state_v149
