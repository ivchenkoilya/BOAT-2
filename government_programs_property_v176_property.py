from __future__ import annotations

import html
import secrets
from typing import Any

import government_v127 as gov

from government_programs_property_v176_common import (
    PROPERTY_ITEMS, WEEK, _fmt, _office_level, _operation, ensure_schema,
)

async def buy_property(core: Any, bot: Any, chat_id: int, actor_id: int, item_key: str) -> str:
    await ensure_schema(core)
    spec = PROPERTY_ITEMS.get(str(item_key))
    if spec is None:
        raise ValueError("Неизвестный объект имущества.")
    offices = await gov._user_offices(core, chat_id, actor_id)
    level = 4 if actor_id == int(core.DEVELOPER_ID) else _office_level(offices)
    if level <= 0:
        raise PermissionError("Покупать имущество могут только действующие государственные чиновники.")
    if level < int(spec["level"]):
        raise PermissionError("Текущая должность не даёт доступ к этому классу имущества.")
    price = int(spec["price"])
    tax = max(1, price * 5 // 100)
    total = price + tax
    now = gov._now()
    conn = core.db._require_connection()
    property_id = secrets.token_urlsafe(12)
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT points,full_name FROM players WHERE chat_id=? AND user_id=?",
            (chat_id, actor_id),
        )
        player = await cursor.fetchone()
        if player is None:
            raise ValueError("Участник не найден.")
        if int(player["points"]) < total:
            raise ValueError(f"Нужно {_fmt(total)}: цена {_fmt(price)} и налог {_fmt(tax)}.")
        cursor = await conn.execute(
            "SELECT 1 FROM government_property_v176 WHERE chat_id=? AND owner_id=? AND item_key=? LIMIT 1",
            (chat_id, actor_id, item_key),
        )
        if await cursor.fetchone() is not None:
            raise ValueError("Этот тип имущества уже есть в вашей декларации.")
        cursor = await conn.execute(
            """
            SELECT 1 FROM government_property_auctions_v176 a
            JOIN government_property_v176 p ON p.property_id=a.property_id
            WHERE a.chat_id=? AND a.status='active' AND a.current_bidder_id=? AND p.item_key=? LIMIT 1
            """,
            (chat_id, actor_id, item_key),
        )
        if await cursor.fetchone() is not None:
            raise ValueError("Вы уже лидируете на аукционе за имущество этого типа.")
        await conn.execute(
            "UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?",
            (total, now, chat_id, actor_id),
        )
        await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
            (tax, now, chat_id),
        )
        await conn.execute(
            """
            INSERT INTO government_property_v176(
              property_id,chat_id,owner_id,item_key,purchase_price,luxury_tax,status,purchased_at,
              next_maintenance_at,debt,seizure_until,updated_at
            ) VALUES(?,?,?,?,?,?,'owned',?,?,0,0,?)
            """,
            (property_id, chat_id, actor_id, item_key, price, tax, now, now + WEEK, now),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (chat_id, actor_id, -total, "official_property_purchase_v176", now),
        )
        await gov._treasury_log(core, chat_id, tax, f"Налог на роскошь: {spec['title']}", "luxury_tax", property_id, actor_id)
        await _operation(
            core, chat_id, actor_id, "property_purchase", f"Покупка: {spec['title']}",
            target_user_id=actor_id, amount=total, property_id=property_id,
            payload={"price": price, "luxury_tax": tax, "item_key": item_key},
        )
        await conn.commit()
    await gov._publish(
        bot, chat_id,
        f"{spec['emoji']} <b>НОВОЕ ИМУЩЕСТВО ЧИНОВНИКА</b>\n\n"
        f"Владелец: <b>{html.escape(str(player['full_name'] or actor_id))}</b>\n"
        f"Объект: <b>{html.escape(spec['title'])}</b>\n"
        f"Цена: <b>{_fmt(price)}</b> · налог в казну: <b>{_fmt(tax)}</b>.",
    )
    return f"Куплено: {spec['title']}. Налог {_fmt(tax)} поступил в казну."


async def pay_property_debt(core: Any, bot: Any, chat_id: int, actor_id: int, property_id: str) -> str:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT * FROM government_property_v176 WHERE property_id=? AND chat_id=? AND owner_id=?",
            (property_id, chat_id, actor_id),
        )
        item = await cursor.fetchone()
        if item is None:
            raise ValueError("Имущество не найдено.")
        debt = int(item["debt"] or 0)
        if debt <= 0:
            raise ValueError("Долга по этому объекту нет.")
        cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (chat_id, actor_id))
        player = await cursor.fetchone()
        if player is None or int(player["points"]) < debt:
            raise ValueError(f"Для погашения требуется {_fmt(debt)} влияния.")
        await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?", (debt, now, chat_id, actor_id))
        await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (debt, now, chat_id))
        await conn.execute(
            "UPDATE government_property_v176 SET debt=0,status='owned',next_maintenance_at=?,updated_at=? WHERE property_id=?",
            (now + WEEK, now, property_id),
        )
        await conn.execute("DELETE FROM government_property_debts_v176 WHERE property_id=?", (property_id,))
        await conn.execute(
            "UPDATE government_property_maintenance_v176 SET paid=1,status='paid_late',paid_at=? WHERE property_id=? AND paid=0",
            (now, property_id),
        )
        await gov._treasury_log(core, chat_id, debt, "Погашение долга по содержанию имущества", "property_debt", property_id, actor_id)
        await _operation(core, chat_id, actor_id, "property_debt_paid", "Погашен долг по содержанию", target_user_id=actor_id, amount=debt, property_id=property_id)
        await conn.commit()
    await gov._publish(bot, chat_id, f"✅ <b>ДОЛГ ПО ИМУЩЕСТВУ ПОГАШЕН</b>\n\nВ казну перечислено <b>{_fmt(debt)}</b> влияния. Арест за долги снят.")
    return f"Долг {_fmt(debt)} погашен, имущество снова активно."


async def process_maintenance(core: Any, bot: Any) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute(
        """
        SELECT * FROM government_property_v176
        WHERE status='owned' AND next_maintenance_at<=?
        ORDER BY next_maintenance_at LIMIT 100
        """,
        (now,),
    )
    rows = list(await cursor.fetchall())
    for row in rows:
        property_id = str(row["property_id"])
        item_key = str(row["item_key"])
        spec = PROPERTY_ITEMS.get(item_key)
        if spec is None:
            continue
        amount = max(1, int(row["purchase_price"]) * int(spec["maintenance_bp"]) // 10_000)
        period_start = int(row["next_maintenance_at"]) - WEEK
        message = ""
        async with core.db.lock:
            cursor2 = await conn.execute("SELECT * FROM government_property_v176 WHERE property_id=?", (property_id,))
            current = await cursor2.fetchone()
            if current is None or str(current["status"]) != "owned" or int(current["next_maintenance_at"]) > now:
                continue
            cursor2 = await conn.execute(
                "SELECT 1 FROM government_property_maintenance_v176 WHERE property_id=? AND period_start=?",
                (property_id, period_start),
            )
            if await cursor2.fetchone() is not None:
                await conn.execute("UPDATE government_property_v176 SET next_maintenance_at=next_maintenance_at+? WHERE property_id=?", (WEEK, property_id))
                await conn.commit()
                continue
            cursor2 = await conn.execute("SELECT points,full_name FROM players WHERE chat_id=? AND user_id=?", (int(row["chat_id"]), int(row["owner_id"])))
            player = await cursor2.fetchone()
            balance = int(player["points"] if player else 0)
            charge_id = secrets.token_urlsafe(12)
            if balance >= amount:
                await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?", (amount, now, int(row["chat_id"]), int(row["owner_id"])))
                await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (amount, now, int(row["chat_id"])))
                await conn.execute(
                    "INSERT INTO government_property_maintenance_v176(charge_id,property_id,chat_id,owner_id,period_start,amount,paid,status,created_at,paid_at) VALUES(?,?,?,?,?,?,1,'paid',?,?)",
                    (charge_id, property_id, int(row["chat_id"]), int(row["owner_id"]), period_start, amount, now, now),
                )
                await conn.execute("UPDATE government_property_v176 SET next_maintenance_at=next_maintenance_at+?,updated_at=? WHERE property_id=?", (WEEK, now, property_id))
                await gov._treasury_log(core, int(row["chat_id"]), amount, f"Содержание: {spec['title']}", "property_maintenance", property_id, int(row["owner_id"]))
                await _operation(core, int(row["chat_id"]), int(row["owner_id"]), "maintenance_paid", f"Содержание: {spec['title']}", target_user_id=int(row["owner_id"]), amount=amount, property_id=property_id)
            else:
                await conn.execute(
                    "INSERT INTO government_property_maintenance_v176(charge_id,property_id,chat_id,owner_id,period_start,amount,paid,status,created_at,paid_at) VALUES(?,?,?,?,?,?,0,'debt',?,0)",
                    (charge_id, property_id, int(row["chat_id"]), int(row["owner_id"]), period_start, amount, now),
                )
                await conn.execute(
                    "UPDATE government_property_v176 SET status='seized_debt',debt=?,next_maintenance_at=next_maintenance_at+?,updated_at=? WHERE property_id=?",
                    (amount, WEEK, now, property_id),
                )
                await conn.execute(
                    "INSERT INTO government_property_debts_v176(property_id,chat_id,owner_id,amount,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(property_id) DO UPDATE SET amount=excluded.amount,updated_at=excluded.updated_at",
                    (property_id, int(row["chat_id"]), int(row["owner_id"]), amount, now),
                )
                await _operation(core, int(row["chat_id"]), int(row["owner_id"]), "maintenance_debt", f"Арест за долг: {spec['title']}", target_user_id=int(row["owner_id"]), amount=amount, property_id=property_id)
                message = (
                    f"🔒 <b>ИМУЩЕСТВО АРЕСТОВАНО ЗА ДОЛГ</b>\n\n"
                    f"Владелец: <b>{html.escape(str(player['full_name'] if player else row['owner_id']))}</b>\n"
                    f"Объект: {spec['emoji']} <b>{html.escape(spec['title'])}</b>\n"
                    f"Долг за содержание: <b>{_fmt(amount)}</b>."
                )
            await conn.commit()
        if message:
            await gov._publish(bot, int(row["chat_id"]), message)

