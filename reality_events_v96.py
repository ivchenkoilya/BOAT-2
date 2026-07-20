from __future__ import annotations

import asyncio
import html
import json
import logging
import random
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aiohttp import web
from aiogram.filters import Command
from aiogram.types import BotCommand, Message

import talent_system


LOGGER = logging.getLogger(__name__)
VERSION = "Reality 96 · События реальности"
EVENT_DURATION = 24 * 60 * 60
LAUNCH_HOUR_UTC = 10
ACTIVE_WINDOW = 7 * 24 * 60 * 60
PROCESS_INTERVAL = 45
SCRIPT_PATH = Path(__file__).resolve().parent / "adminapp_v96" / "events-admin.js"
NIGHT_PATCH_PATH = Path(__file__).resolve().parent / "adminapp_v95" / "night-hunter-admin.js"

EVENTS: dict[str, dict[str, Any]] = {
    "popularity": {
        "emoji": "🌟",
        "title": "Волна популярности",
        "weight": 20,
        "description": "Все активные участники получают +100 влияния, лидер суток — ещё +100.",
    },
    "ego_tax": {
        "emoji": "🧾",
        "title": "Налог на эго",
        "weight": 10,
        "description": "Реальность списывает влияние по роли. Задание, игра или 5 ударов по боссу возвращают налог.",
    },
    "influence_day": {
        "emoji": "🔥",
        "title": "День влияния",
        "weight": 20,
        "description": "+25% к обычным положительным начислениям и +10% к игровым, максимум +500 за сутки.",
    },
    "collective": {
        "emoji": "🌌",
        "title": "Коллективное пробуждение",
        "weight": 20,
        "description": "Беседа вместе набирает карьерное влияние и открывает общие награды.",
    },
    "game_night": {
        "emoji": "🎮",
        "title": "Игровая ночь",
        "weight": 15,
        "description": "Завершите 30 забегов минимум тремя игроками. От одного человека считается до пяти.",
    },
    "boss_fall": {
        "emoji": "👁",
        "title": "Падение Центра",
        "weight": 5,
        "description": "Победите Центр Вселенной. Активные бойцы получат +300 влияния и +2 очка Древа.",
    },
    "tree_awakening": {
        "emoji": "🌳",
        "title": "Пробуждение Древа",
        "weight": 10,
        "description": "Получи влияние, выполни задание и заверши игру или нанеси 5 ударов по боссу.",
    },
}

PROTECTED_REASON_WORDS = (
    "admin",
    "transfer",
    "restore",
    "refund",
    "compensation",
    "stake",
    "hero_day",
    "void",
)
GAME_REASON_WORDS = (
    "game",
    "coin",
    "dice",
    "roulette",
    "fate",
    "heist",
    "rooftop",
    "night-hunter",
    "night_hunter",
    "bet",
)
TASK_REASON_WORDS = ("task", "mission", "secret")
INFLUENCE_ACTION_WORDS = ("influence", "daily", "bonus")
_PROCESS_LOCK = asyncio.Lock()
_RUNTIME_STARTED = False


def _now() -> int:
    return int(time.time())


def _day_start(timestamp: int | None = None) -> int:
    value = datetime.fromtimestamp(timestamp or _now(), timezone.utc)
    start = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return int(start.timestamp())


def _date_key(timestamp: int | None = None) -> str:
    return datetime.fromtimestamp(timestamp or _now(), timezone.utc).date().isoformat()


def _week_key(timestamp: int | None = None) -> str:
    iso = datetime.fromtimestamp(timestamp or _now(), timezone.utc).date().isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _contains(reason: str, words: tuple[str, ...]) -> bool:
    lowered = str(reason or "").casefold()
    return any(word in lowered for word in words)


def _is_event_reason(reason: str) -> bool:
    return str(reason or "").startswith("reality_event_")


def _event_info(key: str) -> dict[str, Any]:
    return EVENTS.get(key, {"emoji": "🌠", "title": key, "description": ""})


def _role_key(core: Any, points: int) -> str:
    value = int(points)
    if value >= int(core.HERO_MIN_POINTS):
        return "hero"
    if value >= int(core.SECONDARY_MIN_POINTS):
        return "secondary"
    if value >= int(core.EXTRAS_MIN_POINTS):
        return "extras"
    if value >= int(core.DUST_MIN_POINTS):
        return "dust"
    return "decoration"


def _tax_for_role(role_key: str) -> int:
    # По просьбе владельца налог удвоен относительно исходной концепции.
    return {
        "decoration": 50,
        "dust": 50,
        "extras": 100,
        "secondary": 150,
        "hero": 200,
    }.get(role_key, 50)


async def _table_exists(conn: Any, name: str) -> bool:
    cursor = await conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    )
    return await cursor.fetchone() is not None


async def _ensure_schema(db: Any) -> None:
    conn = db._require_connection()
    async with db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS reality_events_v96 (
                event_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                event_key TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                starts_at INTEGER NOT NULL,
                ends_at INTEGER NOT NULL,
                target INTEGER NOT NULL DEFAULT 0,
                progress INTEGER NOT NULL DEFAULT 0,
                message_id INTEGER,
                forced INTEGER NOT NULL DEFAULT 0,
                meta_json TEXT NOT NULL DEFAULT '{}',
                result_text TEXT,
                resolved_at INTEGER
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_reality_events_v96_active
            ON reality_events_v96(chat_id) WHERE status='active';
            CREATE INDEX IF NOT EXISTS idx_reality_events_v96_history
            ON reality_events_v96(chat_id,starts_at DESC);

            CREATE TABLE IF NOT EXISTS reality_event_participants_v96 (
                event_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                contribution INTEGER NOT NULL DEFAULT 0,
                game_runs INTEGER NOT NULL DEFAULT 0,
                task_done INTEGER NOT NULL DEFAULT 0,
                influence_done INTEGER NOT NULL DEFAULT 0,
                boss_attacks INTEGER NOT NULL DEFAULT 0,
                boss_damage INTEGER NOT NULL DEFAULT 0,
                event_bonus INTEGER NOT NULL DEFAULT 0,
                tax_amount INTEGER NOT NULL DEFAULT 0,
                tax_refunded INTEGER NOT NULL DEFAULT 0,
                reward_influence INTEGER NOT NULL DEFAULT 0,
                reward_tree INTEGER NOT NULL DEFAULT 0,
                completed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(event_id,user_id),
                FOREIGN KEY(event_id) REFERENCES reality_events_v96(event_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reality_event_sources_v96 (
                event_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(event_id,source_type,source_id)
            );

            CREATE TABLE IF NOT EXISTS reality_event_tree_claims_v96 (
                event_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                reward_key TEXT NOT NULL,
                points INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(event_id,user_id,reward_key)
            );

            CREATE TABLE IF NOT EXISTS reality_event_settings_v96 (
                chat_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                pinned_event TEXT,
                launch_hour_utc INTEGER NOT NULL DEFAULT 10,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reality_event_attempt_grants_v96 (
                event_id TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                game_key TEXT NOT NULL,
                date_key TEXT NOT NULL,
                amount INTEGER NOT NULL,
                applied INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(event_id,user_id,game_key,date_key)
            );
            """
        )
        await conn.commit()


async def _active_users(core: Any, chat_id: int) -> list[Any]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT * FROM players
        WHERE chat_id=? AND updated_at>=?
        ORDER BY points DESC,message_count DESC
        """,
        (chat_id, _now() - ACTIVE_WINDOW),
    )
    return list(await cursor.fetchall())


async def _ensure_participant(core: Any, event_id: str, user_id: int) -> None:
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.execute(
            "INSERT OR IGNORE INTO reality_event_participants_v96(event_id,user_id) VALUES(?,?)",
            (event_id, user_id),
        )
        await conn.commit()


async def _active_event(core: Any, chat_id: int) -> Any | None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM reality_events_v96 WHERE chat_id=? AND status='active' ORDER BY starts_at DESC LIMIT 1",
        (chat_id,),
    )
    return await cursor.fetchone()


async def _event_by_id(core: Any, event_id: str) -> Any | None:
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT * FROM reality_events_v96 WHERE event_id=?", (event_id,))
    return await cursor.fetchone()


async def _award_influence_once(
    core: Any,
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
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT delta FROM score_log WHERE chat_id=? AND user_id=? AND reason=? LIMIT 1",
        (chat_id, user_id, reason),
    )
    row = await cursor.fetchone()
    if row is not None:
        return max(0, int(row["delta"]))
    player = await core.db.get_player(chat_id, user_id)
    if player is None:
        return 0
    method = getattr(core.db, "add_points_with_balance", None)
    if method is not None:
        before, after = await method(chat_id, user_id, base, reason)
        actual = max(0, int(after.points) - int(before.points))
    else:
        before_points = int(player.points)
        after = await core.db.add_points(chat_id, user_id, base, reason)
        actual = max(0, int(after.points) - before_points)
    async with core.db.lock:
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


async def _grant_tree_once(
    core: Any,
    chat_id: int,
    user_id: int,
    points: int,
    event_id: str,
    reward_key: str,
) -> int:
    amount = max(0, int(points))
    if amount <= 0:
        return 0
    try:
        await talent_system.sync_profile(core.db, chat_id, user_id)
    except Exception:
        return 0
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        cursor = await conn.execute(
            """
            INSERT OR IGNORE INTO reality_event_tree_claims_v96(
                event_id,user_id,reward_key,points,created_at
            ) VALUES(?,?,?,?,?)
            """,
            (event_id, user_id, reward_key, amount, now),
        )
        if cursor.rowcount <= 0:
            await conn.commit()
            return 0
        await conn.execute(
            """
            UPDATE talent_profiles
            SET total_points=total_points+?,updated_at=?
            WHERE chat_id=? AND user_id=?
            """,
            (amount, now, chat_id, user_id),
        )
        await conn.execute(
            """
            UPDATE reality_event_participants_v96
            SET reward_tree=reward_tree+?
            WHERE event_id=? AND user_id=?
            """,
            (amount, event_id, user_id),
        )
        await conn.commit()
    return amount


async def _apply_popularity(core: Any, event: Any) -> None:
    chat_id = int(event["chat_id"])
    event_id = str(event["event_id"])
    users = await _active_users(core, chat_id)
    for row in users:
        user_id = int(row["user_id"])
        await _ensure_participant(core, event_id, user_id)
        await _award_influence_once(core, chat_id, user_id, 100, event_id, "popularity")
    if not users:
        return
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT user_id,COALESCE(SUM(delta),0) amount
        FROM score_log
        WHERE chat_id=? AND created_at>=? AND delta>0
          AND reason NOT LIKE 'reality_event_%'
        GROUP BY user_id ORDER BY amount DESC LIMIT 1
        """,
        (chat_id, _now() - 86400),
    )
    leader = await cursor.fetchone()
    leader_id = int(leader["user_id"]) if leader else int(users[0]["user_id"])
    await _ensure_participant(core, event_id, leader_id)
    await _award_influence_once(core, chat_id, leader_id, 100, event_id, "popularity_leader")


async def _apply_tax(core: Any, event: Any) -> None:
    chat_id = int(event["chat_id"])
    event_id = str(event["event_id"])
    users = await _active_users(core, chat_id)
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        for row in users:
            user_id = int(row["user_id"])
            points = max(0, int(row["points"]))
            tax = min(points, _tax_for_role(_role_key(core, points)))
            await conn.execute(
                "INSERT OR IGNORE INTO reality_event_participants_v96(event_id,user_id) VALUES(?,?)",
                (event_id, user_id),
            )
            cursor = await conn.execute(
                "SELECT tax_amount FROM reality_event_participants_v96 WHERE event_id=? AND user_id=?",
                (event_id, user_id),
            )
            participant = await cursor.fetchone()
            if participant is not None and int(participant["tax_amount"]) > 0:
                continue
            if tax > 0:
                await conn.execute(
                    "UPDATE players SET points=MAX(0,points-?),updated_at=? WHERE chat_id=? AND user_id=?",
                    (tax, now, chat_id, user_id),
                )
                await conn.execute(
                    "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                    (chat_id, user_id, -tax, f"reality_event_{event_id}_ego_tax", now),
                )
            await conn.execute(
                "UPDATE reality_event_participants_v96 SET tax_amount=? WHERE event_id=? AND user_id=?",
                (tax, event_id, user_id),
            )
        await conn.commit()


async def _refund_tax(core: Any, event: Any, user_id: int) -> int:
    if str(event["event_key"]) != "ego_tax":
        return 0
    conn = core.db._require_connection()
    chat_id = int(event["chat_id"])
    event_id = str(event["event_id"])
    now = _now()
    async with core.db.lock:
        cursor = await conn.execute(
            """
            SELECT tax_amount,tax_refunded FROM reality_event_participants_v96
            WHERE event_id=? AND user_id=?
            """,
            (event_id, user_id),
        )
        row = await cursor.fetchone()
        if row is None or int(row["tax_refunded"]) or int(row["tax_amount"]) <= 0:
            return 0
        amount = int(row["tax_amount"])
        await conn.execute(
            "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
            (amount, now, chat_id, user_id),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (chat_id, user_id, amount, f"reality_event_{event_id}_tax_refund", now),
        )
        await conn.execute(
            "UPDATE reality_event_participants_v96 SET tax_refunded=1 WHERE event_id=? AND user_id=?",
            (event_id, user_id),
        )
        await conn.commit()
        return amount


async def _choose_event(core: Any, chat_id: int) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT pinned_event FROM reality_event_settings_v96 WHERE chat_id=?",
        (chat_id,),
    )
    settings = await cursor.fetchone()
    pinned = str(settings["pinned_event"] or "") if settings else ""
    if pinned in EVENTS:
        async with core.db.lock:
            await conn.execute(
                "UPDATE reality_event_settings_v96 SET pinned_event=NULL,updated_at=? WHERE chat_id=?",
                (_now(), chat_id),
            )
            await conn.commit()
        return pinned

    cursor = await conn.execute(
        "SELECT event_key,starts_at FROM reality_events_v96 WHERE chat_id=? ORDER BY starts_at DESC LIMIT 10",
        (chat_id,),
    )
    history = list(await cursor.fetchall())
    forbidden = {str(row["event_key"]) for row in history if int(row["starts_at"]) >= _now() - 3 * 86400}
    if history and str(history[0]["event_key"]) == "ego_tax":
        forbidden.add("ego_tax")
    if any(str(row["event_key"]) == "boss_fall" and int(row["starts_at"]) >= _now() - 7 * 86400 for row in history):
        forbidden.add("boss_fall")
    week_start = _now() - datetime.now(timezone.utc).weekday() * 86400
    tree_count = sum(
        1
        for row in history
        if str(row["event_key"]) == "tree_awakening" and int(row["starts_at"]) >= week_start
    )
    if tree_count >= 2:
        forbidden.add("tree_awakening")
    pool = [(key, int(spec["weight"])) for key, spec in EVENTS.items() if key not in forbidden]
    if not pool:
        pool = [(key, int(spec["weight"])) for key, spec in EVENTS.items()]
    keys, weights = zip(*pool)
    return str(random.choices(keys, weights=weights, k=1)[0])


async def _start_event(
    core: Any,
    bot: Any,
    chat_id: int,
    event_key: str | None = None,
    *,
    forced: bool = False,
) -> Any:
    existing = await _active_event(core, chat_id)
    if existing is not None:
        raise ValueError("В этой беседе уже идёт событие реальности.")
    key = event_key if event_key in EVENTS else await _choose_event(core, chat_id)
    users = await _active_users(core, chat_id)
    active_count = len(users)
    target = 0
    if key == "collective":
        target = 2500 if active_count <= 5 else 5000 if active_count <= 10 else 8000 if active_count <= 20 else 12000
    elif key == "game_night":
        target = 30
    elif key == "boss_fall":
        target = 1
    elif key == "tree_awakening":
        target = active_count
    event_id = secrets.token_hex(12)
    now = _now()
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.execute(
            """
            INSERT INTO reality_events_v96(
                event_id,chat_id,event_key,status,starts_at,ends_at,target,progress,forced
            ) VALUES(?,?,?,'active',?,?,?,?,?)
            """,
            (event_id, chat_id, key, now, now + EVENT_DURATION, target, 0, 1 if forced else 0),
        )
        await conn.executemany(
            "INSERT OR IGNORE INTO reality_event_participants_v96(event_id,user_id) VALUES(?,?)",
            [(event_id, int(row["user_id"])) for row in users],
        )
        await conn.commit()
    event = await _event_by_id(core, event_id)
    if key == "popularity":
        await _apply_popularity(core, event)
    elif key == "ego_tax":
        await _apply_tax(core, event)
    text = await _event_text(core, event, None)
    try:
        sent = await bot.send_message(chat_id, text)
        async with core.db.lock:
            await conn.execute(
                "UPDATE reality_events_v96 SET message_id=? WHERE event_id=?",
                (int(sent.message_id), event_id),
            )
            await conn.commit()
    except Exception:
        LOGGER.exception("Не удалось отправить событие в чат %s", chat_id)
    return await _event_by_id(core, event_id)


async def _process_score_sources(core: Any, event: Any) -> None:
    event_id = str(event["event_id"])
    event_key = str(event["event_key"])
    chat_id = int(event["chat_id"])
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT id,user_id,delta,reason,created_at FROM score_log
        WHERE chat_id=? AND created_at>=? AND created_at<=?
        ORDER BY id ASC
        """,
        (chat_id, int(event["starts_at"]), min(_now(), int(event["ends_at"]))),
    )
    rows = list(await cursor.fetchall())
    for row in rows:
        source_id = str(row["id"])
        reason = str(row["reason"] or "")
        if _is_event_reason(reason):
            continue
        async with core.db.lock:
            cursor = await conn.execute(
                "INSERT OR IGNORE INTO reality_event_sources_v96(event_id,source_type,source_id,created_at) VALUES(?,?,?,?)",
                (event_id, "score", source_id, _now()),
            )
            if cursor.rowcount <= 0:
                await conn.commit()
                continue
            user_id = int(row["user_id"])
            delta = int(row["delta"])
            await conn.execute(
                "INSERT OR IGNORE INTO reality_event_participants_v96(event_id,user_id) VALUES(?,?)",
                (event_id, user_id),
            )
            protected = _contains(reason, PROTECTED_REASON_WORDS)
            is_game = _contains(reason, GAME_REASON_WORDS)
            is_task = _contains(reason, TASK_REASON_WORDS)
            if event_key == "influence_day" and delta > 0 and not protected:
                cursor = await conn.execute(
                    "SELECT event_bonus FROM reality_event_participants_v96 WHERE event_id=? AND user_id=?",
                    (event_id, user_id),
                )
                p = await cursor.fetchone()
                used = int(p["event_bonus"] or 0) if p else 0
                rate = 0.10 if is_game else 0.25
                bonus = min(max(0, 500 - used), max(0, int(round(delta * rate))))
                if bonus > 0:
                    now = _now()
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
            if event_key == "collective" and delta > 0 and not protected:
                contribution = max(0, int(delta * 0.20)) if is_game else delta
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
                if delta > 0 and not protected and not is_game and _contains(reason, INFLUENCE_ACTION_WORDS):
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
        if event_key == "ego_tax" and (is_task or is_game) and int(row["delta"]) >= 0:
            await _refund_tax(core, event, int(row["user_id"]))


async def _process_game_sources(core: Any, event: Any) -> None:
    conn = core.db._require_connection()
    if not await _table_exists(conn, "game_runs_v75"):
        return
    event_id = str(event["event_id"])
    event_key = str(event["event_key"])
    cursor = await conn.execute(
        """
        SELECT session_id,user_id,game_key,score,actual_reward,finished_at
        FROM game_runs_v75
        WHERE chat_id=? AND status='finished' AND finished_at>=? AND finished_at<=?
        ORDER BY finished_at ASC
        """,
        (int(event["chat_id"]), int(event["starts_at"]), min(_now(), int(event["ends_at"]))),
    )
    for row in await cursor.fetchall():
        async with core.db.lock:
            cursor = await conn.execute(
                "INSERT OR IGNORE INTO reality_event_sources_v96(event_id,source_type,source_id,created_at) VALUES(?,?,?,?)",
                (event_id, "game", str(row["session_id"]), _now()),
            )
            if cursor.rowcount <= 0:
                await conn.commit()
                continue
            user_id = int(row["user_id"])
            await conn.execute(
                "INSERT OR IGNORE INTO reality_event_participants_v96(event_id,user_id) VALUES(?,?)",
                (event_id, user_id),
            )
            if event_key == "game_night":
                cursor = await conn.execute(
                    "SELECT game_runs FROM reality_event_participants_v96 WHERE event_id=? AND user_id=?",
                    (event_id, user_id),
                )
                p = await cursor.fetchone()
                counted = int(p["game_runs"] or 0) if p else 0
                if counted < 5:
                    await conn.execute(
                        "UPDATE reality_event_participants_v96 SET game_runs=game_runs+1 WHERE event_id=? AND user_id=?",
                        (event_id, user_id),
                    )
                    await conn.execute("UPDATE reality_events_v96 SET progress=progress+1 WHERE event_id=?", (event_id,))
            elif event_key == "tree_awakening":
                await conn.execute(
                    "UPDATE reality_event_participants_v96 SET game_runs=game_runs+1 WHERE event_id=? AND user_id=?",
                    (event_id, user_id),
                )
            await conn.commit()
        if event_key == "ego_tax":
            await _refund_tax(core, event, int(row["user_id"]))


async def _process_boss_sources(core: Any, event: Any) -> None:
    conn = core.db._require_connection()
    if not await _table_exists(conn, "boss_battles"):
        return
    event_id = str(event["event_id"])
    event_key = str(event["event_key"])
    cursor = await conn.execute(
        """
        SELECT bf.user_id,COALESCE(SUM(bf.attacks),0) attacks,
               COALESCE(SUM(bf.damage_done),0) damage
        FROM boss_fighters bf
        JOIN boss_battles bb ON bb.boss_id=bf.boss_id
        WHERE bb.chat_id=? AND bb.created_at<=?
          AND (bb.resolved_at IS NULL OR bb.resolved_at>=?)
        GROUP BY bf.user_id
        """,
        (int(event["chat_id"]), int(event["ends_at"]), int(event["starts_at"])),
    )
    fighters = list(await cursor.fetchall())
    async with core.db.lock:
        for row in fighters:
            user_id = int(row["user_id"])
            attacks = int(row["attacks"] or 0)
            damage = int(row["damage"] or 0)
            await conn.execute(
                "INSERT OR IGNORE INTO reality_event_participants_v96(event_id,user_id) VALUES(?,?)",
                (event_id, user_id),
            )
            await conn.execute(
                """
                UPDATE reality_event_participants_v96
                SET boss_attacks=MAX(boss_attacks,?),boss_damage=MAX(boss_damage,?)
                WHERE event_id=? AND user_id=?
                """,
                (attacks, damage, event_id, user_id),
            )
        if event_key == "boss_fall":
            cursor = await conn.execute(
                """
                SELECT boss_id FROM boss_battles
                WHERE chat_id=? AND status='victory' AND resolved_at>=? AND resolved_at<=?
                ORDER BY resolved_at ASC LIMIT 1
                """,
                (int(event["chat_id"]), int(event["starts_at"]), min(_now(), int(event["ends_at"]))),
            )
            victory = await cursor.fetchone()
            if victory is not None:
                meta = {"boss_id": str(victory["boss_id"])}
                await conn.execute(
                    "UPDATE reality_events_v96 SET progress=1,meta_json=? WHERE event_id=?",
                    (json.dumps(meta, ensure_ascii=False), event_id),
                )
        await conn.commit()
    if event_key in {"ego_tax", "tree_awakening"}:
        for row in fighters:
            if int(row["attacks"] or 0) >= 5:
                if event_key == "ego_tax":
                    await _refund_tax(core, event, int(row["user_id"]))


async def _reward_tree_awakening(core: Any, event: Any) -> None:
    if str(event["event_key"]) != "tree_awakening":
        return
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT user_id FROM reality_event_participants_v96
        WHERE event_id=? AND completed=0 AND influence_done=1 AND task_done=1
          AND (game_runs>=1 OR boss_attacks>=5)
        """,
        (str(event["event_id"]),),
    )
    rows = list(await cursor.fetchall())
    for row in rows:
        user_id = int(row["user_id"])
        async with core.db.lock:
            cursor = await conn.execute(
                "UPDATE reality_event_participants_v96 SET completed=1 WHERE event_id=? AND user_id=? AND completed=0",
                (str(event["event_id"]), user_id),
            )
            await conn.commit()
            if cursor.rowcount <= 0:
                continue
        await _award_influence_once(core, int(event["chat_id"]), user_id, 100, str(event["event_id"]), "tree_awakening")
        await _grant_tree_once(core, int(event["chat_id"]), user_id, 1, str(event["event_id"]), "tree_awakening")
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT COUNT(*) amount FROM reality_event_participants_v96 WHERE event_id=? AND completed=1",
            (str(event["event_id"]),),
        )
        row = await cursor.fetchone()
        await conn.execute(
            "UPDATE reality_events_v96 SET progress=? WHERE event_id=?",
            (int(row["amount"] or 0) if row else 0, str(event["event_id"])),
        )
        await conn.commit()


async def _schedule_attempts(core: Any, event: Any, user_ids: list[int], amount: int = 3) -> None:
    import game_center_v75 as games

    next_date = (datetime.fromtimestamp(int(event["starts_at"]), timezone.utc).date() + timedelta(days=1)).isoformat()
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        for user_id in user_ids:
            for game_key in games.GAME_INFO:
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO reality_event_attempt_grants_v96(
                        event_id,chat_id,user_id,game_key,date_key,amount,created_at
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    (str(event["event_id"]), int(event["chat_id"]), user_id, game_key, next_date, amount, now),
                )
        await conn.commit()


async def _apply_due_attempt_grants(core: Any) -> None:
    import game_center_v75 as games

    conn = core.db._require_connection()
    if not await _table_exists(conn, "game_attempt_limits_v92") or not await _table_exists(conn, "game_daily_v75"):
        return
    cursor = await conn.execute(
        "SELECT * FROM reality_event_attempt_grants_v96 WHERE applied=0 AND date_key<=?",
        (_date_key(),),
    )
    rows = list(await cursor.fetchall())
    for row in rows:
        async with core.db.lock:
            cursor = await conn.execute(
                "SELECT attempt_limit FROM game_attempt_limits_v92 WHERE chat_id=? AND user_id=? AND game_key=? AND date_key=?",
                (int(row["chat_id"]), int(row["user_id"]), str(row["game_key"]), str(row["date_key"])),
            )
            current = await cursor.fetchone()
            base_limit = int(current["attempt_limit"]) if current else int(games.GAME_ATTEMPTS_PER_DAY)
            new_limit = base_limit + int(row["amount"])
            await conn.execute(
                """
                INSERT INTO game_attempt_limits_v92(chat_id,user_id,game_key,date_key,attempt_limit,updated_at)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(chat_id,user_id,game_key,date_key) DO UPDATE SET
                    attempt_limit=excluded.attempt_limit,updated_at=excluded.updated_at
                """,
                (int(row["chat_id"]), int(row["user_id"]), str(row["game_key"]), str(row["date_key"]), new_limit, _now()),
            )
            await conn.execute(
                """
                INSERT INTO game_daily_v75(chat_id,user_id,game_key,date_key,attempts,updated_at)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(chat_id,user_id,game_key,date_key) DO UPDATE SET
                    attempts=game_daily_v75.attempts-?,updated_at=excluded.updated_at
                """,
                (
                    int(row["chat_id"]), int(row["user_id"]), str(row["game_key"]), str(row["date_key"]),
                    -int(row["amount"]), _now(), int(row["amount"]),
                ),
            )
            await conn.execute(
                "UPDATE reality_event_attempt_grants_v96 SET applied=1 WHERE event_id=? AND user_id=? AND game_key=? AND date_key=?",
                (str(row["event_id"]), int(row["user_id"]), str(row["game_key"]), str(row["date_key"])),
            )
            await conn.commit()


async def _resolve_event(core: Any, bot: Any, event: Any, *, force_reward: bool = False, cancelled: bool = False) -> str:
    event_id = str(event["event_id"])
    chat_id = int(event["chat_id"])
    key = str(event["event_key"])
    conn = core.db._require_connection()
    async with core.db.lock:
        cursor = await conn.execute(
            "UPDATE reality_events_v96 SET status='resolving' WHERE event_id=? AND status='active'",
            (event_id,),
        )
        await conn.commit()
        if cursor.rowcount <= 0:
            current = await _event_by_id(core, event_id)
            return str(current["result_text"] or "Событие уже завершено.") if current else "Событие уже завершено."
    await _process_score_sources(core, event)
    await _process_game_sources(core, event)
    await _process_boss_sources(core, event)
    await _reward_tree_awakening(core, event)
    event = await _event_by_id(core, event_id)
    progress = int(event["progress"] or 0)
    target = int(event["target"] or 0)
    success = force_reward or key in {"popularity", "ego_tax", "influence_day", "tree_awakening"} or (target > 0 and progress >= target)
    reward_lines: list[str] = []

    if cancelled:
        success = False
        result = "Событие отменено администратором без наград."
    elif key == "collective" and success:
        cursor = await conn.execute(
            "SELECT user_id,contribution FROM reality_event_participants_v96 WHERE event_id=? AND contribution>=100 ORDER BY contribution DESC",
            (event_id,),
        )
        rows = list(await cursor.fetchall())
        for row in rows:
            user_id = int(row["user_id"])
            await _award_influence_once(core, chat_id, user_id, 200, event_id, "collective_participant")
            if int(row["contribution"]) >= 500:
                await _grant_tree_once(core, chat_id, user_id, 1, event_id, "collective_500")
        if rows:
            await _award_influence_once(core, chat_id, int(rows[0]["user_id"]), 200, event_id, "collective_top")
        reward_lines.append(f"Награды получили {len(rows)} участников.")
        result = "Общая цель выполнена."
    elif key == "game_night" and success:
        cursor = await conn.execute(
            "SELECT user_id,game_runs FROM reality_event_participants_v96 WHERE event_id=? AND game_runs>0",
            (event_id,),
        )
        participants = list(await cursor.fetchall())
        unique = len(participants)
        if unique < 3 and not force_reward:
            success = False
            result = "Не хватило трёх уникальных игроков."
        else:
            ids = [int(row["user_id"]) for row in participants]
            for user_id in ids:
                await _award_influence_once(core, chat_id, user_id, 100, event_id, "game_night_participant")
                if progress >= 60:
                    await _grant_tree_once(core, chat_id, user_id, 1, event_id, "game_night_double")
            await _schedule_attempts(core, event, ids, 3)
            cursor = await conn.execute(
                """
                SELECT user_id,MAX(score) best FROM game_runs_v75
                WHERE chat_id=? AND status='finished' AND finished_at>=? AND finished_at<=?
                GROUP BY user_id ORDER BY best DESC LIMIT 1
                """,
                (chat_id, int(event["starts_at"]), min(_now(), int(event["ends_at"]))),
            )
            best = await cursor.fetchone()
            if best is not None:
                await _award_influence_once(core, chat_id, int(best["user_id"]), 150, event_id, "game_night_best")
            result = "Игровая цель выполнена."
            reward_lines.append(f"Участников: {unique}. Завтра каждому добавится по 3 попытки во все игры.")
    elif key == "boss_fall" and success:
        try:
            meta = json.loads(str(event["meta_json"] or "{}"))
        except Exception:
            meta = {}
        boss_id = str(meta.get("boss_id") or "")
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(damage_done),0) total FROM boss_fighters WHERE boss_id=?",
            (boss_id,),
        )
        total_row = await cursor.fetchone()
        total_damage = max(1, int(total_row["total"] or 0) if total_row else 1)
        cursor = await conn.execute(
            "SELECT * FROM boss_fighters WHERE boss_id=?",
            (boss_id,),
        )
        fighters = list(await cursor.fetchall())
        eligible: list[int] = []
        for row in fighters:
            attacks = int(row["attacks"] or 0)
            damage = int(row["damage_done"] or 0)
            ability_used = int(row["ability_used_at"] or 0) >= int(event["starts_at"])
            if attacks >= 5 or damage >= total_damage * 0.03 or (ability_used and attacks >= 1):
                eligible.append(int(row["user_id"]))
        for user_id in eligible:
            await _award_influence_once(core, chat_id, user_id, 300, event_id, "boss_fall")
            await _grant_tree_once(core, chat_id, user_id, 2, event_id, "boss_fall")
        cursor = await conn.execute("SELECT last_attacker_id FROM boss_battles WHERE boss_id=?", (boss_id,))
        battle = await cursor.fetchone()
        if battle is not None and int(battle["last_attacker_id"] or 0):
            await _award_influence_once(core, chat_id, int(battle["last_attacker_id"]), 100, event_id, "boss_finisher")
        result = "Центр Вселенной повержен."
        reward_lines.append(f"Активных бойцов: {len(eligible)}.")
    elif key == "tree_awakening":
        cursor = await conn.execute(
            "SELECT COUNT(*) amount FROM reality_event_participants_v96 WHERE event_id=? AND completed=1",
            (event_id,),
        )
        row = await cursor.fetchone()
        result = f"Испытание Древа завершили {int(row['amount'] or 0) if row else 0} игроков."
    elif key == "ego_tax":
        cursor = await conn.execute(
            "SELECT COUNT(*) amount FROM reality_event_participants_v96 WHERE event_id=? AND tax_refunded=1",
            (event_id,),
        )
        row = await cursor.fetchone()
        result = f"Налог вернули {int(row['amount'] or 0) if row else 0} участников."
    elif key == "influence_day":
        cursor = await conn.execute(
            "SELECT COALESCE(SUM(event_bonus),0) amount FROM reality_event_participants_v96 WHERE event_id=?",
            (event_id,),
        )
        row = await cursor.fetchone()
        result = f"Событие добавило участникам {int(row['amount'] or 0) if row else 0} влияния."
    elif key == "popularity":
        result = "Волна популярности завершена."
    else:
        result = "Цель не выполнена. Награды не выдаются."

    final_status = "cancelled" if cancelled else "completed" if success else "failed"
    result_text = result + (" " + " ".join(reward_lines) if reward_lines else "")
    async with core.db.lock:
        await conn.execute(
            "UPDATE reality_events_v96 SET status=?,result_text=?,resolved_at=? WHERE event_id=?",
            (final_status, result_text, _now(), event_id),
        )
        await conn.commit()
    try:
        final_event = await _event_by_id(core, event_id)
        if int(final_event["message_id"] or 0):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=int(final_event["message_id"]),
                text=await _event_text(core, final_event, None),
            )
        else:
            await bot.send_message(chat_id, await _event_text(core, final_event, None))
    except Exception:
        LOGGER.exception("Не удалось обновить итог события %s", event_id)
    return result_text


async def _event_text(core: Any, event: Any, user_id: int | None) -> str:
    key = str(event["event_key"])
    info = _event_info(key)
    status = str(event["status"])
    remaining = max(0, int(event["ends_at"]) - _now())
    lines = [
        f"{info['emoji']} <b>{html.escape(str(info['title']).upper())}</b>",
        "",
        html.escape(str(info["description"])),
    ]
    if status == "active":
        lines.append(f"⏳ Осталось: <b>{core.human_duration(remaining)}</b>")
    if int(event["target"] or 0) > 0:
        lines.append(f"📊 Общий прогресс: <b>{int(event['progress'])}/{int(event['target'])}</b>")
    if key == "ego_tax":
        lines.extend(
            [
                "",
                "🪑 Декорация и 🌫 Пыль: <b>−50</b>",
                "👥 Массовка: <b>−100</b>",
                "🎭 Второстепенная роль: <b>−150</b>",
                "👑 Главный герой: <b>−200</b>",
                "",
                "Верни налог: выполни задание, заверши мини-игру или нанеси 5 ударов по боссу.",
            ]
        )
    elif key == "collective":
        lines.append("🏆 Вклад от 100: +200 влияния · от 500: ещё +1 очко Древа.")
    elif key == "game_night":
        lines.append("🏆 Участникам: +100 влияния и +3 попытки во все игры завтра. При 60 забегах — ещё +1 очко Древа.")
    elif key == "boss_fall":
        lines.append("🏆 Активным бойцам: +300 влияния и +2 очка Древа. Последний удар: ещё +100.")
    elif key == "tree_awakening":
        lines.append("🏆 Личная награда: +100 влияния и +1 очко Древа.")
    if user_id:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            "SELECT * FROM reality_event_participants_v96 WHERE event_id=? AND user_id=?",
            (str(event["event_id"]), user_id),
        )
        p = await cursor.fetchone()
        if p:
            lines.append("")
            if key == "collective":
                lines.append(f"👤 Твой вклад: <b>{int(p['contribution'])}</b>")
            elif key == "game_night":
                lines.append(f"👤 Засчитано твоих забегов: <b>{int(p['game_runs'])}/5</b>")
            elif key == "ego_tax":
                state = "возвращён ✅" if int(p["tax_refunded"]) else "можно вернуть"
                lines.append(f"👤 Твой налог: <b>{int(p['tax_amount'])}</b> · {state}")
            elif key == "influence_day":
                lines.append(f"👤 Твой бонус события: <b>+{int(p['event_bonus'])}/500</b>")
            elif key == "tree_awakening":
                game_or_boss = int(p["game_runs"]) >= 1 or int(p["boss_attacks"]) >= 5
                lines.extend(
                    [
                        f"{'✅' if int(p['influence_done']) else '⬜'} Получить влияние",
                        f"{'✅' if int(p['task_done']) else '⬜'} Выполнить задание",
                        f"{'✅' if game_or_boss else '⬜'} Завершить игру или нанести 5 ударов",
                    ]
                )
    if status != "active":
        lines.extend(["", f"🏁 <b>{html.escape(str(event['result_text'] or 'Событие завершено.'))}</b>"])
    return "\n".join(lines)


async def _update_message(core: Any, bot: Any, event: Any) -> None:
    if str(event["status"]) != "active" or not int(event["message_id"] or 0):
        return
    key = str(event["event_key"])
    if key not in {"collective", "game_night", "boss_fall", "tree_awakening"}:
        return
    try:
        await bot.edit_message_text(
            chat_id=int(event["chat_id"]),
            message_id=int(event["message_id"]),
            text=await _event_text(core, event, None),
        )
    except Exception:
        pass


async def _process_event(core: Any, bot: Any, event: Any) -> None:
    before = int(event["progress"] or 0)
    await _process_score_sources(core, event)
    await _process_game_sources(core, event)
    await _process_boss_sources(core, event)
    await _reward_tree_awakening(core, event)
    refreshed = await _event_by_id(core, str(event["event_id"]))
    if refreshed is None:
        return
    if int(refreshed["progress"] or 0) != before:
        await _update_message(core, bot, refreshed)
    if int(refreshed["ends_at"]) <= _now():
        await _resolve_event(core, bot, refreshed)


async def _daily_launch(core: Any, bot: Any) -> None:
    now = _now()
    current = datetime.fromtimestamp(now, timezone.utc)
    if current.hour < LAUNCH_HOUR_UTC:
        return
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT DISTINCT chat_id FROM players
        WHERE chat_id<0 AND updated_at>=?
        """,
        (now - ACTIVE_WINDOW,),
    )
    chats = [int(row["chat_id"]) for row in await cursor.fetchall()]
    for chat_id in chats:
        cursor = await conn.execute(
            "SELECT enabled,launch_hour_utc FROM reality_event_settings_v96 WHERE chat_id=?",
            (chat_id,),
        )
        settings = await cursor.fetchone()
        if settings is not None and not int(settings["enabled"]):
            continue
        launch_hour = int(settings["launch_hour_utc"]) if settings else LAUNCH_HOUR_UTC
        if current.hour < launch_hour:
            continue
        cursor = await conn.execute(
            "SELECT 1 FROM reality_events_v96 WHERE chat_id=? AND starts_at>=? LIMIT 1",
            (chat_id, _day_start(now)),
        )
        if await cursor.fetchone() is not None:
            continue
        if await _active_event(core, chat_id) is not None:
            continue
        try:
            await _start_event(core, bot, chat_id)
        except Exception:
            LOGGER.exception("Не удалось запустить ежедневное событие в %s", chat_id)


async def _runtime_loop(core: Any, bot: Any) -> None:
    await asyncio.sleep(4)
    while True:
        try:
            async with _PROCESS_LOCK:
                await _apply_due_attempt_grants(core)
                conn = core.db._require_connection()
                cursor = await conn.execute("SELECT * FROM reality_events_v96 WHERE status='active'")
                for event in await cursor.fetchall():
                    await _process_event(core, bot, event)
                await _daily_launch(core, bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Ошибка цикла событий реальности")
        await asyncio.sleep(PROCESS_INTERVAL)


async def _admin_state(core: Any, request: web.Request) -> web.Response:
    user, reason = core._webapp_auth(request)
    if user is None or int(user.id) != int(core.DEVELOPER_ID):
        return core.web.json_response({"ok": False, "reason": reason or "Нет доступа."}, status=403)
    try:
        chat_id = int(request.query.get("chat_id") or 0)
    except ValueError:
        chat_id = 0
    conn = core.db._require_connection()
    event = await _active_event(core, chat_id) if chat_id else None
    event_data = None
    participants: list[dict[str, Any]] = []
    if event is not None:
        event_data = dict(event)
        event_data["info"] = _event_info(str(event["event_key"]))
        cursor = await conn.execute(
            """
            SELECT p.*,pl.full_name,pl.username FROM reality_event_participants_v96 p
            LEFT JOIN players pl ON pl.chat_id=? AND pl.user_id=p.user_id
            WHERE p.event_id=?
            ORDER BY p.contribution DESC,p.game_runs DESC,p.reward_influence DESC
            LIMIT 100
            """,
            (chat_id, str(event["event_id"])),
        )
        participants = [dict(row) for row in await cursor.fetchall()]
    cursor = await conn.execute(
        "SELECT * FROM reality_events_v96 WHERE chat_id=? ORDER BY starts_at DESC LIMIT 20",
        (chat_id,),
    )
    history = []
    for row in await cursor.fetchall():
        item = dict(row)
        item["info"] = _event_info(str(row["event_key"]))
        history.append(item)
    cursor = await conn.execute(
        "SELECT enabled,pinned_event,launch_hour_utc FROM reality_event_settings_v96 WHERE chat_id=?",
        (chat_id,),
    )
    settings = await cursor.fetchone()
    return core.web.json_response(
        {
            "ok": True,
            "version": VERSION,
            "event": event_data,
            "participants": participants,
            "history": history,
            "definitions": {key: {**value, "key": key} for key, value in EVENTS.items()},
            "settings": {
                "enabled": bool(int(settings["enabled"])) if settings else True,
                "pinned_event": str(settings["pinned_event"] or "") if settings else "",
                "launch_hour_utc": int(settings["launch_hour_utc"]) if settings else LAUNCH_HOUR_UTC,
            },
        }
    )


async def _admin_action(core: Any, bot: Any, request: web.Request) -> web.Response:
    user, reason = core._webapp_auth(request)
    if user is None or int(user.id) != int(core.DEVELOPER_ID):
        return core.web.json_response({"ok": False, "reason": reason or "Нет доступа."}, status=403)
    try:
        data = await request.json()
    except Exception:
        data = {}
    try:
        chat_id = int(data.get("chat_id") or 0)
    except (TypeError, ValueError):
        chat_id = 0
    if not chat_id:
        return core.web.json_response({"ok": False, "reason": "Сначала выбери беседу."}, status=400)
    action = str(data.get("action") or "")
    conn = core.db._require_connection()
    try:
        if action == "event_start_random":
            event = await _start_event(core, bot, chat_id, forced=True)
            message = f"Запущено: {_event_info(str(event['event_key']))['title']}."
        elif action == "event_start":
            key = str(data.get("event_key") or "")
            if key not in EVENTS:
                raise ValueError("Неизвестное событие.")
            event = await _start_event(core, bot, chat_id, key, forced=True)
            message = f"Запущено: {_event_info(str(event['event_key']))['title']}."
        elif action == "event_reroll":
            current = await _active_event(core, chat_id)
            if current is not None:
                await _resolve_event(core, bot, current, cancelled=True)
            event = await _start_event(core, bot, chat_id, forced=True)
            message = f"Новое событие: {_event_info(str(event['event_key']))['title']}."
        elif action in {"event_finish", "event_reward", "event_cancel"}:
            current = await _active_event(core, chat_id)
            if current is None:
                raise ValueError("Активного события нет.")
            message = await _resolve_event(
                core,
                bot,
                current,
                force_reward=action == "event_reward",
                cancelled=action == "event_cancel",
            )
        elif action == "event_pin":
            key = str(data.get("event_key") or "")
            if key and key not in EVENTS:
                raise ValueError("Неизвестное событие.")
            async with core.db.lock:
                await conn.execute(
                    """
                    INSERT INTO reality_event_settings_v96(chat_id,pinned_event,updated_at)
                    VALUES(?,?,?) ON CONFLICT(chat_id) DO UPDATE SET
                    pinned_event=excluded.pinned_event,updated_at=excluded.updated_at
                    """,
                    (chat_id, key or None, _now()),
                )
                await conn.commit()
            message = "Событие закреплено на следующий автоматический запуск." if key else "Закреплённое событие очищено."
        elif action == "event_toggle":
            enabled = 1 if bool(data.get("enabled")) else 0
            async with core.db.lock:
                await conn.execute(
                    """
                    INSERT INTO reality_event_settings_v96(chat_id,enabled,updated_at)
                    VALUES(?,?,?) ON CONFLICT(chat_id) DO UPDATE SET
                    enabled=excluded.enabled,updated_at=excluded.updated_at
                    """,
                    (chat_id, enabled, _now()),
                )
                await conn.commit()
            message = "Автоматические события включены." if enabled else "Автоматические события выключены."
        else:
            raise ValueError("Неизвестное действие события.")
    except ValueError as exc:
        return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)
    return core.web.json_response({"ok": True, "message": message})


def install_reality_events_v96(core: Any) -> None:
    global _RUNTIME_STARTED
    if getattr(core, "_reality_events_v96_installed", False):
        return
    core._reality_events_v96_installed = True
    core.BOT_VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_events(self: Any) -> None:
        await original_connect(self)
        await _ensure_schema(self)

    core.Database.connect = connect_with_events

    @web.middleware
    async def event_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
        if request.method == "GET" and request.path == "/admin-v96/events-admin.js":
            return web.FileResponse(
                SCRIPT_PATH,
                headers={"Cache-Control": "no-store", "X-Reality-Events": VERSION},
            )
        if request.method == "GET" and request.path == "/admin-v95/night-hunter-admin.js":
            return web.FileResponse(
                NIGHT_PATCH_PATH,
                headers={"Cache-Control": "no-store", "X-Reality-Events": VERSION},
            )
        if request.path == "/events-v96/api/state" and request.method == "GET":
            return await _admin_state(core, request)
        if request.path == "/events-v96/api/action" and request.method == "POST":
            return await _admin_action(core, request.app["bot"], request)
        return await handler(request)

    original_application = core.web.Application

    def application_with_events(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [event_middleware, *middlewares]
        return original_application(*args, **kwargs)

    core.web.Application = application_with_events

    original_start = core.start_webapp_server

    async def start_with_event_runtime(bot: Any):
        global _RUNTIME_STARTED
        runner = await original_start(bot)
        if not _RUNTIME_STARTED:
            _RUNTIME_STARTED = True
            core.spawn_background_task(_runtime_loop(core, bot))
        return runner

    core.start_webapp_server = start_with_event_runtime

    @core.router.message(Command("event", "events", "reality_event"))
    async def cmd_event(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        await core.db.upsert_player(message.chat.id, message.from_user)
        event = await _active_event(core, message.chat.id)
        if event is None:
            await message.answer("🌠 Сегодня событие реальности ещё не запущено.")
            return
        await _ensure_participant(core, str(event["event_id"]), message.from_user.id)
        await message.answer(await _event_text(core, event, message.from_user.id))

    original_commands = core.group_bot_commands

    def commands_with_events() -> list[BotCommand]:
        commands = original_commands()
        if not any(command.command == "event" for command in commands):
            commands.insert(
                next((i + 1 for i, command in enumerate(commands) if command.command == "hero_day"), len(commands)),
                BotCommand(command="event", description="Текущее событие реальности"),
            )
        return commands

    core.group_bot_commands = commands_with_events
