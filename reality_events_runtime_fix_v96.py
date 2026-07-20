from __future__ import annotations

from typing import Any

import reality_events_v96 as events


WAGER_WORDS = ("bot_game", "coin", "dice", "roulette", "bet", "wager", "stake")
MINI_APP_WORDS = (
    "game_influence_hunt",
    "rooftop",
    "heist",
    "night-hunter",
    "night_hunter",
)
MINIMUM_RUN_SECONDS = {
    "rooftop": 12,
    "heist": 18,
    "night-hunter": 25,
}


def install_reality_events_runtime_fix_v96(core: Any) -> None:
    if getattr(core, "_reality_events_runtime_fix_v96_installed", False):
        return
    core._reality_events_runtime_fix_v96_installed = True

    async def award_influence_once(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        amount: int,
        event_id: str,
        reward_key: str,
    ) -> int:
        base = max(0, int(amount))
        if base <= 0:
            return 0
        reason = f"reality_event_{event_id}_{reward_key}"
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT delta FROM score_log WHERE chat_id=? AND user_id=? AND reason=? LIMIT 1",
            (chat_id, user_id, reason),
        )
        row = await cursor.fetchone()
        if row is not None:
            return max(0, int(row["delta"]))
        player = await core_arg.db.get_player(chat_id, user_id)
        if player is None:
            return 0

        method = getattr(core_arg.db, "add_points_with_balance", None)
        if method is not None:
            before, after = await method(chat_id, user_id, base, reason)
            before_points = int(before.points) if hasattr(before, "points") else int(before)
            actual = max(0, int(after.points) - before_points)
        else:
            before_points = int(player.points)
            after = await core_arg.db.add_points(chat_id, user_id, base, reason)
            actual = max(0, int(after.points) - before_points)

        async with core_arg.db.lock:
            await conn.execute(
                """
                UPDATE reality_event_participants_v96
                SET reward_influence=reward_influence+?
                WHERE event_id=? AND user_id=?
                """,
                (actual, event_id, user_id),
            )
            await conn.commit()
        return actual

    async def apply_popularity(core_arg: Any, event: Any) -> None:
        chat_id = int(event["chat_id"])
        event_id = str(event["event_id"])
        users = await events._active_users(core_arg, chat_id)
        for player_row in users:
            user_id = int(player_row["user_id"])
            await events._ensure_participant(core_arg, event_id, user_id)
            await award_influence_once(core_arg, chat_id, user_id, 100, event_id, "popularity")
        if not users:
            return

        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT user_id,delta,reason FROM score_log
            WHERE chat_id=? AND created_at>=? AND delta>0
              AND reason NOT LIKE 'reality_event_%'
            ORDER BY id ASC
            """,
            (chat_id, events._now() - 86400),
        )
        totals: dict[int, int] = {}
        for row in await cursor.fetchall():
            reason = str(row["reason"] or "")
            if events._contains(reason, events.PROTECTED_REASON_WORDS) or events._contains(reason, WAGER_WORDS):
                continue
            user_id = int(row["user_id"])
            totals[user_id] = totals.get(user_id, 0) + int(row["delta"])
        leader_id = max(totals, key=totals.get) if totals else int(users[0]["user_id"])
        await events._ensure_participant(core_arg, event_id, leader_id)
        await award_influence_once(core_arg, chat_id, leader_id, 100, event_id, "popularity_leader")

    async def process_score_sources(core_arg: Any, event: Any) -> None:
        event_id = str(event["event_id"])
        event_key = str(event["event_key"])
        chat_id = int(event["chat_id"])
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT id,user_id,delta,reason,created_at FROM score_log
            WHERE chat_id=? AND created_at>=? AND created_at<=?
            ORDER BY id ASC
            """,
            (chat_id, int(event["starts_at"]), min(events._now(), int(event["ends_at"]))),
        )
        rows = list(await cursor.fetchall())
        for row in rows:
            source_id = str(row["id"])
            reason = str(row["reason"] or "")
            if events._is_event_reason(reason):
                continue
            protected = events._contains(reason, events.PROTECTED_REASON_WORDS)
            is_wager = events._contains(reason, WAGER_WORDS)
            is_mini_app = events._contains(reason, MINI_APP_WORDS)
            is_game = is_wager or is_mini_app or events._contains(reason, events.GAME_REASON_WORDS)
            is_task = events._contains(reason, events.TASK_REASON_WORDS)
            user_id = int(row["user_id"])
            delta = int(row["delta"])

            async with core_arg.db.lock:
                cursor = await conn.execute(
                    "INSERT OR IGNORE INTO reality_event_sources_v96(event_id,source_type,source_id,created_at) VALUES(?,?,?,?)",
                    (event_id, "score", source_id, events._now()),
                )
                if cursor.rowcount <= 0:
                    await conn.commit()
                    continue
                await conn.execute(
                    "INSERT OR IGNORE INTO reality_event_participants_v96(event_id,user_id) VALUES(?,?)",
                    (event_id, user_id),
                )

                if event_key == "influence_day" and delta > 0 and not protected:
                    cursor = await conn.execute(
                        "SELECT event_bonus FROM reality_event_participants_v96 WHERE event_id=? AND user_id=?",
                        (event_id, user_id),
                    )
                    participant = await cursor.fetchone()
                    used = int(participant["event_bonus"] or 0) if participant else 0
                    rate = 0.10 if is_game else 0.25
                    bonus = min(max(0, 500 - used), max(0, int(round(delta * rate))))
                    if bonus > 0:
                        now = events._now()
                        await conn.execute(
                            "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                            (bonus, now, chat_id, user_id),
                        )
                        await conn.execute(
                            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                            (chat_id, user_id, bonus, f"reality_event_{event_id}_influence_bonus", now),
                        )
                        await conn.execute(
                            "UPDATE reality_event_participants_v96 SET event_bonus=event_bonus+? WHERE event_id=? AND user_id=?",
                            (bonus, event_id, user_id),
                        )

                if event_key == "collective" and delta > 0 and not protected and not is_wager:
                    contribution = max(0, int(delta * 0.20)) if is_mini_app else delta
                    if contribution:
                        await conn.execute(
                            "UPDATE reality_event_participants_v96 SET contribution=contribution+? WHERE event_id=? AND user_id=?",
                            (contribution, event_id, user_id),
                        )
                        await conn.execute(
                            "UPDATE reality_events_v96 SET progress=progress+? WHERE event_id=?",
                            (contribution, event_id),
                        )

                if event_key == "tree_awakening":
                    if delta > 0 and not protected and not is_game and events._contains(reason, events.INFLUENCE_ACTION_WORDS):
                        await conn.execute(
                            "UPDATE reality_event_participants_v96 SET influence_done=1 WHERE event_id=? AND user_id=?",
                            (event_id, user_id),
                        )
                    if delta > 0 and is_task:
                        await conn.execute(
                            "UPDATE reality_event_participants_v96 SET task_done=1 WHERE event_id=? AND user_id=?",
                            (event_id, user_id),
                        )
                await conn.commit()

            # Налог возвращают только за настоящее задание. Мини-игры проверяются
            # отдельно по завершённой серверной сессии, а ставки не подходят.
            if event_key == "ego_tax" and is_task and delta >= 0:
                await events._refund_tax(core_arg, event, user_id)

    async def process_game_sources(core_arg: Any, event: Any) -> None:
        conn = core_arg.db._require_connection()
        if not await events._table_exists(conn, "game_runs_v75"):
            return
        event_id = str(event["event_id"])
        event_key = str(event["event_key"])
        cursor = await conn.execute(
            """
            SELECT session_id,user_id,game_key,score,actual_reward,started_at,finished_at
            FROM game_runs_v75
            WHERE chat_id=? AND status='finished' AND finished_at>=? AND finished_at<=?
            ORDER BY finished_at ASC
            """,
            (int(event["chat_id"]), int(event["starts_at"]), min(events._now(), int(event["ends_at"]))),
        )
        for row in await cursor.fetchall():
            game_key = str(row["game_key"])
            duration = max(0, int(row["finished_at"] or 0) - int(row["started_at"] or 0))
            valid_run = duration >= int(MINIMUM_RUN_SECONDS.get(game_key, 12))
            async with core_arg.db.lock:
                cursor = await conn.execute(
                    "INSERT OR IGNORE INTO reality_event_sources_v96(event_id,source_type,source_id,created_at) VALUES(?,?,?,?)",
                    (event_id, "game", str(row["session_id"]), events._now()),
                )
                if cursor.rowcount <= 0:
                    await conn.commit()
                    continue
                user_id = int(row["user_id"])
                await conn.execute(
                    "INSERT OR IGNORE INTO reality_event_participants_v96(event_id,user_id) VALUES(?,?)",
                    (event_id, user_id),
                )
                if valid_run and event_key == "game_night":
                    cursor = await conn.execute(
                        "SELECT game_runs FROM reality_event_participants_v96 WHERE event_id=? AND user_id=?",
                        (event_id, user_id),
                    )
                    participant = await cursor.fetchone()
                    counted = int(participant["game_runs"] or 0) if participant else 0
                    if counted < 5:
                        await conn.execute(
                            "UPDATE reality_event_participants_v96 SET game_runs=game_runs+1 WHERE event_id=? AND user_id=?",
                            (event_id, user_id),
                        )
                        await conn.execute(
                            "UPDATE reality_events_v96 SET progress=progress+1 WHERE event_id=?",
                            (event_id,),
                        )
                elif valid_run and event_key == "tree_awakening":
                    await conn.execute(
                        "UPDATE reality_event_participants_v96 SET game_runs=game_runs+1 WHERE event_id=? AND user_id=?",
                        (event_id, user_id),
                    )
                await conn.commit()
            if valid_run and event_key == "ego_tax":
                await events._refund_tax(core_arg, event, int(row["user_id"]))

    events._award_influence_once = award_influence_once
    events._apply_popularity = apply_popularity
    events._process_score_sources = process_score_sources
    events._process_game_sources = process_game_sources
