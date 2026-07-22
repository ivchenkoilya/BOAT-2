from __future__ import annotations

import time
from typing import Any

import hero_loadouts_v103 as loadouts


VERSION = "Reality 163 · Щиты и возвращение Былогерия"
MAX_BOSS_SHIELDS = 3
SHIELD_REFILL_COOLDOWN_SECONDS = 15
HERO_ABILITY_COOLDOWN_SECONDS = 5 * 60
ATTACK_COOLDOWN_SECONDS = 3


def install_boss_rules_v163(core: Any) -> None:
    """Финальные правила рейда поверх всех старых боевых слоёв."""
    if getattr(core, "_boss_rules_v163_installed", False):
        return
    core._boss_rules_v163_installed = True

    core.BOSS_ATTACK_COOLDOWN_SECONDS = ATTACK_COOLDOWN_SECONDS
    core.ROLE_ABILITY_COOLDOWN_SECONDS = HERO_ABILITY_COOLDOWN_SECONDS
    for role_key in list(getattr(core, "BOSS_ABILITY_COOLDOWNS", {})):
        core.BOSS_ABILITY_COOLDOWNS[role_key] = HERO_ABILITY_COOLDOWN_SECONDS

    # Все герои имеют не более пяти минут перезарядки. Былогерий больше не
    # является одноразовым: сервер проверяет обычный пятиминутный кулдаун.
    for hero in loadouts.HEROES.values():
        hero["cooldown"] = HERO_ABILITY_COOLDOWN_SECONDS
    if 7 in loadouts.HEROES:
        loadouts.HEROES[7]["once"] = False
        loadouts.HEROES[7]["cooldown"] = HERO_ABILITY_COOLDOWN_SECONDS
        loadouts.HEROES[7]["hint"] = (
            "Каждые 5 минут возрождается или входит в режим величия"
        )

    original_connect = core.Database.connect

    async def connect_v163(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS boss_shield_runtime_v163 (
                    boss_id TEXT PRIMARY KEY,
                    refill_ready_at INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            await conn.execute(
                "UPDATE boss_battles SET shield_hits = MIN(MAX(shield_hits, 0), ?)",
                (MAX_BOSS_SHIELDS,),
            )
            # Старый одноразовый флаг больше нигде не должен блокировать способность.
            await conn.execute(
                "DELETE FROM hero_runtime_v103 WHERE effect_key = 'bylo_used'"
            )
            await conn.commit()

    core.Database.connect = connect_v163

    async def shield_runtime_locked(conn: Any, boss_id: str) -> Any:
        await conn.execute(
            """
            INSERT INTO boss_shield_runtime_v163 (boss_id, refill_ready_at, updated_at)
            VALUES (?, 0, ?)
            ON CONFLICT(boss_id) DO NOTHING
            """,
            (str(boss_id), int(time.time())),
        )
        cursor = await conn.execute(
            "SELECT * FROM boss_shield_runtime_v163 WHERE boss_id = ?",
            (str(boss_id),),
        )
        return await cursor.fetchone()

    async def current_shields_locked(conn: Any, boss_id: str) -> int:
        cursor = await conn.execute(
            "SELECT shield_hits FROM boss_battles WHERE boss_id = ?",
            (str(boss_id),),
        )
        row = await cursor.fetchone()
        raw = int(row["shield_hits"] or 0) if row else 0
        shields = max(0, min(MAX_BOSS_SHIELDS, raw))
        if row is not None and raw != shields:
            await conn.execute(
                "UPDATE boss_battles SET shield_hits = ? WHERE boss_id = ?",
                (shields, str(boss_id)),
            )
        return shields

    original_hit = core.Database.boss_apply_hit

    async def hit_v163(
        self: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        conn = self._require_connection()
        async with self.lock:
            before = await current_shields_locked(conn, boss_id)
            await shield_runtime_locked(conn, boss_id)
            await conn.commit()

        result = await original_hit(
            self, boss_id, chat_id, user_id, *args, **kwargs
        )

        now = int(time.time())
        async with self.lock:
            after = await current_shields_locked(conn, boss_id)
            if result.get("ok") and before > 0 and after <= 0:
                ready_at = now + SHIELD_REFILL_COOLDOWN_SECONDS
                await conn.execute(
                    """
                    INSERT INTO boss_shield_runtime_v163 (
                        boss_id, refill_ready_at, updated_at
                    ) VALUES (?, ?, ?)
                    ON CONFLICT(boss_id) DO UPDATE SET
                        refill_ready_at = excluded.refill_ready_at,
                        updated_at = excluded.updated_at
                    """,
                    (str(boss_id), ready_at, now),
                )
                log_text = (
                    "🛡 Щит ЧСВ полностью разбит. Новые 3 заряда будут доступны "
                    "через 15 секунд."
                )
                await conn.execute(
                    "INSERT INTO boss_logs (boss_id, log_text, created_at) VALUES (?, ?, ?)",
                    (str(boss_id), log_text, now),
                )
                result = dict(result)
                result["shield_broken"] = True
                result["shield_refill_ready_at"] = ready_at
                result["shield_hits"] = 0
            await conn.commit()
        return result

    core.Database.boss_apply_hit = hit_v163
    core.Database.r49_boss_apply_hit = hit_v163

    original_boss_action = core.Database.boss_perform_action

    async def boss_action_v163(self: Any, boss_id: str) -> dict[str, Any]:
        conn = self._require_connection()
        now = int(time.time())
        before = 0
        ready_at = 0

        async with self.lock:
            before = await current_shields_locked(conn, boss_id)
            runtime = await shield_runtime_locked(conn, boss_id)
            ready_at = int(runtime["refill_ready_at"] or 0)

            # Не позволяем заранее запланированному щиту обойти 15-секундную
            # перезарядку или бессмысленно накапливаться поверх 3/3.
            if before >= MAX_BOSS_SHIELDS or (before <= 0 and ready_at > now):
                try:
                    cursor = await conn.execute(
                        "SELECT COUNT(*) AS amount FROM boss_fighters "
                        "WHERE boss_id = ? AND player_hp > 0",
                        (str(boss_id),),
                    )
                    alive = await cursor.fetchone()
                    if alive and int(alive["amount"] or 0) > 0:
                        await conn.execute(
                            """
                            UPDATE boss_runtime_v60
                            SET planned_action = 'single'
                            WHERE boss_id = ? AND planned_action = 'shield'
                            """,
                            (str(boss_id),),
                        )
                except Exception:
                    # Старые бои без runtime Reality 60 всё равно будут исправлены
                    # после выполнения действия.
                    pass
            await conn.commit()

        result = await original_boss_action(self, boss_id)
        if not result.get("ok"):
            return result

        action = str(result.get("action") or "")
        corrected_log = ""
        async with self.lock:
            runtime = await shield_runtime_locked(conn, boss_id)
            ready_at = int(runtime["refill_ready_at"] or 0)

            if action == "shield":
                if before <= 0 and ready_at > now:
                    remaining = max(1, ready_at - now)
                    await conn.execute(
                        "UPDATE boss_battles SET shield_hits = 0 WHERE boss_id = ?",
                        (str(boss_id),),
                    )
                    corrected_log = (
                        "🪞 Щит ЧСВ ещё восстанавливается: осталось "
                        f"{remaining} сек. Новые заряды не получены."
                    )
                    shields = 0
                else:
                    shields = MAX_BOSS_SHIELDS
                    await conn.execute(
                        "UPDATE boss_battles SET shield_hits = ? WHERE boss_id = ?",
                        (MAX_BOSS_SHIELDS, str(boss_id)),
                    )
                    await conn.execute(
                        """
                        UPDATE boss_shield_runtime_v163
                        SET refill_ready_at = 0, updated_at = ?
                        WHERE boss_id = ?
                        """,
                        (now, str(boss_id)),
                    )
                    corrected_log = (
                        "🪞 «Все мне завидуют»: Щит ЧСВ восстановлен до 3/3. "
                        "Больше трёх зарядов накопить нельзя."
                    )

                await conn.execute(
                    """
                    UPDATE boss_logs
                    SET log_text = ?
                    WHERE rowid = (
                        SELECT rowid FROM boss_logs
                        WHERE boss_id = ?
                        ORDER BY created_at DESC, rowid DESC
                        LIMIT 1
                    )
                    """,
                    (corrected_log, str(boss_id)),
                )
                result = dict(result)
                result["log"] = corrected_log
                result["shield_hits"] = shields
            else:
                await current_shields_locked(conn, boss_id)
            await conn.commit()

        return result

    core.Database.boss_perform_action = boss_action_v163

    original_ability = core.Database.boss_apply_ability

    async def ability_v163(
        self: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        conn = self._require_connection()
        try:
            cursor = await conn.execute(
                "SELECT skin_id FROM hero_skin_choices_v101 WHERE user_id = ?",
                (int(user_id),),
            )
            row = await cursor.fetchone()
            hero_id = int(row["skin_id"] or 0) if row else 0
        except Exception:
            hero_id = 0

        if hero_id != 7:
            return await original_ability(
                self, boss_id, chat_id, user_id, *args, **kwargs
            )

        now = int(time.time())
        cursor = await conn.execute(
            """
            SELECT ability_used_at FROM boss_fighters
            WHERE boss_id = ? AND user_id = ?
            """,
            (str(boss_id), int(user_id)),
        )
        fighter = await cursor.fetchone()
        if fighter is not None:
            elapsed = now - int(fighter["ability_used_at"] or 0)
            remaining = HERO_ABILITY_COOLDOWN_SECONDS - elapsed
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

        result = await original_ability(
            self, boss_id, chat_id, user_id, *args, **kwargs
        )
        if result.get("ok"):
            async with self.lock:
                await conn.execute(
                    """
                    UPDATE boss_fighters SET ability_used_at = ?
                    WHERE boss_id = ? AND user_id = ?
                    """,
                    (now, str(boss_id), int(user_id)),
                )
                await conn.execute(
                    """
                    DELETE FROM hero_runtime_v103
                    WHERE boss_id = ? AND user_id = ? AND effect_key = 'bylo_used'
                    """,
                    (str(boss_id), int(user_id)),
                )
                await conn.commit()
            result = dict(result)
            result["cooldown"] = HERO_ABILITY_COOLDOWN_SECONDS
            result["repeatable"] = True
        return result

    core.Database.boss_apply_ability = ability_v163

    original_state = core.build_boss_web_state

    async def state_v163(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = await original_state(*args, **kwargs)
        if not result.get("ok"):
            return result

        boss_id = str(
            (args[0] if args else kwargs.get("boss_id"))
            or result.get("battle", {}).get("boss_id")
            or ""
        )
        user_id = int(
            (args[1] if len(args) > 1 else kwargs.get("user_id"))
            or result.get("self", {}).get("user_id")
            or 0
        )
        now = int(result.get("now") or time.time())
        conn = core.db._require_connection()

        async with core.db.lock:
            shields = await current_shields_locked(conn, boss_id)
            runtime = await shield_runtime_locked(conn, boss_id)
            ready_at = int(runtime["refill_ready_at"] or 0)
            await conn.commit()

        battle = result.get("battle")
        if isinstance(battle, dict):
            battle["shield_hits"] = shields
            battle["shield_max"] = MAX_BOSS_SHIELDS
            battle["shield_refill_ready_at"] = ready_at
            battle["shield_refill_left"] = (
                max(0, ready_at - now) if shields <= 0 else 0
            )

        for hero in result.get("hero_catalog") or []:
            if isinstance(hero, dict):
                hero["cooldown"] = HERO_ABILITY_COOLDOWN_SECONDS
                if int(hero.get("id") or 0) == 7:
                    hero["once"] = False
                    hero["hint"] = loadouts.HEROES[7]["hint"]

        me = result.get("self")
        selected_id = int(
            (me or {}).get("hero_id")
            or (me or {}).get("skin_id")
            or 0
        )
        if isinstance(me, dict) and selected_id == 7 and user_id > 0:
            cursor = await conn.execute(
                """
                SELECT ability_used_at FROM boss_fighters
                WHERE boss_id = ? AND user_id = ?
                """,
                (boss_id, user_id),
            )
            fighter = await cursor.fetchone()
            used_at = int(fighter["ability_used_at"] or 0) if fighter else 0
            remaining = max(
                0, HERO_ABILITY_COOLDOWN_SECONDS - (now - used_at)
            )
            me.setdefault("cooldowns", {})["ability"] = remaining
            me["ability_once_used"] = False
            me["ability_name"] = "Возвращение в сюжет"
            me["ability_hint"] = loadouts.HEROES[7]["hint"]
            me["ability_repeatable"] = True

        result["boss_rules_version"] = VERSION
        return result

    core.build_boss_web_state = state_v163
