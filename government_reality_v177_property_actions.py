from __future__ import annotations

import hashlib
from typing import Any

import government_programs_property_v176_property as property176
import government_v127 as gov

from government_reality_v177_common import WEEK, ensure_schema, fmt, operation


async def buy_property(core: Any, bot: Any, chat_id: int, actor_id: int, item_key: str) -> str:
    await ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """SELECT 1 FROM government_voluntary_auctions_v177 a
        JOIN government_property_v176 p ON p.property_id=a.property_id
        WHERE a.chat_id=? AND a.status='active' AND a.current_bidder_id=? AND p.item_key=? LIMIT 1""",
        (int(chat_id), int(actor_id), str(item_key)),
    )
    if await cursor.fetchone() is not None:
        raise ValueError("Вы уже лидируете на аукционе за имущество этого типа.")
    return await property176.buy_property(core, bot, int(chat_id), int(actor_id), str(item_key))


async def owned_item(core: Any, chat_id: int, actor_id: int, property_id: str) -> Any:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_property_v176 WHERE property_id=? AND chat_id=? AND owner_id=?",
        (str(property_id), int(chat_id), int(actor_id)),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ValueError("Имущество не найдено или больше вам не принадлежит.")
    return row


async def blocked_reason(core: Any, chat_id: int, property_id: str) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT 1 FROM government_property_investigations_v176 WHERE chat_id=? AND property_id=? AND status IN ('open','referred','bill_pending') LIMIT 1",
        (int(chat_id), str(property_id)),
    )
    if await cursor.fetchone() is not None:
        return "Имущество участвует в открытом расследовании."
    cursor = await conn.execute(
        "SELECT 1 FROM government_voluntary_auctions_v177 WHERE property_id=? AND status='active' LIMIT 1",
        (str(property_id),),
    )
    return "Имущество уже выставлено на аукцион." if await cursor.fetchone() is not None else ""


async def sell_to_state(core: Any, bot: Any, chat_id: int, actor_id: int, property_id: str, request_id: str) -> str:
    await ensure_schema(core)
    conn = core.db._require_connection()
    if request_id:
        cursor = await conn.execute("SELECT result_text FROM government_property_action_requests_v177 WHERE request_id=?", (request_id,))
        old = await cursor.fetchone()
        if old is not None:
            return str(old["result_text"])
    now = gov._now()
    async with core.db.lock:
        item = await owned_item(core, chat_id, actor_id, property_id)
        if str(item["status"]) != "owned":
            raise ValueError("Продать можно только активное имущество без ареста и аукциона.")
        if int(item["debt"] or 0) > 0:
            raise ValueError("Сначала погасите долг по содержанию имущества.")
        reason = await blocked_reason(core, chat_id, property_id)
        if reason:
            raise ValueError(reason)
        payout = int(item["purchase_price"]) * 70 // 100
        cursor = await conn.execute("SELECT treasury FROM government_state_v127 WHERE chat_id=?", (int(chat_id),))
        state = await cursor.fetchone()
        if state is None or int(state["treasury"]) < payout:
            raise ValueError(f"В казне недостаточно средств для выкупа. Требуется {fmt(payout)}.")
        state_owner_id = -max(1, int.from_bytes(hashlib.sha256(str(property_id).encode("utf-8")).digest()[:8], "big"))
        cursor = await conn.execute(
            "UPDATE government_property_v176 SET owner_id=?,status='state_owned',updated_at=? WHERE property_id=? AND owner_id=? AND status='owned'",
            (state_owner_id, now, str(property_id), int(actor_id)),
        )
        if int(cursor.rowcount or 0) <= 0:
            raise ValueError("Состояние имущества изменилось. Обновите страницу.")
        await conn.execute("UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?", (payout, now, int(chat_id)))
        await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?", (payout, now, int(chat_id), int(actor_id)))
        await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (int(chat_id), int(actor_id), payout, "property_sale_to_state_v177", now))
        await operation(core, chat_id, actor_id, "property_sale_to_state", "Продажа имущества государству", amount=payout, property_id=property_id, target_user_id=actor_id)
        result = f"Имущество продано государству. На баланс начислено {fmt(payout)} влияния."
        if request_id:
            await conn.execute(
                "INSERT INTO government_property_action_requests_v177(request_id,chat_id,actor_id,action,property_id,result_text,created_at) VALUES(?,?,?,?,?,?,?)",
                (request_id, int(chat_id), int(actor_id), "sell", str(property_id), result, now),
            )
        await conn.commit()
    await gov._publish(bot, int(chat_id), f"💰 <b>ГОСУДАРСТВО ВЫКУПИЛО ИМУЩЕСТВО</b>\n\nВладелец получил <b>{fmt(payout)}</b> влияния. Объект перешёл в государственную собственность.")
    return result


async def upgrade_property(core: Any, chat_id: int, actor_id: int, property_id: str) -> str:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        item = await owned_item(core, chat_id, actor_id, property_id)
        if str(item["status"]) != "owned" or int(item["debt"] or 0) > 0:
            raise ValueError("Улучшать можно только активное имущество без долгов.")
        reason = await blocked_reason(core, chat_id, property_id)
        if reason:
            raise ValueError(reason)
        cursor = await conn.execute("SELECT upgrade_level FROM government_property_meta_v177 WHERE property_id=?", (str(property_id),))
        meta = await cursor.fetchone()
        level = int(meta["upgrade_level"] if meta else 0)
        if level >= 3:
            raise ValueError("Достигнут максимальный третий уровень улучшения.")
        cost = int(item["purchase_price"]) * 20 // 100
        cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (int(chat_id), int(actor_id)))
        player = await cursor.fetchone()
        if player is None or int(player["points"]) < cost:
            raise ValueError(f"Для улучшения требуется {fmt(cost)} влияния.")
        await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?", (cost, now, int(chat_id), int(actor_id)))
        await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (cost, now, int(chat_id)))
        await conn.execute(
            "INSERT INTO government_property_meta_v177(property_id,upgrade_level,updated_at) VALUES(?,1,?) ON CONFLICT(property_id) DO UPDATE SET upgrade_level=upgrade_level+1,updated_at=excluded.updated_at",
            (str(property_id), now),
        )
        await operation(core, chat_id, actor_id, "property_upgrade", f"Улучшение до уровня {level+1}", amount=cost, property_id=property_id)
        await conn.commit()
    return f"Имущество улучшено до уровня {level+1}. Стоимость улучшения {fmt(cost)}."


async def insure_property(core: Any, chat_id: int, actor_id: int, property_id: str) -> str:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        item = await owned_item(core, chat_id, actor_id, property_id)
        if str(item["status"]) != "owned":
            raise ValueError("Застраховать можно только активное имущество.")
        cost = int(item["purchase_price"]) * 5 // 100
        cursor = await conn.execute("SELECT insurance_until,insurance_used FROM government_property_meta_v177 WHERE property_id=?", (str(property_id),))
        meta = await cursor.fetchone()
        if meta is not None and int(meta["insurance_until"] or 0) > now and not int(meta["insurance_used"] or 0):
            raise ValueError("Страховка этого объекта ещё действует.")
        cursor = await conn.execute("SELECT points FROM players WHERE chat_id=? AND user_id=?", (int(chat_id), int(actor_id)))
        player = await cursor.fetchone()
        if player is None or int(player["points"]) < cost:
            raise ValueError(f"Для страховки требуется {fmt(cost)} влияния.")
        await conn.execute("UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=?", (cost, now, int(chat_id), int(actor_id)))
        await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (cost, now, int(chat_id)))
        await conn.execute(
            "INSERT INTO government_property_meta_v177(property_id,insurance_until,insurance_used,updated_at) VALUES(?,?,0,?) ON CONFLICT(property_id) DO UPDATE SET insurance_until=excluded.insurance_until,insurance_used=0,updated_at=excluded.updated_at",
            (str(property_id), now + WEEK, now),
        )
        await operation(core, chat_id, actor_id, "property_insurance", "Страховка на 7 дней", amount=cost, property_id=property_id)
        await conn.commit()
    return f"Имущество застраховано на 7 дней. Стоимость {fmt(cost)}."


async def set_primary(core: Any, chat_id: int, actor_id: int, property_id: str) -> str:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        item = await owned_item(core, chat_id, actor_id, property_id)
        if str(item["status"]) != "owned":
            raise ValueError("Главным активом можно сделать только действующее имущество без ареста или аукциона.")
        await conn.execute(
            "UPDATE government_property_meta_v177 SET is_primary=0,updated_at=? WHERE property_id IN(SELECT property_id FROM government_property_v176 WHERE chat_id=? AND owner_id=?)",
            (now, int(chat_id), int(actor_id)),
        )
        await conn.execute(
            "INSERT INTO government_property_meta_v177(property_id,is_primary,updated_at) VALUES(?,1,?) ON CONFLICT(property_id) DO UPDATE SET is_primary=1,updated_at=excluded.updated_at",
            (str(property_id), now),
        )
        await conn.commit()
    return "Главный актив обновлён."


pay_property_debt = property176.pay_property_debt
