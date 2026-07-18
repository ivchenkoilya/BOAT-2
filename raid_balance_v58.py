from __future__ import annotations

import html
import random
import time
from typing import Any


def install_raid_balance_v58(core: Any) -> None:
    """Задаёт единый диапазон обычного и критического урона рейда."""
    if getattr(core, "_raid_balance_v59_installed", False):
        return
    core._raid_balance_v59_installed = True

    async def boss_apply_hit(
        self: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        conn = self._require_connection()
        now = int(time.time())
        async with self.lock:
            cursor = await conn.execute(
                "SELECT * FROM boss_battles WHERE boss_id = ?", (boss_id,)
            )
            battle = await cursor.fetchone()
            if battle is None or int(battle["chat_id"]) != chat_id:
                return {"ok": False, "reason": "Бой не найден."}
            if str(battle["status"]) != "active":
                return {"ok": False, "reason": "Бой уже завершён."}
            if int(battle["ends_at"]) <= now:
                return {"ok": False, "reason": "Время боя закончилось."}

            fighter, reason = await core._r49_ensure_fighter_locked(
                conn, boss_id, chat_id, user_id, now
            )
            if fighter is None:
                return {"ok": False, "reason": reason or "В бой нельзя войти."}
            if int(fighter["player_hp"]) <= 0:
                return {
                    "ok": False,
                    "reason": "Ты выбит из боя. Используй восстановление здоровья.",
                }
            knockout_left = int(fighter["knocked_out_until"]) - now
            if knockout_left > 0:
                return {
                    "ok": False,
                    "reason": f"Ты приходишь в себя ещё {knockout_left} сек.",
                }
            silence_left = int(fighter["silenced_until"]) - now
            if silence_left > 0:
                return {
                    "ok": False,
                    "reason": f"Босс обесценил тебя ещё на {silence_left} сек.",
                }
            remaining = core.BOSS_ATTACK_COOLDOWN_SECONDS - (
                now - int(fighter["last_attack_at"])
            )
            if remaining > 0:
                return {
                    "ok": False,
                    "reason": f"Следующий удар через {remaining} сек.",
                }

            role_key, full_name = await core._r49_role_profile_locked(
                conn, chat_id, user_id, now
            )
            stats = core.BOSS_COMBAT_ROLES[role_key]
            miss = random.random() < 0.03
            critical = (not miss) and random.random() < float(stats["crit_chance"])

            # Reality 59: обычный удар 200–500, критический 800–1200.
            if miss:
                damage = 0
            elif critical:
                damage = random.randint(800, 1200)
            else:
                damage = random.randint(200, 500)

            shield_hits = int(battle["shield_hits"])
            shielded = damage > 0 and shield_hits > 0
            if shielded:
                damage = max(1, int(round(damage * 0.45)))
                shield_hits -= 1

            self_damage = 0
            if role_key == "sabotage_hero" and damage > 0 and random.random() < 0.12:
                self_damage = random.randint(12, 24)

            hp_after = max(0, int(battle["hp"]) - damage)
            phase_after = core.boss_phase_for_hp(hp_after, int(battle["max_hp"]))
            player_hp_after = max(0, int(fighter["player_hp"]) - self_damage)
            knocked_until = int(fighter["knocked_out_until"])
            if player_hp_after <= 0:
                knocked_until = now + core.BOSS_KNOCKOUT_SECONDS

            safe_name_value = html.escape(full_name)
            if miss:
                log_text = f"💨 {safe_name_value} промахнулся по чужому самолюбию."
            elif critical:
                log_text = (
                    f"💥 {safe_name_value} нанёс критический удар: −{damage} HP."
                )
            elif shielded:
                log_text = (
                    f"🪞 Щит ЧСВ смягчил удар {safe_name_value}: −{damage} HP."
                )
            else:
                log_text = f"💢 {safe_name_value} задел его эго: −{damage} HP."
            if self_damage:
                log_text += (
                    f" Саботаж обернулся против него: −{self_damage} собственного HP."
                )

            await conn.execute(
                """
                UPDATE boss_battles
                SET hp = ?, phase = ?, shield_hits = ?, last_attacker_id = ?
                WHERE boss_id = ?
                """,
                (hp_after, phase_after, shield_hits, user_id, boss_id),
            )
            await conn.execute(
                """
                UPDATE boss_fighters
                SET damage_done = damage_done + ?, attacks = attacks + 1,
                    critical_hits = critical_hits + ?, last_attack_at = ?,
                    player_hp = ?, damage_taken = damage_taken + ?,
                    knocked_out_until = ?, role_key = ?
                WHERE boss_id = ? AND user_id = ?
                """,
                (
                    damage,
                    1 if critical else 0,
                    now,
                    player_hp_after,
                    self_damage,
                    knocked_until,
                    role_key,
                    boss_id,
                    user_id,
                ),
            )
            await conn.execute(
                "INSERT INTO boss_logs (boss_id, log_text, created_at) VALUES (?, ?, ?)",
                (boss_id, log_text, now),
            )
            await conn.commit()
            return {
                "ok": True,
                "action": "hit",
                "damage": damage,
                "critical": critical,
                "miss": miss,
                "self_damage": self_damage,
                "hp": hp_after,
                "max_hp": int(battle["max_hp"]),
                "phase": phase_after,
                "phase_changed": phase_after != int(battle["phase"]),
                "defeated": hp_after <= 0,
            }

    core.Database.boss_apply_hit = boss_apply_hit
    core.Database.r49_boss_apply_hit = boss_apply_hit
