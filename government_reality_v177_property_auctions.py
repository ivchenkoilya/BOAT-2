from __future__ import annotations

import math
import secrets
from typing import Any

import government_v127 as gov

from government_reality_v177_common import DAY, ensure_schema, fmt, operation
from government_reality_v177_property_actions import blocked_reason, owned_item


async def start_voluntary_auction(
    core: Any,
    bot: Any,
    chat_id: int,
    actor_id: int,
    property_id: str,
    start_price: int,
    request_id: str,
) -> str:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        if request_id:
            cursor = await conn.execute(
                "SELECT result_text FROM government_property_action_requests_v177 WHERE request_id=?",
                (request_id,),
            )
            old = await cursor.fetchone()
            if old is not None:
                return str(old["result_text"])
        item = await owned_item(core, chat_id, actor_id, property_id)
        if str(item["status"]) != "owned" or int(item["debt"] or 0) > 0:
            raise ValueError("На аукцион допускается только активное имущество без долгов.")
        reason = await blocked_reason(core, chat_id, property_id)
        if reason:
            raise ValueError(reason)
        low = int(item["purchase_price"]) * 50 // 100
        high = int(item["purchase_price"])
        if not low <= int(start_price) <= high:
            raise ValueError(f"Стартовая цена должна быть от {fmt(low)} до {fmt(high)}.")

        # В таблице один слот на объект. Завершённые торги остаются в общем журнале
        # операций, а техническую строку можно безопасно заменить новыми торгами.
        cursor = await conn.execute(
            "SELECT auction_id,status FROM government_voluntary_auctions_v177 WHERE property_id=?",
            (str(property_id),),
        )
        previous = await cursor.fetchone()
        if previous is not None:
            if str(previous["status"]) == "active":
                raise ValueError("Имущество уже выставлено на аукцион.")
            await conn.execute(
                "DELETE FROM government_voluntary_bids_v177 WHERE auction_id=?",
                (str(previous["auction_id"]),),
            )
            await conn.execute(
                "DELETE FROM government_voluntary_auctions_v177 WHERE auction_id=?",
                (str(previous["auction_id"]),),
            )

        auction_id = secrets.token_urlsafe(12)
        await conn.execute(
            "INSERT INTO government_voluntary_auctions_v177(auction_id,chat_id,property_id,seller_id,start_price,current_price,current_bidder_id,status,started_at,ends_at,resolved_at) VALUES(?,?,?,?,?,0,0,'active',?,?,0)",
            (
                auction_id,
                int(chat_id),
                str(property_id),
                int(actor_id),
                int(start_price),
                now,
                now + DAY,
            ),
        )
        await conn.execute(
            "UPDATE government_property_v176 SET status='auction',updated_at=? WHERE property_id=?",
            (now, str(property_id)),
        )
        await operation(
            core,
            chat_id,
            actor_id,
            "voluntary_auction_start",
            "Добровольный аукцион",
            amount=start_price,
            property_id=property_id,
            payload={"auction_id": auction_id},
        )
        result = f"Имущество выставлено на аукцион со стартовой ценой {fmt(start_price)}."
        if request_id:
            await conn.execute(
                "INSERT INTO government_property_action_requests_v177(request_id,chat_id,actor_id,action,property_id,result_text,created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    request_id,
                    int(chat_id),
                    int(actor_id),
                    "auction",
                    str(property_id),
                    result,
                    now,
                ),
            )
        await conn.commit()
    await gov._publish(
        bot,
        int(chat_id),
        "🔨 <b>ДОБРОВОЛЬНЫЙ АУКЦИОН</b>\n\n"
        f"Имущество выставлено на 24 часа. Стартовая цена: <b>{fmt(start_price)}</b>.",
    )
    return result


async def bid_voluntary(
    core: Any,
    chat_id: int,
    bidder_id: int,
    auction_id: str,
    amount: int,
) -> str:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT a.*,p.item_key FROM government_voluntary_auctions_v177 a JOIN government_property_v176 p ON p.property_id=a.property_id WHERE a.auction_id=? AND a.chat_id=?",
            (str(auction_id), int(chat_id)),
        )
        auction = await cursor.fetchone()
        if auction is None or str(auction["status"]) != "active" or int(auction["ends_at"]) <= now:
            raise ValueError("Аукцион завершён.")
        if int(auction["seller_id"]) == int(bidder_id):
            raise PermissionError("Владелец не может делать ставку на собственное имущество.")
        if int(auction["current_bidder_id"]) == int(bidder_id):
            raise ValueError("Вы уже лидируете на этом аукционе.")
        cursor = await conn.execute(
            "SELECT 1 FROM government_property_v176 WHERE chat_id=? AND owner_id=? AND item_key=? LIMIT 1",
            (int(chat_id), int(bidder_id), str(auction["item_key"])),
        )
        if await cursor.fetchone() is not None:
            raise ValueError("У вас уже есть имущество этого типа.")
        current = int(auction["current_price"] or 0)
        minimum = int(auction["start_price"]) if current <= 0 else max(current + 1, math.ceil(current * 1.05))
        if int(amount) < minimum:
            raise ValueError(f"Минимальная ставка — {fmt(minimum)}.")
        cursor = await conn.execute(
            "SELECT points FROM players WHERE chat_id=? AND user_id=?",
            (int(chat_id), int(bidder_id)),
        )
        player = await cursor.fetchone()
        if player is None or int(player["points"]) < int(amount):
            raise ValueError("Недостаточно влияния для ставки.")

        cursor = await conn.execute(
            "UPDATE players SET points=points-?,updated_at=? WHERE chat_id=? AND user_id=? AND points>=?",
            (int(amount), now, int(chat_id), int(bidder_id), int(amount)),
        )
        if int(cursor.rowcount or 0) <= 0:
            raise ValueError("Баланс изменился: средств для ставки уже недостаточно.")
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (int(chat_id), int(bidder_id), -int(amount), "voluntary_auction_bid_v177", now),
        )
        previous_id = int(auction["current_bidder_id"] or 0)
        previous_amount = int(auction["current_price"] or 0)
        if previous_id and previous_amount:
            await conn.execute(
                "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (previous_amount, now, int(chat_id), previous_id),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (int(chat_id), previous_id, previous_amount, "voluntary_auction_bid_refund_v177", now),
            )
        await conn.execute(
            "UPDATE government_voluntary_auctions_v177 SET current_price=?,current_bidder_id=? WHERE auction_id=?",
            (int(amount), int(bidder_id), str(auction_id)),
        )
        await conn.execute(
            "INSERT INTO government_voluntary_bids_v177(bid_id,auction_id,bidder_id,amount,created_at) VALUES(?,?,?,?,?)",
            (secrets.token_urlsafe(12), str(auction_id), int(bidder_id), int(amount), now),
        )
        await operation(
            core,
            chat_id,
            bidder_id,
            "voluntary_auction_bid",
            "Ставка на добровольном аукционе",
            amount=amount,
            property_id=str(auction["property_id"]),
            payload={"auction_id": str(auction_id), "refunded_bidder_id": previous_id},
        )
        await conn.commit()
    return f"Ставка {fmt(amount)} принята."


async def process_voluntary_auctions(core: Any, bot: Any) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute(
        "SELECT * FROM government_voluntary_auctions_v177 WHERE status='active' AND ends_at<=? LIMIT 100",
        (now,),
    )
    for row in list(await cursor.fetchall()):
        message = ""
        async with core.db.lock:
            current = await (
                await conn.execute(
                    "SELECT * FROM government_voluntary_auctions_v177 WHERE auction_id=?",
                    (str(row["auction_id"]),),
                )
            ).fetchone()
            if current is None or str(current["status"]) != "active":
                continue
            bidder = int(current["current_bidder_id"] or 0)
            price = int(current["current_price"] or 0)
            if bidder and price:
                item = await (
                    await conn.execute(
                        "SELECT item_key FROM government_property_v176 WHERE property_id=?",
                        (str(current["property_id"]),),
                    )
                ).fetchone()
                conflict = (
                    await (
                        await conn.execute(
                            "SELECT 1 FROM government_property_v176 WHERE chat_id=? AND owner_id=? AND item_key=? AND property_id<>? LIMIT 1",
                            (
                                int(current["chat_id"]),
                                bidder,
                                str(item["item_key"]),
                                str(current["property_id"]),
                            ),
                        )
                    ).fetchone()
                    if item is not None
                    else None
                )
                if conflict is not None:
                    await conn.execute(
                        "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                        (price, now, int(current["chat_id"]), bidder),
                    )
                    await conn.execute(
                        "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                        (int(current["chat_id"]), bidder, price, "voluntary_auction_conflict_refund_v177", now),
                    )
                    await conn.execute(
                        "UPDATE government_property_v176 SET status='owned',updated_at=? WHERE property_id=?",
                        (now, str(current["property_id"])),
                    )
                    await conn.execute(
                        "UPDATE government_voluntary_auctions_v177 SET status='cancelled_conflict',resolved_at=? WHERE auction_id=?",
                        (now, str(current["auction_id"])),
                    )
                    await operation(
                        core,
                        int(current["chat_id"]),
                        bidder,
                        "voluntary_auction_cancelled",
                        "Аукцион отменён из-за дублирующегося типа имущества",
                        amount=price,
                        property_id=str(current["property_id"]),
                        payload={"auction_id": str(current["auction_id"])},
                    )
                    await conn.commit()
                    message = (
                        "🔨 <b>АУКЦИОН ОТМЕНЁН</b>\n\n"
                        "Победитель уже получил имущество этого типа другим способом. "
                        "Ставка полностью возвращена, объект остался у продавца."
                    )
                    await gov._publish(bot, int(row["chat_id"]), message)
                    continue
                commission = max(1, price * 5 // 100)
                seller_payout = price - commission
                await conn.execute(
                    "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                    (seller_payout, now, int(current["chat_id"]), int(current["seller_id"])),
                )
                await conn.execute(
                    "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                    (
                        int(current["chat_id"]),
                        int(current["seller_id"]),
                        seller_payout,
                        "voluntary_auction_sale_v177",
                        now,
                    ),
                )
                await conn.execute(
                    "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
                    (commission, now, int(current["chat_id"])),
                )
                await gov._treasury_log(
                    core,
                    int(current["chat_id"]),
                    commission,
                    "Комиссия добровольного аукциона",
                    "voluntary_auction_commission_v177",
                    str(current["auction_id"]),
                    int(current["seller_id"]),
                )
                await conn.execute(
                    "UPDATE government_property_v176 SET owner_id=?,status='owned',source_auction_id=?,updated_at=? WHERE property_id=?",
                    (bidder, str(current["auction_id"]), now, str(current["property_id"])),
                )
                await operation(
                    core,
                    int(current["chat_id"]),
                    int(current["seller_id"]),
                    "voluntary_auction_completed",
                    "Добровольный аукцион завершён",
                    amount=price,
                    property_id=str(current["property_id"]),
                    target_user_id=bidder,
                    payload={
                        "auction_id": str(current["auction_id"]),
                        "seller_payout": seller_payout,
                        "commission": commission,
                    },
                )
                message = (
                    "🔨 <b>ДОБРОВОЛЬНЫЙ АУКЦИОН ЗАВЕРШЁН</b>\n\n"
                    f"Победная ставка: <b>{fmt(price)}</b>. "
                    f"Продавец получил <b>{fmt(seller_payout)}</b>, "
                    f"комиссия казны — <b>{fmt(commission)}</b>."
                )
            else:
                await conn.execute(
                    "UPDATE government_property_v176 SET status='owned',updated_at=? WHERE property_id=?",
                    (now, str(current["property_id"])),
                )
                await operation(
                    core,
                    int(current["chat_id"]),
                    int(current["seller_id"]),
                    "voluntary_auction_no_bids",
                    "Аукцион завершён без ставок",
                    property_id=str(current["property_id"]),
                    payload={"auction_id": str(current["auction_id"])},
                )
                message = (
                    "🔨 <b>АУКЦИОН ЗАВЕРШЁН БЕЗ СТАВОК</b>\n\n"
                    "Имущество возвращено владельцу."
                )
            await conn.execute(
                "UPDATE government_voluntary_auctions_v177 SET status='completed',resolved_at=? WHERE auction_id=?",
                (now, str(current["auction_id"])),
            )
            await conn.commit()
        if message:
            await gov._publish(bot, int(row["chat_id"]), message)
