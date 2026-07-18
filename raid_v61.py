from __future__ import annotations

import html
import logging
import time
from datetime import datetime, timezone
from typing import Any


LOGGER = logging.getLogger(__name__)
BOSS_HP = 75_000
TOP_INFLUENCE = (600, 400, 250)
PARTICIPATION_INFLUENCE = 75
FINISHER_INFLUENCE = 100
TOP_SHARDS = (4, 3, 2)
PARTICIPATION_SHARDS = 1
FINISHER_SHARDS = 1
SHARDS_PER_TREE_POINT = 5
WEEKLY_TREE_POINT_CAP = 3
REWARD_REASON = "boss_center_of_universe_v61_victory"


def install_raid_v61(core: Any) -> None:
    """Reality 61: 75k HP, редкая шкала давления и награды знаниями."""
    if getattr(core, "_raid_v61_installed", False):
        return
    core._raid_v61_installed = True

    core.BOSS_MAX_HP = BOSS_HP
    core.BOSS_TOP_REWARDS = TOP_INFLUENCE

    # Reality 60 использует эти значения как глобальные параметры модуля.
    # Меняем их после установки механики: теперь шкала требует примерно
    # 50–60 обычных попаданий и постепенно ослабевает без атак.
    try:
        import raid_v60

        raid_v60.PRESSURE_MAX = 120
        raid_v60.PRESSURE_HIT_GAIN = 2
        raid_v60.PRESSURE_CRIT_BONUS = 1
        raid_v60.PRESSURE_ABILITY_GAIN = 5
        raid_v60.PRESSURE_DECAY_SECONDS = 10
    except Exception:
        LOGGER.exception("Не удалось применить сложный баланс давления Reality 61")

    original_connect = core.Database.connect

    async def connect_with_v61(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_wallets (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    shards INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, user_id)
                );

                CREATE TABLE IF NOT EXISTS knowledge_weekly (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    week_key TEXT NOT NULL,
                    tree_points INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, user_id, week_key)
                );

                CREATE TABLE IF NOT EXISTS boss_v61_rewards (
                    boss_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    place INTEGER NOT NULL,
                    base_influence INTEGER NOT NULL,
                    finisher_influence INTEGER NOT NULL DEFAULT 0,
                    influence_awarded INTEGER NOT NULL DEFAULT 0,
                    shards_awarded INTEGER NOT NULL DEFAULT 0,
                    tree_points_awarded INTEGER NOT NULL DEFAULT 0,
                    is_finisher INTEGER NOT NULL DEFAULT 0,
                    applied_at INTEGER NOT NULL,
                    PRIMARY KEY (boss_id, user_id)
                );

                CREATE INDEX IF NOT EXISTS idx_boss_v61_rewards_boss
                ON boss_v61_rewards (boss_id, place);
                """
            )

            # Сохраняем уже нанесённый урон активным боссам, но увеличиваем
            # их максимальное и текущее здоровье до нового значения.
            await conn.execute(
                """
                UPDATE boss_battles
                SET hp = MIN(?, MAX(0, hp + (? - max_hp))),
                    max_hp = ?
                WHERE status IN ('active', 'resolving')
                  AND max_hp <> ?
                """,
                (BOSS_HP, BOSS_HP, BOSS_HP, BOSS_HP),
            )
            await conn.commit()

    core.Database.connect = connect_with_v61

    def week_key() -> str:
        iso = datetime.now(timezone.utc).date().isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    async def effective_influence(
        database: Any,
        chat_id: int,
        user_id: int,
        amount: int,
    ) -> int:
        try:
            import talent_system

            await talent_system.sync_profile(database, chat_id, user_id)
            adjusted = await talent_system.adjusted_delta(
                database,
                chat_id,
                user_id,
                amount,
                REWARD_REASON,
            )
            return max(0, int(adjusted))
        except Exception:
            LOGGER.exception("Не удалось применить таланты к награде Reality 61")
            return max(0, int(amount))

    async def award_once(
        database: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
        place: int,
        base_influence: int,
        finisher_influence: int,
        shards: int,
        is_finisher: bool,
    ) -> dict[str, int]:
        conn = database._require_connection()
        cursor = await conn.execute(
            """
            SELECT influence_awarded, shards_awarded, tree_points_awarded,
                   is_finisher
            FROM boss_v61_rewards
            WHERE boss_id = ? AND user_id = ?
            """,
            (boss_id, user_id),
        )
        existing = await cursor.fetchone()
        if existing is not None:
            return {
                "influence": int(existing["influence_awarded"]),
                "shards": int(existing["shards_awarded"]),
                "tree_points": int(existing["tree_points_awarded"]),
                "is_finisher": int(existing["is_finisher"]),
            }

        total_base = max(0, base_influence + finisher_influence)
        influence = await effective_influence(
            database,
            chat_id,
            user_id,
            total_base,
        )
        now = int(time.time())
        current_week = week_key()

        async with database.lock:
            try:
                cursor = await conn.execute(
                    """
                    SELECT influence_awarded, shards_awarded,
                           tree_points_awarded, is_finisher
                    FROM boss_v61_rewards
                    WHERE boss_id = ? AND user_id = ?
                    """,
                    (boss_id, user_id),
                )
                existing = await cursor.fetchone()
                if existing is not None:
                    return {
                        "influence": int(existing["influence_awarded"]),
                        "shards": int(existing["shards_awarded"]),
                        "tree_points": int(existing["tree_points_awarded"]),
                        "is_finisher": int(existing["is_finisher"]),
                    }

                cursor = await conn.execute(
                    """
                    UPDATE players
                    SET points = points + ?, updated_at = ?
                    WHERE chat_id = ? AND user_id = ?
                    """,
                    (influence, now, chat_id, user_id),
                )
                if cursor.rowcount <= 0:
                    raise RuntimeError(f"Участник {user_id} не найден")

                await conn.execute(
                    """
                    INSERT INTO score_log (chat_id, user_id, delta, reason, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (chat_id, user_id, influence, REWARD_REASON, now),
                )

                cursor = await conn.execute(
                    """
                    SELECT shards FROM knowledge_wallets
                    WHERE chat_id = ? AND user_id = ?
                    """,
                    (chat_id, user_id),
                )
                wallet = await cursor.fetchone()
                stored_shards = int(wallet["shards"]) if wallet else 0
                total_shards = stored_shards + max(0, int(shards))

                cursor = await conn.execute(
                    """
                    SELECT tree_points FROM knowledge_weekly
                    WHERE chat_id = ? AND user_id = ? AND week_key = ?
                    """,
                    (chat_id, user_id, current_week),
                )
                weekly = await cursor.fetchone()
                weekly_points = int(weekly["tree_points"]) if weekly else 0
                available_conversions = max(0, WEEKLY_TREE_POINT_CAP - weekly_points)
                converted = min(
                    total_shards // SHARDS_PER_TREE_POINT,
                    available_conversions,
                )
                remaining_shards = total_shards - converted * SHARDS_PER_TREE_POINT

                await conn.execute(
                    """
                    INSERT INTO knowledge_wallets (chat_id, user_id, shards, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(chat_id, user_id) DO UPDATE SET
                        shards = excluded.shards,
                        updated_at = excluded.updated_at
                    """,
                    (chat_id, user_id, remaining_shards, now),
                )
                await conn.execute(
                    """
                    INSERT INTO knowledge_weekly (
                        chat_id, user_id, week_key, tree_points, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(chat_id, user_id, week_key) DO UPDATE SET
                        tree_points = knowledge_weekly.tree_points + excluded.tree_points,
                        updated_at = excluded.updated_at
                    """,
                    (chat_id, user_id, current_week, converted, now),
                )

                if converted > 0:
                    await conn.execute(
                        """
                        UPDATE talent_profiles
                        SET total_points = total_points + ?, updated_at = ?
                        WHERE chat_id = ? AND user_id = ?
                        """,
                        (converted, now, chat_id, user_id),
                    )

                await conn.execute(
                    """
                    INSERT INTO boss_v61_rewards (
                        boss_id, user_id, place, base_influence,
                        finisher_influence, influence_awarded,
                        shards_awarded, tree_points_awarded,
                        is_finisher, applied_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        boss_id,
                        user_id,
                        place,
                        base_influence,
                        finisher_influence,
                        influence,
                        shards,
                        converted,
                        1 if is_finisher else 0,
                        now,
                    ),
                )
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

        return {
            "influence": influence,
            "shards": shards,
            "tree_points": converted,
            "is_finisher": 1 if is_finisher else 0,
        }

    async def reward_map(database: Any, boss_id: str) -> dict[int, dict[str, int]]:
        conn = database._require_connection()
        cursor = await conn.execute(
            """
            SELECT user_id, place, influence_awarded, shards_awarded,
                   tree_points_awarded, is_finisher
            FROM boss_v61_rewards
            WHERE boss_id = ?
            ORDER BY place ASC
            """,
            (boss_id,),
        )
        rows = await cursor.fetchall()
        return {
            int(row["user_id"]): {
                "place": int(row["place"]),
                "reward": int(row["influence_awarded"]),
                "shards": int(row["shards_awarded"]),
                "tree_points": int(row["tree_points_awarded"]),
                "is_finisher": int(row["is_finisher"]),
            }
            for row in rows
        }

    async def edit_final_post(bot: Any, battle: Any, final_text: str) -> None:
        try:
            await core.edit_boss_post(
                bot,
                battle,
                change_media=True,
                final_caption=final_text,
                final_phase=5,
            )
        except Exception:
            LOGGER.exception("Не удалось обновить итоговую карточку Reality 61")

    async def resolve_boss_victory(boss_id: str, bot: Any) -> None:
        battle = await core.db.get_boss(boss_id)
        if battle is None or int(battle["hp"]) > 0:
            return

        status = str(battle["status"])
        if status == "active":
            claimed = await core.db.claim_boss_resolution(boss_id)
            if claimed:
                status = "resolving"
            else:
                battle = await core.db.get_boss(boss_id)
                if battle is None:
                    return
                status = str(battle["status"])
        if status not in {"resolving", "victory"}:
            return

        chat_id = int(battle["chat_id"])
        finisher_id = int(battle["last_attacker_id"] or 0)
        participants = await core.db.boss_fighter_rows(boss_id)
        eligible = [row for row in participants if int(row["attacks"]) > 0]
        reward_lines: list[str] = []

        for index, row in enumerate(eligible):
            place = index + 1
            top_three = index < 3
            base_influence = (
                TOP_INFLUENCE[index] if top_three else PARTICIPATION_INFLUENCE
            )
            base_shards = TOP_SHARDS[index] if top_three else PARTICIPATION_SHARDS
            user_id = int(row["user_id"])
            is_finisher = user_id == finisher_id
            finisher_influence = FINISHER_INFLUENCE if is_finisher else 0
            shards = base_shards + (FINISHER_SHARDS if is_finisher else 0)

            try:
                awarded = await award_once(
                    core.db,
                    boss_id,
                    chat_id,
                    user_id,
                    place,
                    base_influence,
                    finisher_influence,
                    shards,
                    is_finisher,
                )
            except Exception:
                LOGGER.exception(
                    "Не удалось выдать награду Reality 61: boss=%s user=%s",
                    boss_id,
                    user_id,
                )
                awarded = {
                    "influence": 0,
                    "shards": 0,
                    "tree_points": 0,
                    "is_finisher": 0,
                }

            player = await core.db.get_player(chat_id, user_id)
            name = (
                core.player_link(player)
                if player is not None
                else html.escape(str(row["full_name"] or user_id))
            )
            marker = ["🥇", "🥈", "🥉"][index] if top_three else "⚔️"
            line = (
                f"{marker} {name} — <b>{int(row['damage_done'])}</b> урона, "
                f"<b>+{awarded['influence']}</b> влияния, "
                f"<b>+{awarded['shards']}</b> осколков"
            )
            if awarded["tree_points"] > 0:
                line += f", <b>+{awarded['tree_points']}</b> очк. древа"
            if awarded["is_finisher"]:
                line += " · 💀 последний удар"
            reward_lines.append(line)

        if not reward_lines:
            reward_lines.append("Никто не успел нанести ни одного удара.")

        final_text = core.normalize_output_text(
            "🏆 <b>ЦЕНТР ВСЕЛЕННОЙ СВЕРГНУТ</b> 🏆\n\n"
            "Эго босса разрушено. Влияние и осколки знаний начислены.\n\n"
            + "\n".join(reward_lines)
        )[:1024]

        await core.db.finish_boss(boss_id, "victory", final_text)
        refreshed = await core.db.get_boss(boss_id)
        if refreshed is not None:
            core.spawn_background_task(edit_final_post(bot, refreshed, final_text))

    original_build_state = core.build_boss_web_state

    async def build_state_v61(boss_id: str, user_id: int) -> dict[str, Any]:
        result = await original_build_state(boss_id, user_id)
        if not result.get("ok"):
            return result

        result["reward_rules"] = {
            "top_influence": list(TOP_INFLUENCE),
            "participation_influence": PARTICIPATION_INFLUENCE,
            "finisher_influence": FINISHER_INFLUENCE,
            "top_shards": list(TOP_SHARDS),
            "participation_shards": PARTICIPATION_SHARDS,
            "finisher_shards": FINISHER_SHARDS,
            "shards_per_tree_point": SHARDS_PER_TREE_POINT,
            "weekly_tree_point_cap": WEEKLY_TREE_POINT_CAP,
        }

        battle = result.get("battle") or {}
        if int(battle.get("hp", 1)) > 0 and str(battle.get("status")) != "victory":
            return result

        rewards = await reward_map(core.db, boss_id)
        victory = result.setdefault("victory", {})
        victory.update(
            {
                "visible": True,
                "resolved": str(battle.get("status")) == "victory",
                "title": "ЦЕНТР ВСЕЛЕННОЙ СВЕРГНУТ",
            }
        )
        rankings = victory.get("rankings") or []
        for ranking in rankings:
            info = rewards.get(int(ranking.get("user_id", 0)), {})
            ranking["reward"] = int(info.get("reward", 0))
            ranking["shards"] = int(info.get("shards", 0))
            ranking["tree_points"] = int(info.get("tree_points", 0))
            ranking["is_finisher"] = bool(info.get("is_finisher", 0))

        self_info = rewards.get(user_id, {})
        victory["self_reward"] = int(self_info.get("reward", 0))
        victory["self_shards"] = int(self_info.get("shards", 0))
        victory["self_tree_points"] = int(self_info.get("tree_points", 0))
        victory["is_finisher"] = bool(self_info.get("is_finisher", 0))
        return result

    core.resolve_boss_victory = resolve_boss_victory
    core.build_boss_web_state = build_state_v61
