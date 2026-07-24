from __future__ import annotations

import math
from typing import Any

import government_reality_v177_common as reality177
import government_v127 as gov
from government_reality_v179_common import BUILDINGS, SOURCE_TITLES, ensure_schema as ensure_schema_v179
from government_reality_v179_trust import trust_state

from government_reality_v180_common import (
    DISTRICTS,
    PLOTS,
    STATIC_LANDMARKS,
    SCHEMA_SQL,
    district_for,
)

PROGRAM_DISTRICTS = {
    "anti_crisis": "government",
    "festival": "culture",
    "social_help": "social",
    "oversight_operation": "security",
    "market_intervention": "government",
    "election_campaign": "government",
    "infrastructure": "industrial",
    "education_grants": "social",
    "emergency_social": "social",
    "cyber_defense": "security",
    "anti_corruption_audit": "security",
    "economy_support": "industrial",
    "information_campaign": "culture",
    "emergency_mode": "security",
    "science_project": "culture",
    "housing_subsidy": "social",
}


async def ensure_schema(core: Any) -> None:
    if getattr(core, "_government_reality_v180_schema_ready", False):
        return
    await ensure_schema_v179(core)
    conn = core.db._require_connection()
    async with core.db.lock:
        if getattr(core, "_government_reality_v180_schema_ready", False):
            return
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()
    core._government_reality_v180_schema_ready = True


def _available_plot(used: set[str], district: str) -> dict[str, Any]:
    for plot in PLOTS:
        if str(plot["district"]) == str(district) and str(plot["plot_id"]) not in used:
            return dict(plot)
    for plot in PLOTS:
        if str(plot["plot_id"]) not in used:
            return dict(plot)
    index = len(used) + 1
    return {
        "plot_id": f"overflow-{index}",
        "district": str(district),
        "slot_no": index,
        "x": 10 + (index * 13) % 80,
        "y": 12 + (index * 17) % 76,
    }


async def sync_map(core: Any, chat_id: int) -> None:
    """Synchronise visual placement with canonical Reality 179 projects/buildings."""
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            """SELECT project_id,building_key,status FROM government_construction_projects_v179
            WHERE chat_id=? AND status NOT IN ('cancelled') ORDER BY created_at,project_id""",
            (int(chat_id),),
        )
        projects = [dict(row) for row in await cursor.fetchall()]
        project_ids = {str(row["project_id"]) for row in projects}

        cursor = await conn.execute(
            """SELECT building_id,project_id,building_key,status FROM government_buildings_v179
            WHERE chat_id=? ORDER BY completed_at,building_id""",
            (int(chat_id),),
        )
        buildings = [dict(row) for row in await cursor.fetchall()]
        building_ids = {str(row["building_id"]) for row in buildings}

        cursor = await conn.execute(
            "SELECT plot_id,project_id,building_id FROM government_map_plots_v180 WHERE chat_id=?",
            (int(chat_id),),
        )
        existing = [dict(row) for row in await cursor.fetchall()]
        used = {str(row["plot_id"]) for row in existing}

        for row in existing:
            project_id = str(row.get("project_id") or "")
            building_id = str(row.get("building_id") or "")
            if building_id and building_id not in building_ids:
                await conn.execute(
                    "UPDATE government_map_plots_v180 SET building_id=NULL,updated_at=? WHERE chat_id=? AND plot_id=?",
                    (now, int(chat_id), str(row["plot_id"])),
                )
                building_id = ""
            if project_id and project_id not in project_ids and not building_id:
                await conn.execute(
                    "DELETE FROM government_map_plots_v180 WHERE chat_id=? AND plot_id=?",
                    (int(chat_id), str(row["plot_id"])),
                )
                used.discard(str(row["plot_id"]))

        for project in projects:
            project_id = str(project["project_id"])
            cursor = await conn.execute(
                "SELECT plot_id FROM government_map_plots_v180 WHERE project_id=?",
                (project_id,),
            )
            placement = await cursor.fetchone()
            if placement is not None:
                await conn.execute(
                    """UPDATE government_map_plots_v180
                    SET building_key=?,status=?,updated_at=? WHERE project_id=?""",
                    (str(project["building_key"]), str(project["status"]), now, project_id),
                )
                continue
            district = district_for(str(project["building_key"]))
            plot = _available_plot(used, district)
            used.add(str(plot["plot_id"]))
            await conn.execute(
                """INSERT INTO government_map_plots_v180(
                chat_id,plot_id,district,slot_no,x,y,project_id,building_id,building_key,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,NULL,?,?,?,?)""",
                (
                    int(chat_id), str(plot["plot_id"]), str(plot["district"]),
                    int(plot["slot_no"]), int(plot["x"]), int(plot["y"]),
                    project_id, str(project["building_key"]), str(project["status"]), now, now,
                ),
            )

        for building in buildings:
            building_id = str(building["building_id"])
            project_id = str(building.get("project_id") or "")
            cursor = await conn.execute(
                """SELECT plot_id FROM government_map_plots_v180
                WHERE building_id=? OR (?<>'' AND project_id=?) LIMIT 1""",
                (building_id, project_id, project_id),
            )
            placement = await cursor.fetchone()
            if placement is not None:
                await conn.execute(
                    """UPDATE government_map_plots_v180
                    SET building_id=?,building_key=?,status=?,updated_at=? WHERE chat_id=? AND plot_id=?""",
                    (
                        building_id, str(building["building_key"]), str(building["status"]), now,
                        int(chat_id), str(placement["plot_id"]),
                    ),
                )
                continue
            district = district_for(str(building["building_key"]))
            plot = _available_plot(used, district)
            used.add(str(plot["plot_id"]))
            await conn.execute(
                """INSERT INTO government_map_plots_v180(
                chat_id,plot_id,district,slot_no,x,y,project_id,building_id,building_key,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    int(chat_id), str(plot["plot_id"]), str(plot["district"]),
                    int(plot["slot_no"]), int(plot["x"]), int(plot["y"]),
                    project_id or None, building_id, str(building["building_key"]),
                    str(building["status"]), now, now,
                ),
            )
        await conn.commit()


async def _top_contributors(conn: Any, project_id: str) -> list[dict[str, Any]]:
    cursor = await conn.execute(
        """SELECT c.user_id,SUM(c.amount) amount,p.full_name,p.username
        FROM government_construction_contributions_v179 c
        LEFT JOIN players p ON p.chat_id=c.chat_id AND p.user_id=c.user_id
        WHERE c.project_id=? GROUP BY c.user_id,p.full_name,p.username
        ORDER BY amount DESC,c.user_id LIMIT 3""",
        (str(project_id),),
    )
    result: list[dict[str, Any]] = []
    for row in await cursor.fetchall():
        username = str(row["username"] or "").strip().lstrip("@")
        name = str(row["full_name"] or "").strip() or (f"@{username}" if username else f"ID {int(row['user_id'])}")
        result.append({"user_id": int(row["user_id"]), "name": name, "amount": int(row["amount"] or 0)})
    return result


def _project_progress(project: Any, now: int) -> int:
    status = str(project["status"])
    if status in {"completed"}:
        return 100
    if status == "building":
        starts_at = int(project["starts_at"] or 0)
        completes_at = int(project["completes_at"] or 0)
        if completes_at <= starts_at:
            return 100
        return max(1, min(99, int((now - starts_at) * 100 / (completes_at - starts_at))))
    return max(0, min(100, int(project["funded_amount"] or 0) * 100 // max(1, int(project["total_cost"] or 1))))


async def map_state(core: Any, chat_id: int, viewer_id: int) -> dict[str, Any]:
    await sync_map(core, int(chat_id))
    conn = core.db._require_connection()
    now = gov._now()

    cursor = await conn.execute(
        "SELECT * FROM government_map_plots_v180 WHERE chat_id=? ORDER BY district,slot_no",
        (int(chat_id),),
    )
    placements = [dict(row) for row in await cursor.fetchall()]
    objects: list[dict[str, Any]] = []
    district_counts = {key: 0 for key in DISTRICTS}

    for placement in placements:
        project_id = str(placement.get("project_id") or "")
        building_id = str(placement.get("building_id") or "")
        project = None
        building = None
        if project_id:
            cursor = await conn.execute(
                """SELECT p.*,pl.full_name initiator_name,pl.username initiator_username
                FROM government_construction_projects_v179 p
                LEFT JOIN players pl ON pl.chat_id=p.chat_id AND pl.user_id=p.initiator_id
                WHERE p.project_id=?""",
                (project_id,),
            )
            project = await cursor.fetchone()
        if building_id:
            cursor = await conn.execute(
                """SELECT b.*,pl.full_name initiator_name,pl.username initiator_username
                FROM government_buildings_v179 b
                LEFT JOIN players pl ON pl.chat_id=b.chat_id AND pl.user_id=b.initiator_id
                WHERE b.building_id=?""",
                (building_id,),
            )
            building = await cursor.fetchone()
        key = str(placement["building_key"])
        spec = BUILDINGS.get(key, {"emoji": "🏗", "title": key, "cost": 0, "effect": ""})
        source_key = str((building["source_key"] if building is not None else project["source_key"] if project is not None else "") or "")
        initiator_name = ""
        initiator_id = 0
        if building is not None or project is not None:
            row = building if building is not None else project
            username = str(row["initiator_username"] or "").strip().lstrip("@")
            initiator_name = str(row["initiator_name"] or "").strip() or (f"@{username}" if username else f"ID {int(row['initiator_id'])}")
            initiator_id = int(row["initiator_id"])
        status = str(building["status"] if building is not None else project["status"] if project is not None else placement["status"])
        progress = 100 if building is not None else _project_progress(project, now) if project is not None else 0
        total_cost = int(project["total_cost"] if project is not None else spec.get("cost", 0))
        funded = int(project["funded_amount"] if project is not None else total_cost if building is not None else 0)
        item = {
            **placement,
            "emoji": str(spec.get("emoji", "🏗")),
            "title": str(spec.get("title", key)),
            "effect": str(spec.get("effect", "")),
            "cost": int(spec.get("cost", total_cost)),
            "maintenance": max(1, int(spec.get("cost", 0)) * int(spec.get("maintenance_bp", 0)) // 10_000) if spec.get("maintenance_bp") else 0,
            "source_key": source_key,
            "source_title": SOURCE_TITLES.get(source_key, source_key),
            "initiator_id": initiator_id,
            "initiator_name": initiator_name,
            "status": status,
            "progress": progress,
            "funded_amount": funded,
            "total_cost": total_cost,
            "remaining": max(0, total_cost - funded),
            "starts_at": int(project["starts_at"] or 0) if project is not None else 0,
            "completes_at": int(project["completes_at"] or 0) if project is not None else 0,
            "completed_at": int(building["completed_at"] or 0) if building is not None else 0,
            "next_income_at": int(building["next_income_at"] or 0) if building is not None else 0,
            "next_maintenance_at": int(building["next_maintenance_at"] or 0) if building is not None else 0,
            "maintenance_debt": int(building["maintenance_debt"] or 0) if building is not None else 0,
            "contributors": await _top_contributors(conn, project_id) if project_id else [],
        }
        objects.append(item)
        district_counts[str(placement["district"])] = district_counts.get(str(placement["district"]), 0) + 1

    cursor = await conn.execute(
        "SELECT treasury FROM government_state_v127 WHERE chat_id=?",
        (int(chat_id),),
    )
    state_row = await cursor.fetchone()
    treasury = int(state_row["treasury"] if state_row else 0)
    trust = await trust_state(core, int(chat_id))

    cursor = await conn.execute(
        """SELECT program_key,started_at,ends_at FROM government_programs_v176
        WHERE chat_id=? AND ends_at>? ORDER BY started_at DESC LIMIT 10""",
        (int(chat_id), now),
    )
    active_programs = []
    for row in await cursor.fetchall():
        key = str(row["program_key"])
        spec = reality177.PROGRAMS.get(key)
        if spec is None:
            continue
        active_programs.append({
            "key": key,
            "emoji": str(spec["emoji"]),
            "title": str(spec["title"]),
            "district": PROGRAM_DISTRICTS.get(key, "government"),
            "ends_at": int(row["ends_at"]),
        })

    built = sum(1 for item in objects if item["building_id"])
    active = sum(1 for item in objects if item["building_id"] and item["status"] == "active")
    underfunded = sum(1 for item in objects if item["status"] == "underfunded")
    construction = sum(1 for item in objects if item["status"] in {"awaiting_vote", "awaiting_funding", "building"})
    debt = sum(int(item["maintenance_debt"]) for item in objects)
    development = max(0, min(100, active * 8 + construction * 2 + max(0, built - underfunded) * 2))
    financial = max(0, min(100, int(math.log10(max(1, treasury + 1)) * 15) - min(35, debt // 50_000)))
    welfare_keys = {"school", "hospital", "housing", "culture_house"}
    welfare = max(0, min(100, sum(12 if item["status"] == "active" else 4 for item in objects if item["building_key"] in welfare_keys)))

    used_plot_ids = {str(item["plot_id"]) for item in objects}
    empty_plots = [dict(plot) for plot in PLOTS if str(plot["plot_id"]) not in used_plot_ids]

    return {
        "version": "Reality 180",
        "districts": [{"key": key, **value, "objects": district_counts.get(key, 0)} for key, value in DISTRICTS.items()],
        "landmarks": [dict(item) for item in STATIC_LANDMARKS],
        "empty_plots": empty_plots,
        "objects": objects,
        "active_programs": active_programs,
        "metrics": {
            "treasury": treasury,
            "trust": int(trust.get("overall", 50)),
            "trust_label": str(trust.get("label", "Нейтральное доверие")),
            "development": development,
            "financial_stability": financial,
            "welfare": welfare,
            "built": built,
            "active": active,
            "underfunded": underfunded,
            "construction": construction,
            "maintenance_debt": debt,
        },
    }
