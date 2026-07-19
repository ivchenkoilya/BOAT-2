from __future__ import annotations

import contextvars
import html
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import talent_system

LOGGER = logging.getLogger(__name__)
VERSION = "Reality 85 · Быстрое древо знаний"
START_POINTS = 5
POINT_STEP = 500
GAME_SHARE = 0.20
GAME_WEEKLY_CAREER_CAP = 2_000
TASK_WEEKLY_CAP = 4
ACTIVITY_DAY_STEPS = (2, 4, 6)
BOSS_TOP_TREE = (6, 5, 4)
BOSS_PARTICIPATION_TREE = 3
BOSS_WEEKLY_CAP = 15
BOSS_FINISHER_TREE = 1

GAME_WORDS = ("coin", "dice", "roulette", "game", "fate", "heist", "rooftop", "roof", "casino", "bet")
TASK_WORDS = ("task", "mission")
ACTIVITY_WORDS = ("message", "reaction", "voice", "reply", "activity", "media", "sticker")
EXCLUDED_WORDS = ("admin", "transfer", "restore", "refund", "compensation", "hero_day", "sabotage", "impeachment", "rebellion", "boss")
_guard: contextvars.ContextVar[bool] = contextvars.ContextVar("knowledge_v85_guard", default=False)


def _week() -> str:
    iso = datetime.now(timezone.utc).date().isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _day() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _has(reason: str, words: tuple[str, ...]) -> bool:
    value = str(reason or "").casefold()
    return any(word in value for word in words)


def _entitled(career: int) -> int:
    return START_POINTS + max(0, int(career)) // POINT_STEP


def _legacy(balance: int) -> int:
    return min(15, 3 + max(0, int(balance)) // 500)


def _score_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[int, int, int, str] | None:
    try:
        return (
            int(kwargs["chat_id"] if "chat_id" in kwargs else args[0]),
            int(kwargs["user_id"] if "user_id" in kwargs else args[1]),
            int(kwargs["delta"] if "delta" in kwargs else args[2]),
            str(kwargs["reason"] if "reason" in kwargs else args[3]),
        )
    except (IndexError, KeyError, TypeError, ValueError):
        return None


async def _schema(db: Any) -> None:
    conn = db._require_connection()
    async with db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_economy_v85(
                chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
                career INTEGER NOT NULL DEFAULT 0,entitled INTEGER NOT NULL DEFAULT 0,
                game_wins INTEGER NOT NULL DEFAULT 0,tasks INTEGER NOT NULL DEFAULT 0,
                boss_wins INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id));
            CREATE TABLE IF NOT EXISTS knowledge_week_v85(
                chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,week_key TEXT NOT NULL,
                game_career INTEGER NOT NULL DEFAULT 0,task_points INTEGER NOT NULL DEFAULT 0,
                activity_points INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id,week_key));
            CREATE TABLE IF NOT EXISTS knowledge_days_v85(
                chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,week_key TEXT NOT NULL,
                day_key TEXT NOT NULL,created_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id,week_key,day_key));
            CREATE TABLE IF NOT EXISTS knowledge_achievements_v85(
                chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,key TEXT NOT NULL,
                points INTEGER NOT NULL,awarded_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id,key));
            CREATE TABLE IF NOT EXISTS knowledge_boss_events_v85(
                boss_id TEXT NOT NULL,user_id INTEGER NOT NULL,chat_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,PRIMARY KEY(boss_id,user_id));
            CREATE TABLE IF NOT EXISTS knowledge_finisher_events_v85(
                boss_id TEXT NOT NULL,user_id INTEGER NOT NULL,created_at INTEGER NOT NULL,
                PRIMARY KEY(boss_id,user_id));
            CREATE TABLE IF NOT EXISTS knowledge_weekly(
                chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,week_key TEXT NOT NULL,
                tree_points INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id,week_key));
            """
        )
        await conn.commit()


async def _achievement(conn: Any, chat_id: int, user_id: int, key: str, points: int, now: int) -> int:
    cursor = await conn.execute(
        "INSERT OR IGNORE INTO knowledge_achievements_v85(chat_id,user_id,key,points,awarded_at) VALUES(?,?,?,?,?)",
        (chat_id, user_id, key, points, now),
    )
    return points if cursor.rowcount > 0 else 0


async def _ensure(db: Any, chat_id: int, user_id: int, base_sync: Any, synced: bool = False) -> None:
    player = await db.get_player(chat_id, user_id)
    if player is None:
        return
    if not synced:
        await base_sync(db, chat_id, user_id)
    conn = db._require_connection()
    now = int(time.time())
    seed = max(0, int(player.points))
    target = _entitled(seed)
    async with db.lock:
        cursor = await conn.execute("SELECT 1 FROM knowledge_economy_v85 WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        if await cursor.fetchone() is not None:
            return
        await conn.execute(
            "INSERT INTO knowledge_economy_v85(chat_id,user_id,career,entitled,updated_at) VALUES(?,?,?,?,?)",
            (chat_id, user_id, seed, target, now),
        )
        grant = max(0, target - _legacy(seed))
        if grant:
            await conn.execute(
                "UPDATE talent_profiles SET total_points=total_points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (grant, now, chat_id, user_id),
            )
        await conn.commit()


async def _positive(core: Any, db: Any, chat_id: int, user_id: int, delta: int, reason: str) -> None:
    if delta <= 0 or _has(reason, EXCLUDED_WORDS):
        return
    is_game = _has(reason, GAME_WORDS)
    is_task = _has(reason, TASK_WORDS)
    is_activity = _has(reason, ACTIVITY_WORDS)
    conn = db._require_connection()
    now, week = int(time.time()), _week()
    async with db.lock:
        cursor = await conn.execute(
            "SELECT career,entitled,game_wins,tasks FROM knowledge_economy_v85 WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        profile = await cursor.fetchone()
        if profile is None:
            return
        await conn.execute(
            "INSERT OR IGNORE INTO knowledge_week_v85(chat_id,user_id,week_key,updated_at) VALUES(?,?,?,?)",
            (chat_id, user_id, week, now),
        )
        cursor = await conn.execute(
            "SELECT game_career,task_points,activity_points FROM knowledge_week_v85 WHERE chat_id=? AND user_id=? AND week_key=?",
            (chat_id, user_id, week),
        )
        weekly = await cursor.fetchone()
        game_career = int(weekly["game_career"])
        task_points = int(weekly["task_points"])
        activity_points = int(weekly["activity_points"])
        game_wins = int(profile["game_wins"])
        tasks = int(profile["tasks"])
        direct = 0
        career_add = int(delta)

        if is_game:
            requested = max(0, int(delta * GAME_SHARE))
            career_add = min(requested, max(0, GAME_WEEKLY_CAREER_CAP - game_career))
            game_career += career_add
            game_wins += 1
            if game_wins >= 25:
                direct += await _achievement(conn, chat_id, user_id, "game25", 2, now)
        if is_task:
            tasks += 1
            if task_points < TASK_WEEKLY_CAP:
                task_points += 1
                direct += 1
            if tasks >= 50:
                direct += await _achievement(conn, chat_id, user_id, "tasks50", 3, now)
        if is_activity:
            await conn.execute(
                "INSERT OR IGNORE INTO knowledge_days_v85(chat_id,user_id,week_key,day_key,created_at) VALUES(?,?,?,?,?)",
                (chat_id, user_id, week, _day(), now),
            )
            cursor = await conn.execute(
                "SELECT COUNT(*) amount FROM knowledge_days_v85 WHERE chat_id=? AND user_id=? AND week_key=?",
                (chat_id, user_id, week),
            )
            row = await cursor.fetchone()
            deserved = sum(int(row["amount"]) >= threshold for threshold in ACTIVITY_DAY_STEPS)
            if deserved > activity_points:
                direct += deserved - activity_points
                activity_points = deserved

        career = int(profile["career"]) + max(0, career_add)
        entitled = _entitled(career)
        career_grant = max(0, entitled - int(profile["entitled"]))
        cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        player = await cursor.fetchone()
        if player is not None and int(player["points"]) >= int(core.HERO_MIN_POINTS):
            direct += await _achievement(conn, chat_id, user_id, "hero", 2, now)

        await conn.execute(
            "UPDATE knowledge_economy_v85 SET career=?,entitled=?,game_wins=?,tasks=?,updated_at=? WHERE chat_id=? AND user_id=?",
            (career, entitled, game_wins, tasks, now, chat_id, user_id),
        )
        await conn.execute(
            "UPDATE knowledge_week_v85 SET game_career=?,task_points=?,activity_points=?,updated_at=? WHERE chat_id=? AND user_id=? AND week_key=?",
            (game_career, task_points, activity_points, now, chat_id, user_id, week),
        )
        grant = career_grant + direct
        if grant:
            await conn.execute(
                "UPDATE talent_profiles SET total_points=total_points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (grant, now, chat_id, user_id),
            )
        await conn.commit()


async def _boss_achievement(core: Any, db: Any, boss_id: str, chat_id: int, user_id: int) -> None:
    conn = db._require_connection()
    now = int(time.time())
    async with db.lock:
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO knowledge_boss_events_v85(boss_id,user_id,chat_id,created_at) VALUES(?,?,?,?)",
            (boss_id, user_id, chat_id, now),
        )
        if cursor.rowcount <= 0:
            return
        await conn.execute(
            "UPDATE knowledge_economy_v85 SET boss_wins=boss_wins+1,updated_at=? WHERE chat_id=? AND user_id=?",
            (now, chat_id, user_id),
        )
        cursor = await conn.execute(
            "SELECT boss_wins FROM knowledge_economy_v85 WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        row = await cursor.fetchone()
        wins = int(row["boss_wins"]) if row else 0
        grant = await _achievement(conn, chat_id, user_id, "boss1", 1, now)
        if wins >= 10:
            grant += await _achievement(conn, chat_id, user_id, "boss10", 3, now)
        cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        player = await cursor.fetchone()
        if player is not None and int(player["points"]) >= int(core.HERO_MIN_POINTS):
            grant += await _achievement(conn, chat_id, user_id, "hero", 2, now)
        if grant:
            await conn.execute(
                "UPDATE talent_profiles SET total_points=total_points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (grant, now, chat_id, user_id),
            )
        await conn.commit()


async def _finisher_point(db: Any, boss_id: str, chat_id: int, user_id: int) -> int:
    if not user_id:
        return 0
    conn = db._require_connection()
    now, week = int(time.time()), _week()
    async with db.lock:
        cursor = await conn.execute(
            "SELECT tree_points_requested,tree_points_awarded,is_finisher FROM boss_v64_rewards WHERE boss_id=? AND user_id=?",
            (boss_id, user_id),
        )
        reward = await cursor.fetchone()
        if reward is None or not int(reward["is_finisher"]):
            return 0
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO knowledge_finisher_events_v85(boss_id,user_id,created_at) VALUES(?,?,?)",
            (boss_id, user_id, now),
        )
        if cursor.rowcount <= 0:
            return 0
        cursor = await conn.execute(
            "SELECT tree_points FROM knowledge_weekly WHERE chat_id=? AND user_id=? AND week_key=?",
            (chat_id, user_id, week),
        )
        row = await cursor.fetchone()
        weekly = int(row["tree_points"]) if row else 0
        extra = min(BOSS_FINISHER_TREE, max(0, BOSS_WEEKLY_CAP - weekly))
        await conn.execute(
            "UPDATE boss_v64_rewards SET tree_points_requested=tree_points_requested+?,tree_points_awarded=tree_points_awarded+? WHERE boss_id=? AND user_id=?",
            (BOSS_FINISHER_TREE, extra, boss_id, user_id),
        )
        if extra:
            await conn.execute(
                "UPDATE knowledge_weekly SET tree_points=tree_points+?,updated_at=? WHERE chat_id=? AND user_id=? AND week_key=?",
                (extra, now, chat_id, user_id, week),
            )
            await conn.execute(
                "UPDATE talent_profiles SET total_points=total_points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (extra, now, chat_id, user_id),
            )
        await conn.commit()
        return extra


def install_knowledge_economy_v85(core: Any) -> None:
    if getattr(core, "_knowledge_economy_v85_installed", False):
        return
    core._knowledge_economy_v85_installed = True
    core.BOT_VERSION = VERSION
    base_sync = talent_system.sync_profile

    old_connect = core.Database.connect
    async def connect(self: Any) -> None:
        await old_connect(self)
        await _schema(self)
    core.Database.connect = connect

    async def sync(db: Any, chat_id: int, user_id: int) -> dict[str, int]:
        await base_sync(db, chat_id, user_id)
        await _ensure(db, chat_id, user_id, base_sync, True)
        return await base_sync(db, chat_id, user_id)
    talent_system.sync_profile = sync

    for name in ("add_points", "add_points_with_balance"):
        old = getattr(core.Database, name, None)
        if old is None:
            continue
        async def wrapper(self: Any, *args: Any, __old=old, **kwargs: Any):
            if _guard.get():
                return await __old(self, *args, **kwargs)
            parsed = _score_args(args, kwargs)
            if parsed is None:
                return await __old(self, *args, **kwargs)
            chat_id, user_id, delta, reason = parsed
            if delta > 0:
                await _ensure(self, chat_id, user_id, base_sync)
            token = _guard.set(True)
            try:
                result = await __old(self, *args, **kwargs)
            finally:
                _guard.reset(token)
            if delta > 0:
                try:
                    await _positive(core, self, chat_id, user_id, delta, reason)
                except Exception:
                    LOGGER.exception("Ошибка экономики древа: chat=%s user=%s reason=%s", chat_id, user_id, reason)
            return result
        setattr(core.Database, name, wrapper)

    import raid_v64_direct_tree as raid
    raid.TOP_TREE_POINTS = BOSS_TOP_TREE
    raid.PARTICIPATION_TREE_POINTS = BOSS_PARTICIPATION_TREE
    raid.WEEKLY_TREE_POINT_CAP = BOSS_WEEKLY_CAP

    old_resolve = core.resolve_boss_victory
    async def resolve(boss_id: str, bot: Any) -> None:
        before = await core.db.get_boss(boss_id)
        if before is None:
            return await old_resolve(boss_id, bot)
        chat_id = int(before["chat_id"])
        finisher = int(before["last_attacker_id"] or 0)
        await old_resolve(boss_id, bot)
        if finisher:
            extra = await _finisher_point(core.db, boss_id, chat_id, finisher)
            if extra:
                player = await core.db.get_player(chat_id, finisher)
                name = core.player_link(player) if player is not None else html.escape(str(finisher))
                await bot.send_message(
                    chat_id,
                    f"💀 {name} нанёс последний удар и получает ещё <b>+{extra}</b> очко древа.",
                )
        conn = core.db._require_connection()
        cursor = await conn.execute("SELECT user_id FROM boss_v64_rewards WHERE boss_id=?", (boss_id,))
        for row in await cursor.fetchall():
            user_id = int(row["user_id"])
            await _ensure(core.db, chat_id, user_id, base_sync)
            await _boss_achievement(core, core.db, boss_id, chat_id, user_id)
    core.resolve_boss_victory = resolve

    old_state = core.build_boss_web_state
    async def state(boss_id: str, user_id: int) -> dict[str, Any]:
        result = await old_state(boss_id, user_id)
        if result.get("ok"):
            rules = result.setdefault("reward_rules", {})
            rules.update({
                "top_tree_points": list(BOSS_TOP_TREE),
                "participation_tree_points": BOSS_PARTICIPATION_TREE,
                "finisher_tree_points": BOSS_FINISHER_TREE,
                "weekly_tree_point_cap": BOSS_WEEKLY_CAP,
            })
        return result
    core.build_boss_web_state = state

    old_file = core.web.FileResponse
    def file_response(path: Any, *args: Any, **kwargs: Any):
        result = old_file(path, *args, **kwargs)
        file_path = Path(path)
        if file_path.name == "index.html" and file_path.parent.name == "talent_app":
            old = "Ты получаешь 3 стартовых очка и ещё по одному за каждые 500 очков влияния. Уже открытые очки не отнимаются при потере влияния."
            new = "Ты получаешь 5 стартовых очков и ещё по одному за каждые 500 карьерного влияния без лимита. Босс, задания, активные дни и достижения дают дополнительные очки, а от мини-игр в прогресс идёт 20% положительной награды."
            try:
                result.text = str(result.text).replace(old, new)
            except Exception:
                LOGGER.exception("Не удалось обновить подсказку древа")
        return result
    core.web.FileResponse = file_response
