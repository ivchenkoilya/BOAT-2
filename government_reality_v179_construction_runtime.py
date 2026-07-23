from __future__ import annotations

import html
import secrets
from typing import Any

import government_v127 as gov

from government_reality_v179_common import BUILDINGS, DAY, MAX_BUILDINGS_PER_TYPE, WEEK, ensure_schema, score_title
from government_reality_v179_construction_core import (
    BASE_PROPOSERS, PROFILE_SOURCES, _log, debit_source_locked, effects_snapshot, source_balance,
)
from government_reality_v179_trust import adjust_trust


async def process_construction(core: Any, bot: Any) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()

    cursor = await conn.execute(
        """SELECT p.project_id,p.chat_id,p.initiator_id,p.bill_id,b.status bill_status
        FROM government_construction_projects_v179 p JOIN government_bills_v127 b ON b.bill_id=p.bill_id
        WHERE p.status='awaiting_vote' AND b.status IN ('rejected','vetoed','expired')"""
    )
    rejected_rows = list(await cursor.fetchall())
    for row in rejected_rows:
        await conn.execute("UPDATE government_construction_projects_v179 SET status='cancelled',cancelled_reason=?,updated_at=? WHERE project_id=? AND status='awaiting_vote'", (f"Законопроект: {row['bill_status']}", now, str(row["project_id"])))
    await conn.commit()
    for row in rejected_rows:
        await adjust_trust(core, int(row["chat_id"]), int(row["initiator_id"]), -3, "Строительный проект отклонён", "construction", f"project-rejected:{row['project_id']}", 0)

    cursor = await conn.execute("SELECT * FROM government_construction_projects_v179 WHERE status='building' AND completes_at<=?", (now,))
    for project in list(await cursor.fetchall()):
        spec = BUILDINGS[str(project["building_key"])]
        async with core.db.lock:
            try:
                cursor2 = await conn.execute("UPDATE government_construction_projects_v179 SET status='completed',updated_at=? WHERE project_id=? AND status='building'", (now, str(project["project_id"])))
                if int(cursor2.rowcount or 0) <= 0:
                    continue
                cursor2 = await conn.execute("SELECT COUNT(*) amount FROM government_buildings_v179 WHERE chat_id=? AND building_key=?", (int(project["chat_id"]), str(project["building_key"])))
                level_no = int((await cursor2.fetchone())["amount"]) + 1
                building_id = secrets.token_urlsafe(12)
                await conn.execute(
                    """INSERT INTO government_buildings_v179(
                    building_id,project_id,chat_id,building_key,level_no,status,source_key,initiator_id,
                    completed_at,next_income_at,next_maintenance_at,maintenance_debt,updated_at)
                    VALUES(?,?,?,?,?,'active',?,?,?,?,?,0,?)""",
                    (building_id, str(project["project_id"]), int(project["chat_id"]), str(project["building_key"]), level_no, str(project["source_key"]), int(project["initiator_id"]), now, now + DAY if str(project["building_key"]) == "factory" else 0, now + WEEK, now),
                )
                await conn.execute("INSERT INTO government_building_effects_v179(building_id,effect_key,value,active,updated_at) VALUES(?,?,?,1,?)", (building_id, str(project["building_key"]), level_no, now))
                await _log(core, int(project["chat_id"]), "construction_completed", f"Завершено строительство: {spec['title']}", project_id=str(project["project_id"]), building_id=building_id, actor_id=int(project["initiator_id"]), amount=int(project["total_cost"]))
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise
        await adjust_trust(core, int(project["chat_id"]), int(project["initiator_id"]), int(spec["trust"]), f"Завершено строительство: {spec['title']}", "construction", f"project-completed:{project['project_id']}", 0)
        await gov._publish(bot, int(project["chat_id"]), f"{spec['emoji']} <b>ГОСУДАРСТВЕННЫЙ ОБЪЕКТ ПОСТРОЕН</b>\n\n<b>{html.escape(spec['title'])}</b> начал работу.\nЭффект: {html.escape(spec['effect'])}")

    cursor = await conn.execute("SELECT * FROM government_buildings_v179 WHERE building_key='factory' AND status='active' AND next_income_at>0 AND next_income_at<=?", (now,))
    for building in list(await cursor.fetchall()):
        period_at = int(building["next_income_at"])
        effects = await effects_snapshot(core, int(building["chat_id"]))
        amount = int(BUILDINGS["factory"]["cost"]) // 45
        amount += amount * int(effects["factory_income_bonus_percent"]) // 100
        async with core.db.lock:
            cursor2 = await conn.execute("INSERT OR IGNORE INTO government_building_income_v179(building_id,period_at,amount,created_at) VALUES(?,?,?,?)", (str(building["building_id"]), period_at, amount, now))
            if int(cursor2.rowcount or 0) > 0:
                await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (amount, now, int(building["chat_id"])))
                await conn.execute("UPDATE government_buildings_v179 SET next_income_at=?,updated_at=? WHERE building_id=?", (period_at + DAY, now, str(building["building_id"])))
                await gov._treasury_log(core, int(building["chat_id"]), amount, "Доход государственного завода", "factory_income_v179", str(building["building_id"]), 0)
                await _log(core, int(building["chat_id"]), "factory_income", "Доход государственного завода", building_id=str(building["building_id"]), amount=amount)
                await conn.commit()

    cursor = await conn.execute("SELECT * FROM government_buildings_v179 WHERE next_maintenance_at<=?", (now,))
    for building in list(await cursor.fetchall()):
        spec = BUILDINGS[str(building["building_key"])]
        period_at = int(building["next_maintenance_at"])
        amount = max(1, int(spec["cost"]) * int(spec["maintenance_bp"]) // 10_000)
        source_key = str(building["source_key"])
        paid = False
        async with core.db.lock:
            cursor2 = await conn.execute("SELECT 1 FROM government_building_maintenance_v179 WHERE building_id=? AND period_at=?", (str(building["building_id"]), period_at))
            if await cursor2.fetchone() is not None:
                await conn.execute("UPDATE government_buildings_v179 SET next_maintenance_at=? WHERE building_id=?", (period_at + WEEK, str(building["building_id"])))
                await conn.commit()
                continue
            try:
                await debit_source_locked(core, int(building["chat_id"]), source_key, amount)
                paid = True
            except ValueError:
                paid = False
            await conn.execute("INSERT INTO government_building_maintenance_v179(building_id,period_at,amount,paid,source_key,created_at) VALUES(?,?,?,?,?,?)", (str(building["building_id"]), period_at, amount, 1 if paid else 0, source_key, now))
            if paid:
                await conn.execute("UPDATE government_buildings_v179 SET next_maintenance_at=?,updated_at=? WHERE building_id=?", (period_at + WEEK, now, str(building["building_id"])))
                await _log(core, int(building["chat_id"]), "maintenance_paid", f"Оплачено содержание: {spec['title']}", building_id=str(building["building_id"]), amount=amount)
            else:
                await conn.execute("UPDATE government_buildings_v179 SET status='underfunded',maintenance_debt=maintenance_debt+?,next_maintenance_at=?,updated_at=? WHERE building_id=?", (amount, period_at + WEEK, now, str(building["building_id"])))
                await conn.execute("INSERT INTO government_building_debts_v179(building_id,chat_id,amount,updated_at) VALUES(?,?,?,?) ON CONFLICT(building_id) DO UPDATE SET amount=government_building_debts_v179.amount+excluded.amount,updated_at=excluded.updated_at", (str(building["building_id"]), int(building["chat_id"]), amount, now))
                await conn.execute("UPDATE government_building_effects_v179 SET active=0,updated_at=? WHERE building_id=?", (now, str(building["building_id"])))
                await _log(core, int(building["chat_id"]), "maintenance_debt", f"Недостаточное финансирование: {spec['title']}", building_id=str(building["building_id"]), amount=amount)
            await conn.commit()
        if paid:
            await adjust_trust(core, int(building["chat_id"]), int(building["initiator_id"]), 1, "Содержание государственного объекта оплачено вовремя", "construction_maintenance", f"maintenance-paid:{building['building_id']}:{period_at}", 0)
        else:
            await adjust_trust(core, int(building["chat_id"]), int(building["initiator_id"]), -2, "Объект остался без финансирования", "construction_maintenance", f"maintenance-debt:{building['building_id']}:{period_at}", 0)


async def construction_state(core: Any, chat_id: int, viewer_id: int) -> dict[str, Any]:
    await ensure_schema(core)
    conn = core.db._require_connection()
    offices = await gov._user_offices(core, int(chat_id), int(viewer_id))
    is_admin = int(viewer_id) == int(core.DEVELOPER_ID)
    sanctioned = await gov._has_active_sanctions(core, int(chat_id), int(viewer_id))
    can_propose = bool(is_admin or (not sanctioned and (set(offices).intersection(BASE_PROPOSERS) or any(key in PROFILE_SOURCES for key in offices))))
    catalog = []
    for key, spec in BUILDINGS.items():
        cursor = await conn.execute("SELECT COUNT(*) amount FROM government_construction_projects_v179 WHERE chat_id=? AND building_key=? AND status NOT IN ('cancelled')", (int(chat_id), key))
        count = int((await cursor.fetchone())["amount"])
        balances = {source: await source_balance(core, int(chat_id), source) for source in spec["sources"]}
        catalog.append({"key": key, **spec, "sources": [{"key": source, "title": SOURCE_TITLES[source], "balance": balances[source]} for source in spec["sources"]], "count": count, "available": count < MAX_BUILDINGS_PER_TYPE})
    cursor = await conn.execute("""SELECT p.*,pl.full_name initiator_name FROM government_construction_projects_v179 p LEFT JOIN players pl ON pl.chat_id=p.chat_id AND pl.user_id=p.initiator_id WHERE p.chat_id=? ORDER BY p.created_at DESC LIMIT 80""", (int(chat_id),))
    projects = [{**dict(row), "initiator_name": str(row["initiator_name"] or f"ID {row['initiator_id']}"), "spec": {"emoji": BUILDINGS[str(row["building_key"])]["emoji"], "title": BUILDINGS[str(row["building_key"])]["title"]}, "remaining": max(0, int(row["total_cost"]) - int(row["funded_amount"]))} for row in await cursor.fetchall()]
    cursor = await conn.execute("""SELECT b.*,p.full_name initiator_name FROM government_buildings_v179 b LEFT JOIN players p ON p.chat_id=b.chat_id AND p.user_id=b.initiator_id WHERE b.chat_id=? ORDER BY b.completed_at DESC""", (int(chat_id),))
    buildings = [{**dict(row), "initiator_name": str(row["initiator_name"] or f"ID {row['initiator_id']}"), "spec": {"emoji": BUILDINGS[str(row["building_key"])]["emoji"], "title": BUILDINGS[str(row["building_key"])]["title"], "effect": BUILDINGS[str(row["building_key"])]["effect"], "maintenance": max(1, BUILDINGS[str(row["building_key"])]["cost"] * BUILDINGS[str(row["building_key"])]["maintenance_bp"] // 10_000)}} for row in await cursor.fetchall()]
    cursor = await conn.execute("""SELECT s.*,p.full_name FROM government_construction_scores_v179 s LEFT JOIN players p ON p.chat_id=s.chat_id AND p.user_id=s.user_id WHERE s.chat_id=? ORDER BY s.score DESC,s.amount DESC LIMIT 20""", (int(chat_id),))
    ranking = [{**dict(row), "name": str(row["full_name"] or f"ID {row['user_id']}"), "title": score_title(int(row["score"]))} for row in await cursor.fetchall()]
    cursor = await conn.execute("SELECT * FROM government_construction_log_v179 WHERE chat_id=? ORDER BY created_at DESC LIMIT 40", (int(chat_id),))
    history = [dict(row) for row in await cursor.fetchall()]
    return {"catalog": catalog, "projects": projects, "buildings": buildings, "effects": await effects_snapshot(core, int(chat_id)), "ranking": ranking, "history": history, "can_propose": can_propose, "offices": offices}
