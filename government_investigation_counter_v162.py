from __future__ import annotations

from typing import Any

import government_crisis_v131 as crisis
import government_v127 as gov


VERSION = "Reality 162 · Точный счётчик расследований"


async def _evidence_totals(core: Any, theft_ids: list[str]) -> dict[str, dict[str, int]]:
    if not theft_ids:
        return {}
    conn = core.db._require_connection()
    placeholders = ",".join("?" for _ in theft_ids)
    try:
        cursor = await conn.execute(
            f"""
            SELECT theft_id,
                   COUNT(*) AS checks,
                   COALESCE(SUM(points), 0) AS points,
                   COUNT(DISTINCT office_key) AS organs
            FROM government_theft_evidence_v153
            WHERE theft_id IN ({placeholders})
            GROUP BY theft_id
            """,
            tuple(str(value) for value in theft_ids),
        )
    except Exception:
        return {}
    return {
        str(row["theft_id"]): {
            "checks": int(row["checks"] or 0),
            "points": int(row["points"] or 0),
            "organs": int(row["organs"] or 0),
        }
        for row in await cursor.fetchall()
    }


def install_government_investigation_counter_v162(core: Any) -> None:
    if getattr(core, "_government_investigation_counter_v162_installed", False):
        return
    core._government_investigation_counter_v162_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    previous_serialize = crisis._serialize_crisis

    async def serialize_with_real_investigation_count(
        core_arg: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await previous_serialize(core_arg, int(chat_id), int(user_id))
        theft = payload.setdefault("theft", {})
        items = list(theft.get("items") or [])
        totals = await _evidence_totals(
            core_arg,
            [str(item.get("theft_id") or "") for item in items if item.get("theft_id")],
        )
        for item in items:
            value = totals.get(str(item.get("theft_id") or ""), {})
            modern_checks = int(value.get("checks") or 0)
            legacy_checks = int(item.get("investigations") or 0)
            item["investigations"] = max(legacy_checks, modern_checks)
            item["evidence_points"] = int(value.get("points") or 0)
            item["evidence_organs"] = int(value.get("organs") or 0)
        theft["items"] = items
        payload["version"] = VERSION
        return payload

    crisis._serialize_crisis = serialize_with_real_investigation_count
