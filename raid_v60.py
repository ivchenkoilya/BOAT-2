from __future__ import annotations

import html
import logging
import random
import time
from typing import Any


LOGGER = logging.getLogger(__name__)
PRESSURE_MAX = 100
PRESSURE_DECAY_SECONDS = 15
PRESSURE_HIT_GAIN = 9
PRESSURE_CRIT_BONUS = 5
PRESSURE_ABILITY_GAIN = 20
TEAM_STRIKE_DAMAGE = (1200, 1800)

ACTION_INFO: dict[str, dict[str, str]] = {
    "shield": {
        "name": "Все мне завидуют",
        "icon": "🪞",
        "target": "Щит ЧСВ",
        "hint": "Босс усилит свою защиту",
    },
    "silence": {
        "name": "Тебя никто не слушает",
        "icon": "🗯",
        "target": "один герой",
        "hint": "Один участник временно потеряет возможность атаковать",
    },
    "single": {
        "name": "Сокрушить самооценку",
        "icon": "🌌",
        "target": "один герой",
        "hint": "Сильный удар по случайному участнику",
    },
    "mass": {
        "name": "Вы всего лишь массовка",
        "icon": "👥",
        "target": "весь отряд",
        "hint": "Урон получат все незащищённые герои",
    },
}


def install_raid_v60(core: Any) -> None:
    """Добавляет предупреждения атак, давление отряда и расширенную статистику."""
    if getattr(core, "_raid_v60_installed", False):
        return
    core._raid_v60_installed = True

    original_connect = core.Database.connect

    async def connect_with_v60(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS boss_runtime_v60 (
                    boss_id TEXT PRIMARY KEY,
                    pressure INTEGER NOT NULL DEFAULT 0,
                    pressure_updated_at INTEGER NOT NULL DEFAULT 0,
                    planned_action TEXT,
                    planned_for INTEGER NOT NULL DEFAULT 0,
                    last_combo_at INTEGER NOT NULL DEFAULT 0,
                    last_combo_damage INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_boss_runtime_v60_combo
                ON boss_runtime_v60 (last_combo_at);
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_v60

    def choose_action(phase: int, has_fighters: bool) -> str:
        if not has_fighters:
            return "shield"
        pool = ["single", "single", "shield"]
        if phase >= 2:
            pool.append("mass")
        if phase >= 3:
            pool.extend(["silence", "mass"])
        if phase >= 4:
            pool.extend(["single", "mass"])
        return random.choice(pool)

    async def ensure_runtime_locked(
        conn: Any,
        boss_id: str,
        now: int,
    ) -> Any:
        await conn.execute(
            """
            INSERT OR IGNORE INTO boss_runtime_v60 (
                boss_id, pressure, pressure_updated_at
            ) VALUES (?, 0, ?)
            """,
            (boss_id, now),
        )
        cursor = await conn.execute(
            "SELECT * FROM boss_runtime_v60 WHERE boss_id = ?",
            (boss_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("Не удалось создать состояние рейда Reality 60")
        return row

    def decayed_pressure(row: Any, now: int) -> tuple[int, int]:
        pressure = max(0, int(row["pressure"]))
        updated_at = int(row["pressure_updated_at"] or now)
        steps = max(0, (now - updated_at) // PRESSURE_DECAY_SECONDS)
        if steps:
            pressure = max(0, pressure - steps)
            updated_at += steps * PRESSURE_DECAY_SECONDS
        return pressure, updated_at

    async def runtime_snapshot(database: Any, boss_id: str) -> dict[str, Any]:
        conn = database._require_connection()
        now = int(time.time())
        async with database.lock:
            cursor = await conn.execute(
                "SELECT * FROM boss_battles WHERE boss_id = ?",
                (boss_id,),
            )
            battle = await cursor.fetchone()
            if battle is None:
                return {
                    "pressure": 0,
                    "pressure_max": PRESSURE_MAX,
                    "next_action_key": "shield",
                    **ACTION_INFO["shield"],
                }

            cursor = await conn.execute(
                "SELECT COUNT(*) AS amount FROM boss_fighters WHERE boss_id = ? AND player_hp > 0",
                (boss_id,),
            )
            fighter_count_row = await cursor.fetchone()
            has_fighters = bool(fighter_count_row and int(fighter_count_row["amount"]) > 0)
            runtime = await ensure_runtime_locked(conn, boss_id, now)
            pressure, pressure_updated_at = decayed_pressure(runtime, now)

            planned_action = str(runtime["planned_action"] or "")
            planned_for = int(runtime["planned_for"] or 0)
            next_action_at = int(battle["next_action_at"])
            if (
                planned_action not in ACTION_INFO
                or planned_for != next_action_at
            ):
                planned_action = choose_action(int(battle["phase"]), has_fighters)
                planned_for = next_action_at

            await conn.execute(
                """
                UPDATE boss_runtime_v60
                SET pressure = ?, pressure_updated_at = ?,
                    planned_action = ?, planned_for = ?
                WHERE boss_id = ?
                """,
                (
                    pressure,
                    pressure_updated_at,
                    planned_action,
                    planned_for,
                    boss_id,
                ),
            )
            await conn.commit()

            info = ACTION_INFO[planned_action]
            return {
                "pressure": pressure,
                "pressure_max": PRESSURE_MAX,
                "next_action_key": planned_action,
                "next_action_name": info["name"],
                "next_action_icon": info["icon"],
                "next_action_target": info["target"],
                "next_action_hint": info["hint"],
                "last_combo_at": int(runtime["last_combo_at"] or 0),
                "last_combo_damage": int(runtime["last_combo_damage"] or 0),
            }

    async def add_pressure(
        database: Any,
        boss_id: str,
        user_id: int,
        gain: int,
    ) -> dict[str, Any]:
        conn = database._require_connection()
        now = int(time.time())
        result = {
            "pressure": 0,
            "pressure_max": PRESSURE_MAX,
            "team_strike_damage": 0,
        }

        async with database.lock:
            cursor = await conn.execute(
                "SELECT * FROM boss_battles WHERE boss_id = ?",
                (boss_id,),
            )
            battle = await cursor.fetchone()
            if (
                battle is None
                or str(battle["status"]) != "active"
                or int(battle["hp"]) <= 0
            ):
                return result

            runtime = await ensure_runtime_locked(conn, boss_id, now)
            pressure, _ = decayed_pressure(runtime, now)
            pressure = min(PRESSURE_MAX, pressure + max(0, int(gain)))
            combo_damage = 0
            combo_at = int(runtime["last_combo_at"] or 0)

            if pressure >= PRESSURE_MAX:
                rolled = random.randint(*TEAM_STRIKE_DAMAGE)
                hp_before = int(battle["hp"])
                combo_damage = min(hp_before, rolled)
                hp_after = max(0, hp_before - combo_damage)
                phase_after = core.boss_phase_for_hp(
                    hp_after,
                    int(battle["max_hp"]),
                )
                pressure = 0
                combo_at = now

                await conn.execute(
                    """
                    UPDATE boss_battles
                    SET hp = ?, phase = ?, last_attacker_id = ?
                    WHERE boss_id = ?
                    """,
                    (hp_after, phase_after, user_id, boss_id),
                )
                await conn.execute(
                    """
                    UPDATE boss_fighters
                    SET damage_done = damage_done + ?
                    WHERE boss_id = ? AND user_id = ?
                    """,
                    (combo_damage, boss_id, user_id),
                )
                await conn.execute(
                    """
                    INSERT INTO boss_logs (boss_id, log_text, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        boss_id,
                        f"⚡ Давление отряда достигло максимума: коллективное унижение нанесло −{combo_damage} HP.",
                        now,
                    ),
                )
                result.update(
                    {
                        "hp": hp_after,
                        "phase": phase_after,
                        "defeated": hp_after <= 0,
                        "team_strike_damage": combo_damage,
                    }
                )

            await conn.execute(
                """
                UPDATE boss_runtime_v60
                SET pressure = ?, pressure_updated_at = ?,
                    last_combo_at = ?, last_combo_damage = ?
                WHERE boss_id = ?
                """,
                (
                    pressure,
                    now,
                    combo_at,
                    combo_damage if combo_damage else int(runtime["last_combo_damage"] or 0),
                    boss_id,
                ),
            )
            await conn.commit()

        result["pressure"] = pressure
        return result

    original_hit = core.Database.boss_apply_hit

    async def hit_with_pressure(
        self: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        result = await original_hit(
            self,
            boss_id,
            chat_id,
            user_id,
            *args,
            **kwargs,
        )
        if (
            not result.get("ok")
            or int(result.get("damage", 0)) <= 0
            or result.get("defeated")
        ):
            return result
        gain = PRESSURE_HIT_GAIN
        if result.get("critical"):
            gain += PRESSURE_CRIT_BONUS
        pressure_result = await add_pressure(self, boss_id, user_id, gain)
        updated = dict(result)
        updated.update(pressure_result)
        updated["damage"] = int(result.get("damage", 0)) + int(
            pressure_result.get("team_strike_damage", 0)
        )
        updated["phase_changed"] = bool(result.get("phase_changed")) or (
            "phase" in pressure_result
            and int(pressure_result["phase"]) != int(result.get("phase", 1))
        )
        return updated

    core.Database.boss_apply_hit = hit_with_pressure
    core.Database.r49_boss_apply_hit = hit_with_pressure

    original_ability = core.Database.boss_apply_ability

    async def ability_with_pressure(
        self: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        result = await original_ability(
            self,
            boss_id,
            chat_id,
            user_id,
            *args,
            **kwargs,
        )
        if (
            not result.get("ok")
            or int(result.get("damage", 0)) <= 0
            or result.get("defeated")
        ):
            return result
        pressure_result = await add_pressure(
            self,
            boss_id,
            user_id,
            PRESSURE_ABILITY_GAIN,
        )
        updated = dict(result)
        updated.update(pressure_result)
        updated["damage"] = int(result.get("damage", 0)) + int(
            pressure_result.get("team_strike_damage", 0)
        )
        updated["phase_changed"] = bool(result.get("phase_changed")) or (
            "phase" in pressure_result
            and int(pressure_result["phase"]) != int(result.get("phase", 1))
        )
        return updated

    core.Database.boss_apply_ability = ability_with_pressure

    async def boss_perform_action(self: Any, boss_id: str) -> dict[str, Any]:
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
            if int(battle["next_action_at"]) > now:
                return {"ok": False, "reason": "not_due"}

            next_action_at = now + core.BOSS_ACTION_INTERVAL_SECONDS
            runtime = await ensure_runtime_locked(conn, boss_id, now)

            if int(battle["skip_next_action"]) > 0:
                log_text = "🌫 Центр Вселенной потерялся в пыли и пропустил ответную атаку."
                action = "skip"
                affected: list[dict[str, Any]] = []
                await conn.execute(
                    """
                    UPDATE boss_battles
                    SET skip_next_action = 0, next_action_at = ?
                    WHERE boss_id = ?
                    """,
                    (next_action_at, boss_id),
                )
            else:
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
                phase = int(battle["phase"])
                planned = str(runtime["planned_action"] or "")
                if (
                    planned not in ACTION_INFO
                    or int(runtime["planned_for"] or 0) != int(battle["next_action_at"])
                ):
                    planned = choose_action(phase, bool(fighters))
                action = planned
                log_text = ""
                affected = []

                if action == "shield":
                    shield = 2 + phase
                    await conn.execute(
                        "UPDATE boss_battles SET shield_hits = shield_hits + ? WHERE boss_id = ?",
                        (shield, boss_id),
                    )
                    log_text = f"🪞 «Все мне завидуют»: следующие {shield} удара ослаблены."
                elif action == "silence":
                    target = random.choice(fighters)
                    target_id = int(target["user_id"])
                    name = html.escape(
                        str(target["full_name"] or f"Участник {target_id}")
                    )
                    if int(target["protected"]) > 0:
                        await conn.execute(
                            "UPDATE boss_fighters SET protected = 0 WHERE boss_id = ? AND user_id = ?",
                            (boss_id, target_id),
                        )
                        log_text = f"🛡 {name} отразил попытку обесценивания."
                    else:
                        duration = 25 + phase * 8
                        await conn.execute(
                            "UPDATE boss_fighters SET silenced_until = ? WHERE boss_id = ? AND user_id = ?",
                            (now + duration, boss_id, target_id),
                        )
                        log_text = (
                            f"🗯 «Тебя никто не слушает»: {name} лишён атак "
                            f"на {duration} сек."
                        )
                else:
                    targets = [random.choice(fighters)] if action == "single" else fighters
                    damage_range = (
                        (18 + phase * 6, 28 + phase * 8)
                        if action == "single"
                        else (8 + phase * 4, 14 + phase * 6)
                    )
                    lines: list[str] = []
                    for target in targets:
                        target_id = int(target["user_id"])
                        name = html.escape(
                            str(target["full_name"] or f"Участник {target_id}")
                        )
                        if int(target["protected"]) > 0:
                            await conn.execute(
                                "UPDATE boss_fighters SET protected = 0 WHERE boss_id = ? AND user_id = ?",
                                (boss_id, target_id),
                            )
                            lines.append(f"{name} отразил удар")
                            affected.append(
                                {
                                    "user_id": target_id,
                                    "damage": 0,
                                    "protected": True,
                                }
                            )
                            continue
                        damage = random.randint(*damage_range)
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
                            (
                                hp_after,
                                damage,
                                knocked_until,
                                boss_id,
                                target_id,
                            ),
                        )
                        lines.append(
                            f"{name} −{damage} HP"
                            + (" и выбит" if hp_after <= 0 else "")
                        )
                        affected.append(
                            {
                                "user_id": target_id,
                                "damage": damage,
                                "hp": hp_after,
                                "knocked_out": hp_after <= 0,
                            }
                        )
                    title = (
                        "🌌 «Сокрушить самооценку»"
                        if action == "single"
                        else "👥 «Вы всего лишь массовка»"
                    )
                    log_text = title + ": " + "; ".join(lines) + "."

                await conn.execute(
                    "UPDATE boss_battles SET next_action_at = ? WHERE boss_id = ?",
                    (next_action_at, boss_id),
                )

            cursor = await conn.execute(
                "SELECT COUNT(*) AS amount FROM boss_fighters WHERE boss_id = ? AND player_hp > 0",
                (boss_id,),
            )
            alive_row = await cursor.fetchone()
            next_planned = choose_action(
                int(battle["phase"]),
                bool(alive_row and int(alive_row["amount"]) > 0),
            )
            await conn.execute(
                """
                UPDATE boss_runtime_v60
                SET planned_action = ?, planned_for = ?
                WHERE boss_id = ?
                """,
                (next_planned, next_action_at, boss_id),
            )
            await conn.execute(
                "INSERT INTO boss_logs (boss_id, log_text, created_at) VALUES (?, ?, ?)",
                (boss_id, log_text, now),
            )
            await conn.commit()
            return {
                "ok": True,
                "action": action,
                "log": log_text,
                "affected": affected,
            }

    core.Database.boss_perform_action = boss_perform_action

    original_build_state = core.build_boss_web_state

    async def build_state_v60(boss_id: str, user_id: int) -> dict[str, Any]:
        result = await original_build_state(boss_id, user_id)
        if not result.get("ok"):
            return result

        snapshot = await runtime_snapshot(core.db, boss_id)
        battle = result.setdefault("battle", {})
        battle.update(snapshot)

        fighters_by_id = {
            int(item.get("user_id", 0)): item
            for item in result.get("fighters", [])
        }
        victory = result.get("victory")
        if isinstance(victory, dict):
            rankings = victory.get("rankings") or []
            for ranking in rankings:
                fighter = fighters_by_id.get(int(ranking.get("user_id", 0)), {})
                ranking.update(
                    {
                        "attacks": int(fighter.get("attacks", 0)),
                        "critical_hits": int(fighter.get("critical_hits", 0)),
                        "healing_done": int(fighter.get("healing_done", 0)),
                        "damage_taken": int(fighter.get("damage_taken", 0)),
                    }
                )

            self_fighter = fighters_by_id.get(user_id, {})
            critical_hits = int(self_fighter.get("critical_hits", 0))
            healing_done = int(self_fighter.get("healing_done", 0))
            attacks = int(self_fighter.get("attacks", 0))
            if critical_hits:
                best_moment = f"Критический натиск: {critical_hits} критических ударов"
            elif healing_done:
                best_moment = f"Поддержка отряда: восстановлено {healing_done} HP"
            elif attacks:
                best_moment = f"Боевой темп: выполнено {attacks} атак"
            else:
                best_moment = "Участие в финальной победе"

            victory["self_stats"] = {
                "damage": int(self_fighter.get("damage", 0)),
                "attacks": attacks,
                "critical_hits": critical_hits,
                "healing_done": healing_done,
                "damage_taken": int(self_fighter.get("damage_taken", 0)),
                "best_moment": best_moment,
            }
            victory["team_damage"] = sum(
                int(item.get("damage", 0))
                for item in result.get("fighters", [])
            )

        return result

    core.build_boss_web_state = build_state_v60
