from __future__ import annotations

import json
from typing import Any

import government_v127 as gov

VERSION = "Reality 167 · Заместитель главы Надзора"
OFFICE_KEY = "oversight_deputy"
OFFICE_SPEC = {"emoji": "🕵️", "title": "Заместитель главы Надзора за гондонами", "threshold": 200_000, "seats": 1}
DAY = 86_400
WEEK = 7 * DAY

def _routes(app: Any) -> set[tuple[str, str]]:
    return {
        (
            str(getattr(route, "method", "") or "").upper(),
            str(getattr(getattr(route, "resource", None), "canonical", "") or ""),
        )
        for route in app.router.routes()
    }

async def _person(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    person = await gov._player_dict(core, chat_id, user_id)
    if person is None:
        raise ValueError("Участник не найден в этой беседе.")
    return person

async def _access(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    offices = await gov._user_offices(core, chat_id, user_id)
    admin = user_id == int(core.DEVELOPER_ID)
    return {
        "offices": offices,
        "is_admin": admin,
        "is_head": "oversight" in offices,
        "is_deputy": OFFICE_KEY in offices,
        "can_manage": admin or "oversight" in offices or OFFICE_KEY in offices,
        "can_propose_appointment": admin or "president" in offices or "oversight" in offices,
        "can_file_complaint": True,
    }

async def _cases(core: Any, chat_id: int, case_type: str) -> list[dict[str, Any]]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT c.*,p.full_name target_name,p.username target_username
        FROM government_cases_v128 c
        LEFT JOIN players p ON p.chat_id=c.chat_id AND p.user_id=c.target_user_id
        WHERE c.chat_id=? AND c.institution='oversight_deputy' AND c.case_type=?
        ORDER BY CASE c.status WHEN 'open' THEN 0 WHEN 'investigating' THEN 1
                              WHEN 'referred' THEN 2 ELSE 3 END,c.updated_at DESC
        LIMIT 60
        """,
        (chat_id, case_type),
    )
    result = []
    for row in await cursor.fetchall():
        payload = gov._json(row["payload_json"], {})
        name = str(row["target_name"] or (f"@{row['target_username']}" if row["target_username"] else "") or f"ID {row['target_user_id']}")
        if case_type == "complaint":
            result.append({
                "complaint_id": str(row["case_id"]),
                "author_id": int(row["created_by"]),
                "author_name": str(payload.get("author_name") or f"ID {row['created_by']}"),
                "target_user_id": int(row["target_user_id"]),
                "target_name": name,
                "reason": str(row["description"]),
                "evidence": str(payload.get("evidence") or ""),
                "status": "pending" if str(row["status"]) == "open" else str(row["status"]),
                "assigned_to": int(payload.get("assigned_to") or 0),
                "created_at": int(row["created_at"]),
                "updated_at": int(row["updated_at"]),
            })
        else:
            result.append({
                "case_id": str(row["case_id"]),
                "complaint_id": str(payload.get("complaint_id") or ""),
                "target_user_id": int(row["target_user_id"]),
                "target_name": name,
                "opened_by": int(row["created_by"]),
                "case_type": "inspection",
                "title": str(row["title"]),
                "facts": str(row["description"]),
                "status": str(row["status"]),
                "conclusion": str(payload.get("conclusion") or ""),
                "bill_id": str(payload.get("bill_id") or ""),
                "created_at": int(row["created_at"]),
                "updated_at": int(row["updated_at"]),
            })
    return result

async def _warnings(core: Any, chat_id: int) -> list[dict[str, Any]]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT l.*,p.full_name target_name,p.username target_username
        FROM government_power_log_v128 l
        LEFT JOIN players p ON p.chat_id=l.chat_id AND p.user_id=l.target_user_id
        WHERE l.chat_id=? AND l.action_key='deputy_warning'
        ORDER BY l.created_at DESC LIMIT 60
        """,
        (chat_id,),
    )
    now = gov._now()
    rows = []
    for row in await cursor.fetchall():
        payload = gov._json(row["payload_json"], {})
        rows.append({
            "warning_id": str(row["action_id"]),
            "target_user_id": int(row["target_user_id"]),
            "target_name": str(row["target_name"] or (f"@{row['target_username']}" if row["target_username"] else "") or f"ID {row['target_user_id']}"),
            "issued_by": int(row["actor_id"]),
            "reason": str(row["detail"]),
            "expires_at": int(payload.get("expires_at") or 0),
            "active": int(payload.get("expires_at") or 0) > now,
            "created_at": int(row["created_at"]),
        })
    return rows

async def _usage(core: Any, chat_id: int, actor_id: int, action: str, period: int) -> tuple[int, int]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT COUNT(*) amount,COALESCE(MAX(created_at),0) latest
        FROM government_power_log_v128
        WHERE chat_id=? AND actor_id=? AND action_key=? AND created_at>=?
        """,
        (chat_id, actor_id, action, gov._now() - period),
    )
    row = await cursor.fetchone()
    return int(row["amount"]), int(row["latest"])

async def _state(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    access = await _access(core, chat_id, user_id)
    used, latest = await _usage(core, chat_id, user_id, "deputy_inspection", DAY)
    limit = 999 if access["is_admin"] else 3 if access["is_head"] else 1
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT MAX(created_at) latest FROM government_power_log_v128 WHERE chat_id=? AND action_key='deputy_weekly_report'",
        (chat_id,),
    )
    row = await cursor.fetchone()
    report_at = int(row["latest"] or 0)
    return {
        **access,
        "office_key": OFFICE_KEY,
        "office_spec": OFFICE_SPEC,
        "inspection_limit_24h": limit,
        "inspection_used_24h": used,
        "inspection_available_at": latest + DAY if used >= limit and latest else 0,
        "last_report_at": report_at,
        "report_available_at": report_at + WEEK if report_at else 0,
        "complaints": await _cases(core, chat_id, "complaint"),
        "cases": await _cases(core, chat_id, "inspection"),
        "warnings": await _warnings(core, chat_id),
    }
