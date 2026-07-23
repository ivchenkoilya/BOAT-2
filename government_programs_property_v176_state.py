from __future__ import annotations

import json
import math
import secrets
from typing import Any

import government_treasury_management_v164 as treasury
import government_v127 as gov

from government_programs_property_v176_common import (
    PROGRAMS, PROPERTY_ITEMS, _fmt, _json, _office_level, _program_cost, ensure_schema,
)

async def programs_state(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    await ensure_schema(core)
    await treasury._ensure_schema(core)
    offices = await gov._user_offices(core, chat_id, user_id)
    is_admin = user_id == int(core.DEVELOPER_ID)
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT structure_key,balance FROM government_structure_funds_v164 WHERE chat_id=?", (chat_id,))
    balances = {str(row["structure_key"]): int(row["balance"] or 0) for row in await cursor.fetchall()}
    now = gov._now()
    cursor = await conn.execute(
        "SELECT * FROM government_programs_v176 WHERE chat_id=? ORDER BY started_at DESC LIMIT 30",
        (chat_id,),
    )
    history = []
    latest: dict[str, Any] = {}
    for row in await cursor.fetchall():
        item = {
            "run_id": str(row["run_id"]), "program_key": str(row["program_key"]),
            "cost": int(row["cost"]), "actor_id": int(row["actor_id"]), "status": str(row["status"]),
            "started_at": int(row["started_at"]), "ends_at": int(row["ends_at"]),
            "cooldown_until": int(row["cooldown_until"]), "payload": _json(row["payload_json"], {}),
        }
        history.append(item)
        latest.setdefault(item["program_key"], item)
    programs = []
    for key, spec in PROGRAMS.items():
        balance = balances.get(str(spec["fund_key"]), 0)
        last = latest.get(key, {})
        cooldown_until = int(last.get("cooldown_until") or 0)
        programs.append({
            "key": key, "emoji": spec["emoji"], "title": spec["title"], "fund_key": spec["fund_key"],
            "fund_title": treasury.STRUCTURES[spec["fund_key"]]["title"], "fund_balance": balance,
            "effect": spec["effect"], "min_cost": int(spec["min_cost"]), "max_cost": int(spec["max_cost"]),
            "calculated_cost": _program_cost(key, balance, int(spec["min_cost"])),
            "can_start": bool(is_admin or set(offices).intersection(spec["roles"])),
            "cooldown_until": cooldown_until, "cooldown_remaining": gov._remaining(cooldown_until) if cooldown_until > now else "",
            "active": bool(last and str(last.get("status")) == "active" and int(last.get("ends_at") or 0) > now),
            "ends_at": int(last.get("ends_at") or 0),
        })
    cursor = await conn.execute(
        "SELECT effect_key,value,payload_json,starts_at,ends_at FROM government_program_effects_v176 WHERE chat_id=? AND active=1 AND ends_at>? ORDER BY ends_at",
        (chat_id, now),
    )
    effects = [{"effect_key": str(row["effect_key"]), "value": int(row["value"]), "payload": _json(row["payload_json"], {}), "starts_at": int(row["starts_at"]), "ends_at": int(row["ends_at"])} for row in await cursor.fetchall()]
    cursor = await conn.execute("SELECT * FROM government_property_operations_v176 WHERE chat_id=? AND operation_type='program_start' ORDER BY created_at DESC LIMIT 20", (chat_id,))
    expenses = [{"operation_id": str(row["operation_id"]), "actor_id": int(row["actor_id"]), "amount": int(row["amount"]), "detail": str(row["detail"]), "created_at": int(row["created_at"]), "payload": _json(row["payload_json"], {})} for row in await cursor.fetchall()]
    return {"programs": programs, "active_effects": effects, "history": history, "expenses": expenses, "can_expanded_report": bool((is_admin or set(offices).intersection({"oversight", "oversight_deputy"})) and any(item["effect_key"] == "oversight_operation" for item in effects))}


async def property_state(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    offices = await gov._user_offices(core, chat_id, user_id)
    is_admin = user_id == int(core.DEVELOPER_ID)
    level = 4 if is_admin else _office_level(offices)
    cursor = await conn.execute("SELECT * FROM government_property_v176 WHERE chat_id=? AND owner_id=? ORDER BY purchased_at DESC", (chat_id, user_id))
    my_rows = list(await cursor.fetchall())
    my_items = []
    my_keys = set()
    for row in my_rows:
        spec = PROPERTY_ITEMS.get(str(row["item_key"]), {"emoji": "🏛", "title": str(row["item_key"]), "price": int(row["purchase_price"]), "maintenance_bp": 0})
        my_keys.add(str(row["item_key"]))
        my_items.append({
            "property_id": str(row["property_id"]), "item_key": str(row["item_key"]), "emoji": spec["emoji"], "title": spec["title"],
            "purchase_price": int(row["purchase_price"]), "luxury_tax": int(row["luxury_tax"]), "status": str(row["status"]),
            "purchased_at": int(row["purchased_at"]), "next_maintenance_at": int(row["next_maintenance_at"]),
            "debt": int(row["debt"]), "seizure_until": int(row["seizure_until"]),
            "maintenance_amount": max(1, int(row["purchase_price"]) * int(spec.get("maintenance_bp", 0)) // 10_000),
        })
    catalog = [
        {"key": key, **spec, "allowed": bool(level >= int(spec["level"])), "owned": key in my_keys, "luxury_tax": int(spec["price"]) * 5 // 100, "total_cost": int(spec["price"]) * 105 // 100}
        for key, spec in PROPERTY_ITEMS.items()
    ]

    cursor = await conn.execute(
        """
        SELECT p.user_id,p.full_name,p.points,p.career_points,GROUP_CONCAT(o.office_key) offices
        FROM government_offices_v127 o JOIN players p ON p.chat_id=o.chat_id AND p.user_id=o.user_id
        WHERE o.chat_id=? AND o.ends_at>? GROUP BY p.user_id,p.full_name,p.points,p.career_points
        ORDER BY p.career_points DESC
        """,
        (chat_id, now),
    )
    officials = list(await cursor.fetchall())
    cursor = await conn.execute("SELECT * FROM government_property_v176 WHERE chat_id=? AND owner_id>0 ORDER BY purchased_at DESC", (chat_id,))
    all_properties = list(await cursor.fetchall())
    by_owner: dict[int, list[Any]] = {}
    for row in all_properties:
        by_owner.setdefault(int(row["owner_id"]), []).append(row)
    cursor = await conn.execute(
        """
        SELECT target_user_id,
          COALESCE(SUM(CASE WHEN operation_type='maintenance_paid' THEN amount ELSE 0 END),0) maintenance_paid
        FROM government_property_operations_v176 WHERE chat_id=? GROUP BY target_user_id
        """,
        (chat_id,),
    )
    maintenance = {int(row["target_user_id"]): int(row["maintenance_paid"] or 0) for row in await cursor.fetchall()}
    declarations = []
    for official in officials:
        uid = int(official["user_id"])
        props = by_owner.get(uid, [])
        items = []
        total_value = tax_paid = seized_count = 0
        for row in props:
            spec = PROPERTY_ITEMS.get(str(row["item_key"]), {"emoji": "🏛", "title": str(row["item_key"])})
            total_value += int(row["purchase_price"])
            tax_paid += int(row["luxury_tax"])
            if str(row["status"]).startswith("seized"):
                seized_count += 1
            items.append({"property_id": str(row["property_id"]), "item_key": str(row["item_key"]), "emoji": spec["emoji"], "title": spec["title"], "value": int(row["purchase_price"]), "status": str(row["status"]), "debt": int(row["debt"])})
        declarations.append({
            "user_id": uid, "name": str(official["full_name"] or f"ID {uid}"), "balance": int(official["points"]),
            "career_points": int(official["career_points"]), "offices": [value for value in str(official["offices"] or "").split(",") if value],
            "items": items, "total_value": total_value, "luxury_tax_paid": tax_paid,
            "maintenance_paid": maintenance.get(uid, 0), "seized_count": seized_count,
        })
    ranking = sorted(
        [
            {"user_id": uid, "name": next((str(item["name"]) for item in declarations if int(item["user_id"]) == uid), f"ID {uid}"),
             "total_value": sum(int(row["purchase_price"]) for row in props if str(row["status"]) != "state_owned"),
             "count": len([row for row in props if str(row["status"]) != "state_owned"]),
             "most_expensive": max((int(row["purchase_price"]) for row in props), default=0),
             "tax_paid": sum(int(row["luxury_tax"]) for row in props)}
            for uid, props in by_owner.items()
        ],
        key=lambda item: (item["total_value"], item["tax_paid"]), reverse=True,
    )[:30]

    cursor = await conn.execute(
        """
        SELECT a.*,p.item_key,owner.full_name former_owner_name,bidder.full_name bidder_name
        FROM government_property_auctions_v176 a
        JOIN government_property_v176 p ON p.property_id=a.property_id
        LEFT JOIN players owner ON owner.chat_id=a.chat_id AND owner.user_id=a.former_owner_id
        LEFT JOIN players bidder ON bidder.chat_id=a.chat_id AND bidder.user_id=a.current_bidder_id
        WHERE a.chat_id=? AND a.status='active' ORDER BY a.ends_at
        """,
        (chat_id,),
    )
    auctions = []
    for row in await cursor.fetchall():
        spec = PROPERTY_ITEMS.get(str(row["item_key"]), {"emoji": "🏛", "title": str(row["item_key"])})
        current = int(row["current_price"] or 0)
        minimum = int(row["start_price"]) if current <= 0 else max(current + 1, math.ceil(current * 1.05))
        auctions.append({
            "auction_id": str(row["auction_id"]), "property_id": str(row["property_id"]), "item_key": str(row["item_key"]),
            "emoji": spec["emoji"], "title": spec["title"], "former_owner_id": int(row["former_owner_id"]),
            "former_owner_name": str(row["former_owner_name"] or f"ID {row['former_owner_id']}"),
            "start_price": int(row["start_price"]), "current_price": current,
            "current_bidder_id": int(row["current_bidder_id"]), "current_bidder_name": str(row["bidder_name"] or ""),
            "minimum_bid": minimum, "ends_at": int(row["ends_at"]),
            "can_bid": bool(int(row["former_owner_id"]) != user_id and int(row["current_bidder_id"]) != user_id),
        })
    cursor = await conn.execute(
        """
        SELECT i.*,p.full_name target_name FROM government_property_investigations_v176 i
        LEFT JOIN players p ON p.chat_id=i.chat_id AND p.user_id=i.target_user_id
        WHERE i.chat_id=? ORDER BY CASE i.status WHEN 'open' THEN 0 WHEN 'referred' THEN 1 WHEN 'bill_pending' THEN 2 ELSE 3 END,i.updated_at DESC LIMIT 50
        """,
        (chat_id,),
    )
    investigations = [{
        "investigation_id": str(row["investigation_id"]), "target_user_id": int(row["target_user_id"]),
        "target_name": str(row["target_name"] or f"ID {row['target_user_id']}"), "property_id": str(row["property_id"] or ""),
        "reason": str(row["reason"]), "status": str(row["status"]), "action_key": str(row["action_key"]),
        "result": str(row["result"]), "bill_id": str(row["bill_id"]), "created_by": int(row["created_by"]),
        "created_at": int(row["created_at"]), "updated_at": int(row["updated_at"]),
    } for row in await cursor.fetchall()]
    can_investigate = bool(is_admin or set(offices).intersection({"oversight", "oversight_deputy"}))
    return {
        "level": level, "catalog": catalog, "my_items": my_items, "declarations": declarations,
        "ranking": ranking, "auctions": auctions, "investigations": investigations,
        "can_investigate": can_investigate, "is_official": bool(offices),
    }

async def refresh_declaration(core: Any, chat_id: int, user_id: int) -> str:
    state = await property_state(core, chat_id, user_id)
    declaration = next((item for item in state["declarations"] if int(item["user_id"]) == int(user_id)), None)
    if declaration is None:
        raise ValueError("Публичная декларация доступна только действующему чиновнику.")
    conn = core.db._require_connection()
    declaration_id = secrets.token_urlsafe(12)
    await conn.execute(
        """
        INSERT INTO government_property_declarations_v176(
          declaration_id,chat_id,user_id,balance,total_value,luxury_tax_paid,
          maintenance_paid,seized_count,snapshot_json,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?)
        """,
        (
            declaration_id, chat_id, user_id, int(declaration["balance"]), int(declaration["total_value"]),
            int(declaration["luxury_tax_paid"]), int(declaration["maintenance_paid"]), int(declaration["seized_count"]),
            json.dumps(declaration, ensure_ascii=False), gov._now(),
        ),
    )
    await conn.commit()
    return "Декларация обновлена и сохранена в государственном журнале."

