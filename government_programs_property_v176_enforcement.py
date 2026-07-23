from __future__ import annotations

import html
import json
import math
import secrets
from typing import Any

import government_institutions_v128 as institutions
import government_oversight_deputy_v167_data as oversight_data
import government_v127 as gov

from government_programs_property_v176_common import (
    DAY, WEEK, PROPERTY_ITEMS, _fmt, _json, _operation, ensure_schema,
)

async def open_investigation(core: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    await ensure_schema(core)
    access = await oversight_data._access(core, chat_id, actor_id)
    if not access["can_manage"]:
        raise PermissionError("Имущественные проверки доступны главе Надзора и его заместителю.")
    target_id = gov._as_int(data.get("target_user_id"))
    target = await gov._player_dict(core, chat_id, target_id)
    if target is None:
        raise ValueError("Проверяемый участник не найден.")
    reason = str(data.get("reason") or "").strip()
    if not 10 <= len(reason) <= 800:
        raise ValueError("Основание проверки должно содержать 10–800 символов.")
    property_id = str(data.get("property_id") or "")
    conn = core.db._require_connection()
    if property_id:
        cursor = await conn.execute("SELECT 1 FROM government_property_v176 WHERE property_id=? AND chat_id=? AND owner_id=?", (property_id, chat_id, target_id))
        if await cursor.fetchone() is None:
            raise ValueError("Выбранное имущество не принадлежит проверяемому.")
    investigation_id = secrets.token_urlsafe(12)
    now = gov._now()
    await conn.execute(
        """
        INSERT INTO government_property_investigations_v176(
          investigation_id,chat_id,target_user_id,property_id,reason,status,created_by,created_at,updated_at
        ) VALUES(?,?,?,?,?,'open',?,?,?)
        """,
        (investigation_id, chat_id, target_id, property_id, reason, actor_id, now, now),
    )
    await _operation(core, chat_id, actor_id, "property_investigation_open", reason, target_user_id=target_id, property_id=property_id, payload={"investigation_id": investigation_id})
    await conn.commit()
    await gov._publish(
        bot, chat_id,
        f"🔎 <b>ОТКРЫТА ИМУЩЕСТВЕННАЯ ПРОВЕРКА</b>\n\n"
        f"Проверяемый: <b>{html.escape(target['name'])}</b>\n"
        f"Основание: {html.escape(reason)}\n\nДо решения участник не считается виновным.",
    )
    return f"Имущественная проверка {investigation_id} открыта."


async def _create_property_bill(core: Any, bot: Any, chat_id: int, actor_id: int, row: Any, action: str, note: str) -> str:
    if not await gov._deputy_ids(core, chat_id):
        raise ValueError("Сначала необходимо избрать состав Госдумы.")
    bill_type = "property_seizure" if action == "seize" else "property_confiscation"
    title = "О временном аресте имущества" if action == "seize" else "О конфискации имущества"
    number = await gov._next_number(core, chat_id, "bill_seq")
    bill_id = secrets.token_urlsafe(12)
    now = gov._now()
    payload = {
        "investigation_id": str(row["investigation_id"]),
        "property_id": str(row["property_id"]),
        "target_user_id": int(row["target_user_id"]),
    }
    conn = core.db._require_connection()
    await conn.execute(
        """
        INSERT INTO government_bills_v127(
          bill_id,chat_id,number,title,description,bill_type,payload_json,author_id,
          status,created_at,voting_ends_at,president_review_ends_at,resolved_at
        ) VALUES(?,?,?,?,?,?,?,?,'voting',?,?,0,0)
        """,
        (bill_id, chat_id, number, title, note, bill_type, json.dumps(payload, ensure_ascii=False), actor_id, now, now + gov.BILL_VOTING_SECONDS),
    )
    await conn.execute(
        "UPDATE government_property_investigations_v176 SET status='bill_pending',action_key=?,bill_id=?,result=?,updated_at=? WHERE investigation_id=?",
        (action, bill_id, note, now, str(row["investigation_id"])),
    )
    await conn.commit()
    await gov._publish(bot, chat_id, f"🏛 <b>ИМУЩЕСТВЕННОЕ ПРЕДЛОЖЕНИЕ №{number}</b>\n\n{html.escape(title)}\nОснование: {html.escape(note)}\n\nРешение проходит Госдуму и подпись Президента.")
    return bill_id


async def investigation_action(core: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    await ensure_schema(core)
    access = await oversight_data._access(core, chat_id, actor_id)
    if not access["can_manage"]:
        raise PermissionError("Действие доступно руководству Надзора.")
    investigation_id = str(data.get("investigation_id") or "")
    action = str(data.get("decision") or "")
    note = str(data.get("note") or "").strip()
    if action not in {"clear", "warning", "refer", "seize", "confiscate"}:
        raise ValueError("Неизвестное решение по проверке.")
    if not 5 <= len(note) <= 800:
        raise ValueError("Заключение должно содержать 5–800 символов.")
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT * FROM government_property_investigations_v176 WHERE investigation_id=? AND chat_id=?", (investigation_id, chat_id))
    row = await cursor.fetchone()
    if row is None or str(row["status"]) not in {"open", "referred"}:
        raise ValueError("Открытая имущественная проверка не найдена.")
    if action in {"seize", "confiscate"}:
        if not str(row["property_id"]):
            raise ValueError("Для ареста или конфискации нужно выбрать конкретный объект имущества.")
        bill_id = await _create_property_bill(core, bot, chat_id, actor_id, row, action, note)
        return f"Предложение передано в Госдуму: {bill_id}."
    now = gov._now()
    if action == "clear":
        status, result = "cleared", "Проверяемый оправдан"
    elif action == "warning":
        status, result = "warning", "Выдано официальное предупреждение"
        await institutions._log(core, chat_id, actor_id, "oversight_deputy", "property_warning", "Имущественное предупреждение", note, int(row["target_user_id"]), {"investigation_id": investigation_id})
    else:
        status, result = "referred", "Материалы переданы прокурору"
        case_id = secrets.token_urlsafe(10)
        await conn.execute(
            """
            INSERT INTO government_cases_v128(
              case_id,chat_id,institution,case_type,title,description,target_user_id,status,
              payload_json,created_by,created_at,updated_at,resolved_at
            ) VALUES(?,?,'prosecutor','investigation',?,?,?,'open',?,?,?, ?,0)
            """,
            (case_id, chat_id, "Имущественная проверка"[:140], note, int(row["target_user_id"]), json.dumps({"property_investigation_id": investigation_id}, ensure_ascii=False), actor_id, now, now),
        )
    await conn.execute(
        "UPDATE government_property_investigations_v176 SET status=?,action_key=?,result=?,updated_at=?,resolved_at=? WHERE investigation_id=?",
        (status, action, note, now, now if status != "referred" else 0, investigation_id),
    )
    await _operation(core, chat_id, actor_id, f"property_investigation_{action}", note, target_user_id=int(row["target_user_id"]), property_id=str(row["property_id"]), payload={"investigation_id": investigation_id})
    await conn.commit()
    await gov._publish(bot, chat_id, f"📁 <b>РЕШЕНИЕ ПО ИМУЩЕСТВЕННОЙ ПРОВЕРКЕ</b>\n\n{html.escape(result)}.\nЗаключение: {html.escape(note)}")
    return f"Решение сохранено: {result}."


async def enact_property_bill(core: Any, bot: Any, bill: Any, actor_id: int) -> None:
    await ensure_schema(core)
    bill_type = str(bill["bill_type"])
    if bill_type not in {"property_seizure", "property_confiscation"}:
        raise ValueError("Неимущественный законопроект передан в имущественный обработчик.")
    payload = _json(bill["payload_json"], {})
    property_id = str(payload.get("property_id") or "")
    investigation_id = str(payload.get("investigation_id") or "")
    chat_id = int(bill["chat_id"])
    conn = core.db._require_connection()
    now = gov._now()
    law_number = await gov._next_number(core, chat_id, "law_seq")
    auction_id = ""
    async with core.db.lock:
        cursor = await conn.execute("SELECT * FROM government_property_v176 WHERE property_id=? AND chat_id=?", (property_id, chat_id))
        item = await cursor.fetchone()
        if item is None:
            raise ValueError("Имущество из законопроекта больше не существует.")
        if bill_type == "property_seizure":
            if str(item["status"]) in {"auction", "state_owned"}:
                raise ValueError("Этот объект уже изъят у владельца.")
            await conn.execute("UPDATE government_property_v176 SET status='seized_investigation',seizure_until=?,updated_at=? WHERE property_id=?", (now + DAY, now, property_id))
            result_text = "Имущество арестовано на 24 часа"
        else:
            if str(item["status"]) in {"auction", "state_owned"}:
                raise ValueError("Конфискация этого объекта уже исполнена.")
            auction_id = secrets.token_urlsafe(12)
            start_price = max(1, int(item["purchase_price"]) * 60 // 100)
            await conn.execute(
                """
                INSERT INTO government_property_auctions_v176(
                  auction_id,chat_id,property_id,former_owner_id,start_price,current_price,
                  current_bidder_id,status,started_at,ends_at,resolved_at
                ) VALUES(?,?,?,?,?,0,0,'active',?,?,0)
                """,
                (auction_id, chat_id, property_id, int(item["owner_id"]), start_price, now, now + DAY),
            )
            await conn.execute(
                "UPDATE government_property_v176 SET status='auction',debt=0,confiscated_by=?,confiscated_at=?,seizure_until=0,updated_at=? WHERE property_id=?",
                (actor_id, now, now, property_id),
            )
            await conn.execute("DELETE FROM government_property_debts_v176 WHERE property_id=?", (property_id,))
            result_text = f"Имущество конфисковано и выставлено на аукцион со стартом {_fmt(start_price)}"
        law_id = secrets.token_urlsafe(12)
        await conn.execute(
            """
            INSERT INTO government_laws_v127(
              law_id,chat_id,number,title,text,law_type,payload_json,bill_id,enacted_at,active
            ) VALUES(?,?,?,?,?,?,?,?,?,1)
            """,
            (law_id, chat_id, law_number, str(bill["title"]), str(bill["description"]), bill_type, str(bill["payload_json"]), str(bill["bill_id"]), now),
        )
        await conn.execute("UPDATE government_bills_v127 SET status='enacted',resolved_at=? WHERE bill_id=?", (now, str(bill["bill_id"])))
        await conn.execute("UPDATE government_property_investigations_v176 SET status='resolved',result=?,resolved_at=?,updated_at=? WHERE investigation_id=?", (result_text, now, now, investigation_id))
        await _operation(core, chat_id, actor_id, bill_type, result_text, target_user_id=int(item["owner_id"]), property_id=property_id, payload={"auction_id": auction_id, "bill_id": str(bill["bill_id"])})
        await conn.commit()
    await gov._publish(bot, chat_id, f"⚖️ <b>ИМУЩЕСТВЕННОЕ РЕШЕНИЕ ВСТУПИЛО В СИЛУ</b>\n\n{html.escape(result_text)}.")


async def bid_auction(core: Any, bot: Any, chat_id: int, bidder_id: int, auction_id: str, amount: int) -> str:
    await ensure_schema(core)
    if amount <= 0:
        raise ValueError("Ставка должна быть положительной.")
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            """
            SELECT a.*,p.item_key,p.status property_status FROM government_property_auctions_v176 a
            JOIN government_property_v176 p ON p.property_id=a.property_id
            WHERE a.auction_id=? AND a.chat_id=?
            """,
            (auction_id, chat_id),
        )
        auction = await cursor.fetchone()
        if auction is None or str(auction["status"]) != "active" or int(auction["ends_at"]) <= now:
            raise ValueError("Аукцион завершён.")
        if int(auction["former_owner_id"]) == bidder_id:
            raise PermissionError("Бывший владелец не может выкупить конфискованное имущество на этом аукционе.")
        if int(auction["current_bidder_id"]) == bidder_id:
            raise ValueError("Вы уже лидируете. Нельзя бессмысленно перебивать собственную ставку.")
        cursor = await conn.execute(
            """
            SELECT 1 FROM government_property_auctions_v176 other
            JOIN government_property_v176 other_property ON other_property.property_id=other.property_id
            WHERE other.chat_id=? AND other.status='active' AND other.current_bidder_id=?
              AND other.auction_id<>? AND other_property.item_key=? LIMIT 1
            """,
            (chat_id, bidder_id, auction_id, str(auction["item_key"])),
        )
        if await cursor.fetchone() is not None:
            raise ValueError("Вы уже лидируете на другом аукционе за имущество этого типа.")
        cursor = await conn.execute(
            "SELECT 1 FROM government_property_v176 WHERE chat_id=? AND owner_id=? AND item_key=? AND status IN ('owned','seized_debt','seized_investigation')",
            (chat_id, bidder_id, str(auction["item_key"])),
        )
        if await cursor.fetchone() is not None:
            raise ValueError("У вас уже есть имущество этого типа.")
        current = int(auction["current_price"] or 0)
        minimum = int(auction["start_price"]) if current <= 0 else max(current + 1, math.ceil(current * 1.05))
        if amount < minimum:
            raise ValueError(f"Минимальная следующая ставка — {_fmt(minimum)}.")
        cursor = await conn.execute("SELECT points,full_name FROM players WHERE chat_id=? AND user_id=?", (chat_id, bidder_id))
        bidder = await cursor.fetchone()
        if bidder is None or int(bidder["points"]) < amount:
            raise ValueError("Недостаточно влияния для блокировки ставки.")
        await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?", (amount, now, chat_id, bidder_id))
        previous_bidder = int(auction["current_bidder_id"] or 0)
        if previous_bidder and current > 0:
            await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?", (current, now, chat_id, previous_bidder))
            await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, previous_bidder, current, "property_auction_refund_v176", now))
        bid_id = secrets.token_urlsafe(12)
        await conn.execute("INSERT INTO government_property_bids_v176(bid_id,auction_id,bidder_id,amount,created_at) VALUES(?,?,?,?,?)", (bid_id, auction_id, bidder_id, amount, now))
        await conn.execute("UPDATE government_property_auctions_v176 SET current_price=?,current_bidder_id=? WHERE auction_id=?", (amount, bidder_id, auction_id))
        await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, bidder_id, -amount, "property_auction_bid_v176", now))
        await _operation(core, chat_id, bidder_id, "auction_bid", "Ставка на государственном аукционе", target_user_id=bidder_id, amount=amount, property_id=str(auction["property_id"]), payload={"auction_id": auction_id})
        await conn.commit()
    await gov._publish(bot, chat_id, f"🔨 <b>НОВАЯ СТАВКА НА АУКЦИОНЕ</b>\n\nУчастник: <b>{html.escape(str(bidder['full_name'] or bidder_id))}</b>\nСтавка: <b>{_fmt(amount)}</b>.")
    return f"Ставка {_fmt(amount)} принята и заблокирована до следующей ставки или завершения аукциона."


async def process_auctions(core: Any, bot: Any) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute("SELECT auction_id FROM government_property_auctions_v176 WHERE status='active' AND ends_at<=? ORDER BY ends_at LIMIT 100", (now,))
    ids = [str(row["auction_id"]) for row in await cursor.fetchall()]
    for auction_id in ids:
        publish_chat = 0
        publish_text = ""
        async with core.db.lock:
            cursor2 = await conn.execute(
                """
                SELECT a.*,p.item_key FROM government_property_auctions_v176 a
                JOIN government_property_v176 p ON p.property_id=a.property_id
                WHERE a.auction_id=? AND a.status='active'
                """,
                (auction_id,),
            )
            auction = await cursor2.fetchone()
            if auction is None or int(auction["ends_at"]) > now:
                continue
            publish_chat = int(auction["chat_id"])
            bidder_id = int(auction["current_bidder_id"] or 0)
            price = int(auction["current_price"] or 0)
            spec = PROPERTY_ITEMS.get(str(auction["item_key"]), {"title": str(auction["item_key"]), "emoji": "🏛"})
            if bidder_id and price > 0:
                await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (price, now, publish_chat))
                await conn.execute(
                    "UPDATE government_property_v176 SET owner_id=?,status='owned',debt=0,seizure_until=0,source_auction_id=?,next_maintenance_at=?,updated_at=? WHERE property_id=?",
                    (bidder_id, auction_id, now + WEEK, now, str(auction["property_id"])),
                )
                await conn.execute("UPDATE government_property_auctions_v176 SET status='resolved',resolved_at=? WHERE auction_id=?", (now, auction_id))
                await gov._treasury_log(core, publish_chat, price, f"Государственный аукцион: {spec['title']}", "property_auction", auction_id, bidder_id)
                await _operation(core, publish_chat, bidder_id, "auction_resolved", f"Победа в аукционе: {spec['title']}", target_user_id=bidder_id, amount=price, property_id=str(auction["property_id"]), payload={"auction_id": auction_id})
                cursor3 = await conn.execute("SELECT full_name FROM players WHERE chat_id=? AND user_id=?", (publish_chat, bidder_id))
                winner = await cursor3.fetchone()
                publish_text = f"🔨 <b>АУКЦИОН ЗАВЕРШЁН</b>\n\n{spec['emoji']} {html.escape(spec['title'])}\nПобедитель: <b>{html.escape(str(winner['full_name'] if winner else bidder_id))}</b>\nВ казну поступило <b>{_fmt(price)}</b>."
            else:
                await conn.execute("UPDATE government_property_v176 SET owner_id=0,status='state_owned',updated_at=? WHERE property_id=?", (now, str(auction["property_id"])))
                await conn.execute("UPDATE government_property_auctions_v176 SET status='expired',resolved_at=? WHERE auction_id=?", (now, auction_id))
                publish_text = f"🔨 <b>АУКЦИОН ЗАВЕРШЁН БЕЗ СТАВОК</b>\n\n{spec['emoji']} {html.escape(spec['title'])} осталось в собственности государства."
            await conn.commit()
        if publish_text:
            await gov._publish(bot, publish_chat, publish_text)


async def release_temporary_seizures(core: Any) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    await conn.execute(
        "UPDATE government_property_v176 SET status='owned',seizure_until=0,updated_at=? WHERE status='seized_investigation' AND seizure_until>0 AND seizure_until<=?",
        (now, now),
    )
    await conn.commit()

