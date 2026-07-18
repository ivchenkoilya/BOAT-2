from __future__ import annotations

import html
import logging
import time
from typing import Any


LOGGER = logging.getLogger(__name__)
REWARD_REASON = "boss_center_of_universe_victory"


def install_raid_v59_fix(core: Any) -> None:
    """Надёжно завершает рейд, выдаёт награды и отдаёт итог Mini App."""
    if getattr(core, "_raid_v59_fix_installed", False):
        return
    core._raid_v59_fix_installed = True

    original_connect = core.Database.connect

    async def connect_with_victory_rewards(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS boss_victory_rewards (
                    boss_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    place INTEGER NOT NULL,
                    base_reward INTEGER NOT NULL,
                    applied_reward INTEGER NOT NULL DEFAULT 0,
                    applied_at INTEGER,
                    PRIMARY KEY (boss_id, user_id),
                    UNIQUE (boss_id, place)
                );

                CREATE INDEX IF NOT EXISTS idx_boss_victory_rewards_boss
                ON boss_victory_rewards (boss_id, place);
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_victory_rewards

    async def _effective_reward(
        database: Any,
        chat_id: int,
        user_id: int,
        base_reward: int,
    ) -> int:
        try:
            import talent_system

            adjusted = await talent_system.adjusted_delta(
                database,
                chat_id,
                user_id,
                base_reward,
                REWARD_REASON,
            )
            return max(0, int(adjusted))
        except Exception:
            LOGGER.exception("Не удалось применить таланты к награде за рейд")
            return max(0, int(base_reward))

    async def _award_once(
        database: Any,
        boss_id: str,
        chat_id: int,
        user_id: int,
        place: int,
        base_reward: int,
    ) -> int:
        conn = database._require_connection()

        cursor = await conn.execute(
            """
            SELECT applied_reward, applied_at
            FROM boss_victory_rewards
            WHERE boss_id = ? AND user_id = ?
            """,
            (boss_id, user_id),
        )
        existing = await cursor.fetchone()
        if existing is not None and existing["applied_at"] is not None:
            return int(existing["applied_reward"])

        reward = await _effective_reward(database, chat_id, user_id, base_reward)
        now = int(time.time())

        async with database.lock:
            try:
                cursor = await conn.execute(
                    """
                    SELECT applied_reward, applied_at
                    FROM boss_victory_rewards
                    WHERE boss_id = ? AND user_id = ?
                    """,
                    (boss_id, user_id),
                )
                existing = await cursor.fetchone()
                if existing is not None and existing["applied_at"] is not None:
                    return int(existing["applied_reward"])

                cursor = await conn.execute(
                    """
                    UPDATE players
                    SET points = points + ?, updated_at = ?
                    WHERE chat_id = ? AND user_id = ?
                    """,
                    (reward, now, chat_id, user_id),
                )
                if cursor.rowcount <= 0:
                    raise RuntimeError(
                        f"Не найден участник {user_id} для награды за босса {boss_id}"
                    )

                await conn.execute(
                    """
                    INSERT INTO score_log (chat_id, user_id, delta, reason, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (chat_id, user_id, reward, REWARD_REASON, now),
                )
                await conn.execute(
                    """
                    INSERT INTO boss_victory_rewards (
                        boss_id, user_id, place, base_reward,
                        applied_reward, applied_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(boss_id, user_id) DO UPDATE SET
                        place = excluded.place,
                        base_reward = excluded.base_reward,
                        applied_reward = excluded.applied_reward,
                        applied_at = excluded.applied_at
                    """,
                    (boss_id, user_id, place, base_reward, reward, now),
                )
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise
        return reward

    async def _reward_map(database: Any, boss_id: str) -> dict[int, dict[str, int]]:
        conn = database._require_connection()
        cursor = await conn.execute(
            """
            SELECT user_id, place, base_reward, applied_reward, applied_at
            FROM boss_victory_rewards
            WHERE boss_id = ?
            ORDER BY place ASC
            """,
            (boss_id,),
        )
        rows = await cursor.fetchall()
        return {
            int(row["user_id"]): {
                "place": int(row["place"]),
                "base_reward": int(row["base_reward"]),
                "reward": int(row["applied_reward"]),
                "applied_at": int(row["applied_at"] or 0),
            }
            for row in rows
        }

    async def _edit_final_post(bot: Any, battle: Any, final_text: str) -> None:
        try:
            await core.edit_boss_post(
                bot,
                battle,
                change_media=True,
                final_caption=final_text,
                final_phase=5,
            )
        except Exception:
            LOGGER.exception("Не удалось обновить финальную карточку босса")

    async def resolve_boss_victory(boss_id: str, bot: Any) -> None:
        battle = await core.db.get_boss(boss_id)
        if battle is None or int(battle["hp"]) > 0:
            return

        status = str(battle["status"])
        if status == "active":
            claimed = await core.db.claim_boss_resolution(boss_id)
            if not claimed:
                battle = await core.db.get_boss(boss_id)
                if battle is None:
                    return
                status = str(battle["status"])
            else:
                status = "resolving"
        if status not in {"resolving", "victory"}:
            return

        chat_id = int(battle["chat_id"])
        participants = await core.db.boss_fighter_rows(boss_id)
        eligible = [row for row in participants if int(row["attacks"]) > 0]
        reward_lines: list[str] = []

        for index, row in enumerate(eligible[:3]):
            place = index + 1
            base_reward = int(core.BOSS_TOP_REWARDS[index])
            try:
                reward = await _award_once(
                    core.db,
                    boss_id,
                    chat_id,
                    int(row["user_id"]),
                    place,
                    base_reward,
                )
            except Exception:
                LOGGER.exception(
                    "Не удалось начислить награду за босса: boss=%s user=%s",
                    boss_id,
                    row["user_id"],
                )
                reward = 0

            player = await core.db.get_player(chat_id, int(row["user_id"]))
            name = (
                core.player_link(player)
                if player is not None
                else html.escape(str(row["full_name"] or row["user_id"]))
            )
            reward_lines.append(
                f"{['🥇','🥈','🥉'][index]} {name} — "
                f"<b>{int(row['damage_done'])}</b> урона, <b>+{reward}</b>"
            )

        if not reward_lines:
            reward_lines.append("Никто не успел нанести урон.")

        participant_lines: list[str] = []
        for index, row in enumerate(participants, start=1):
            player = await core.db.get_player(chat_id, int(row["user_id"]))
            name = (
                core.player_link(player)
                if player is not None
                else html.escape(str(row["full_name"] or row["user_id"]))
            )
            participant_lines.append(
                f"{index}. {name} — {int(row['damage_done'])} урона"
            )

        final_text = core.normalize_output_text(
            "🏆 <b>ЦЕНТР ВСЕЛЕННОЙ СВЕРГНУТ</b> 🏆\n\n"
            "Его эго рассыпалось вместе с троном. Награды уже начислены.\n\n"
            "<b>Топ-3 и награды:</b>\n"
            + "\n".join(reward_lines)
            + "\n\n<b>Все участники:</b>\n"
            + ("\n".join(participant_lines) if participant_lines else "Участников нет.")
        )[:1024]

        await core.db.finish_boss(boss_id, "victory", final_text)
        refreshed = await core.db.get_boss(boss_id)
        if refreshed is not None:
            core.spawn_background_task(_edit_final_post(bot, refreshed, final_text))

    original_build_state = core.build_boss_web_state

    async def build_boss_web_state(boss_id: str, user_id: int) -> dict[str, Any]:
        result = await original_build_state(boss_id, user_id)
        if not result.get("ok"):
            return result

        battle_row = await core.db.get_boss(boss_id)
        if battle_row is None:
            return result
        status = str(battle_row["status"])
        hp = int(battle_row["hp"])
        if hp > 0 and status not in {"resolving", "victory"}:
            return result

        rewards = await _reward_map(core.db, boss_id)
        fighters = sorted(
            list(result.get("fighters") or []),
            key=lambda item: (-int(item.get("damage", 0)), -int(item.get("attacks", 0))),
        )
        rankings: list[dict[str, Any]] = []
        for index, fighter in enumerate(fighters, start=1):
            reward_info = rewards.get(int(fighter.get("user_id", 0)), {})
            rankings.append(
                {
                    "place": index,
                    "user_id": int(fighter.get("user_id", 0)),
                    "name": str(fighter.get("name") or "Участник"),
                    "damage": int(fighter.get("damage", 0)),
                    "reward": int(reward_info.get("reward", 0)),
                    "is_self": bool(fighter.get("is_self")),
                }
            )

        self_reward = int(rewards.get(user_id, {}).get("reward", 0))
        result["victory"] = {
            "visible": True,
            "resolved": status == "victory",
            "title": "ЦЕНТР ВСЕЛЕННОЙ СВЕРГНУТ",
            "self_reward": self_reward,
            "rankings": rankings,
            "result_text": str(battle_row["result_text"] or ""),
        }
        return result

    core.resolve_boss_victory = resolve_boss_victory
    core.build_boss_web_state = build_boss_web_state
