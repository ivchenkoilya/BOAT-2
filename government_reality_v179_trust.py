from __future__ import annotations

import secrets
from typing import Any

import government_v127 as gov

from government_reality_v179_common import DAY, clamp_trust, ensure_schema


TRUST_LABELS = (
    (20, "Критическое доверие"),
    (40, "Низкое доверие"),
    (60, "Нейтральное доверие"),
    (80, "Высокое доверие"),
    (101, "Народное доверие"),
)


def trust_label(value: int) -> str:
    rating = clamp_trust(value)
    return next(label for limit, label in TRUST_LABELS if rating < limit)


async def adjust_trust(
    core: Any,
    chat_id: int,
    user_id: int,
    delta: int,
    reason: str,
    source: str,
    event_key: str,
    actor_id: int = 0,
) -> bool:
    """Change canonical government_offices_v127.trust once per event key."""
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT 1 FROM government_trust_events_v179 WHERE event_key=?",
            (str(event_key),),
        )
        if await cursor.fetchone() is not None:
            return False
        cursor = await conn.execute(
            """SELECT office_key,seat_no,starts_at,trust FROM government_offices_v127
            WHERE chat_id=? AND user_id=? AND ends_at>?""",
            (int(chat_id), int(user_id), now),
        )
        offices = list(await cursor.fetchall())
        for office in offices:
            after = clamp_trust(int(office["trust"] or 50) + int(delta))
            await conn.execute(
                """UPDATE government_offices_v127 SET trust=?
                WHERE chat_id=? AND office_key=? AND seat_no=? AND starts_at=?""",
                (
                    after,
                    int(chat_id),
                    str(office["office_key"]),
                    int(office["seat_no"]),
                    int(office["starts_at"]),
                ),
            )
            await conn.execute(
                """INSERT INTO government_official_rating_log_v177(
                log_id,chat_id,user_id,office_key,seat_no,office_starts_at,delta,rating_after,
                reason,source,actor_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    secrets.token_urlsafe(12),
                    int(chat_id),
                    int(user_id),
                    str(office["office_key"]),
                    int(office["seat_no"]),
                    int(office["starts_at"]),
                    int(delta),
                    after,
                    str(reason),
                    str(source),
                    int(actor_id),
                    now,
                ),
            )
        await conn.execute(
            """INSERT INTO government_trust_events_v179(
            event_key,chat_id,user_id,delta,reason,source,actor_id,created_at)
            VALUES(?,?,?,?,?,?,?,?)""",
            (
                str(event_key),
                int(chat_id),
                int(user_id),
                int(delta),
                str(reason),
                str(source),
                int(actor_id),
                now,
            ),
        )
        await conn.commit()
    return bool(offices)


async def _group_average(conn: Any, chat_id: int, keys: tuple[str, ...], now: int) -> float | None:
    placeholders = ",".join("?" for _ in keys)
    cursor = await conn.execute(
        f"""SELECT AVG(trust) value FROM government_offices_v127
        WHERE chat_id=? AND office_key IN ({placeholders}) AND ends_at>?""",
        (int(chat_id), *keys, int(now)),
    )
    row = await cursor.fetchone()
    return float(row["value"]) if row and row["value"] is not None else None


async def recalculate_trust(core: Any, chat_id: int, force: bool = False) -> dict[str, Any]:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute(
        "SELECT overall_trust,last_recalc_at FROM government_trust_state_v179 WHERE chat_id=?",
        (int(chat_id),),
    )
    existing = await cursor.fetchone()
    if existing is not None and not force and int(existing["last_recalc_at"] or 0) + 3600 > now:
        value = clamp_trust(int(existing["overall_trust"] or 50))
        return {"overall": value, "label": trust_label(value), "updated_at": int(existing["last_recalc_at"])}

    groups = [
        (30, ("president",)),
        (10, ("chair",)),
        (15, ("deputy",)),
        (15, ("finance",)),
        (10, ("oversight", "oversight_deputy", "security", "prosecutor")),
        (20, ("central_bank", "auditor", "cec", "ombudsman", "press", "supreme_court")),
    ]
    weighted = 0.0
    available_weight = 0
    breakdown: list[dict[str, Any]] = []
    for weight, keys in groups:
        average = await _group_average(conn, int(chat_id), keys, now)
        if average is None:
            continue
        weighted += average * weight
        available_weight += weight
        breakdown.append({"keys": list(keys), "weight": weight, "rating": round(average, 1)})
    overall = clamp_trust(round(weighted / available_weight)) if available_weight else 50
    await conn.execute(
        """INSERT INTO government_trust_state_v179(chat_id,overall_trust,last_recalc_at,updated_at)
        VALUES(?,?,?,?) ON CONFLICT(chat_id) DO UPDATE SET
        overall_trust=excluded.overall_trust,last_recalc_at=excluded.last_recalc_at,updated_at=excluded.updated_at""",
        (int(chat_id), overall, now, now),
    )
    await conn.commit()
    return {"overall": overall, "label": trust_label(overall), "updated_at": now, "breakdown": breakdown}


async def presidential_state_adjustment(core: Any, chat_id: int) -> None:
    """A bounded hourly state signal; never changes trust merely by opening the page."""
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    bucket = now // 3600
    cursor = await conn.execute(
        """SELECT user_id FROM government_offices_v127
        WHERE chat_id=? AND office_key='president' AND ends_at>? LIMIT 1""",
        (int(chat_id), now),
    )
    president = await cursor.fetchone()
    if president is None:
        return
    cursor = await conn.execute(
        "SELECT treasury FROM government_state_v127 WHERE chat_id=?",
        (int(chat_id),),
    )
    state = await cursor.fetchone()
    treasury = int(state["treasury"] if state else 0)
    cursor = await conn.execute(
        """SELECT
        SUM(CASE WHEN status='completed' AND updated_at>=? THEN 1 ELSE 0 END) completed,
        SUM(CASE WHEN status='frozen' THEN 1 ELSE 0 END) frozen
        FROM government_construction_projects_v179 WHERE chat_id=?""",
        (now - 7 * DAY, int(chat_id)),
    )
    projects = await cursor.fetchone()
    completed = int(projects["completed"] or 0) if projects else 0
    frozen = int(projects["frozen"] or 0) if projects else 0
    delta = 0
    reasons: list[str] = []
    if treasury >= 1_000_000:
        delta += 1
        reasons.append("устойчивая общая казна")
    if completed:
        delta += min(2, completed)
        reasons.append("завершённые стройки")
    if frozen:
        delta -= min(3, frozen)
        reasons.append("замороженные стройки")
    if not delta:
        return
    await adjust_trust(
        core,
        int(chat_id),
        int(president["user_id"]),
        delta,
        ", ".join(reasons).capitalize(),
        "state_health",
        f"president-state:{chat_id}:{bucket}",
        0,
    )


async def trust_state(core: Any, chat_id: int) -> dict[str, Any]:
    overall = await recalculate_trust(core, int(chat_id))
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """SELECT source,COALESCE(SUM(delta),0) delta FROM government_trust_events_v179
        WHERE chat_id=? AND created_at>=? GROUP BY source ORDER BY ABS(delta) DESC""",
        (int(chat_id), gov._now() - 7 * DAY),
    )
    sources = [dict(row) for row in await cursor.fetchall()]
    cursor = await conn.execute(
        """SELECT user_id,delta,reason,source,created_at FROM government_trust_events_v179
        WHERE chat_id=? ORDER BY created_at DESC LIMIT 20""",
        (int(chat_id),),
    )
    history = [dict(row) for row in await cursor.fetchall()]
    return {**overall, "sources_7d": sources, "history": history}
