from __future__ import annotations

import secrets
from typing import Any

import government_v127 as gov

from government_reality_v177_common import DAY, RATING_VOTE_COOLDOWN, ROLE_NAMES, ensure_schema


def clamp(value: int) -> int:
    return max(0, min(100, int(value)))


async def adjust_rating(core: Any, chat_id: int, user_id: int, delta: int, reason: str, source: str, actor_id: int = 0) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute(
        """SELECT office_key,seat_no,starts_at,trust FROM government_offices_v127
        WHERE chat_id=? AND user_id=? AND ends_at>? ORDER BY starts_at DESC""",
        (int(chat_id), int(user_id), now),
    )
    rows = list(await cursor.fetchall())
    for row in rows:
        after = clamp(int(row["trust"] or 50) + int(delta))
        await conn.execute(
            "UPDATE government_offices_v127 SET trust=? WHERE chat_id=? AND office_key=? AND seat_no=? AND starts_at=?",
            (after, int(chat_id), str(row["office_key"]), int(row["seat_no"]), int(row["starts_at"])),
        )
        await conn.execute(
            """INSERT INTO government_official_rating_log_v177(
            log_id,chat_id,user_id,office_key,seat_no,office_starts_at,delta,rating_after,
            reason,source,actor_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (secrets.token_urlsafe(12), int(chat_id), int(user_id), str(row["office_key"]), int(row["seat_no"]),
             int(row["starts_at"]), int(delta), after, str(reason), str(source), int(actor_id), now),
        )


async def rate_official(core: Any, chat_id: int, voter_id: int, target_user_id: int, value: int) -> str:
    await ensure_schema(core)
    if int(voter_id) == int(target_user_id):
        raise PermissionError("Нельзя оценивать собственную работу.")
    if int(value) not in {-1, 1}:
        raise ValueError("Неизвестная оценка.")
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            """SELECT office_key,seat_no,starts_at,trust FROM government_offices_v127
            WHERE chat_id=? AND user_id=? AND ends_at>? ORDER BY starts_at DESC LIMIT 1""",
            (int(chat_id), int(target_user_id), now),
        )
        office = await cursor.fetchone()
        if office is None:
            raise ValueError("Оценивать можно только действующего чиновника.")
        cursor = await conn.execute(
            """SELECT created_at FROM government_official_rating_votes_v177
            WHERE chat_id=? AND voter_id=? AND target_user_id=? ORDER BY created_at DESC LIMIT 1""",
            (int(chat_id), int(voter_id), int(target_user_id)),
        )
        previous = await cursor.fetchone()
        if previous is not None and int(previous["created_at"]) + RATING_VOTE_COOLDOWN > now:
            raise ValueError(f"Повторно оценить этого чиновника можно через {gov._remaining(int(previous['created_at']) + RATING_VOTE_COOLDOWN)}.")
        after = clamp(int(office["trust"] or 50) + int(value))
        await conn.execute(
            "UPDATE government_offices_v127 SET trust=? WHERE chat_id=? AND office_key=? AND seat_no=?",
            (after, int(chat_id), str(office["office_key"]), int(office["seat_no"])),
        )
        await conn.execute(
            """INSERT INTO government_official_rating_votes_v177(
            vote_id,chat_id,voter_id,target_user_id,office_key,seat_no,office_starts_at,value,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (secrets.token_urlsafe(12), int(chat_id), int(voter_id), int(target_user_id), str(office["office_key"]),
             int(office["seat_no"]), int(office["starts_at"]), int(value), now),
        )
        await conn.execute(
            """INSERT INTO government_official_rating_log_v177(
            log_id,chat_id,user_id,office_key,seat_no,office_starts_at,delta,rating_after,
            reason,source,actor_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (secrets.token_urlsafe(12), int(chat_id), int(target_user_id), str(office["office_key"]),
             int(office["seat_no"]), int(office["starts_at"]), int(value), after,
             "Общественная оценка", "public_vote", int(voter_id), now),
        )
        await conn.commit()
    return "Оценка работы чиновника учтена."


async def archive_expired_terms(core: Any) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    await conn.execute(
        """INSERT OR IGNORE INTO government_official_terms_v177(
        chat_id,office_key,seat_no,user_id,starts_at,ends_at,final_rating,archived_at)
        SELECT chat_id,office_key,seat_no,user_id,starts_at,ends_at,trust,?
        FROM government_offices_v127 WHERE ends_at<=?""",
        (now, now),
    )
    await conn.commit()


async def ratings_state(core: Any, chat_id: int, viewer_id: int) -> dict[str, Any]:
    await archive_expired_terms(core)
    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute(
        """SELECT o.*,p.full_name,p.username FROM government_offices_v127 o
        LEFT JOIN players p ON p.chat_id=o.chat_id AND p.user_id=o.user_id
        WHERE o.chat_id=? AND o.ends_at>? ORDER BY CASE o.office_key WHEN 'president' THEN 0 ELSE 1 END,o.trust DESC""",
        (int(chat_id), now),
    )
    officials = []
    for row in await cursor.fetchall():
        starts_at = int(row["starts_at"])
        user_id = int(row["user_id"])
        cursor2 = await conn.execute(
            """SELECT COALESCE(SUM(CASE WHEN value=1 THEN 1 ELSE 0 END),0) approvals,
            COALESCE(SUM(CASE WHEN value=-1 THEN 1 ELSE 0 END),0) disapprovals
            FROM government_official_rating_votes_v177 WHERE chat_id=? AND target_user_id=? AND office_starts_at=?""",
            (int(chat_id), user_id, starts_at),
        )
        votes = await cursor2.fetchone()
        cursor2 = await conn.execute(
            """SELECT COALESCE(SUM(delta),0) delta FROM government_official_rating_log_v177
            WHERE chat_id=? AND user_id=? AND office_starts_at=? AND created_at>=?""",
            (int(chat_id), user_id, starts_at, now - 7 * DAY),
        )
        week = await cursor2.fetchone()
        cursor2 = await conn.execute(
            """SELECT reason,delta,rating_after,source,created_at FROM government_official_rating_log_v177
            WHERE chat_id=? AND user_id=? AND office_starts_at=? ORDER BY created_at DESC LIMIT 6""",
            (int(chat_id), user_id, starts_at),
        )
        history = [dict(item) for item in await cursor2.fetchall()]
        cursor2 = await conn.execute(
            """SELECT created_at FROM government_official_rating_votes_v177
            WHERE chat_id=? AND voter_id=? AND target_user_id=? ORDER BY created_at DESC LIMIT 1""",
            (int(chat_id), int(viewer_id), user_id),
        )
        mine = await cursor2.fetchone()
        officials.append({
            "user_id": user_id,
            "name": str(row["full_name"] or (f"@{row['username']}" if row["username"] else f"ID {user_id}")),
            "office_key": str(row["office_key"]), "seat_no": int(row["seat_no"]),
            "office_title": ROLE_NAMES.get(str(row["office_key"]), str(row["office_key"])),
            "rating": clamp(int(row["trust"] or 50)), "delta_7d": int(week["delta"] if week else 0),
            "approvals": int(votes["approvals"] if votes else 0), "disapprovals": int(votes["disapprovals"] if votes else 0),
            "history": history, "can_rate": bool(user_id != int(viewer_id) and (mine is None or int(mine["created_at"]) + DAY <= now)),
            "next_vote_at": int(mine["created_at"] + DAY if mine else 0), "starts_at": starts_at, "ends_at": int(row["ends_at"]),
        })
    cursor = await conn.execute(
        """SELECT t.*,p.full_name FROM government_official_terms_v177 t
        LEFT JOIN players p ON p.chat_id=t.chat_id AND p.user_id=t.user_id
        WHERE t.chat_id=? ORDER BY t.ends_at DESC LIMIT 30""",
        (int(chat_id),),
    )
    archive = [{**dict(row), "name": str(row["full_name"] or f"ID {row['user_id']}"), "office_title": ROLE_NAMES.get(str(row["office_key"]), str(row["office_key"]))} for row in await cursor.fetchall()]
    return {"officials": officials, "archive": archive}
