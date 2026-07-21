from __future__ import annotations

import html
import json
import math
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message

import sanctions_v126 as sanctions


VERSION = "Reality 127 · Государство реальности"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
GOV_PREFIX = "government_"
TERM_SECONDS = 7 * 24 * 60 * 60
NOMINATION_SECONDS = 24 * 60 * 60
VOTING_SECONDS = 24 * 60 * 60
BILL_VOTING_SECONDS = 12 * 60 * 60
PRESIDENT_REVIEW_SECONDS = 12 * 60 * 60
DEPUTY_SEATS = 5
MOSCOW = timezone(timedelta(hours=3))
_RUNTIME_STARTED = False

OFFICES: dict[str, dict[str, Any]] = {
    "president": {"emoji": "🦅", "title": "Президент реальности", "threshold": 900_000, "seats": 1},
    "chair": {"emoji": "🏛", "title": "Председатель Госдумы", "threshold": 500_000, "seats": 1},
    "deputy": {"emoji": "🗳", "title": "Депутат Госдумы", "threshold": 200_000, "seats": DEPUTY_SEATS},
    "finance": {"emoji": "💰", "title": "Министр финансов", "threshold": 500_000, "seats": 1},
    "oversight": {"emoji": "🚨", "title": "Глава Надзора за гандонами", "threshold": 500_000, "seats": 1},
}

BILL_TYPES: dict[str, dict[str, str]] = {
    "general": {"emoji": "📜", "title": "Обычный закон"},
    "tax_policy": {"emoji": "🏦", "title": "Налоговая политика"},
    "budget": {"emoji": "💸", "title": "Бюджетная выплата"},
    "appointment": {"emoji": "🎖", "title": "Назначение чиновника"},
    "sanction": {"emoji": "🚫", "title": "Санкционное постановление"},
}


def _now() -> int:
    return int(time.time())


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json(value: Any, default: Any) -> Any:
    if isinstance(value, type(default)):
        return value
    try:
        parsed = json.loads(str(value or ""))
        return parsed if isinstance(parsed, type(default)) else default
    except Exception:
        return default


def _date_text(timestamp: int) -> str:
    if int(timestamp or 0) <= 0:
        return "не определено"
    return datetime.fromtimestamp(int(timestamp), MOSCOW).strftime("%d.%m.%Y · %H:%M МСК")


def _remaining(timestamp: int) -> str:
    seconds = max(0, int(timestamp or 0) - _now())
    if seconds <= 0:
        return "завершено"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days} д. {hours} ч."
    if hours:
        return f"{hours} ч. {minutes} мин."
    return f"{max(1, minutes)} мин."


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        canonical = str(getattr(resource, "canonical", "") or "")
        result.add((str(getattr(route, "method", "") or "").upper(), canonical))
    return result


def _government_link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_SHORT_NAME and core.BOT_PUBLIC_USERNAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/{core.WEBAPP_SHORT_NAME}"
            f"?startapp={GOV_PREFIX}{int(chat_id)}"
        )
    if core.WEBAPP_PUBLIC_URL:
        return (
            f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/government-v127/"
            f"?chat_id={int(chat_id)}&build=127-{_now()}"
        )
    return ""


def _parse_chat_id(start_param: str | None, data: dict[str, Any], request: Any) -> int:
    raw = str(start_param or "")
    if raw.startswith(GOV_PREFIX):
        raw = raw[len(GOV_PREFIX):]
    else:
        raw = str(data.get("chat_id") or request.query.get("chat_id") or "")
    chat_id = _as_int(raw)
    if chat_id >= 0:
        raise ValueError("Государство привязывается только к групповой беседе.")
    return chat_id


async def _payload(request: Any) -> dict[str, Any]:
    try:
        value = await request.json()
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


async def _auth(core: Any, request: Any) -> tuple[Any, int, dict[str, Any]]:
    user, start_param = core._webapp_auth(request)
    if user is None:
        raise PermissionError(start_param or "Нет авторизации Telegram.")
    data = await _payload(request)
    chat_id = _parse_chat_id(start_param, data, request)
    player = await core.db.get_player(chat_id, int(user.id))
    if player is None:
        raise PermissionError("Сначала используй бота в этой беседе.")
    return user, chat_id, data


async def _ensure_state(core: Any, chat_id: int) -> Any:
    conn = core.db._require_connection()
    now = _now()
    await conn.execute(
        """
        INSERT OR IGNORE INTO government_state_v127(
            chat_id,treasury,tax_enabled,tax_day,tax_hour,next_tax_at,
            wealth_1,wealth_2,wealth_3,rate_1_bps,rate_2_bps,rate_3_bps,rate_4_bps,
            max_tax,bill_seq,law_seq,created_at,updated_at
        ) VALUES(?,0,0,0,10,0,10000,50000,200000,0,200,400,600,30000,0,0,?,?)
        """,
        (int(chat_id), now, now),
    )
    await conn.commit()
    cursor = await conn.execute("SELECT * FROM government_state_v127 WHERE chat_id=?", (int(chat_id),))
    return await cursor.fetchone()


async def _chat_title(bot: Any, chat_id: int) -> str:
    try:
        chat = await bot.get_chat(int(chat_id))
        return str(chat.title or chat.full_name or chat_id)
    except Exception:
        return str(chat_id)


async def _player_dict(core: Any, chat_id: int, user_id: int) -> dict[str, Any] | None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """SELECT user_id,username,full_name,points,career_points,message_count
           FROM players WHERE chat_id=? AND user_id=? LIMIT 1""",
        (int(chat_id), int(user_id)),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "user_id": int(row["user_id"]),
        "username": str(row["username"] or ""),
        "name": str(row["full_name"] or f"ID {row['user_id']}"),
        "points": int(row["points"] or 0),
        "career_points": int(row["career_points"] or 0),
        "message_count": int(row["message_count"] or 0),
    }


async def _has_active_sanctions(core: Any, chat_id: int, user_id: int) -> bool:
    try:
        return bool(await sanctions.active_sanctions(core, int(chat_id), int(user_id)))
    except Exception:
        return False


async def _office_rows(core: Any, chat_id: int) -> list[Any]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT o.*,p.username,p.full_name,p.points,p.career_points
        FROM government_offices_v127 o
        LEFT JOIN players p ON p.chat_id=o.chat_id AND p.user_id=o.user_id
        WHERE o.chat_id=? AND o.ends_at>?
        ORDER BY CASE o.office_key WHEN 'president' THEN 0 WHEN 'chair' THEN 1
          WHEN 'deputy' THEN 2 WHEN 'finance' THEN 3 ELSE 4 END,o.seat_no
        """,
        (int(chat_id), _now()),
    )
    return list(await cursor.fetchall())


async def _user_offices(core: Any, chat_id: int, user_id: int) -> list[str]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """SELECT office_key FROM government_offices_v127
           WHERE chat_id=? AND user_id=? AND ends_at>? ORDER BY office_key""",
        (int(chat_id), int(user_id), _now()),
    )
    return [str(row["office_key"]) for row in await cursor.fetchall()]


async def _holds(core: Any, chat_id: int, user_id: int, *keys: str) -> bool:
    offices = await _user_offices(core, chat_id, user_id)
    return any(key in offices for key in keys)


async def _deputy_ids(core: Any, chat_id: int) -> list[int]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """SELECT DISTINCT user_id FROM government_offices_v127
           WHERE chat_id=? AND office_key IN ('deputy','chair') AND ends_at>?""",
        (int(chat_id), _now()),
    )
    return [int(row["user_id"]) for row in await cursor.fetchall()]


def _office_dict(row: Any) -> dict[str, Any]:
    key = str(row["office_key"])
    spec = OFFICES.get(key, {"emoji": "🏛", "title": key})
    return {
        "office_key": key,
        "seat_no": int(row["seat_no"]),
        "emoji": spec["emoji"],
        "title": spec["title"],
        "user_id": int(row["user_id"]),
        "username": str(row["username"] or ""),
        "name": str(row["full_name"] or f"ID {row['user_id']}"),
        "career_points": int(row["career_points"] or 0),
        "trust": int(row["trust"] or 50),
        "starts_at": int(row["starts_at"]),
        "ends_at": int(row["ends_at"]),
        "remaining": _remaining(int(row["ends_at"])),
    }


async def _eligible_users(core: Any, chat_id: int, limit: int = 80) -> list[dict[str, Any]]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """SELECT user_id,username,full_name,points,career_points,message_count
           FROM players WHERE chat_id=?
           ORDER BY career_points DESC,message_count DESC,points DESC LIMIT ?""",
        (int(chat_id), int(limit)),
    )
    return [
        {
            "user_id": int(row["user_id"]),
            "username": str(row["username"] or ""),
            "name": str(row["full_name"] or f"ID {row['user_id']}"),
            "points": int(row["points"] or 0),
            "career_points": int(row["career_points"] or 0),
            "message_count": int(row["message_count"] or 0),
        }
        for row in await cursor.fetchall()
    ]


async def _next_number(core: Any, chat_id: int, field: str) -> int:
    if field not in {"bill_seq", "law_seq"}:
        raise ValueError("Неизвестная нумерация.")
    conn = core.db._require_connection()
    async with core.db.lock:
        await _ensure_state(core, chat_id)
        await conn.execute(
            f"UPDATE government_state_v127 SET {field}={field}+1,updated_at=? WHERE chat_id=?",
            (_now(), int(chat_id)),
        )
        cursor = await conn.execute(
            f"SELECT {field} value FROM government_state_v127 WHERE chat_id=?", (int(chat_id),)
        )
        row = await cursor.fetchone()
        await conn.commit()
    return int(row["value"] if row else 1)


async def _active_election(core: Any, chat_id: int, office_key: str = "") -> Any | None:
    conn = core.db._require_connection()
    if office_key:
        cursor = await conn.execute(
            """SELECT * FROM government_elections_v127
               WHERE chat_id=? AND office_key=? AND phase IN ('nomination','voting')
               ORDER BY created_at DESC LIMIT 1""",
            (int(chat_id), office_key),
        )
    else:
        cursor = await conn.execute(
            """SELECT * FROM government_elections_v127
               WHERE chat_id=? AND phase IN ('nomination','voting')
               ORDER BY created_at DESC LIMIT 1""",
            (int(chat_id),),
        )
    return await cursor.fetchone()


async def _serialize_election(core: Any, row: Any, user_id: int) -> dict[str, Any]:
    conn = core.db._require_connection()
    election_id = str(row["election_id"])
    cursor = await conn.execute(
        """
        SELECT c.user_id,c.program,c.created_at,p.username,p.full_name,p.career_points,
               COUNT(v.voter_id) votes
        FROM government_candidates_v127 c
        LEFT JOIN players p ON p.chat_id=? AND p.user_id=c.user_id
        LEFT JOIN government_election_votes_v127 v
          ON v.election_id=c.election_id AND v.candidate_id=c.user_id
        WHERE c.election_id=?
        GROUP BY c.user_id,c.program,c.created_at,p.username,p.full_name,p.career_points
        ORDER BY votes DESC,c.created_at ASC
        """,
        (int(row["chat_id"]), election_id),
    )
    candidates = [
        {
            "user_id": int(item["user_id"]),
            "program": str(item["program"] or ""),
            "username": str(item["username"] or ""),
            "name": str(item["full_name"] or f"ID {item['user_id']}"),
            "career_points": int(item["career_points"] or 0),
            "votes": int(item["votes"] or 0),
        }
        for item in await cursor.fetchall()
    ]
    cursor = await conn.execute(
        "SELECT candidate_id FROM government_election_votes_v127 WHERE election_id=? AND voter_id=?",
        (election_id, int(user_id)),
    )
    vote = await cursor.fetchone()
    spec = OFFICES[str(row["office_key"])]
    deadline = int(row["nomination_ends_at"]) if str(row["phase"]) == "nomination" else int(row["voting_ends_at"])
    return {
        "election_id": election_id,
        "office_key": str(row["office_key"]),
        "office_title": spec["title"],
        "emoji": spec["emoji"],
        "seats": int(row["seats"]),
        "phase": str(row["phase"]),
        "created_at": int(row["created_at"]),
        "deadline": deadline,
        "remaining": _remaining(deadline),
        "candidates": candidates,
        "my_vote": int(vote["candidate_id"]) if vote else 0,
    }


async def _bill_votes(core: Any, bill_id: str) -> dict[str, int]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT vote,COUNT(*) amount FROM government_bill_votes_v127 WHERE bill_id=? GROUP BY vote",
        (str(bill_id),),
    )
    result = {"yes": 0, "no": 0, "abstain": 0}
    for row in await cursor.fetchall():
        key = str(row["vote"])
        if key in result:
            result[key] = int(row["amount"])
    return result


async def _serialize_bill(core: Any, row: Any, user_id: int) -> dict[str, Any]:
    conn = core.db._require_connection()
    votes = await _bill_votes(core, str(row["bill_id"]))
    cursor = await conn.execute(
        "SELECT vote FROM government_bill_votes_v127 WHERE bill_id=? AND voter_id=?",
        (str(row["bill_id"]), int(user_id)),
    )
    mine = await cursor.fetchone()
    cursor = await conn.execute(
        "SELECT username,full_name FROM players WHERE chat_id=? AND user_id=?",
        (int(row["chat_id"]), int(row["author_id"])),
    )
    author = await cursor.fetchone()
    spec = BILL_TYPES.get(str(row["bill_type"]), {"emoji": "📜", "title": "Закон"})
    deadline = int(row["voting_ends_at"]) if str(row["status"]) == "voting" else 0
    if str(row["status"]) == "president_review":
        deadline = int(row["president_review_ends_at"])
    return {
        "bill_id": str(row["bill_id"]),
        "number": int(row["number"]),
        "title": str(row["title"]),
        "description": str(row["description"]),
        "bill_type": str(row["bill_type"]),
        "type_title": spec["title"],
        "emoji": spec["emoji"],
        "payload": _json(row["payload_json"], {}),
        "author_id": int(row["author_id"]),
        "author_name": str(author["full_name"] if author else f"ID {row['author_id']}"),
        "status": str(row["status"]),
        "votes": votes,
        "my_vote": str(mine["vote"]) if mine else "",
        "created_at": int(row["created_at"]),
        "deadline": deadline,
        "remaining": _remaining(deadline) if deadline else "",
        "resolved_at": int(row["resolved_at"] or 0),
    }


def _serialize_law(row: Any) -> dict[str, Any]:
    spec = BILL_TYPES.get(str(row["law_type"]), {"emoji": "⚖️", "title": "Закон"})
    return {
        "law_id": str(row["law_id"]),
        "number": int(row["number"]),
        "title": str(row["title"]),
        "text": str(row["text"]),
        "law_type": str(row["law_type"]),
        "type_title": spec["title"],
        "emoji": spec["emoji"],
        "payload": _json(row["payload_json"], {}),
        "enacted_at": int(row["enacted_at"]),
        "active": bool(int(row["active"])),
    }


async def _publish(bot: Any, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(int(chat_id), text)
    except Exception:
        pass


async def _start_election(core: Any, bot: Any, chat_id: int, office_key: str, actor_id: int) -> str:
    if office_key not in {"president", "deputy", "chair"}:
        raise ValueError("Для этой должности выборы не проводятся.")
    if await _active_election(core, chat_id, office_key):
        raise ValueError("Выборы на эту должность уже идут.")
    if office_key == "chair":
        if not await _deputy_ids(core, chat_id):
            raise ValueError("Сначала необходимо избрать депутатов.")
        if not (await _holds(core, chat_id, actor_id, "deputy", "chair") or actor_id == int(core.DEVELOPER_ID)):
            raise PermissionError("Выборы председателя может начать депутат или владелец бота.")
    elif actor_id != int(core.DEVELOPER_ID):
        existing = await _office_rows(core, chat_id)
        if any(str(row["office_key"]) == office_key for row in existing):
            raise PermissionError("Досрочные выборы запускает только владелец бота.")
    now = _now()
    election_id = secrets.token_urlsafe(12)
    spec = OFFICES[office_key]
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_elections_v127(
             election_id,chat_id,office_key,seats,phase,nomination_ends_at,
             voting_ends_at,term_seconds,created_by,created_at,resolved_at
           ) VALUES(?,?,?,?, 'nomination', ?,0,?,?,?,0)""",
        (election_id, int(chat_id), office_key, int(spec["seats"]), now + NOMINATION_SECONDS,
         TERM_SECONDS, int(actor_id), now),
    )
    await conn.commit()
    await _publish(
        bot, chat_id,
        f"{spec['emoji']} <b>ОТКРЫТЫ ВЫБОРЫ: {html.escape(str(spec['title']).upper())}</b>\n\n"
        f"Начался этап выдвижения кандидатов.\nМест: <b>{int(spec['seats'])}</b>\n"
        f"Выдвижение завершится: <b>{_date_text(now + NOMINATION_SECONDS)}</b>\n\n"
        "Кандидатуры и программы принимаются в Mini App «Государство реальности».",
    )
    return election_id


async def _nominate(core: Any, chat_id: int, user_id: int, election_id: str, program: str) -> None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_elections_v127 WHERE election_id=? AND chat_id=?",
        (str(election_id), int(chat_id)),
    )
    election = await cursor.fetchone()
    if election is None or str(election["phase"]) != "nomination" or int(election["nomination_ends_at"]) <= _now():
        raise ValueError("Этап выдвижения уже завершён.")
    office_key = str(election["office_key"])
    spec = OFFICES[office_key]
    player = await _player_dict(core, chat_id, user_id)
    if player is None:
        raise ValueError("Участник не найден.")
    if int(player["career_points"]) < int(spec["threshold"]):
        raise ValueError(f"Для должности требуется {_fmt(int(spec['threshold']))} карьерного влияния.")
    if await _has_active_sanctions(core, chat_id, user_id):
        raise PermissionError("Участник с активными санкциями не может баллотироваться.")
    if office_key == "chair" and not await _holds(core, chat_id, user_id, "deputy", "chair"):
        raise PermissionError("Председателем может стать только действующий депутат.")
    offices = await _user_offices(core, chat_id, user_id)
    if office_key != "chair" and any(key != "chair" for key in offices):
        raise PermissionError("Нельзя занимать несколько государственных должностей одновременно.")
    clean = str(program or "").strip()
    if len(clean) < 10 or len(clean) > 600:
        raise ValueError("Программа кандидата должна содержать от 10 до 600 символов.")
    await conn.execute(
        """INSERT INTO government_candidates_v127(election_id,user_id,program,created_at)
           VALUES(?,?,?,?) ON CONFLICT(election_id,user_id) DO UPDATE SET
           program=excluded.program,created_at=excluded.created_at""",
        (str(election_id), int(user_id), clean, _now()),
    )
    await conn.commit()


async def _vote_election(core: Any, chat_id: int, voter_id: int, election_id: str, candidate_id: int) -> None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_elections_v127 WHERE election_id=? AND chat_id=?",
        (str(election_id), int(chat_id)),
    )
    election = await cursor.fetchone()
    if election is None or str(election["phase"]) != "voting" or int(election["voting_ends_at"]) <= _now():
        raise ValueError("Голосование уже завершено.")
    if await _has_active_sanctions(core, chat_id, voter_id):
        raise PermissionError("Участник с активными санкциями не допускается к голосованию.")
    if str(election["office_key"]) == "chair" and voter_id not in await _deputy_ids(core, chat_id):
        raise PermissionError("Председателя выбирают действующие депутаты.")
    cursor = await conn.execute(
        "SELECT 1 FROM government_candidates_v127 WHERE election_id=? AND user_id=?",
        (str(election_id), int(candidate_id)),
    )
    if await cursor.fetchone() is None:
        raise ValueError("Кандидат не найден.")
    await conn.execute(
        """INSERT INTO government_election_votes_v127(election_id,voter_id,candidate_id,created_at)
           VALUES(?,?,?,?) ON CONFLICT(election_id,voter_id) DO UPDATE SET
           candidate_id=excluded.candidate_id,created_at=excluded.created_at""",
        (str(election_id), int(voter_id), int(candidate_id), _now()),
    )
    await conn.commit()


async def _assign_office(core: Any, chat_id: int, office_key: str, user_id: int, seat_no: int,
                         actor_id: int, term_seconds: int = TERM_SECONDS) -> None:
    now = _now()
    conn = core.db._require_connection()
    if office_key not in OFFICES:
        raise ValueError("Неизвестная должность.")
    if office_key != "chair":
        await conn.execute(
            "DELETE FROM government_offices_v127 WHERE chat_id=? AND user_id=? AND ends_at>? AND office_key<>'chair'",
            (int(chat_id), int(user_id), now),
        )
    await conn.execute(
        """INSERT INTO government_offices_v127(
             chat_id,office_key,seat_no,user_id,starts_at,ends_at,trust,appointed_by
           ) VALUES(?,?,?,?,?,?,50,?)
           ON CONFLICT(chat_id,office_key,seat_no) DO UPDATE SET
           user_id=excluded.user_id,starts_at=excluded.starts_at,ends_at=excluded.ends_at,
           trust=50,appointed_by=excluded.appointed_by""",
        (int(chat_id), office_key, int(seat_no), int(user_id), now,
         now + max(3600, int(term_seconds)), int(actor_id)),
    )
    await conn.commit()


async def _create_bill(core: Any, bot: Any, chat_id: int, author_id: int, bill_type: str,
                       title: str, description: str, payload: dict[str, Any]) -> str:
    if bill_type not in BILL_TYPES:
        raise ValueError("Неизвестный вид законопроекта.")
    offices = await _user_offices(core, chat_id, author_id)
    is_admin = author_id == int(core.DEVELOPER_ID)
    if not (is_admin or set(offices) & {"president", "chair", "deputy", "finance", "oversight"}):
        raise PermissionError("Законопроекты могут вносить только действующие чиновники.")
    if bill_type == "tax_policy" and not (is_admin or set(offices) & {"president", "finance", "deputy"}):
        raise PermissionError("Налоговый закон может внести президент, министр финансов или депутат.")
    if bill_type == "budget" and not (is_admin or set(offices) & {"president", "finance", "deputy"}):
        raise PermissionError("Бюджетную выплату может предложить президент, министр финансов или депутат.")
    if bill_type == "appointment" and not (is_admin or "president" in offices):
        raise PermissionError("Кандидатуру министра или главы Надзора предлагает президент.")
    if bill_type == "sanction" and not (is_admin or set(offices) & {"president", "oversight", "deputy"}):
        raise PermissionError("Санкционное предложение может внести президент, глава Надзора или депутат.")
    clean_title = str(title or "").strip()
    clean_description = str(description or "").strip()
    if len(clean_title) < 5 or len(clean_title) > 120:
        raise ValueError("Название должно содержать от 5 до 120 символов.")
    if len(clean_description) < 10 or len(clean_description) > 1200:
        raise ValueError("Описание должно содержать от 10 до 1200 символов.")
    if not await _deputy_ids(core, chat_id):
        raise ValueError("Сначала необходимо избрать состав Госдумы.")
    payload = dict(payload or {})
    if bill_type == "tax_policy":
        rates = [
            max(0, min(30, _as_int(payload.get("rate_1"), 0))),
            max(0, min(30, _as_int(payload.get("rate_2"), 2))),
            max(0, min(30, _as_int(payload.get("rate_3"), 4))),
            max(0, min(30, _as_int(payload.get("rate_4"), 6))),
        ]
        thresholds = [
            max(0, _as_int(payload.get("wealth_1"), 10_000)),
            max(1, _as_int(payload.get("wealth_2"), 50_000)),
            max(2, _as_int(payload.get("wealth_3"), 200_000)),
        ]
        if not thresholds[0] < thresholds[1] < thresholds[2]:
            raise ValueError("Пороги богатства должны идти по возрастанию.")
        payload = {
            "rate_1": rates[0], "rate_2": rates[1], "rate_3": rates[2], "rate_4": rates[3],
            "wealth_1": thresholds[0], "wealth_2": thresholds[1], "wealth_3": thresholds[2],
            "max_tax": max(0, min(1_000_000, _as_int(payload.get("max_tax"), 30_000))),
            "enabled": bool(payload.get("enabled", True)),
        }
    elif bill_type == "budget":
        target_id = _as_int(payload.get("target_user_id"))
        amount = _as_int(payload.get("amount"))
        if await _player_dict(core, chat_id, target_id) is None:
            raise ValueError("Получатель выплаты не найден.")
        if amount <= 0 or amount > 1_000_000:
            raise ValueError("Размер выплаты должен быть от 1 до 1 000 000.")
        payload = {"target_user_id": target_id, "amount": amount}
    elif bill_type == "appointment":
        office_key = str(payload.get("office_key") or "")
        target_id = _as_int(payload.get("target_user_id"))
        if office_key not in {"finance", "oversight"}:
            raise ValueError("Можно назначить министра финансов или главу Надзора.")
        candidate = await _player_dict(core, chat_id, target_id)
        if candidate is None:
            raise ValueError("Кандидат не найден.")
        if int(candidate["career_points"]) < int(OFFICES[office_key]["threshold"]):
            raise ValueError("Кандидату не хватает карьерного влияния.")
        if await _has_active_sanctions(core, chat_id, target_id):
            raise PermissionError("Участника с активными санкциями назначить нельзя.")
        payload = {"office_key": office_key, "target_user_id": target_id}
    elif bill_type == "sanction":
        target_id = _as_int(payload.get("target_user_id"))
        types = [str(item) for item in payload.get("types", []) if str(item) in sanctions.SANCTION_TYPES]
        duration = _as_int(payload.get("duration"), 86_400)
        reason = str(payload.get("reason") or clean_description).strip()
        if await _player_dict(core, chat_id, target_id) is None:
            raise ValueError("Участник для санкций не найден.")
        if not types:
            raise ValueError("Выбери хотя бы один вид санкций.")
        if duration not in sanctions.ALLOWED_DURATIONS:
            raise ValueError("Недопустимый срок санкций.")
        payload = {"target_user_id": target_id, "types": types, "duration": duration, "reason": reason[:500]}
    number = await _next_number(core, chat_id, "bill_seq")
    bill_id = secrets.token_urlsafe(12)
    now = _now()
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_bills_v127(
             bill_id,chat_id,number,title,description,bill_type,payload_json,
             author_id,status,created_at,voting_ends_at,president_review_ends_at,resolved_at
           ) VALUES(?,?,?,?,?,?,?,?, 'voting', ?,?,0,0)""",
        (bill_id, int(chat_id), int(number), clean_title, clean_description, bill_type,
         json.dumps(payload, ensure_ascii=False), int(author_id), now, now + BILL_VOTING_SECONDS),
    )
    await conn.commit()
    spec = BILL_TYPES[bill_type]
    author = await _player_dict(core, chat_id, author_id)
    await _publish(
        bot, chat_id,
        f"{spec['emoji']} <b>В ГОСДУМУ ВНЕСЁН ЗАКОНОПРОЕКТ №{number}</b>\n\n"
        f"<b>{html.escape(clean_title)}</b>\n\n{html.escape(clean_description)}\n\n"
        f"Автор: <b>{html.escape(author['name'] if author else str(author_id))}</b>\n"
        f"Голосование завершится: <b>{_date_text(now + BILL_VOTING_SECONDS)}</b>\n\n"
        "Голосование проходит в Mini App «Государство реальности».",
    )
    return bill_id


async def _vote_bill(core: Any, chat_id: int, voter_id: int, bill_id: str, vote: str) -> None:
    if vote not in {"yes", "no", "abstain"}:
        raise ValueError("Неизвестный вариант голосования.")
    if voter_id not in await _deputy_ids(core, chat_id):
        raise PermissionError("По законопроектам голосуют только депутаты.")
    if await _has_active_sanctions(core, chat_id, voter_id):
        raise PermissionError("Депутат с активными санкциями временно не голосует.")
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_bills_v127 WHERE bill_id=? AND chat_id=?",
        (str(bill_id), int(chat_id)),
    )
    bill = await cursor.fetchone()
    if bill is None or str(bill["status"]) != "voting" or int(bill["voting_ends_at"]) <= _now():
        raise ValueError("Голосование по законопроекту завершено.")
    await conn.execute(
        """INSERT INTO government_bill_votes_v127(bill_id,voter_id,vote,created_at)
           VALUES(?,?,?,?) ON CONFLICT(bill_id,voter_id) DO UPDATE SET
           vote=excluded.vote,created_at=excluded.created_at""",
        (str(bill_id), int(voter_id), vote, _now()),
    )
    await conn.commit()


async def _treasury_log(core: Any, chat_id: int, delta: int, reason: str,
                        source_type: str, source_id: str, actor_id: int) -> None:
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_treasury_log_v127(
             chat_id,delta,reason,source_type,source_id,actor_id,created_at
           ) VALUES(?,?,?,?,?,?,?)""",
        (int(chat_id), int(delta), str(reason), str(source_type), str(source_id), int(actor_id), _now()),
    )


async def _enact_bill(core: Any, bot: Any, bill: Any, actor_id: int) -> None:
    bill_id = str(bill["bill_id"])
    chat_id = int(bill["chat_id"])
    bill_type = str(bill["bill_type"])
    payload = _json(bill["payload_json"], {})
    conn = core.db._require_connection()
    state = await _ensure_state(core, chat_id)
    if bill_type == "tax_policy":
        await conn.execute(
            """UPDATE government_state_v127 SET
               tax_enabled=?,wealth_1=?,wealth_2=?,wealth_3=?,
               rate_1_bps=?,rate_2_bps=?,rate_3_bps=?,rate_4_bps=?,max_tax=?,
               next_tax_at=CASE WHEN next_tax_at<=? THEN ? ELSE next_tax_at END,updated_at=?
               WHERE chat_id=?""",
            (1 if payload.get("enabled", True) else 0, _as_int(payload.get("wealth_1"), 10_000),
             _as_int(payload.get("wealth_2"), 50_000), _as_int(payload.get("wealth_3"), 200_000),
             _as_int(payload.get("rate_1")) * 100, _as_int(payload.get("rate_2"), 2) * 100,
             _as_int(payload.get("rate_3"), 4) * 100, _as_int(payload.get("rate_4"), 6) * 100,
             _as_int(payload.get("max_tax"), 30_000), _now(), _now() + 7 * 86400, _now(), chat_id),
        )
    elif bill_type == "budget":
        amount = _as_int(payload.get("amount"))
        target_id = _as_int(payload.get("target_user_id"))
        if int(state["treasury"]) < amount:
            raise ValueError("В казне недостаточно влияния для исполнения закона.")
        await conn.execute("UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?",
                           (amount, _now(), chat_id))
        await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                           (amount, _now(), chat_id, target_id))
        await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                           (chat_id, target_id, amount, "government_budget_v127", _now()))
        await _treasury_log(core, chat_id, -amount, str(bill["title"]), "budget", bill_id, actor_id)
    elif bill_type == "appointment":
        await _assign_office(core, chat_id, str(payload.get("office_key")),
                             _as_int(payload.get("target_user_id")), 1, actor_id)
    elif bill_type == "sanction":
        types, expires_at = await sanctions.issue_sanctions(
            core, chat_id, _as_int(payload.get("target_user_id")),
            [str(item) for item in payload.get("types", [])], _as_int(payload.get("duration")),
            str(payload.get("reason") or bill["description"]), int(actor_id),
        )
        await sanctions.send_issue_notice(
            core, bot, chat_id, _as_int(payload.get("target_user_id")), types,
            _as_int(payload.get("duration")), str(payload.get("reason") or bill["description"]), expires_at,
        )
    law_number = await _next_number(core, chat_id, "law_seq")
    law_id = secrets.token_urlsafe(12)
    now = _now()
    await conn.execute(
        """INSERT INTO government_laws_v127(
             law_id,chat_id,number,title,text,law_type,payload_json,bill_id,enacted_at,active
           ) VALUES(?,?,?,?,?,?,?,?,?,1)""",
        (law_id, chat_id, law_number, str(bill["title"]), str(bill["description"]),
         bill_type, str(bill["payload_json"]), bill_id, now),
    )
    await conn.execute("UPDATE government_bills_v127 SET status='enacted',resolved_at=? WHERE bill_id=?",
                       (now, bill_id))
    await conn.commit()
    spec = BILL_TYPES.get(bill_type, {"emoji": "⚖️"})
    await _publish(
        bot, chat_id,
        f"⚖️ <b>ЗАКОН №{law_number} ВСТУПИЛ В СИЛУ</b>\n\n"
        f"{spec['emoji']} <b>{html.escape(str(bill['title']))}</b>\n\n"
        f"{html.escape(str(bill['description']))}\n\n"
        "Закон одобрен Госдумой и утверждён Президентом реальности.",
    )


async def _president_decision(core: Any, bot: Any, chat_id: int, actor_id: int,
                              bill_id: str, decision: str) -> None:
    if not (actor_id == int(core.DEVELOPER_ID) or await _holds(core, chat_id, actor_id, "president")):
        raise PermissionError("Подписывать и отклонять законы может Президент реальности.")
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT * FROM government_bills_v127 WHERE bill_id=? AND chat_id=?",
                                (str(bill_id), int(chat_id)))
    bill = await cursor.fetchone()
    if bill is None or str(bill["status"]) != "president_review":
        raise ValueError("Законопроект не ожидает решения президента.")
    if decision == "sign":
        await _enact_bill(core, bot, bill, actor_id)
        return
    if decision != "veto":
        raise ValueError("Неизвестное решение.")
    await conn.execute("UPDATE government_bills_v127 SET status='vetoed',resolved_at=? WHERE bill_id=?",
                       (_now(), str(bill_id)))
    await conn.commit()
    await _publish(
        bot, chat_id,
        f"🛑 <b>ПРЕЗИДЕНТСКОЕ ВЕТО</b>\n\n"
        f"Законопроект №{int(bill['number'])} «{html.escape(str(bill['title']))}» отклонён Президентом реальности.\n\n"
        "Госдума может преодолеть вето большинством не менее двух третей.",
    )


async def _override_veto(core: Any, bot: Any, chat_id: int, actor_id: int, bill_id: str) -> None:
    if not (actor_id == int(core.DEVELOPER_ID) or await _holds(core, chat_id, actor_id, "chair")):
        raise PermissionError("Преодоление вето запускает Председатель Госдумы.")
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT * FROM government_bills_v127 WHERE bill_id=? AND chat_id=?",
                                (str(bill_id), int(chat_id)))
    bill = await cursor.fetchone()
    if bill is None or str(bill["status"]) != "vetoed":
        raise ValueError("Для этого законопроекта нет действующего вето.")
    deputies = await _deputy_ids(core, chat_id)
    votes = await _bill_votes(core, bill_id)
    required = max(1, math.ceil(len(deputies) * 2 / 3))
    if int(votes["yes"]) < required:
        raise ValueError(f"Для преодоления вето нужно минимум {required} голосов «за».")
    await _enact_bill(core, bot, bill, actor_id)


def _tax_rate(balance: int, state: Any) -> int:
    value = max(0, int(balance))
    if value <= int(state["wealth_1"]):
        return int(state["rate_1_bps"])
    if value <= int(state["wealth_2"]):
        return int(state["rate_2_bps"])
    if value <= int(state["wealth_3"]):
        return int(state["rate_3_bps"])
    return int(state["rate_4_bps"])


async def _run_tax(core: Any, bot: Any, chat_id: int, actor_id: int, automatic: bool) -> dict[str, int]:
    state = await _ensure_state(core, chat_id)
    if not int(state["tax_enabled"]) and automatic:
        return {"paid": 0, "due": 0, "debt": 0, "taxpayers": 0}
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT user_id,points FROM players WHERE chat_id=? AND points>0 ORDER BY user_id",
                                (int(chat_id),))
    rows = list(await cursor.fetchall())
    total_due = total_paid = debt_added = taxpayers = 0
    now = _now()
    run_id = secrets.token_urlsafe(10)
    async with core.db.lock:
        for row in rows:
            balance = int(row["points"])
            rate_bps = _tax_rate(balance, state)
            due = min(int(state["max_tax"]), max(0, balance * rate_bps // 10_000))
            if due <= 0:
                continue
            paid = min(balance, due)
            debt = due - paid
            taxpayers += 1
            total_due += due
            total_paid += paid
            debt_added += debt
            if paid:
                await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?",
                                   (paid, now, int(chat_id), int(row["user_id"])))
                await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                                   (int(chat_id), int(row["user_id"]), -paid, "government_wealth_tax_v127", now))
            if debt:
                await conn.execute(
                    """INSERT INTO government_tax_debts_v127(chat_id,user_id,amount,updated_at)
                       VALUES(?,?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET
                       amount=government_tax_debts_v127.amount+excluded.amount,updated_at=excluded.updated_at""",
                    (int(chat_id), int(row["user_id"]), debt, now),
                )
        await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury+?,next_tax_at=?,updated_at=? WHERE chat_id=?",
            (total_paid, now + 7 * 86400, now, int(chat_id)),
        )
        await conn.execute(
            """INSERT INTO government_tax_runs_v127(
                 run_id,chat_id,total_due,total_paid,debt_added,taxpayers,created_at
               ) VALUES(?,?,?,?,?,?,?)""",
            (run_id, int(chat_id), total_due, total_paid, debt_added, taxpayers, now),
        )
        if total_paid:
            await _treasury_log(core, chat_id, total_paid, "Сбор налога на богатство", "tax", run_id, actor_id)
        await conn.commit()
    await _publish(
        bot, chat_id,
        "🏦 <b>НАЛОГОВЫЙ ПЕРИОД ЗАВЕРШЁН</b>\n\n"
        f"Налогоплательщиков: <b>{taxpayers}</b>\nНачислено: <b>{_fmt(total_due)}</b>\n"
        f"Поступило в казну: <b>{_fmt(total_paid)}</b>\nНовая задолженность: <b>{_fmt(debt_added)}</b>\n\n"
        "🧾 Постановление Налоговой службы реальности исполнено.",
    )
    return {"paid": total_paid, "due": total_due, "debt": debt_added, "taxpayers": taxpayers}


async def _pay_tax_debt(core: Any, chat_id: int, user_id: int, requested: int = 0) -> int:
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT amount FROM government_tax_debts_v127 WHERE chat_id=? AND user_id=?",
                                (int(chat_id), int(user_id)))
    debt_row = await cursor.fetchone()
    debt = int(debt_row["amount"] if debt_row else 0)
    if debt <= 0:
        raise ValueError("Налоговой задолженности нет.")
    player = await _player_dict(core, chat_id, user_id)
    if player is None or int(player["points"]) <= 0:
        raise ValueError("На балансе нет влияния для погашения.")
    amount = min(debt, int(player["points"]), requested if requested > 0 else debt)
    now = _now()
    async with core.db.lock:
        await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?",
                           (amount, now, int(chat_id), int(user_id)))
        await conn.execute("UPDATE government_tax_debts_v127 SET amount=MAX(0,amount-?),updated_at=? WHERE chat_id=? AND user_id=?",
                           (amount, now, int(chat_id), int(user_id)))
        await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
                           (amount, now, int(chat_id)))
        await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                           (int(chat_id), int(user_id), -amount, "government_tax_debt_repayment_v127", now))
        await _treasury_log(core, chat_id, amount, "Погашение налогового долга", "tax_debt", str(user_id), user_id)
        await conn.commit()
    return amount


async def _state(core: Any, bot: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    state = await _ensure_state(core, chat_id)
    conn = core.db._require_connection()
    offices_rows = await _office_rows(core, chat_id)
    offices = [_office_dict(row) for row in offices_rows]
    my_offices = await _user_offices(core, chat_id, user_id)
    player = await _player_dict(core, chat_id, user_id)
    cursor = await conn.execute("SELECT * FROM government_elections_v127 WHERE chat_id=? ORDER BY created_at DESC LIMIT 12",
                                (int(chat_id),))
    elections = [await _serialize_election(core, row, user_id) for row in await cursor.fetchall()]
    cursor = await conn.execute("SELECT * FROM government_bills_v127 WHERE chat_id=? ORDER BY created_at DESC LIMIT 30",
                                (int(chat_id),))
    bills = [await _serialize_bill(core, row, user_id) for row in await cursor.fetchall()]
    cursor = await conn.execute("SELECT * FROM government_laws_v127 WHERE chat_id=? ORDER BY enacted_at DESC LIMIT 30",
                                (int(chat_id),))
    laws = [_serialize_law(row) for row in await cursor.fetchall()]
    cursor = await conn.execute("SELECT * FROM government_treasury_log_v127 WHERE chat_id=? ORDER BY log_id DESC LIMIT 40",
                                (int(chat_id),))
    treasury_log = [
        {"id": int(row["log_id"]), "delta": int(row["delta"]), "reason": str(row["reason"]),
         "source_type": str(row["source_type"]), "actor_id": int(row["actor_id"]),
         "created_at": int(row["created_at"])}
        for row in await cursor.fetchall()
    ]
    cursor = await conn.execute("SELECT amount FROM government_tax_debts_v127 WHERE chat_id=? AND user_id=?",
                                (int(chat_id), int(user_id)))
    debt_row = await cursor.fetchone()
    cursor = await conn.execute(
        "SELECT COALESCE(SUM(amount),0) total,COUNT(CASE WHEN amount>0 THEN 1 END) people FROM government_tax_debts_v127 WHERE chat_id=?",
        (int(chat_id),),
    )
    debt_total_row = await cursor.fetchone()
    eligible = await _eligible_users(core, chat_id)
    active_sanction = await _has_active_sanctions(core, chat_id, user_id)
    deputies = await _deputy_ids(core, chat_id)
    is_admin = int(user_id) == int(core.DEVELOPER_ID)
    return {
        "ok": True,
        "version": VERSION,
        "chat": {"chat_id": int(chat_id), "title": await _chat_title(bot, chat_id)},
        "user": {**(player or {"user_id": user_id, "name": f"ID {user_id}", "points": 0, "career_points": 0}),
                 "offices": my_offices, "sanctioned": active_sanction, "is_admin": is_admin},
        "offices": offices,
        "office_specs": OFFICES,
        "elections": elections,
        "bills": bills,
        "laws": laws,
        "eligible_users": eligible,
        "treasury": {"balance": int(state["treasury"]), "log": treasury_log},
        "tax": {
            "enabled": bool(int(state["tax_enabled"])), "next_tax_at": int(state["next_tax_at"]),
            "next_tax_text": _date_text(int(state["next_tax_at"])) if int(state["next_tax_at"]) else "не назначен",
            "wealth_1": int(state["wealth_1"]), "wealth_2": int(state["wealth_2"]),
            "wealth_3": int(state["wealth_3"]), "rate_1": int(state["rate_1_bps"]) / 100,
            "rate_2": int(state["rate_2_bps"]) / 100, "rate_3": int(state["rate_3_bps"]) / 100,
            "rate_4": int(state["rate_4_bps"]) / 100, "max_tax": int(state["max_tax"]),
            "my_debt": int(debt_row["amount"] if debt_row else 0),
            "total_debt": int(debt_total_row["total"] if debt_total_row else 0),
            "debtors": int(debt_total_row["people"] if debt_total_row else 0),
        },
        "permissions": {
            "can_start_president": is_admin or not any(item["office_key"] == "president" for item in offices),
            "can_start_deputy": is_admin or not any(item["office_key"] == "deputy" for item in offices),
            "can_start_chair": is_admin or "deputy" in my_offices or "chair" in my_offices,
            "can_create_bill": is_admin or bool(set(my_offices) & {"president", "chair", "deputy", "finance", "oversight"}),
            "can_vote_bill": int(user_id) in deputies,
            "can_president": is_admin or "president" in my_offices,
            "can_chair": is_admin or "chair" in my_offices,
            "can_manage_tax": is_admin or bool(set(my_offices) & {"president", "finance"}),
            "can_propose_sanction": is_admin or bool(set(my_offices) & {"president", "oversight", "deputy"}),
        },
    }


async def _process_elections(core: Any, bot: Any) -> None:
    conn = core.db._require_connection()
    now = _now()
    cursor = await conn.execute(
        "SELECT * FROM government_elections_v127 WHERE phase='nomination' AND nomination_ends_at<=? ORDER BY nomination_ends_at",
        (now,),
    )
    for election in await cursor.fetchall():
        cursor2 = await conn.execute("SELECT COUNT(*) amount FROM government_candidates_v127 WHERE election_id=?",
                                     (str(election["election_id"]),))
        count = int((await cursor2.fetchone())["amount"])
        if count <= 0:
            await conn.execute("UPDATE government_elections_v127 SET phase='cancelled',resolved_at=? WHERE election_id=?",
                               (now, str(election["election_id"])))
            await conn.commit()
            continue
        voting_ends = now + VOTING_SECONDS
        await conn.execute("UPDATE government_elections_v127 SET phase='voting',voting_ends_at=? WHERE election_id=?",
                           (voting_ends, str(election["election_id"])))
        await conn.commit()
        spec = OFFICES[str(election["office_key"])]
        await _publish(
            bot, int(election["chat_id"]),
            f"🗳 <b>НАЧАЛО ГОЛОСОВАНИЯ</b>\n\nДолжность: {spec['emoji']} <b>{html.escape(str(spec['title']))}</b>\n"
            f"Кандидатов: <b>{count}</b>\nГолосование завершится: <b>{_date_text(voting_ends)}</b>\n\n"
            "Один участник — один голос. Выбор доступен в государственном Mini App.",
        )
    cursor = await conn.execute(
        "SELECT * FROM government_elections_v127 WHERE phase='voting' AND voting_ends_at<=? ORDER BY voting_ends_at",
        (now,),
    )
    for election in await cursor.fetchall():
        election_id = str(election["election_id"])
        cursor2 = await conn.execute(
            """SELECT c.user_id,c.created_at,COUNT(v.voter_id) votes
               FROM government_candidates_v127 c LEFT JOIN government_election_votes_v127 v
               ON v.election_id=c.election_id AND v.candidate_id=c.user_id
               WHERE c.election_id=? GROUP BY c.user_id,c.created_at
               ORDER BY votes DESC,c.created_at ASC,c.user_id ASC""",
            (election_id,),
        )
        ranked = list(await cursor2.fetchall())
        winners = ranked[:int(election["seats"])]
        office_key = str(election["office_key"])
        await conn.execute("DELETE FROM government_offices_v127 WHERE chat_id=? AND office_key=?",
                           (int(election["chat_id"]), office_key))
        for index, winner in enumerate(winners, 1):
            await _assign_office(core, int(election["chat_id"]), office_key, int(winner["user_id"]),
                                 index, int(election["created_by"]), int(election["term_seconds"]))
        await conn.execute("UPDATE government_elections_v127 SET phase='resolved',resolved_at=? WHERE election_id=?",
                           (now, election_id))
        await conn.commit()
        spec = OFFICES[office_key]
        lines: list[str] = []
        for index, winner in enumerate(winners, 1):
            person = await _player_dict(core, int(election["chat_id"]), int(winner["user_id"]))
            lines.append(f"{index}. <b>{html.escape(person['name'] if person else str(winner['user_id']))}</b> — {int(winner['votes'])} голосов")
        await _publish(
            bot, int(election["chat_id"]),
            f"{spec['emoji']} <b>ВЫБОРЫ ЗАВЕРШЕНЫ</b>\n\nДолжность: <b>{html.escape(str(spec['title']))}</b>\n\n"
            + ("\n".join(lines) if lines else "Победитель не определён.") + "\n\nСрок полномочий: <b>7 дней</b>.",
        )


async def _process_bills(core: Any, bot: Any) -> None:
    conn = core.db._require_connection()
    now = _now()
    cursor = await conn.execute(
        "SELECT * FROM government_bills_v127 WHERE status='voting' AND voting_ends_at<=? ORDER BY voting_ends_at",
        (now,),
    )
    for bill in await cursor.fetchall():
        votes = await _bill_votes(core, str(bill["bill_id"]))
        deputies = await _deputy_ids(core, int(bill["chat_id"]))
        quorum = max(1, math.ceil(len(deputies) / 2))
        participation = votes["yes"] + votes["no"] + votes["abstain"]
        passed = participation >= quorum and votes["yes"] > votes["no"]
        if not passed:
            await conn.execute("UPDATE government_bills_v127 SET status='rejected',resolved_at=? WHERE bill_id=?",
                               (now, str(bill["bill_id"])))
            await conn.commit()
            await _publish(bot, int(bill["chat_id"]),
                f"❌ <b>ЗАКОНОПРОЕКТ №{int(bill['number'])} ОТКЛОНЁН</b>\n\n«{html.escape(str(bill['title']))}»\n\n"
                f"За: <b>{votes['yes']}</b> · Против: <b>{votes['no']}</b> · Воздержались: <b>{votes['abstain']}</b>.")
            continue
        if str(bill["bill_type"]) == "appointment":
            try:
                await _enact_bill(core, bot, bill, int(bill["author_id"]))
            except Exception:
                await conn.execute("UPDATE government_bills_v127 SET status='rejected',resolved_at=? WHERE bill_id=?",
                                   (now, str(bill["bill_id"])))
                await conn.commit()
            continue
        review_ends = now + PRESIDENT_REVIEW_SECONDS
        await conn.execute("UPDATE government_bills_v127 SET status='president_review',president_review_ends_at=? WHERE bill_id=?",
                           (review_ends, str(bill["bill_id"])))
        await conn.commit()
        await _publish(
            bot, int(bill["chat_id"]),
            f"✅ <b>ГОСДУМА ОДОБРИЛА ЗАКОНОПРОЕКТ №{int(bill['number'])}</b>\n\n«{html.escape(str(bill['title']))}»\n\n"
            f"За: <b>{votes['yes']}</b> · Против: <b>{votes['no']}</b> · Воздержались: <b>{votes['abstain']}</b>.\n\n"
            f"Документ передан Президенту. Срок решения: <b>{_date_text(review_ends)}</b>.",
        )
    await conn.execute("UPDATE government_bills_v127 SET status='expired',resolved_at=? WHERE status='president_review' AND president_review_ends_at<=?",
                       (now, now))
    await conn.commit()


async def _process_terms(core: Any, bot: Any) -> None:
    conn = core.db._require_connection()
    now = _now()
    cursor = await conn.execute("SELECT * FROM government_offices_v127 WHERE ends_at<=? ORDER BY chat_id,office_key,seat_no",
                                (now,))
    rows = list(await cursor.fetchall())
    if not rows:
        return
    await conn.execute("DELETE FROM government_offices_v127 WHERE ends_at<=?", (now,))
    await conn.commit()
    groups: dict[int, list[Any]] = {}
    for row in rows:
        groups.setdefault(int(row["chat_id"]), []).append(row)
    for chat_id, items in groups.items():
        titles = [OFFICES.get(str(row["office_key"]), {"title": row["office_key"]})["title"] for row in items]
        await _publish(bot, chat_id, "⌛ <b>СРОК ПОЛНОМОЧИЙ ЗАВЕРШЁН</b>\n\n" +
                       "\n".join(f"• {html.escape(str(title))}" for title in titles) +
                       "\n\nОсвободившиеся должности доступны для новых выборов.")


async def _process_taxes(core: Any, bot: Any) -> None:
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT chat_id FROM government_state_v127 WHERE tax_enabled=1 AND next_tax_at>0 AND next_tax_at<=?",
                                (_now(),))
    for row in await cursor.fetchall():
        try:
            await _run_tax(core, bot, int(row["chat_id"]), 0, True)
        except Exception:
            core.logging.exception("Ошибка автоматического налогового периода Reality 127")


async def _runtime_loop(core: Any, bot: Any) -> None:
    await core.asyncio.sleep(5)
    while True:
        try:
            await _process_elections(core, bot)
            await _process_bills(core, bot)
            await _process_terms(core, bot)
            await _process_taxes(core, bot)
        except Exception:
            core.logging.exception("Ошибка государственного цикла Reality 127")
        await core.asyncio.sleep(30)


def install_government_v127(core: Any) -> None:
    global _RUNTIME_STARTED
    if getattr(core, "_government_v127_installed", False):
        return
    core._government_v127_installed = True
    core.GOVERNMENT_VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_government(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS government_state_v127(
                    chat_id INTEGER PRIMARY KEY,treasury INTEGER NOT NULL DEFAULT 0,
                    tax_enabled INTEGER NOT NULL DEFAULT 0,tax_day INTEGER NOT NULL DEFAULT 0,
                    tax_hour INTEGER NOT NULL DEFAULT 10,next_tax_at INTEGER NOT NULL DEFAULT 0,
                    wealth_1 INTEGER NOT NULL DEFAULT 10000,wealth_2 INTEGER NOT NULL DEFAULT 50000,
                    wealth_3 INTEGER NOT NULL DEFAULT 200000,rate_1_bps INTEGER NOT NULL DEFAULT 0,
                    rate_2_bps INTEGER NOT NULL DEFAULT 200,rate_3_bps INTEGER NOT NULL DEFAULT 400,
                    rate_4_bps INTEGER NOT NULL DEFAULT 600,max_tax INTEGER NOT NULL DEFAULT 30000,
                    bill_seq INTEGER NOT NULL DEFAULT 0,law_seq INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS government_offices_v127(
                    chat_id INTEGER NOT NULL,office_key TEXT NOT NULL,seat_no INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,starts_at INTEGER NOT NULL,ends_at INTEGER NOT NULL,
                    trust INTEGER NOT NULL DEFAULT 50,appointed_by INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(chat_id,office_key,seat_no)
                );
                CREATE INDEX IF NOT EXISTS idx_government_office_user_v127
                ON government_offices_v127(chat_id,user_id,ends_at);
                CREATE TABLE IF NOT EXISTS government_elections_v127(
                    election_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL,office_key TEXT NOT NULL,
                    seats INTEGER NOT NULL,phase TEXT NOT NULL,nomination_ends_at INTEGER NOT NULL,
                    voting_ends_at INTEGER NOT NULL DEFAULT 0,term_seconds INTEGER NOT NULL,
                    created_by INTEGER NOT NULL,created_at INTEGER NOT NULL,resolved_at INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS government_candidates_v127(
                    election_id TEXT NOT NULL,user_id INTEGER NOT NULL,program TEXT NOT NULL,
                    created_at INTEGER NOT NULL,PRIMARY KEY(election_id,user_id)
                );
                CREATE TABLE IF NOT EXISTS government_election_votes_v127(
                    election_id TEXT NOT NULL,voter_id INTEGER NOT NULL,candidate_id INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,PRIMARY KEY(election_id,voter_id)
                );
                CREATE TABLE IF NOT EXISTS government_bills_v127(
                    bill_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL,number INTEGER NOT NULL,
                    title TEXT NOT NULL,description TEXT NOT NULL,bill_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',author_id INTEGER NOT NULL,status TEXT NOT NULL,
                    created_at INTEGER NOT NULL,voting_ends_at INTEGER NOT NULL,
                    president_review_ends_at INTEGER NOT NULL DEFAULT 0,resolved_at INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_government_bills_chat_v127
                ON government_bills_v127(chat_id,created_at DESC);
                CREATE TABLE IF NOT EXISTS government_bill_votes_v127(
                    bill_id TEXT NOT NULL,voter_id INTEGER NOT NULL,vote TEXT NOT NULL,
                    created_at INTEGER NOT NULL,PRIMARY KEY(bill_id,voter_id)
                );
                CREATE TABLE IF NOT EXISTS government_laws_v127(
                    law_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL,number INTEGER NOT NULL,
                    title TEXT NOT NULL,text TEXT NOT NULL,law_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',bill_id TEXT NOT NULL,
                    enacted_at INTEGER NOT NULL,active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS government_treasury_log_v127(
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id INTEGER NOT NULL,delta INTEGER NOT NULL,
                    reason TEXT NOT NULL,source_type TEXT NOT NULL,source_id TEXT NOT NULL,
                    actor_id INTEGER NOT NULL,created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS government_tax_debts_v127(
                    chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,amount INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL,PRIMARY KEY(chat_id,user_id)
                );
                CREATE TABLE IF NOT EXISTS government_tax_runs_v127(
                    run_id TEXT PRIMARY KEY,chat_id INTEGER NOT NULL,total_due INTEGER NOT NULL,
                    total_paid INTEGER NOT NULL,debt_added INTEGER NOT NULL,taxpayers INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                );
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_government

    async def state_api(request: Any):
        try:
            user, chat_id, _ = await _auth(core, request)
            return core.web.json_response(await _state(core, request.app["bot"], chat_id, int(user.id)))
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    async def action_api(request: Any):
        try:
            user, chat_id, data = await _auth(core, request)
            action = str(data.get("action") or "")
            bot = request.app["bot"]
            user_id = int(user.id)
            if action == "start_election":
                election_id = await _start_election(core, bot, chat_id, str(data.get("office_key") or ""), user_id)
                message = f"Выборы открыты: {election_id}."
            elif action == "nominate":
                await _nominate(core, chat_id, user_id, str(data.get("election_id") or ""), str(data.get("program") or ""))
                message = "Кандидатура зарегистрирована."
            elif action == "vote_election":
                await _vote_election(core, chat_id, user_id, str(data.get("election_id") or ""), _as_int(data.get("candidate_id")))
                message = "Голос учтён."
            elif action == "create_bill":
                bill_id = await _create_bill(
                    core, bot, chat_id, user_id, str(data.get("bill_type") or "general"),
                    str(data.get("title") or ""), str(data.get("description") or ""),
                    data.get("payload") if isinstance(data.get("payload"), dict) else {},
                )
                message = f"Законопроект зарегистрирован: {bill_id}."
            elif action == "vote_bill":
                await _vote_bill(core, chat_id, user_id, str(data.get("bill_id") or ""), str(data.get("vote") or ""))
                message = "Голос по законопроекту учтён."
            elif action == "president_decision":
                await _president_decision(core, bot, chat_id, user_id, str(data.get("bill_id") or ""), str(data.get("decision") or ""))
                message = "Решение президента исполнено."
            elif action == "override_veto":
                await _override_veto(core, bot, chat_id, user_id, str(data.get("bill_id") or ""))
                message = "Президентское вето преодолено."
            elif action == "tax_toggle":
                if not (user_id == int(core.DEVELOPER_ID) or await _holds(core, chat_id, user_id, "president", "finance")):
                    raise PermissionError("Управлять налоговым циклом может президент или министр финансов.")
                enabled = bool(data.get("enabled"))
                conn = core.db._require_connection()
                await _ensure_state(core, chat_id)
                await conn.execute(
                    """UPDATE government_state_v127 SET tax_enabled=?,
                       next_tax_at=CASE WHEN ?=1 AND next_tax_at<=? THEN ? ELSE next_tax_at END,
                       updated_at=? WHERE chat_id=?""",
                    (1 if enabled else 0, 1 if enabled else 0, _now(), _now() + 7 * 86400, _now(), chat_id),
                )
                await conn.commit()
                message = "Автоматический налоговый цикл включён." if enabled else "Автоматический налоговый цикл отключён."
            elif action == "tax_run":
                if not (user_id == int(core.DEVELOPER_ID) or await _holds(core, chat_id, user_id, "president", "finance")):
                    raise PermissionError("Провести налоговый период может президент или министр финансов.")
                result = await _run_tax(core, bot, chat_id, user_id, False)
                message = f"В казну поступило {_fmt(result['paid'])} влияния."
            elif action == "pay_tax_debt":
                paid = await _pay_tax_debt(core, chat_id, user_id, _as_int(data.get("amount")))
                message = f"Погашено {_fmt(paid)} налогового долга."
            else:
                raise ValueError("Неизвестное государственное действие.")
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    def file_response(path: Path):
        return core.web.FileResponse(path, headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache", "Expires": "0", "X-Government": "reality-127",
        })

    async def index(_: Any):
        return file_response(APP_DIR / "index.html")

    async def asset(request: Any):
        name = request.match_info["name"]
        if name not in {"app.css", "app.js"}:
            raise core.web.HTTPNotFound()
        return file_response(APP_DIR / name)

    @core.web.middleware
    async def government_entry_middleware(request: Any, handler: Any):
        if request.method == "GET":
            start_param = str(request.query.get("tgWebAppStartParam") or request.query.get("startapp") or "")
            if start_param.startswith(GOV_PREFIX):
                return await index(request)
        return await handler(request)

    previous_application = core.web.Application

    def application_with_government_entry(*args: Any, **kwargs: Any):
        middlewares = list(kwargs.pop("middlewares", []) or [])
        kwargs["middlewares"] = [government_entry_middleware, *middlewares]
        return previous_application(*args, **kwargs)

    core.web.Application = application_with_government_entry
    original_start = core.start_webapp_server

    async def start_with_government(bot: Any):
        global _RUNTIME_STARTED
        if not APP_DIR.is_dir():
            raise RuntimeError(f"Не найдена папка государства Reality 127: {APP_DIR}")
        original_runner = core.web.AppRunner

        def runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            def add_get(path: str, handler: Any) -> None:
                if ("GET", path) not in keys and ("*", path) not in keys:
                    app.router.add_get(path, handler)
                    keys.add(("GET", path))
            def add_post(path: str, handler: Any) -> None:
                if ("POST", path) not in keys and ("*", path) not in keys:
                    app.router.add_post(path, handler)
                    keys.add(("POST", path))
            add_get("/government-v127", index)
            add_get("/government-v127/", index)
            add_get("/government-v127/{name:app\\.css|app\\.js}", asset)
            add_get("/government-v127/api/state", state_api)
            add_post("/government-v127/api/action", action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_factory
        try:
            runner = await original_start(bot)
        finally:
            core.web.AppRunner = original_runner
        if not _RUNTIME_STARTED:
            _RUNTIME_STARTED = True
            core.spawn_background_task(_runtime_loop(core, bot))
        return runner

    core.start_webapp_server = start_with_government

    original_commands = core.group_bot_commands

    def commands_with_government() -> list[BotCommand]:
        commands = list(original_commands())
        if any(item.command == "government" for item in commands):
            return commands
        index_value = next((i + 1 for i, item in enumerate(commands) if item.command == "finance"), len(commands))
        commands.insert(index_value, BotCommand(command="government", description="Президент, Госдума, казна и законы"))
        return commands

    core.group_bot_commands = commands_with_government

    @core.router.message(Command("government", "state", "gov"))
    async def cmd_government_v127(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = _government_link(core, chat_id)
        if not link:
            await message.answer("⚠️ Адрес государственного Mini App не настроен.")
            return
        await message.answer(
            "🏛 <b>ГОСУДАРСТВО РЕАЛЬНОСТИ · REALITY 127</b>\n\n"
            "Президент, Госдума, выборы, законы, казна, налоги и Надзор работают отдельно для этой беседы.\n\n"
            "Карьерное влияние открывает доступ к должностям, а обычное влияние используется в бюджете и налоговой системе.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🏛 ОТКРЫТЬ ГОСУДАРСТВО", url=link)
            ]]),
        )

    handlers = core.router.message.handlers
    preferred = [handler for handler in handlers if getattr(handler.callback, "__name__", "") == "cmd_government_v127"]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
