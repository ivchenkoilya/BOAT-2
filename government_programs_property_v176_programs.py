from __future__ import annotations

import html
import json
import math
import secrets
from typing import Any

import finance_investments_v127_core as investment_core
import finance_investments_v127_market as investment_market
import government_oversight_deputy_v167_data as oversight_data
import government_treasury_management_v164 as treasury
import government_v127 as gov

from government_programs_property_v176_common import (
    DAY, WEEK, PROGRAMS, _active_effect, _fmt, _json, _operation,
    _program_cost, ensure_schema, oversight_bonus,
)

async def run_program(core: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    await ensure_schema(core)
    await treasury._ensure_schema(core)
    program_key = str(data.get("program_key") or "")
    spec = PROGRAMS.get(program_key)
    if spec is None:
        raise ValueError("Неизвестная государственная программа.")
    offices = await gov._user_offices(core, chat_id, actor_id)
    is_admin = actor_id == int(core.DEVELOPER_ID)
    if not (is_admin or set(offices).intersection(spec["roles"])):
        raise PermissionError("У вашей должности нет права запускать эту программу.")
    if await gov._has_active_sanctions(core, chat_id, actor_id) and not is_admin:
        raise PermissionError("Чиновник с активными санкциями не может расходовать фонд.")

    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute(
        "SELECT balance FROM government_structure_funds_v164 WHERE chat_id=? AND structure_key=?",
        (chat_id, spec["fund_key"]),
    )
    fund_row = await cursor.fetchone()
    balance = int(fund_row["balance"] if fund_row else 0)
    requested = gov._as_int(data.get("amount"), int(spec["min_cost"]))
    cost = _program_cost(program_key, balance, requested)
    if cost <= 0 or balance < cost:
        raise ValueError(f"В фонде недостаточно средств. Требуется {_fmt(cost)}, доступно {_fmt(balance)}.")

    cursor = await conn.execute(
        """
        SELECT * FROM government_programs_v176
        WHERE chat_id=? AND program_key=? AND cooldown_until>?
        ORDER BY started_at DESC LIMIT 1
        """,
        (chat_id, program_key, now),
    )
    previous = await cursor.fetchone()
    if previous is not None:
        raise ValueError(f"Программа на перезарядке ещё {gov._remaining(int(previous['cooldown_until']))}.")

    payload: dict[str, Any] = {}
    recipients: list[tuple[int, str, int]] = []
    publish_extra = ""
    duration = int(spec["duration"])
    status = "active" if duration > 0 else "completed"
    ends_at = now + duration if duration > 0 else now

    if program_key == "festival":
        cursor = await conn.execute(
            """
            SELECT user_id,full_name,message_count FROM players
            WHERE chat_id=? ORDER BY message_count DESC,career_points DESC LIMIT 5
            """,
            (chat_id,),
        )
        winners = list(await cursor.fetchall())
        if not winners:
            raise ValueError("Нет активных участников для фестиваля.")
        pool = cost * 80 // 100
        each, remainder = divmod(pool, len(winners))
        recipients = [
            (int(row["user_id"]), str(row["full_name"] or f"ID {row['user_id']}"), each + (1 if i < remainder else 0))
            for i, row in enumerate(winners)
        ]
        payload = {"prize_pool": pool, "winners": [item[0] for item in recipients]}
    elif program_key == "social_help":
        count = max(3, min(5, gov._as_int(data.get("recipient_count"), 5)))
        cursor = await conn.execute(
            """
            SELECT p.user_id,p.full_name,p.points FROM players p
            WHERE p.chat_id=? AND NOT EXISTS(
              SELECT 1 FROM government_offices_v127 o
              WHERE o.chat_id=p.chat_id AND o.user_id=p.user_id AND o.ends_at>?
            )
            ORDER BY p.points ASC,p.message_count DESC LIMIT ?
            """,
            (chat_id, now, count),
        )
        people = list(await cursor.fetchall())
        if len(people) < 3:
            raise ValueError("Для социальной помощи требуется минимум три участника без высокой должности.")
        each, remainder = divmod(cost, len(people))
        recipients = [
            (int(row["user_id"]), str(row["full_name"] or f"ID {row['user_id']}"), each + (1 if i < remainder else 0))
            for i, row in enumerate(people)
        ]
        payload = {"recipients": [item[0] for item in recipients]}
    elif program_key == "market_intervention":
        symbol = str(data.get("symbol") or "").upper()
        if symbol not in investment_core.STOCKS:
            raise ValueError("Выберите существующую акцию.")
        await investment_market._initialize_market(core, chat_id)
        payload = {"symbol": symbol}
    elif program_key == "election_campaign":
        cursor = await conn.execute(
            """
            SELECT election_id,office_key FROM government_elections_v127
            WHERE chat_id=? AND phase IN ('nomination','voting')
            ORDER BY created_at DESC
            """,
            (chat_id,),
        )
        elections = list(await cursor.fetchall())
        if not elections:
            raise ValueError("Сейчас нет активных выборов для кампании.")
        payload = {
            "election_ids": [str(row["election_id"]) for row in elections],
            "participation_pool": cost // 2,
            "settled": False,
        }
    elif program_key == "oversight_operation":
        payload = {"extra_inspections": 1, "expanded_report": True}

    run_id = secrets.token_urlsafe(12)
    effect_id = secrets.token_urlsafe(12)
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT balance FROM government_structure_funds_v164 WHERE chat_id=? AND structure_key=?",
            (chat_id, spec["fund_key"]),
        )
        locked = await cursor.fetchone()
        if locked is None or int(locked["balance"]) < cost:
            raise ValueError("Баланс фонда изменился: средств уже недостаточно.")
        cursor = await conn.execute(
            """
            SELECT 1 FROM government_programs_v176
            WHERE chat_id=? AND program_key=? AND cooldown_until>? LIMIT 1
            """,
            (chat_id, program_key, now),
        )
        if await cursor.fetchone() is not None:
            raise ValueError("Эта программа уже была запущена другим чиновником.")
        await conn.execute(
            "UPDATE government_structure_funds_v164 SET balance=balance-?,updated_at=? WHERE chat_id=? AND structure_key=?",
            (cost, now, chat_id, spec["fund_key"]),
        )
        await conn.execute(
            """
            INSERT INTO government_programs_v176(
              run_id,chat_id,program_key,fund_key,cost,actor_id,status,payload_json,
              started_at,ends_at,cooldown_until,resolved_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                run_id, chat_id, program_key, spec["fund_key"], cost, actor_id, status,
                json.dumps(payload, ensure_ascii=False), now, ends_at, now + int(spec["cooldown"]),
                now if status == "completed" else 0,
            ),
        )
        if duration > 0:
            value = 40 if program_key == "anti_crisis" else 1 if program_key == "oversight_operation" else cost
            await conn.execute(
                """
                INSERT INTO government_program_effects_v176(
                  effect_id,chat_id,effect_key,source_run_id,value,payload_json,starts_at,ends_at,active
                ) VALUES(?,?,?,?,?,?,?,?,1)
                """,
                (effect_id, chat_id, program_key, run_id, value, json.dumps(payload, ensure_ascii=False), now, ends_at),
            )
        for user_id, _name, amount in recipients:
            if amount <= 0:
                continue
            await conn.execute(
                "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (amount, now, chat_id, user_id),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (chat_id, user_id, amount, f"government_program_{program_key}_v176", now),
            )
        if program_key == "market_intervention":
            symbol = str(payload["symbol"])
            cursor = await conn.execute(
                "SELECT price FROM finance_market_v127 WHERE chat_id=? AND symbol=?",
                (chat_id, symbol),
            )
            market = await cursor.fetchone()
            if market is None:
                raise ValueError("Биржа не успела создать выбранную акцию.")
            price = int(market["price"])
            impulse_bp = max(50, min(250, 50 + cost // 2_000))
            adjusted = max(5, round(price * (1 + impulse_bp / 10_000)))
            adjusted = min(adjusted, max(price + 1, round(price * 1.025)))
            bucket = now // investment_core.MARKET_TICK_SECONDS
            await conn.execute(
                """
                UPDATE finance_market_v127 SET previous_price=price,price=?,high_price=MAX(high_price,?),
                  last_event=?,last_event_at=? WHERE chat_id=? AND symbol=?
                """,
                (adjusted, adjusted, f"Финансовая интервенция государства: {impulse_bp / 100:.2f}%", now, chat_id, symbol),
            )
            await conn.execute(
                """
                INSERT INTO finance_stock_history_v127(chat_id,symbol,bucket,price,volume)
                VALUES(?,?,?,?,?) ON CONFLICT(chat_id,symbol,bucket) DO UPDATE SET price=excluded.price
                """,
                (chat_id, symbol, bucket, adjusted, max(1, cost // 1_000)),
            )
            payload.update({"impulse_bp": impulse_bp, "price_before": price, "price_after": adjusted})
            await conn.execute(
                "UPDATE government_programs_v176 SET payload_json=? WHERE run_id=?",
                (json.dumps(payload, ensure_ascii=False), run_id),
            )
        await _operation(
            core, chat_id, actor_id, "program_start", f"{spec['title']}: расход фонда",
            amount=cost, program_run_id=run_id, payload={"program_key": program_key, "fund_key": spec["fund_key"]},
        )
        await conn.commit()

    if recipients:
        publish_extra = "\n" + "\n".join(
            f"• <b>{html.escape(name)}</b>: {_fmt(amount)}" for _uid, name, amount in recipients
        )
    await gov._publish(
        bot,
        chat_id,
        f"{spec['emoji']} <b>{html.escape(spec['title'].upper())}</b>\n\n"
        f"Из фонда «<b>{html.escape(treasury.STRUCTURES[spec['fund_key']]['title'])}</b>» "
        f"списано <b>{_fmt(cost)}</b> влияния.\n"
        f"Инициатор: <b>{html.escape(str((await gov._player_dict(core, chat_id, actor_id) or {}).get('name') or actor_id))}</b>\n\n"
        f"{html.escape(spec['effect'])}{publish_extra}",
    )
    return f"Программа «{spec['title']}» запущена. Из фонда списано {_fmt(cost)}."


async def apply_anti_crisis(core: Any, chat_id: int, before: dict[str, int]) -> None:
    effect = await _active_effect(core, chat_id, "anti_crisis")
    if effect is None or not before:
        return
    conn = core.db._require_connection()
    now = gov._now()
    bucket = now // investment_core.MARKET_TICK_SECONDS
    async with core.db.lock:
        for symbol, old_price in before.items():
            cursor = await conn.execute(
                "SELECT price FROM finance_market_v127 WHERE chat_id=? AND symbol=?",
                (chat_id, symbol),
            )
            row = await cursor.fetchone()
            if row is None:
                continue
            price = int(row["price"])
            if price >= int(old_price):
                continue
            decline = int(old_price) - price
            recovered = max(1, math.floor(decline * 0.40))
            adjusted = min(int(old_price), price + recovered)
            await conn.execute(
                "UPDATE finance_market_v127 SET price=?,low_price=MIN(low_price,?),last_event=?,last_event_at=? WHERE chat_id=? AND symbol=?",
                (adjusted, adjusted, "Антикризисный пакет смягчил падение", now, chat_id, symbol),
            )
            await conn.execute(
                "UPDATE finance_stock_history_v127 SET price=? WHERE chat_id=? AND symbol=? AND bucket=?",
                (adjusted, chat_id, symbol, bucket),
            )
        await conn.commit()


async def process_expired_effects(core: Any, bot: Any) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute("SELECT * FROM government_program_effects_v176 WHERE active=1 AND ends_at<=? ORDER BY ends_at LIMIT 100", (now,))
    rows = list(await cursor.fetchall())
    for row in rows:
        effect_id = str(row["effect_id"])
        effect_key = str(row["effect_key"])
        chat_id = int(row["chat_id"])
        payload = _json(row["payload_json"], {})
        publish = ""
        async with core.db.lock:
            cursor2 = await conn.execute("SELECT active FROM government_program_effects_v176 WHERE effect_id=?", (effect_id,))
            current = await cursor2.fetchone()
            if current is None or not int(current["active"]):
                continue
            if effect_key == "election_campaign" and not payload.get("settled"):
                ids = [str(value) for value in payload.get("election_ids", []) if str(value)]
                voters: list[int] = []
                if ids:
                    placeholders = ",".join("?" for _ in ids)
                    cursor3 = await conn.execute(
                        f"SELECT DISTINCT voter_id FROM government_election_votes_v127 WHERE election_id IN ({placeholders})",
                        tuple(ids),
                    )
                    voters = [int(item["voter_id"]) for item in await cursor3.fetchall()]
                pool = max(0, int(payload.get("participation_pool") or 0))
                if voters and pool > 0:
                    each, remainder = divmod(pool, len(voters))
                    for index, voter_id in enumerate(voters):
                        reward = each + (1 if index < remainder else 0)
                        await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?", (reward, now, chat_id, voter_id))
                        await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (chat_id, voter_id, reward, "election_campaign_reward_v176", now))
                    publish = f"🗳 <b>ИЗБИРАТЕЛЬНАЯ КАМПАНИЯ ЗАВЕРШЕНА</b>\n\nНаграду за участие получили <b>{len(voters)}</b> участников. Призовой фонд: <b>{_fmt(pool)}</b>. Результаты голосования не изменялись."
                elif pool > 0:
                    await conn.execute(
                        "UPDATE government_structure_funds_v164 SET balance=balance+?,updated_at=? WHERE chat_id=? AND structure_key='election_commission'",
                        (pool, now, chat_id),
                    )
                payload["settled"] = True
                await conn.execute("UPDATE government_program_effects_v176 SET payload_json=? WHERE effect_id=?", (json.dumps(payload, ensure_ascii=False), effect_id))
            await conn.execute("UPDATE government_program_effects_v176 SET active=0 WHERE effect_id=?", (effect_id,))
            await conn.execute("UPDATE government_programs_v176 SET status='completed',resolved_at=? WHERE run_id=?", (now, str(row["source_run_id"])))
            await conn.commit()
        if publish:
            await gov._publish(bot, chat_id, publish)


async def expanded_oversight_report(core: Any, bot: Any, chat_id: int, actor_id: int) -> str:
    access = await oversight_data._access(core, chat_id, actor_id)
    if not access["can_manage"]:
        raise PermissionError("Расширенный отчёт доступен руководству Надзора.")
    effect = await _active_effect(core, chat_id, "oversight_operation")
    if effect is None:
        raise ValueError("Сначала запустите программу «Операция Надзора».")
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT 1 FROM government_property_operations_v176 WHERE chat_id=? AND operation_type='expanded_oversight_report' AND program_run_id=? LIMIT 1",
        (chat_id, str(effect["source_run_id"])),
    )
    if await cursor.fetchone() is not None:
        raise ValueError("Расширенный отчёт по этой операции уже опубликован.")
    since = gov._now() - WEEK
    async def count(sql: str, params: tuple[Any, ...]) -> int:
        cursor = await conn.execute(sql, params)
        row = await cursor.fetchone()
        return int(row["amount"] if row else 0)
    complaints = await count("SELECT COUNT(*) amount FROM government_cases_v128 WHERE chat_id=? AND institution='oversight_deputy' AND case_type='complaint' AND created_at>=?", (chat_id, since))
    inspections = await count("SELECT COUNT(*) amount FROM government_cases_v128 WHERE chat_id=? AND institution='oversight_deputy' AND case_type='inspection' AND created_at>=?", (chat_id, since))
    property_checks = await count("SELECT COUNT(*) amount FROM government_property_investigations_v176 WHERE chat_id=? AND created_at>=?", (chat_id, since))
    seized = await count("SELECT COUNT(*) amount FROM government_property_v176 WHERE chat_id=? AND status LIKE 'seized%'", (chat_id,))
    await _operation(core, chat_id, actor_id, "expanded_oversight_report", "Расширенный отчёт Операции Надзора", program_run_id=str(effect["source_run_id"]), payload={"complaints": complaints, "inspections": inspections, "property_checks": property_checks, "seized": seized})
    await conn.commit()
    await gov._publish(bot, chat_id, f"📊 <b>РАСШИРЕННЫЙ ОТЧЁТ НАДЗОРА</b>\n\nЖалоб за 7 дней: <b>{complaints}</b>\nОбычных проверок: <b>{inspections}</b>\nИмущественных проверок: <b>{property_checks}</b>\nАрестованных объектов: <b>{seized}</b>")
    return "Расширенный отчёт опубликован."

