from __future__ import annotations

import math
import secrets
from typing import Any

import government_v127 as gov

from government_reality_v177_common import WEEK, ensure_schema, fmt, operation


async def property_state_v177(core: Any, chat_id: int, user_id: int, base: dict[str, Any]) -> dict[str, Any]:
    await ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT m.* FROM government_property_meta_v177 m JOIN government_property_v176 p ON p.property_id=m.property_id WHERE p.chat_id=?",
        (int(chat_id),),
    )
    metas = {str(row["property_id"]): dict(row) for row in await cursor.fetchall()}
    for item in base.get("my_items", []):
        meta = metas.get(str(item["property_id"]), {})
        level = int(meta.get("upgrade_level") or 0)
        item.update({
            "upgrade_level": level, "insurance_until": int(meta.get("insurance_until") or 0),
            "insurance_used": bool(meta.get("insurance_used") or 0), "is_primary": bool(meta.get("is_primary") or 0),
            "sell_price": int(item["purchase_price"]) * 70 // 100,
            "upgrade_cost": int(item["purchase_price"]) * 20 // 100,
            "insurance_cost": int(item["purchase_price"]) * 5 // 100,
            "prestige_value": int(item["purchase_price"]) * (100 + level * 20) // 100,
            "maintenance_amount": int(item.get("maintenance_amount") or 0) * (100 + level * 10) // 100,
        })
    primary_by_owner: dict[int, dict[str, Any]] = {}
    declaration_by_owner = {int(person["user_id"]): person for person in base.get("declarations", [])}
    for person in base.get("declarations", []):
        total = 0
        for item in person.get("items", []):
            meta = metas.get(str(item["property_id"]), {})
            level = int(meta.get("upgrade_level") or 0)
            item["upgrade_level"] = level
            item["is_primary"] = bool(meta.get("is_primary") or 0)
            item["prestige_value"] = int(item.get("value") or 0) * (100 + level * 20) // 100
            total += int(item["prestige_value"])
            if item["is_primary"]:
                primary_by_owner[int(person["user_id"])] = item
        person["total_value"] = total
        person["primary_asset"] = primary_by_owner.get(int(person["user_id"]))
    for rank in base.get("ranking", []):
        person = declaration_by_owner.get(int(rank["user_id"]))
        if person is not None:
            rank["total_value"] = int(person["total_value"])
            rank["primary_asset"] = person.get("primary_asset")
    base["primary_asset"] = next((item for item in base.get("my_items", []) if item.get("is_primary")), None)
    cursor = await conn.execute(
        """SELECT a.*,p.item_key,p.purchase_price,s.full_name seller_name,b.full_name bidder_name
        FROM government_voluntary_auctions_v177 a JOIN government_property_v176 p ON p.property_id=a.property_id
        LEFT JOIN players s ON s.chat_id=a.chat_id AND s.user_id=a.seller_id
        LEFT JOIN players b ON b.chat_id=a.chat_id AND b.user_id=a.current_bidder_id
        WHERE a.chat_id=? AND a.status='active' ORDER BY a.ends_at""",
        (int(chat_id),),
    )
    voluntary = []
    for row in await cursor.fetchall():
        current = int(row["current_price"] or 0)
        voluntary.append({
            **dict(row),
            "minimum_bid": int(row["start_price"]) if current <= 0 else max(current + 1, math.ceil(current * 1.05)),
            "seller_name": str(row["seller_name"] or f"ID {row['seller_id']}"),
            "bidder_name": str(row["bidder_name"] or ""),
            "can_bid": int(row["seller_id"]) != int(user_id) and int(row["current_bidder_id"] or 0) != int(user_id),
        })
    base["voluntary_auctions"] = voluntary
    state = await (await conn.execute("SELECT treasury FROM government_state_v127 WHERE chat_id=?", (int(chat_id),))).fetchone()
    base["treasury_balance"] = int(state["treasury"] if state else 0)
    cursor = await conn.execute("SELECT operation_type,amount,detail,property_id,created_at FROM government_property_operations_v176 WHERE chat_id=? ORDER BY created_at DESC LIMIT 50", (int(chat_id),))
    base["operations"] = [dict(row) for row in await cursor.fetchall()]
    return base


async def process_maintenance_v177(core: Any, bot: Any) -> None:
    from government_programs_property_v176_common import PROPERTY_ITEMS
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute(
        """SELECT p.*,COALESCE(m.upgrade_level,0) upgrade_level,COALESCE(m.insurance_until,0) insurance_until,
        COALESCE(m.insurance_used,0) insurance_used FROM government_property_v176 p
        LEFT JOIN government_property_meta_v177 m ON m.property_id=p.property_id
        WHERE p.status='owned' AND p.next_maintenance_at<=? ORDER BY p.next_maintenance_at LIMIT 100""",
        (now,),
    )
    for row in list(await cursor.fetchall()):
        spec = PROPERTY_ITEMS.get(str(row["item_key"]))
        if spec is None:
            continue
        property_id = str(row["property_id"])
        period_start = int(row["next_maintenance_at"]) - WEEK
        base_amount = max(1, int(row["purchase_price"]) * int(spec["maintenance_bp"]) // 10_000)
        amount = max(1, base_amount * (100 + int(row["upgrade_level"] or 0) * 10) // 100)
        message = ""
        async with core.db.lock:
            if await (await conn.execute("SELECT 1 FROM government_property_maintenance_v176 WHERE property_id=? AND period_start=?", (property_id, period_start))).fetchone() is not None:
                await conn.execute("UPDATE government_property_v176 SET next_maintenance_at=next_maintenance_at+? WHERE property_id=?", (WEEK, property_id))
                await conn.commit()
                continue
            player = await (await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (int(row["chat_id"]), int(row["owner_id"])))).fetchone()
            balance = int(player["points"] if player else 0)
            charge_id = secrets.token_urlsafe(12)
            if balance >= amount:
                await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?", (amount, now, int(row["chat_id"]), int(row["owner_id"])))
                await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (amount, now, int(row["chat_id"])))
                await conn.execute("INSERT INTO government_property_maintenance_v176(charge_id,property_id,chat_id,owner_id,period_start,amount,paid,status,created_at,paid_at) VALUES(?,?,?,?,?,?,1,'paid_v177',?,?)", (charge_id, property_id, int(row["chat_id"]), int(row["owner_id"]), period_start, amount, now, now))
                await conn.execute("UPDATE government_property_v176 SET next_maintenance_at=next_maintenance_at+?,updated_at=? WHERE property_id=?", (WEEK, now, property_id))
                await operation(core, int(row["chat_id"]), int(row["owner_id"]), "maintenance_paid", "Содержание имущества Reality 177", amount=amount, property_id=property_id, target_user_id=int(row["owner_id"]))
            elif int(row["insurance_until"] or 0) > now and not int(row["insurance_used"] or 0):
                await conn.execute("INSERT INTO government_property_maintenance_v176(charge_id,property_id,chat_id,owner_id,period_start,amount,paid,status,created_at,paid_at) VALUES(?,?,?,?,?,?,1,'insured_v177',?,?)", (charge_id, property_id, int(row["chat_id"]), int(row["owner_id"]), period_start, amount, now, now))
                await conn.execute("UPDATE government_property_meta_v177 SET insurance_used=1,updated_at=? WHERE property_id=?", (now, property_id))
                await conn.execute("UPDATE government_property_v176 SET next_maintenance_at=next_maintenance_at+?,updated_at=? WHERE property_id=?", (WEEK, now, property_id))
                message = f"🛡 <b>СТРАХОВКА ИМУЩЕСТВА СРАБОТАЛА</b>\n\nОбъект защищён от ареста за просрочку на сумму <b>{fmt(amount)}</b>. Страховка использована."
            else:
                await conn.execute("INSERT INTO government_property_maintenance_v176(charge_id,property_id,chat_id,owner_id,period_start,amount,paid,status,created_at,paid_at) VALUES(?,?,?,?,?,?,0,'debt_v177',?,0)", (charge_id, property_id, int(row["chat_id"]), int(row["owner_id"]), period_start, amount, now))
                await conn.execute("UPDATE government_property_v176 SET status='seized_debt',debt=?,next_maintenance_at=next_maintenance_at+?,updated_at=? WHERE property_id=?", (amount, WEEK, now, property_id))
                await conn.execute("INSERT INTO government_property_debts_v176(property_id,chat_id,owner_id,amount,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(property_id) DO UPDATE SET amount=excluded.amount,updated_at=excluded.updated_at", (property_id, int(row["chat_id"]), int(row["owner_id"]), amount, now))
                message = f"🔒 <b>ИМУЩЕСТВО АРЕСТОВАНО ЗА ДОЛГ</b>\n\nДолг за содержание: <b>{fmt(amount)}</b>."
            await conn.commit()
        if message:
            await gov._publish(bot, int(row["chat_id"]), message)
