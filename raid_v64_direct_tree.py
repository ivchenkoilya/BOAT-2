from __future__ import annotations

import html
import logging
import time
from datetime import datetime, timezone
from typing import Any


LOGGER = logging.getLogger(__name__)
TOP_INFLUENCE = (600, 400, 250)
TOP_TREE_POINTS = (4, 3, 2)
PARTICIPATION_INFLUENCE = 75
PARTICIPATION_TREE_POINTS = 1
FINISHER_INFLUENCE = 100
WEEKLY_TREE_POINT_CAP = 12
REWARD_REASON = "boss_center_of_universe_v64_victory"


def install_raid_v64_direct_tree(core: Any) -> None:
    """Убирает осколки и выдаёт очки древа напрямую за победу в рейде."""
    if getattr(core, "_raid_v64_direct_tree_installed", False):
        return
    core._raid_v64_direct_tree_installed = True

    original_connect = core.Database.connect

    async def connect_with_direct_tree_rewards(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS boss_v64_rewards (
                    boss_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    place INTEGER NOT NULL,
                    base_influence INTEGER NOT NULL,
                    finisher_influence INTEGER NOT NULL DEFAULT 0,
                    influence_awarded INTEGER NOT NULL DEFAULT 0,
                    tree_points_requested INTEGER NOT NULL DEFAULT 0,
                    tree_points_awarded INTEGER NOT NULL DEFAULT 0,
                    is_finisher INTEGER NOT NULL DEFAULT 0,
                    applied_at INTEGER NOT NULL,
                    PRIMARY KEY (boss_id, user_id)
                );

                CREATE INDEX IF NOT EXISTS idx_boss_v64_rewards_boss
                ON boss_v64_rewards (boss_id, place);
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_direct_tree_rewards

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

            adjusted = await talent_system.adjusted_delta(
                database,
                chat_id,
                user_id,
                amount,
                REWARD_REASON,
            )
            return max(0, int(adjusted))
        except Exception:
            LOGGER.exception("Не удалось применить талант к рейдовой награде")
            return max(0, int(amount))

    async def legacy_reward(
        conn: Any,
        boss_id: str,
        user_id: int,
    ) -> dict[str, int] | None:
        """Не допускает повторной награды за бой, закрытый старой системой."""
        try:
            cursor = await conn.execute(
                """
                SELECT influence_awarded, tree_points_awarded, is_finisher
                FROM boss_v61_rewards
                WHERE boss_id = ? AND user_id = ?
                """,
                (boss_id, user_id),
            )
            row = await cursor.fetchone()
        except Exception:
            return None
        if row is None:
            return None
        return {
            "influence": int(row["influence_awarded"]),
            "tree_points": int(row["tree_points_awarded"]),
            "tree_points_requested": int(row["tree_points_awarded"]),
            "is_finisher": int(row["is_finisher"]),
            "weekly_total": 0,
            "legacy": 1,
        }

    async def stored_reward(
        conn: Any,
        boss_id: str,
        user_id: int,
    ) -> dict[str, int] | None:
        cursor = await conn.execute(
            """
            SELECT influence_awarded, tree_points_requested,
                   tree_points_awarded, is_finisher
            FROM boss_v64_rewards
            WHERE boss_id = ? AND user_id = ?
            """,
            (boss_id, user_id),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "influence": int(row["influence_awarded"]),
            "tree_points": int(row["tree_points_awarded"]),
            "tree_points_requested": int(row["tree_points_requested"]),
            "is_finisher": int(row["is_finisher"]),
            "weekly_total": 0,
            "legacy": 0,
        }

    async def award_once(
        database: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
        place: int,
        base_influence: int,
        finisher_influence: int,
        requested_tree_points: int,
        is_finisher: bool,
    ) -> dict[str, int]:
        import talent_system

        # Создаём профиль до общей транзакции, чтобы затем безопасно прибавить
        # рейдовые очки поверх очков, положенных за влияние.
        await talent_system.sync_profile(database, chat_id, user_id)

        conn = database._require_connection()
        existing = await stored_reward(conn, boss_id, user_id)
        if existing is not None:
            return existing
        old_reward = await legacy_reward(conn, boss_id, user_id)
        if old_reward is not None:
            return old_reward

        total_base = max(0, int(base_influence) + int(finisher_influence))
        influence = await effective_influence(database, chat_id, user_id, total_base)
        now = int(time.time())
        current_week = week_key()

        async with database.lock:
            try:
                existing = await stored_reward(conn, boss_id, user_id)
                if existing is not None:
                    return existing
                old_reward = await legacy_reward(conn, boss_id, user_id)
                if old_reward is not None:
                    return old_reward

                cursor = await conn.execute(
                    """
                    SELECT points FROM players
                    WHERE chat_id = ? AND user_id = ?
                    """,
                    (chat_id, user_id),
                )
                player = await cursor.fetchone()
                if player is None:
                    raise RuntimeError(f"Участник {user_id} не найден")

                points_before = int(player["points"])
                points_after = points_before + influence
                old_entitlement = talent_system._entitled_points(points_before)
                new_entitlement = talent_system._entitled_points(points_after)
                entitlement_gain = max(0, new_entitlement - old_entitlement)

                await conn.execute(
                    """
                    UPDATE players
                    SET points = ?, updated_at = ?
                    WHERE chat_id = ? AND user_id = ?
                    """,
                    (points_after, now, chat_id, user_id),
                )
                await conn.execute(
                    """
                    INSERT INTO score_log (chat_id, user_id, delta, reason, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (chat_id, user_id, influence, REWARD_REASON, now),
                )

                cursor = await conn.execute(
                    """
                    SELECT tree_points FROM knowledge_weekly
                    WHERE chat_id = ? AND user_id = ? AND week_key = ?
                    """,
                    (chat_id, user_id, current_week),
                )
                weekly = await cursor.fetchone()
                weekly_before = int(weekly["tree_points"]) if weekly else 0
                available = max(0, WEEKLY_TREE_POINT_CAP - weekly_before)
                awarded_tree_points = min(
                    max(0, int(requested_tree_points)),
                    available,
                )
                weekly_after = weekly_before + awarded_tree_points

                await conn.execute(
                    """
                    INSERT INTO knowledge_weekly (
                        chat_id, user_id, week_key, tree_points, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(chat_id, user_id, week_key) DO UPDATE SET
                        tree_points = excluded.tree_points,
                        updated_at = excluded.updated_at
                    """,
                    (chat_id, user_id, current_week, weekly_after, now),
                )

                await conn.execute(
                    """
                    UPDATE talent_profiles
                    SET total_points = total_points + ?, updated_at = ?
                    WHERE chat_id = ? AND user_id = ?
                    """,
                    (
                        awarded_tree_points + entitlement_gain,
                        now,
                        chat_id,
                        user_id,
                    ),
                )

                await conn.execute(
                    """
                    INSERT INTO boss_v64_rewards (
                        boss_id, user_id, place, base_influence,
                        finisher_influence, influence_awarded,
                        tree_points_requested, tree_points_awarded,
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
                        requested_tree_points,
                        awarded_tree_points,
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
            "tree_points": awarded_tree_points,
            "tree_points_requested": requested_tree_points,
            "is_finisher": 1 if is_finisher else 0,
            "weekly_total": weekly_after,
            "legacy": 0,
        }

    async def reward_map(database: Any, boss_id: str) -> dict[int, dict[str, int]]:
        conn = database._require_connection()
        cursor = await conn.execute(
            """
            SELECT user_id, place, influence_awarded,
                   tree_points_requested, tree_points_awarded, is_finisher
            FROM boss_v64_rewards
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
                "tree_points": int(row["tree_points_awarded"]),
                "tree_points_requested": int(row["tree_points_requested"]),
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
            LOGGER.exception("Не удалось обновить итоговую карточку Reality 64")

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
            requested_tree_points = (
                TOP_TREE_POINTS[index] if top_three else PARTICIPATION_TREE_POINTS
            )
            user_id = int(row["user_id"])
            is_finisher = user_id == finisher_id
            finisher_influence = FINISHER_INFLUENCE if is_finisher else 0

            try:
                awarded = await award_once(
                    core.db,
                    boss_id,
                    chat_id,
                    user_id,
                    place,
                    base_influence,
                    finisher_influence,
                    requested_tree_points,
                    is_finisher,
                )
            except Exception:
                LOGGER.exception(
                    "Не удалось выдать прямую награду: boss=%s user=%s",
                    boss_id,
                    user_id,
                )
                awarded = {
                    "influence": 0,
                    "tree_points": 0,
                    "tree_points_requested": requested_tree_points,
                    "is_finisher": 0,
                    "weekly_total": 0,
                    "legacy": 0,
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
                f"<b>+{awarded['tree_points']}</b> очк. древа"
            )
            if (
                awarded["tree_points"] < awarded["tree_points_requested"]
                and not awarded.get("legacy")
            ):
                line += " · недельный лимит"
            if awarded["is_finisher"]:
                line += " · 💀 последний удар"
            reward_lines.append(line)

        if not reward_lines:
            reward_lines.append("Никто не успел нанести ни одного удара.")

        final_text = core.normalize_output_text(
            "🏆 <b>ЦЕНТР ВСЕЛЕННОЙ СВЕРГНУТ</b> 🏆\n\n"
            "Активным участникам начислены влияние и очки древа.\n\n"
            + "\n".join(reward_lines)
        )[:1024]

        await core.db.finish_boss(boss_id, "victory", final_text)
        refreshed = await core.db.get_boss(boss_id)
        if refreshed is not None:
            core.spawn_background_task(edit_final_post(bot, refreshed, final_text))

    original_build_state = core.build_boss_web_state

    async def build_state_v64(boss_id: str, user_id: int) -> dict[str, Any]:
        result = await original_build_state(boss_id, user_id)
        if not result.get("ok"):
            return result

        result["reward_rules"] = {
            "top_influence": list(TOP_INFLUENCE),
            "top_tree_points": list(TOP_TREE_POINTS),
            "participation_influence": PARTICIPATION_INFLUENCE,
            "participation_tree_points": PARTICIPATION_TREE_POINTS,
            "finisher_influence": FINISHER_INFLUENCE,
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
            ranking["tree_points"] = int(info.get("tree_points", 0))
            ranking["tree_points_requested"] = int(
                info.get("tree_points_requested", 0)
            )
            ranking["is_finisher"] = bool(info.get("is_finisher", 0))
            ranking.pop("shards", None)

        self_info = rewards.get(user_id, {})
        victory["self_reward"] = int(self_info.get("reward", 0))
        victory["self_tree_points"] = int(self_info.get("tree_points", 0))
        victory["self_tree_points_requested"] = int(
            self_info.get("tree_points_requested", 0)
        )
        victory["is_finisher"] = bool(self_info.get("is_finisher", 0))
        victory.pop("self_shards", None)
        return result

    core.resolve_boss_victory = resolve_boss_victory
    core.build_boss_web_state = build_state_v64
