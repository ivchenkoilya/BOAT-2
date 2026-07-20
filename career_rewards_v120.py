from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from career_model_v120 import deterministic_range, meta_get, meta_set, now, table_exists

SCAN_INTERVAL = 4
_RUNTIME_STARTED = False


async def award(
    core: Any,
    chat_id: int,
    user_id: int,
    amount: int,
    source_type: str,
    source_id: str,
    reason: str,
) -> int:
    value = max(0, int(amount))
    if value <= 0 or int(chat_id) >= 0 or int(user_id) <= 0:
        return 0
    conn = core.db._require_connection()
    created_at = now()
    async with core.db.lock:
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO career_sources_v120("
            "source_type,source_id,chat_id,user_id,amount,created_at"
            ") VALUES(?,?,?,?,?,?)",
            (source_type, source_id, int(chat_id), int(user_id), value, created_at),
        )
        if cursor.rowcount <= 0:
            await conn.commit()
            return 0
        await conn.execute(
            "UPDATE players SET career_points=MAX(0,career_points+?),"
            "career_initialized=1,updated_at=MAX(updated_at,?) WHERE chat_id=? AND user_id=?",
            (value, created_at, int(chat_id), int(user_id)),
        )
        await conn.execute(
            "INSERT INTO career_log_v120(chat_id,user_id,delta,reason,source_type,source_id,created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (int(chat_id), int(user_id), value, reason, source_type, source_id, created_at),
        )
        await conn.commit()
    return value


def score_award(row: Any) -> tuple[int, str, str, str] | None:
    if int(row["delta"] or 0) <= 0:
        return None
    reason = str(row["reason"] or "")
    low = reason.casefold()
    if any(word in low for word in (
        "transfer", "finance", "loan", "repay", "admin", "restore", "refund",
        "compensation", "sabotage", "impeachment", "rebellion", "hero_day",
        "reality_event_", "boss", "void",
    )):
        return None
    source_id = str(row["id"])
    if "bot_game_coin" in low or "bot_game_dice" in low:
        date_key = datetime.fromtimestamp(int(row["created_at"]), timezone.utc).date().isoformat()
        daily_id = f"{int(row['chat_id'])}:{int(row['user_id'])}:{date_key}"
        return 500, "first_wager_win", daily_id, "Первая победа дня в кубике или монетке"
    if any(word in low for word in ("game_influence_hunt", "rooftop", "heist", "night-hunter", "night_hunter")):
        return None
    if "achievement" in low or "achiev" in low or "достижен" in low:
        amount = deterministic_range(f"achievement:{source_id}:{reason}", 5_000, 50_000)
        return amount, "achievement", source_id, "Достижение"
    if "secret" in low or "mission" in low:
        amount = deterministic_range(f"mission:{source_id}:{reason}", 3_000, 5_000)
        return amount, "mission", source_id, "Сложное или тайное задание"
    if "task" in low:
        return 1_500, "task", source_id, "Задание"
    if "daily" in low and "bonus" in low:
        return 1_000, "daily_bonus", source_id, "Ежедневный бонус"
    if "influence" in low:
        amount = deterministic_range(f"influence:{source_id}:{reason}", 1_500, 3_000)
        return amount, "influence", source_id, "Увеличение влияния"
    return None


async def process_score_log(core: Any) -> None:
    conn = core.db._require_connection()
    cursor_value = await meta_get(core, "score_cursor", 0)
    while True:
        cursor = await conn.execute(
            "SELECT id,chat_id,user_id,delta,reason,created_at FROM score_log "
            "WHERE id>? ORDER BY id ASC LIMIT 500",
            (cursor_value,),
        )
        rows = list(await cursor.fetchall())
        if not rows:
            return
        for row in rows:
            spec = score_award(row)
            if spec is not None:
                amount, source_type, source_id, reason = spec
                await award(core, row["chat_id"], row["user_id"], amount, source_type, source_id, reason)
        cursor_value = int(rows[-1]["id"])
        await meta_set(core, "score_cursor", cursor_value)
        if len(rows) < 500:
            return


async def process_mini_apps(core: Any) -> None:
    conn = core.db._require_connection()
    if not await table_exists(conn, "game_runs_v75"):
        return
    started_at = await meta_get(core, "career_started_at", now())
    cursor = await conn.execute(
        "SELECT session_id,chat_id,user_id,game_key FROM game_runs_v75 "
        "WHERE status='finished' AND finished_at>=? ORDER BY finished_at ASC LIMIT 2000",
        (started_at,),
    )
    for row in await cursor.fetchall():
        session_id = str(row["session_id"])
        amount = deterministic_range(f"mini:{session_id}", 500, 1_500)
        await award(
            core, row["chat_id"], row["user_id"], amount, "mini_app", session_id,
            f"Завершение Mini App: {row['game_key']}",
        )


async def process_bosses(core: Any) -> None:
    conn = core.db._require_connection()
    if not await table_exists(conn, "boss_battles") or not await table_exists(conn, "boss_fighters"):
        return
    started_at = await meta_get(core, "career_started_at", now())
    cursor = await conn.execute(
        "SELECT boss_id,chat_id,status,last_attacker_id FROM boss_battles "
        "WHERE status!='active' AND COALESCE(resolved_at,0)>=? ORDER BY resolved_at ASC LIMIT 500",
        (started_at,),
    )
    for battle in await cursor.fetchall():
        boss_id = str(battle["boss_id"])
        chat_id = int(battle["chat_id"])
        fighters_cursor = await conn.execute(
            "SELECT user_id,attacks,damage_done FROM boss_fighters "
            "WHERE boss_id=? AND attacks>0 ORDER BY damage_done DESC,attacks DESC",
            (boss_id,),
        )
        fighters = list(await fighters_cursor.fetchall())
        for fighter in fighters:
            user_id = int(fighter["user_id"])
            await award(core, chat_id, user_id, 3_000, "boss_participation", boss_id, "Участие в боссе")
            if str(battle["status"]) == "victory":
                await award(core, chat_id, user_id, 10_000, "boss_victory", boss_id, "Победа над боссом")
        if str(battle["status"]) == "victory" and fighters:
            await award(core, chat_id, fighters[0]["user_id"], 5_000, "boss_top", boss_id, "Лучший по урону")
            finisher = int(battle["last_attacker_id"] or 0)
            if finisher:
                await award(core, chat_id, finisher, 3_000, "boss_finisher", boss_id, "Последний удар по боссу")


def event_activity(row: Any) -> int:
    fields = (
        "contribution", "game_runs", "task_done", "influence_done", "boss_attacks",
        "boss_damage", "event_bonus", "tax_refunded", "reward_influence", "completed",
    )
    return sum(max(0, int(row[field] or 0)) for field in fields)


def event_score(row: Any) -> int:
    return (
        int(row["contribution"] or 0)
        + int(row["game_runs"] or 0) * 1_000
        + int(row["task_done"] or 0) * 3_000
        + int(row["influence_done"] or 0) * 2_000
        + int(row["boss_damage"] or 0)
        + int(row["event_bonus"] or 0)
        + int(row["tax_refunded"] or 0) * 5_000
        + int(row["completed"] or 0) * 5_000
    )


async def process_events(core: Any) -> None:
    conn = core.db._require_connection()
    if not await table_exists(conn, "reality_events_v96") or not await table_exists(conn, "reality_event_participants_v96"):
        return
    started_at = await meta_get(core, "career_started_at", now())
    cursor = await conn.execute(
        "SELECT event_id,chat_id,status FROM reality_events_v96 "
        "WHERE status IN ('completed','failed') AND COALESCE(resolved_at,0)>=? "
        "ORDER BY resolved_at ASC LIMIT 500",
        (started_at,),
    )
    for event in await cursor.fetchall():
        event_id = str(event["event_id"])
        participants_cursor = await conn.execute(
            "SELECT * FROM reality_event_participants_v96 WHERE event_id=?",
            (event_id,),
        )
        participants = [row for row in await participants_cursor.fetchall() if event_activity(row) > 0]
        for participant in participants:
            user_id = int(participant["user_id"])
            await award(core, event["chat_id"], user_id, 2_000, "event_participation", event_id, "Участие в событии дня")
            if str(event["status"]) == "completed":
                await award(core, event["chat_id"], user_id, 8_000, "event_success", event_id, "Успешное событие дня")
        if str(event["status"]) == "completed" and participants:
            best = max(participants, key=event_score)
            await award(core, event["chat_id"], best["user_id"], 5_000, "event_best", event_id, "Лучший участник события")


async def process_all(core: Any) -> None:
    await process_score_log(core)
    await process_mini_apps(core)
    await process_bosses(core)
    await process_events(core)


async def runtime_loop(core: Any) -> None:
    await asyncio.sleep(3)
    while True:
        try:
            await process_all(core)
        except asyncio.CancelledError:
            raise
        except Exception:
            core.logging.exception("Ошибка карьерного цикла Reality 120")
        await asyncio.sleep(SCAN_INTERVAL)


def install_career_rewards_v120(core: Any) -> None:
    global _RUNTIME_STARTED
    if getattr(core, "_career_rewards_v120_installed", False):
        return
    core._career_rewards_v120_installed = True
    core.add_career_points = lambda chat_id, user_id, amount, reason, source_id: award(
        core, chat_id, user_id, amount, "manual", source_id, reason
    )
    original_start = core.start_webapp_server

    async def start_with_career_rewards(bot: Any):
        global _RUNTIME_STARTED
        runner = await original_start(bot)
        if not _RUNTIME_STARTED:
            _RUNTIME_STARTED = True
            core.spawn_background_task(runtime_loop(core))
        return runner

    core.start_webapp_server = start_with_career_rewards
