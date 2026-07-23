from __future__ import annotations

import html
import json
import secrets
from typing import Any

import government_reality_v177_funds as fund_bridge
import government_v127 as gov

from government_reality_v179_common import (
    BUILDINGS,
    DAY,
    DIRECT_PROJECT_LIMIT,
    MAX_BUILDINGS_PER_TYPE,
    SOURCE_TITLES,
    WEEK,
    ensure_schema,
    score_title,
)
from government_reality_v179_trust import adjust_trust


PROFILE_SOURCES = {
    "finance": {"state_treasury", "finance_ministry", "event_fund", "social_fund", "reserve"},
    "oversight": {"oversight"}, "oversight_deputy": {"oversight"},
    "security": {"oversight", "reserve"}, "ombudsman": {"social_fund"},
    "press": {"event_fund"}, "central_bank": {"finance_ministry"},
    "auditor": {"state_treasury", "finance_ministry"},
}
BASE_PROPOSERS = {"president", "finance", "chair", "deputy"}


def _diminishing(count: int, first: int, second: int, third: int) -> int:
    return (0, first, first + second, first + second + third)[max(0, min(3, int(count)))]


async def active_count(core: Any, chat_id: int, building_key: str) -> int:
    await ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """SELECT COUNT(*) amount FROM government_buildings_v179
        WHERE chat_id=? AND building_key=? AND status='active'""",
        (int(chat_id), str(building_key)),
    )
    row = await cursor.fetchone()
    return int(row["amount"] if row else 0)


async def effects_snapshot(core: Any, chat_id: int) -> dict[str, Any]:
    counts = {key: await active_count(core, int(chat_id), key) for key in BUILDINGS}
    return {
        "counts": counts,
        "education_bonus_percent": _diminishing(counts["school"], 10, 6, 3),
        "social_bonus_percent": _diminishing(counts["hospital"], 10, 6, 3),
        "festival_bonus_percent": _diminishing(counts["culture_house"], 10, 6, 3),
        "science_bonus_percent": _diminishing(counts["science"], 15, 8, 4),
        "property_maintenance_discount_percent": _diminishing(counts["housing"], 5, 3, 2),
        "bank_fee_discount_percent": _diminishing(counts["state_bank"], 10, 6, 3),
        "treasury_loss_reduction_percent": _diminishing(counts["police"], 10, 6, 3),
        "factory_income_bonus_percent": _diminishing(counts["power_plant"], 15, 8, 4),
        "reporting_bonus": counts["administration"],
    }


async def source_balance(core: Any, chat_id: int, source_key: str) -> int:
    await gov._ensure_state(core, int(chat_id))
    await fund_bridge.migrate_funds(core)
    return await source_balance_locked(core, int(chat_id), str(source_key))


async def source_balance_locked(core: Any, chat_id: int, source_key: str) -> int:
    conn = core.db._require_connection()
    if str(source_key) == "state_treasury":
        cursor = await conn.execute(
            "SELECT treasury FROM government_state_v127 WHERE chat_id=?",
            (int(chat_id),),
        )
    else:
        cursor = await conn.execute(
            "SELECT balance FROM government_structure_funds_v164 WHERE chat_id=? AND structure_key=?",
            (int(chat_id), str(source_key)),
        )
    row = await cursor.fetchone()
    if row is None:
        return 0
    return int(row["treasury"] if str(source_key) == "state_treasury" else row["balance"])


async def debit_source_locked(core: Any, chat_id: int, source_key: str, amount: int) -> None:
    conn = core.db._require_connection()
    if str(source_key) == "state_treasury":
        cursor = await conn.execute(
            """UPDATE government_state_v127 SET treasury=treasury-?,updated_at=?
            WHERE chat_id=? AND treasury>=?""",
            (int(amount), gov._now(), int(chat_id), int(amount)),
        )
        if int(cursor.rowcount or 0) <= 0:
            raise ValueError("В общей казне недостаточно средств.")
        return
    await fund_bridge.debit_fund_locked(core, int(chat_id), str(source_key), int(amount))


async def _log(core: Any, chat_id: int, operation_type: str, detail: str, *, project_id: str = "", building_id: str = "", actor_id: int = 0, amount: int = 0) -> None:
    await core.db._require_connection().execute(
        """INSERT INTO government_construction_log_v179(
        log_id,chat_id,project_id,building_id,operation_type,actor_id,amount,detail,created_at)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        (secrets.token_urlsafe(12), int(chat_id), str(project_id), str(building_id), str(operation_type), int(actor_id), int(amount), str(detail), gov._now()),
    )


async def _can_propose(core: Any, chat_id: int, user_id: int, source_key: str) -> tuple[list[str], str]:
    offices = await gov._user_offices(core, int(chat_id), int(user_id))
    if int(user_id) == int(core.DEVELOPER_ID):
        return offices, "Владелец проекта"
    if await gov._has_active_sanctions(core, int(chat_id), int(user_id)):
        raise PermissionError("Чиновник с активными санкциями не может начинать строительство.")
    allowed = bool(set(offices).intersection(BASE_PROPOSERS))
    if not allowed:
        allowed = any(str(source_key) in PROFILE_SOURCES.get(key, set()) for key in offices)
    if not allowed:
        raise PermissionError("У вашей должности нет права предлагать этот строительный проект.")
    office = next((key for key in offices if key in BASE_PROPOSERS), offices[0] if offices else "")
    return offices, office


async def _start_if_ready_locked(core: Any, project_id: str) -> bool:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_construction_projects_v179 WHERE project_id=?",
        (str(project_id),),
    )
    project = await cursor.fetchone()
    if project is None or str(project["status"]) != "awaiting_funding":
        return False
    if int(project["funded_amount"]) < int(project["total_cost"]):
        return False
    spec = BUILDINGS[str(project["building_key"])]
    now = gov._now()
    cursor = await conn.execute(
        """UPDATE government_construction_projects_v179
        SET status='building',starts_at=?,completes_at=?,updated_at=?
        WHERE project_id=? AND status='awaiting_funding' AND funded_amount>=total_cost""",
        (now, now + int(spec["duration"]), now, str(project_id)),
    )
    if int(cursor.rowcount or 0) <= 0:
        return False
    await _log(core, int(project["chat_id"]), "construction_started", f"Начато строительство: {spec['title']}", project_id=str(project_id), actor_id=int(project["initiator_id"]), amount=int(project["total_cost"]))
    return True


async def _create_bill_locked(core: Any, chat_id: int, actor_id: int, project_id: str, spec: dict[str, Any], number: int) -> str:
    conn = core.db._require_connection()
    bill_id = secrets.token_urlsafe(12)
    now = gov._now()
    await conn.execute(
        """INSERT INTO government_bills_v127(
        bill_id,chat_id,number,title,description,bill_type,payload_json,author_id,status,
        created_at,voting_ends_at,president_review_ends_at,resolved_at)
        VALUES(?,?,?,?,?,'general',?,?,'voting',?,?,0,0)""",
        (
            bill_id, int(chat_id), int(number), f"Строительство: {spec['title']}",
            f"Утвердить государственный проект стоимостью {gov._fmt(int(spec['cost']))} влияния.",
            json.dumps({"construction_project_id": str(project_id)}, ensure_ascii=False),
            int(actor_id), now, now + int(gov.BILL_VOTING_SECONDS),
        ),
    )
    return bill_id


async def propose_project(core: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    await ensure_schema(core)
    await fund_bridge.migrate_funds(core)
    key = str(data.get("building_key") or "")
    spec = BUILDINGS.get(key)
    if spec is None:
        raise ValueError("Неизвестный государственный объект.")
    source_key = str(data.get("source_key") or spec["sources"][0])
    if source_key not in spec["sources"]:
        raise ValueError("Этот объект нельзя финансировать из выбранного источника.")
    offices, office = await _can_propose(core, int(chat_id), int(actor_id), source_key)
    request_id = str(data.get("request_id") or "").strip() or secrets.token_urlsafe(16)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT project_id,status FROM government_construction_projects_v179 WHERE request_id=?",
        (request_id,),
    )
    prior = await cursor.fetchone()
    if prior is not None:
        return f"Проект уже зарегистрирован: {prior['project_id']} · {prior['status']}."
    cursor = await conn.execute(
        """SELECT COUNT(*) amount FROM government_construction_projects_v179
        WHERE chat_id=? AND building_key=? AND status NOT IN ('cancelled')""",
        (int(chat_id), key),
    )
    count = int((await cursor.fetchone())["amount"])
    if count >= MAX_BUILDINGS_PER_TYPE:
        raise ValueError("Можно иметь максимум три объекта одного типа.")

    project_id = secrets.token_urlsafe(12)
    now = gov._now()
    direct = bool(int(actor_id) == int(core.DEVELOPER_ID) or ("president" in offices and int(spec["cost"]) <= DIRECT_PROJECT_LIMIT))
    status = "awaiting_funding" if direct else "awaiting_vote"
    bill_id = ""
    bill_number = 0 if direct else await gov._next_number(core, int(chat_id), "bill_seq")
    direct_available = await source_balance(core, int(chat_id), source_key) if direct else 0
    async with core.db.lock:
        try:
            await conn.execute(
                """INSERT INTO government_construction_projects_v179(
                project_id,chat_id,building_key,initiator_id,initiator_office,source_key,total_cost,
                funded_amount,status,request_id,bill_id,created_at,starts_at,completes_at,cancelled_reason,updated_at)
                VALUES(?,?,?,?,?,?,?,0,?,?,?, ?,0,0,'',?)""",
                (project_id, int(chat_id), key, int(actor_id), str(office), source_key, int(spec["cost"]), status, request_id, bill_id, now, now),
            )
            if not direct:
                bill_id = await _create_bill_locked(core, int(chat_id), int(actor_id), project_id, spec, bill_number)
                await conn.execute(
                    "UPDATE government_construction_projects_v179 SET bill_id=?,updated_at=? WHERE project_id=?",
                    (bill_id, now, project_id),
                )
            else:
                if direct_available >= int(spec["cost"]):
                    await debit_source_locked(core, int(chat_id), source_key, int(spec["cost"]))
                    await conn.execute(
                        "UPDATE government_construction_projects_v179 SET funded_amount=? WHERE project_id=?",
                        (int(spec["cost"]), project_id),
                    )
                    await conn.execute(
                        """INSERT INTO government_construction_funding_v179(
                        funding_id,project_id,chat_id,source_type,source_key,actor_id,amount,request_id,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?)""",
                        (secrets.token_urlsafe(12), project_id, int(chat_id), "government", source_key, int(actor_id), int(spec["cost"]), f"direct:{request_id}", now),
                    )
                    await _start_if_ready_locked(core, project_id)
            await _log(core, int(chat_id), "project_proposed", f"Предложен объект: {spec['title']}", project_id=project_id, actor_id=int(actor_id), amount=int(spec["cost"]))
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    if direct:
        text = f"{spec['emoji']} <b>ГОСУДАРСТВЕННАЯ СТРОЙКА СОЗДАНА</b>\n\n<b>{html.escape(spec['title'])}</b>\nСтоимость: <b>{gov._fmt(spec['cost'])}</b>\nИсточник: <b>{html.escape(SOURCE_TITLES[source_key])}</b>\n\nПроект утверждён прямым решением Президента и начнётся после полного финансирования."
    else:
        text = f"{spec['emoji']} <b>СТРОИТЕЛЬНЫЙ ПРОЕКТ ВНЕСЁН В ГОСДУМУ</b>\n\n<b>{html.escape(spec['title'])}</b>\nСтоимость: <b>{gov._fmt(spec['cost'])}</b>\nЗаконопроект: <b>{html.escape(bill_id)}</b>."
    await gov._publish(bot, int(chat_id), text)
    return f"Проект «{spec['title']}» зарегистрирован."


async def approve_project(core: Any, bot: Any, chat_id: int, project_id: str, actor_id: int) -> None:
    await ensure_schema(core)
    await fund_bridge.migrate_funds(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_construction_projects_v179 WHERE project_id=? AND chat_id=?",
        (str(project_id), int(chat_id)),
    )
    project = await cursor.fetchone()
    if project is None or str(project["status"]) != "awaiting_vote":
        return
    available = await source_balance_locked(core, int(chat_id), str(project["source_key"]))
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT * FROM government_construction_projects_v179 WHERE project_id=? AND chat_id=?",
            (str(project_id), int(chat_id)),
        )
        project = await cursor.fetchone()
        if project is None or str(project["status"]) != "awaiting_vote":
            return
        await conn.execute(
            "UPDATE government_construction_projects_v179 SET status='awaiting_funding',updated_at=? WHERE project_id=?",
            (gov._now(), str(project_id)),
        )
        remaining = int(project["total_cost"]) - int(project["funded_amount"])
        if remaining > 0 and available >= remaining:
            try:
                await debit_source_locked(core, int(chat_id), str(project["source_key"]), remaining)
            except ValueError:
                remaining = 0
            if remaining > 0:
                await conn.execute(
                    "UPDATE government_construction_projects_v179 SET funded_amount=funded_amount+? WHERE project_id=?",
                    (remaining, str(project_id)),
                )
                await conn.execute(
                    """INSERT INTO government_construction_funding_v179(
                    funding_id,project_id,chat_id,source_type,source_key,actor_id,amount,request_id,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (secrets.token_urlsafe(12), str(project_id), int(chat_id), "government", str(project["source_key"]), int(actor_id), remaining, f"law:{project['bill_id']}", gov._now()),
                )
        await _start_if_ready_locked(core, str(project_id))
        await _log(core, int(chat_id), "project_approved", "Проект утверждён законом", project_id=str(project_id), actor_id=int(actor_id))
        await conn.commit()
    await gov._publish(bot, int(chat_id), "🏗 <b>СТРОИТЕЛЬНЫЙ ПРОЕКТ УТВЕРЖДЁН</b>\n\nФинансирование и начало работ доступны во вкладке «Строительство».")
