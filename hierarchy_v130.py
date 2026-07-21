from __future__ import annotations

import html
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message

import career_model_v120 as career
import government_v127 as government


VERSION = "Reality 130 · Иерархия реальности"
APP_DIR = Path(__file__).resolve().parent / "hierarchyapp_v130"
PREFIX = "hierarchy_"
ACTIVE_WINDOW_SECONDS = 14 * 24 * 60 * 60

ROLE_SPECS = (
    (career.CAREER_CENTER, "🌌", "Центр Вселенной"),
    (career.CAREER_HERO, "👑", "Главный герой"),
    (career.CAREER_SECONDARY, "🎭", "Второстепенная роль"),
    (career.CAREER_EXTRAS, "👥", "Массовка"),
    (career.CAREER_DUST, "🌫", "Пыль"),
    (0, "🪑", "Декорация"),
)

OFFICE_ORDER = {
    "president": 0,
    "chair": 1,
    "deputy": 2,
    "finance": 3,
    "central_bank": 4,
    "oversight": 5,
    "supreme_court": 6,
    "prosecutor": 7,
    "auditor": 8,
    "cec": 9,
    "ombudsman": 10,
    "security": 11,
    "press": 12,
}


def _now() -> int:
    return int(time.time())


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _role(career_points: int) -> tuple[str, str]:
    value = max(0, int(career_points))
    for threshold, emoji, title in ROLE_SPECS:
        if value >= threshold:
            return emoji, title
    return "🪑", "Декорация"


def recommended_deputy_seats(active_count: int) -> int:
    active = max(1, int(active_count))
    if active <= 3:
        return 1
    if active <= 7:
        return 3
    if active <= 15:
        return 5
    return 7


async def active_user_count(core: Any, chat_id: int) -> int:
    conn = core.db._require_connection()
    cutoff = _now() - ACTIVE_WINDOW_SECONDS
    cursor = await conn.execute(
        """
        SELECT COUNT(*) amount
        FROM players p
        LEFT JOIN user_behavior b
          ON b.chat_id=p.chat_id AND b.user_id=p.user_id
        WHERE p.chat_id=?
          AND MAX(COALESCE(p.updated_at,0),COALESCE(b.updated_at,0))>=?
          AND (p.message_count>0 OR COALESCE(b.messages,0)>0)
        """,
        (int(chat_id), cutoff),
    )
    row = await cursor.fetchone()
    count = int(row["amount"] if row else 0)
    if count > 0:
        return count
    cursor = await conn.execute("SELECT COUNT(*) amount FROM players WHERE chat_id=?", (int(chat_id),))
    row = await cursor.fetchone()
    return max(1, int(row["amount"] if row else 1))


async def _ensure_schema(core: Any) -> None:
    if getattr(core, "_hierarchy_v130_schema_ready", False):
        return
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS hierarchy_rank_snapshots_v130(
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                date_key TEXT NOT NULL,
                rank INTEGER NOT NULL,
                power_score INTEGER NOT NULL,
                points INTEGER NOT NULL,
                career_points INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id,date_key)
            );
            CREATE INDEX IF NOT EXISTS idx_hierarchy_snapshot_chat_v130
            ON hierarchy_rank_snapshots_v130(chat_id,date_key,user_id);
            """
        )
        await conn.commit()
    core._hierarchy_v130_schema_ready = True


async def _table_exists(conn: Any, name: str) -> bool:
    cursor = await conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (str(name),),
    )
    return await cursor.fetchone() is not None


def _type_map(core: Any) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for item in getattr(core, "TODAY_TYPES", []):
        if isinstance(item, dict) and item.get("key"):
            result[str(item["key"])] = {
                "emoji": str(item.get("emoji") or "🎭"),
                "title": str(item.get("title") or item["key"]),
            }
    return result


def _norm(value: int | float, maximum: int | float) -> float:
    if float(maximum or 0) <= 0:
        return 0.0
    return max(0.0, min(1.0, float(value) / float(maximum)))


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add(
            (
                str(getattr(route, "method", "") or "").upper(),
                str(getattr(resource, "canonical", "") or ""),
            )
        )
    return result


def _link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_SHORT_NAME and core.BOT_PUBLIC_USERNAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/{core.WEBAPP_SHORT_NAME}"
            f"?startapp={PREFIX}{int(chat_id)}"
        )
    if core.WEBAPP_PUBLIC_URL:
        return (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/hierarchy-v130/"
            f"?chat_id={int(chat_id)}&build=130-{_now()}"
        )
    return ""


def _parse_chat_id(start_param: str | None, request: Any) -> int:
    raw = str(start_param or "")
    if raw.startswith(PREFIX):
        raw = raw[len(PREFIX):]
    else:
        raw = str(request.query.get("chat_id") or "")
    chat_id = _as_int(raw)
    if chat_id >= 0:
        raise ValueError("Иерархия доступна только для групповой беседы.")
    return chat_id


async def _auth(core: Any, request: Any) -> tuple[Any, int]:
    user, start_param = core._webapp_auth(request)
    if user is None:
        raise PermissionError(start_param or "Нет авторизации Telegram.")
    chat_id = _parse_chat_id(start_param, request)
    player = await core.db.get_player(chat_id, int(user.id))
    if player is None:
        raise PermissionError("Сначала используй бота в этой беседе.")
    return user, chat_id


async def _participant_state(core: Any, chat_id: int, viewer_id: int) -> dict[str, Any]:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    now = _now()
    cutoff = now - ACTIVE_WINDOW_SECONDS

    talent_exists = await _table_exists(conn, "talent_profiles")
    type_exists = await _table_exists(conn, "today_type_assignments")
    behavior_exists = await _table_exists(conn, "user_behavior")

    talent_join = (
        "LEFT JOIN talent_profiles tp ON tp.chat_id=p.chat_id AND tp.user_id=p.user_id"
        if talent_exists else ""
    )
    type_join = (
        "LEFT JOIN today_type_assignments tt ON tt.chat_id=p.chat_id AND tt.user_id=p.user_id AND tt.expires_at>?"
        if type_exists else ""
    )
    behavior_join = (
        "LEFT JOIN user_behavior b ON b.chat_id=p.chat_id AND b.user_id=p.user_id"
        if behavior_exists else ""
    )
    query_params: list[Any] = []
    if type_exists:
        query_params.append(now)
    query_params.append(int(chat_id))

    cursor = await conn.execute(
        f"""
        SELECT p.user_id,p.username,p.full_name,p.points,p.career_points,
               p.message_count,p.updated_at,
               {('COALESCE(tp.total_points,0)' if talent_exists else '0')} talent_total,
               {('COALESCE(tp.spent_points,0)' if talent_exists else '0')} talent_spent,
               {('COALESCE(tt.type_key,\'\')' if type_exists else "''")} type_key,
               {('COALESCE(b.messages,0)' if behavior_exists else 'p.message_count')} behavior_messages,
               {('COALESCE(b.replies_sent,0)' if behavior_exists else '0')} replies_sent,
               {('COALESCE(b.replies_received,0)' if behavior_exists else '0')} replies_received,
               {('COALESCE(b.reactions_received,0)' if behavior_exists else '0')} reactions_received,
               {('COALESCE(b.reactions_given,0)' if behavior_exists else '0')} reactions_given,
               {('COALESCE(b.positive_actions,0)' if behavior_exists else '0')} positive_actions,
               {('COALESCE(b.negative_actions,0)' if behavior_exists else '0')} negative_actions,
               {('COALESCE(b.top_checks,0)' if behavior_exists else '0')} top_checks,
               {('COALESCE(b.profile_checks,0)' if behavior_exists else '0')} profile_checks,
               {('COALESCE(b.inline_uses,0)' if behavior_exists else '0')} inline_uses,
               {('COALESCE(b.updated_at,0)' if behavior_exists else '0')} behavior_updated_at
        FROM players p
        {talent_join}
        {type_join}
        {behavior_join}
        WHERE p.chat_id=?
        ORDER BY p.career_points DESC,p.points DESC,p.message_count DESC
        """,
        tuple(query_params),
    )
    rows = list(await cursor.fetchall())

    talent_branches: dict[int, dict[str, int]] = {}
    if await _table_exists(conn, "talent_levels"):
        cursor = await conn.execute(
            """
            SELECT user_id,
              SUM(CASE WHEN skill_id LIKE 'damage%' THEN level ELSE 0 END) damage,
              SUM(CASE WHEN skill_id LIKE 'influence%' THEN level ELSE 0 END) influence,
              SUM(CASE WHEN skill_id LIKE 'defense%' THEN level ELSE 0 END) defense,
              SUM(CASE WHEN skill_id LIKE 'rewards%' THEN level ELSE 0 END) rewards
            FROM talent_levels WHERE chat_id=? GROUP BY user_id
            """,
            (int(chat_id),),
        )
        for row in await cursor.fetchall():
            talent_branches[int(row["user_id"])] = {
                "damage": int(row["damage"] or 0),
                "influence": int(row["influence"] or 0),
                "defense": int(row["defense"] or 0),
                "rewards": int(row["rewards"] or 0),
            }

    offices_by_user: dict[int, list[dict[str, Any]]] = {}
    government_rows: list[dict[str, Any]] = []
    if await _table_exists(conn, "government_offices_v127"):
        cursor = await conn.execute(
            """
            SELECT office_key,seat_no,user_id,trust,ends_at
            FROM government_offices_v127
            WHERE chat_id=? AND ends_at>?
            ORDER BY office_key,seat_no
            """,
            (int(chat_id), now),
        )
        for row in await cursor.fetchall():
            key = str(row["office_key"])
            spec = government.OFFICES.get(key, {"emoji": "🏛", "title": key})
            item = {
                "office_key": key,
                "seat_no": int(row["seat_no"]),
                "user_id": int(row["user_id"]),
                "emoji": str(spec.get("emoji") or "🏛"),
                "title": str(spec.get("title") or key),
                "trust": int(row["trust"] or 50),
                "ends_at": int(row["ends_at"]),
                "remaining": government._remaining(int(row["ends_at"])),
            }
            offices_by_user.setdefault(int(row["user_id"]), []).append(item)
            government_rows.append(item)

    bills: dict[int, int] = {}
    if await _table_exists(conn, "government_bills_v127"):
        cursor = await conn.execute(
            "SELECT author_id,COUNT(*) amount FROM government_bills_v127 WHERE chat_id=? GROUP BY author_id",
            (int(chat_id),),
        )
        bills = {int(row["author_id"]): int(row["amount"]) for row in await cursor.fetchall()}

    bill_votes: dict[int, int] = {}
    if await _table_exists(conn, "government_bill_votes_v127"):
        cursor = await conn.execute(
            """
            SELECT v.voter_id,COUNT(*) amount
            FROM government_bill_votes_v127 v
            JOIN government_bills_v127 b ON b.bill_id=v.bill_id
            WHERE b.chat_id=? GROUP BY v.voter_id
            """,
            (int(chat_id),),
        )
        bill_votes = {int(row["voter_id"]): int(row["amount"]) for row in await cursor.fetchall()}

    power_actions: dict[int, int] = {}
    if await _table_exists(conn, "government_power_log_v128"):
        cursor = await conn.execute(
            "SELECT actor_id,COUNT(*) amount FROM government_power_log_v128 WHERE chat_id=? GROUP BY actor_id",
            (int(chat_id),),
        )
        power_actions = {int(row["actor_id"]): int(row["amount"]) for row in await cursor.fetchall()}

    game_stats: dict[int, dict[str, int]] = {}
    cursor = await conn.execute(
        """
        SELECT user_id,
          SUM(CASE WHEN delta>0 THEN delta ELSE 0 END) won,
          SUM(CASE WHEN delta<0 THEN -delta ELSE 0 END) lost,
          SUM(CASE WHEN delta>0 THEN 1 ELSE 0 END) wins,
          SUM(CASE WHEN delta<0 THEN 1 ELSE 0 END) losses
        FROM score_log
        WHERE chat_id=? AND (
          lower(reason) LIKE '%game%' OR lower(reason) LIKE '%roulette%' OR
          lower(reason) LIKE '%casino%' OR lower(reason) LIKE '%ego_challenge%' OR
          lower(reason) LIKE '%heist%' OR lower(reason) LIKE '%hunter%' OR
          lower(reason) LIKE '%roof%' OR lower(reason) LIKE '%vault%' OR
          lower(reason) LIKE '%coin%' OR lower(reason) LIKE '%dice%'
        )
        GROUP BY user_id
        """,
        (int(chat_id),),
    )
    for row in await cursor.fetchall():
        game_stats[int(row["user_id"])] = {
            "won": int(row["won"] or 0),
            "lost": int(row["lost"] or 0),
            "wins": int(row["wins"] or 0),
            "losses": int(row["losses"] or 0),
        }

    types = _type_map(core)
    participants: list[dict[str, Any]] = []
    for row in rows:
        user_id = int(row["user_id"])
        last_activity = max(int(row["updated_at"] or 0), int(row["behavior_updated_at"] or 0))
        messages = max(int(row["message_count"] or 0), int(row["behavior_messages"] or 0))
        active = last_activity >= cutoff and messages > 0
        branches = talent_branches.get(user_id, {"damage": 0, "influence": 0, "defense": 0, "rewards": 0})
        office_items = offices_by_user.get(user_id, [])
        game = game_stats.get(user_id, {"won": 0, "lost": 0, "wins": 0, "losses": 0})
        role_emoji, role_title = _role(int(row["career_points"] or 0))
        type_key = str(row["type_key"] or "")
        type_spec = types.get(type_key, {})
        activity_score = (
            messages
            + int(row["replies_sent"] or 0) * 3
            + int(row["replies_received"] or 0) * 2
            + int(row["reactions_received"] or 0) * 4
            + int(row["reactions_given"] or 0)
            + int(row["positive_actions"] or 0) * 3
        )
        government_score = (
            len(office_items) * 40
            + bills.get(user_id, 0) * 12
            + bill_votes.get(user_id, 0) * 4
            + power_actions.get(user_id, 0) * 8
        )
        aura = max(1, min(1000, 100 + int(row["reactions_received"] or 0) * 8 + int(row["replies_received"] or 0) * 4 + int(row["positive_actions"] or 0) * 5))
        chsv = max(1, min(1000, 100 + int(row["top_checks"] or 0) * 5 + int(row["profile_checks"] or 0) * 3 + int(row["inline_uses"] or 0) + int(row["positive_actions"] or 0) * 2))
        participants.append(
            {
                "user_id": user_id,
                "username": str(row["username"] or ""),
                "name": str(row["full_name"] or f"ID {user_id}"),
                "points": int(row["points"] or 0),
                "career_points": int(row["career_points"] or 0),
                "role_emoji": role_emoji,
                "role_title": role_title,
                "type_key": type_key,
                "type_emoji": str(type_spec.get("emoji") or ""),
                "type_title": str(type_spec.get("title") or ""),
                "talent_total": int(row["talent_total"] or 0),
                "talent_spent": int(row["talent_spent"] or 0),
                "talent_available": max(0, int(row["talent_total"] or 0) - int(row["talent_spent"] or 0)),
                "talent_branches": branches,
                "offices": office_items,
                "government_actions": power_actions.get(user_id, 0),
                "bills_authored": bills.get(user_id, 0),
                "bill_votes": bill_votes.get(user_id, 0),
                "government_score": government_score,
                "messages": messages,
                "replies_sent": int(row["replies_sent"] or 0),
                "replies_received": int(row["replies_received"] or 0),
                "reactions_received": int(row["reactions_received"] or 0),
                "activity_score": activity_score,
                "game_won": game["won"],
                "game_lost": game["lost"],
                "game_profit": game["won"] - game["lost"],
                "game_wins": game["wins"],
                "game_losses": game["losses"],
                "aura": aura,
                "chsv": chsv,
                "active": active,
                "last_activity": last_activity,
            }
        )

    maxima = {
        "career": max([item["career_points"] for item in participants] or [1]),
        "points": max([max(0, item["points"]) for item in participants] or [1]),
        "talents": max([item["talent_spent"] for item in participants] or [1]),
        "government": max([item["government_score"] for item in participants] or [1]),
        "activity": max([item["activity_score"] for item in participants] or [1]),
        "games": max([max(0, item["game_profit"]) for item in participants] or [1]),
    }
    for item in participants:
        score = 1000 * (
            0.35 * _norm(item["career_points"], maxima["career"])
            + 0.25 * _norm(max(0, item["points"]), maxima["points"])
            + 0.15 * _norm(item["talent_spent"], maxima["talents"])
            + 0.10 * _norm(item["government_score"], maxima["government"])
            + 0.10 * _norm(item["activity_score"], maxima["activity"])
            + 0.05 * _norm(max(0, item["game_profit"]), maxima["games"])
        )
        item["power_score"] = int(round(score))

    participants.sort(
        key=lambda item: (
            -int(item["power_score"]),
            -int(item["career_points"]),
            -int(item["points"]),
            int(item["user_id"]),
        )
    )

    old_date = datetime.fromtimestamp(now - 6 * 86400, timezone.utc).date().isoformat()
    today = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
    for rank, item in enumerate(participants, 1):
        item["rank"] = rank
        cursor = await conn.execute(
            """
            SELECT rank FROM hierarchy_rank_snapshots_v130
            WHERE chat_id=? AND user_id=? AND date_key<=?
            ORDER BY date_key DESC LIMIT 1
            """,
            (int(chat_id), int(item["user_id"]), old_date),
        )
        old = await cursor.fetchone()
        item["rank_change"] = int(old["rank"]) - rank if old else 0

    async with core.db.lock:
        await conn.executemany(
            """
            INSERT INTO hierarchy_rank_snapshots_v130(
              chat_id,user_id,date_key,rank,power_score,points,career_points,created_at
            ) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(chat_id,user_id,date_key) DO UPDATE SET
              rank=excluded.rank,power_score=excluded.power_score,
              points=excluded.points,career_points=excluded.career_points,
              created_at=excluded.created_at
            """,
            [
                (
                    int(chat_id), int(item["user_id"]), today, int(item["rank"]),
                    int(item["power_score"]), int(item["points"]),
                    int(item["career_points"]), now,
                )
                for item in participants
            ],
        )
        await conn.commit()

    names = {int(item["user_id"]): str(item["name"]) for item in participants}
    government_rows.sort(key=lambda item: (OFFICE_ORDER.get(str(item["office_key"]), 99), int(item["seat_no"])))
    for item in government_rows:
        item["name"] = names.get(int(item["user_id"]), f"ID {item['user_id']}")

    active = sum(1 for item in participants if item["active"])
    active = active or min(len(participants), 1)
    return {
        "ok": True,
        "version": VERSION,
        "chat": {"chat_id": int(chat_id), "title": await government._chat_title(core.bot if hasattr(core, 'bot') else None, chat_id) if False else str(chat_id)},
        "user_id": int(viewer_id),
        "participants": participants,
        "government": government_rows,
        "summary": {
            "total": len(participants),
            "active": active,
            "total_points": sum(int(item["points"]) for item in participants),
            "total_career": sum(int(item["career_points"]) for item in participants),
            "deputy_seats": recommended_deputy_seats(active),
        },
    }


async def _state(core: Any, bot: Any, chat_id: int, viewer_id: int) -> dict[str, Any]:
    state = await _participant_state(core, chat_id, viewer_id)
    state["chat"]["title"] = await government._chat_title(bot, chat_id)
    return state


def install_hierarchy_v130(core: Any) -> None:
    if getattr(core, "_hierarchy_v130_installed", False):
        return
    core._hierarchy_v130_installed = True
    core.HIERARCHY_VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_hierarchy(self: Any) -> None:
        await original_connect(self)
        core._hierarchy_v130_schema_ready = False
        await _ensure_schema(core)

    core.Database.connect = connect_with_hierarchy

    async def state_api(request: Any):
        try:
            user, chat_id = await _auth(core, request)
            return core.web.json_response(
                await _state(core, request.app["bot"], chat_id, int(user.id))
            )
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            core.logging.exception("Ошибка Иерархии реальности Reality 130")
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    def file_response(path: Path):
        return core.web.FileResponse(
            path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Hierarchy": "reality-130",
            },
        )

    async def index(_: Any):
        return file_response(APP_DIR / "index.html")

    async def asset(request: Any):
        name = str(request.match_info["name"])
        if name not in {"app.css", "app.js"}:
            raise core.web.HTTPNotFound()
        return file_response(APP_DIR / name)

    @core.web.middleware
    async def hierarchy_entry(request: Any, handler: Any):
        if request.method.upper() == "GET":
            start_param = str(
                request.query.get("tgWebAppStartParam")
                or request.query.get("startapp")
                or ""
            )
            if start_param.startswith(PREFIX):
                return await index(request)
        return await handler(request)

    previous_application = core.web.Application

    def application_with_hierarchy(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [hierarchy_entry, *middlewares]
        return previous_application(*args, **kwargs)

    core.web.Application = application_with_hierarchy
    original_start = core.start_webapp_server

    async def start_with_hierarchy(bot: Any):
        if not APP_DIR.is_dir():
            raise RuntimeError(f"Не найдена папка Иерархии Reality 130: {APP_DIR}")
        original_runner = core.web.AppRunner

        def runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/hierarchy-v130") not in keys:
                app.router.add_get("/hierarchy-v130", index)
            if ("GET", "/hierarchy-v130/") not in keys:
                app.router.add_get("/hierarchy-v130/", index)
            if ("GET", "/hierarchy-v130/{name:app\\.css|app\\.js}") not in keys:
                app.router.add_get("/hierarchy-v130/{name:app\\.css|app\\.js}", asset)
            if ("GET", "/hierarchy-v130/api/state") not in keys:
                app.router.add_get("/hierarchy-v130/api/state", state_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_factory
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_hierarchy

    original_commands = core.group_bot_commands

    def commands_with_hierarchy() -> list[BotCommand]:
        commands = [item for item in original_commands() if item.command != "hierarchy"]
        position = next(
            (index + 1 for index, item in enumerate(commands) if item.command == "government"),
            len(commands),
        )
        commands.insert(
            position,
            BotCommand(
                command="hierarchy",
                description="Топ, участники, таланты, типажи и власть",
            ),
        )
        return commands

    core.group_bot_commands = commands_with_hierarchy

    handlers = core.router.message.handlers
    handlers[:] = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") != "cmd_hierarchy_v130"
    ]

    @core.router.message(Command("hierarchy", "ratings", "participants"))
    async def cmd_hierarchy_v130(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = _link(core, chat_id)
        if not link:
            await message.answer("⚠️ Адрес Mini App «Иерархия реальности» не настроен.")
            return
        active = await active_user_count(core, chat_id)
        deputies = recommended_deputy_seats(active)
        await message.answer(
            "👑 <b>ИЕРАРХИЯ РЕАЛЬНОСТИ · REALITY 130</b>\n\n"
            "Общий топ, паспорта участников, карьерные звания, типажи, Древо "
            "талантов, игры, активность и государственные должности в одном приложении.\n\n"
            f"Сейчас активно: <b>{active}</b>. Рекомендуемый состав Госдумы: "
            f"<b>{deputies} депутата</b>.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="👑 ОТКРЫТЬ ИЕРАРХИЮ",
                        url=link,
                    )
                ]]
            ),
        )

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_hierarchy_v130"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
