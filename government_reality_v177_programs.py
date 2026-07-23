from __future__ import annotations

import html
import json
import random
import secrets
from typing import Any

import finance_investments_v127_core as market_core
import finance_investments_v127_market as market
import government_v127 as gov
import government_treasury_management_v164 as treasury

from government_reality_v177_common import DAY, PROGRAMS, ROLE_NAMES, fmt, json_value, program_cost, role_label, ensure_schema, operation
from government_reality_v177_funds import debit_fund_locked, fund_balance, migrate_funds, structures_state
from government_reality_v177_ratings import adjust_rating

OLD_EFFECTS = {"anti_crisis", "oversight_operation", "election_campaign"}


async def _effect(core: Any, chat_id: int, key: str) -> Any | None:
    conn = core.db._require_connection()
    now = gov._now()
    table = "government_program_effects_v176" if key in OLD_EFFECTS else "government_program_effects_v177"
    cursor = await conn.execute(f"SELECT * FROM {table} WHERE chat_id=? AND effect_key=? AND active=1 AND ends_at>? ORDER BY ends_at DESC LIMIT 1", (int(chat_id), str(key), now))
    return await cursor.fetchone()


async def programs_state(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    await migrate_funds(core)
    await ensure_schema(core)
    conn = core.db._require_connection()
    offices = await gov._user_offices(core, int(chat_id), int(user_id))
    sanctioned = await gov._has_active_sanctions(core, int(chat_id), int(user_id))
    is_admin = int(user_id) == int(core.DEVELOPER_ID)
    now = gov._now()
    structures = {item["key"]: item for item in await structures_state(core, int(chat_id))}
    cursor = await conn.execute("SELECT * FROM government_programs_v176 WHERE chat_id=? ORDER BY started_at DESC LIMIT 80", (int(chat_id),))
    history = [dict(row) for row in await cursor.fetchall()]
    latest: dict[str, dict[str, Any]] = {}
    for row in history:
        latest.setdefault(str(row["program_key"]), row)
    cards = []
    for key, spec in PROGRAMS.items():
        balance = int(structures.get(str(spec["fund_key"]), {}).get("balance") or 0)
        last = latest.get(key, {})
        active = bool(str(last.get("status") or "") == "active" and int(last.get("ends_at") or 0) > now)
        cooldown_until = int(last.get("cooldown_until") or 0)
        cost = program_cost(key, balance, int(spec["min_cost"]))
        can_role = bool(is_admin or set(offices).intersection(spec["roles"]))
        reason = ""
        if sanctioned and not is_admin:
            reason = "У чиновника активные санкции"
        elif not can_role:
            titles = [ROLE_NAMES.get(role, role) for role in sorted(spec["roles"])]
            reason = "Доступно: " + ", ".join(titles)
        elif active:
            reason = f"Программа уже действует до {gov._date_text(int(last.get('ends_at') or 0))}"
        elif cooldown_until > now:
            reason = f"Перезарядка: ещё {gov._remaining(cooldown_until)}"
        elif balance < cost:
            reason = f"Недостаточно средств: {fmt(balance)} из {fmt(cost)}"
        cards.append({
            "key": key, "emoji": spec["emoji"], "title": spec["title"], "effect": spec["effect"],
            "fund_key": spec["fund_key"], "fund_title": structures.get(str(spec["fund_key"]), {}).get("title", str(spec["fund_key"])),
            "fund_balance": balance, "min_cost": int(spec["min_cost"]), "max_cost": int(spec["max_cost"]),
            "calculated_cost": cost, "duration": int(spec["duration"]), "cooldown": int(spec["cooldown"]),
            "can_start": bool(not reason), "unavailable_reason": reason, "active": active,
            "ends_at": int(last.get("ends_at") or 0), "cooldown_until": cooldown_until,
            "requires_target": key == "housing_subsidy", "requires_symbol": key in {"market_intervention"},
            "manual_amount": spec["cost_mode"] == "manual",
        })
    cursor = await conn.execute("SELECT * FROM government_program_effects_v177 WHERE chat_id=? AND active=1 AND ends_at>? ORDER BY ends_at", (int(chat_id), now))
    effects = [dict(row) for row in await cursor.fetchall()]
    cursor = await conn.execute("SELECT * FROM government_program_effects_v176 WHERE chat_id=? AND active=1 AND ends_at>? ORDER BY ends_at", (int(chat_id), now))
    effects.extend(dict(row) for row in await cursor.fetchall())
    return {"programs": cards, "history": history[:30], "active_effects": effects, "structures": list(structures.values()), "sanctioned": bool(sanctioned)}


async def _recipients(core: Any, chat_id: int, mode: str, count: int, exclude_officials: bool = False) -> list[Any]:
    conn = core.db._require_connection()
    if mode == "career":
        order = "career_points ASC,points ASC,message_count DESC"
    else:
        order = "points ASC,career_points ASC,message_count DESC"
    exclusion = " AND NOT EXISTS(SELECT 1 FROM government_offices_v127 o WHERE o.chat_id=players.chat_id AND o.user_id=players.user_id AND o.ends_at>?)" if exclude_officials else ""
    params = (int(chat_id), gov._now(), int(count)) if exclude_officials else (int(chat_id), int(count))
    cursor = await conn.execute(f"SELECT user_id,full_name,points,career_points FROM players WHERE chat_id=?{exclusion} ORDER BY {order} LIMIT ?", params)
    return list(await cursor.fetchall())


async def _publish_once(core: Any, bot: Any, run_id: str) -> None:
    """Claim and publish one outbox row without sending the same run twice."""
    conn = core.db._require_connection()
    now = gov._now()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT * FROM government_program_publications_v177 WHERE run_id=?",
            (str(run_id),),
        )
        row = await cursor.fetchone()
        if row is None or str(row["status"]) == "sent":
            return
        if str(row["status"]) == "sending" and int(row["updated_at"] or 0) > now - 120:
            return
        cursor = await conn.execute(
            """UPDATE government_program_publications_v177
            SET status='sending',updated_at=?
            WHERE run_id=? AND status<>'sent'""",
            (now, str(run_id)),
        )
        if int(cursor.rowcount or 0) <= 0:
            return
        await conn.commit()
    try:
        await bot.send_message(int(row["chat_id"]), str(row["text"]))
    except Exception as exc:
        async with core.db.lock:
            await conn.execute(
                """UPDATE government_program_publications_v177
                SET status='pending',attempts=attempts+1,last_error=?,updated_at=?
                WHERE run_id=? AND status='sending'""",
                (str(exc)[:500], gov._now(), str(run_id)),
            )
            await conn.commit()
        return
    async with core.db.lock:
        await conn.execute(
            """UPDATE government_program_publications_v177
            SET status='sent',attempts=attempts+1,last_error='',updated_at=?
            WHERE run_id=? AND status='sending'""",
            (gov._now(), str(run_id)),
        )
        await conn.commit()


async def run_program(core: Any, bot: Any, chat_id: int, actor_id: int, data: dict[str, Any]) -> str:
    await migrate_funds(core)
    await ensure_schema(core)
    key = str(data.get("program_key") or "")
    spec = PROGRAMS.get(key)
    if spec is None:
        raise ValueError("Неизвестная государственная программа.")
    request_id = str(data.get("request_id") or "").strip() or secrets.token_urlsafe(16)
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT result_text,run_id FROM government_program_requests_v177 WHERE request_id=?", (request_id,))
    prior = await cursor.fetchone()
    if prior is not None:
        await _publish_once(core, bot, str(prior["run_id"]))
        return str(prior["result_text"])
    offices = await gov._user_offices(core, int(chat_id), int(actor_id))
    is_admin = int(actor_id) == int(core.DEVELOPER_ID)
    if not (is_admin or set(offices).intersection(spec["roles"])):
        raise PermissionError("У вашей должности нет права запускать эту программу.")
    if await gov._has_active_sanctions(core, int(chat_id), int(actor_id)) and not is_admin:
        raise PermissionError("Чиновник с активными санкциями не может расходовать государственный фонд.")
    balance = await fund_balance(core, int(chat_id), str(spec["fund_key"]))
    requested = gov._as_int(data.get("amount"), int(spec["min_cost"]))
    cost = program_cost(key, balance, requested)
    if balance < cost:
        raise ValueError(f"В фонде недостаточно средств. Требуется {fmt(cost)}, доступно {fmt(balance)}.")
    now = gov._now()
    cursor = await conn.execute("SELECT cooldown_until FROM government_programs_v176 WHERE chat_id=? AND program_key=? AND cooldown_until>? ORDER BY started_at DESC LIMIT 1", (int(chat_id), key, now))
    cooldown = await cursor.fetchone()
    if cooldown is not None:
        raise ValueError(f"Программа на перезарядке ещё {gov._remaining(int(cooldown['cooldown_until']))}.")
    run_id = secrets.token_urlsafe(12)
    payload: dict[str, Any] = {}
    duration = int(spec["duration"])
    ends_at = now + duration if duration else now
    status = "active" if duration else "completed"
    public_details: list[str] = []
    if key in {"market_intervention", "economy_support"}:
        await market._initialize_market(core, int(chat_id))
    async with core.db.lock:
        try:
            cursor = await conn.execute(
                "SELECT result_text,run_id FROM government_program_requests_v177 WHERE request_id=?",
                (request_id,),
            )
            prior_locked = await cursor.fetchone()
            if prior_locked is not None:
                return str(prior_locked["result_text"])
            cursor = await conn.execute(
                """SELECT cooldown_until FROM government_programs_v176
                WHERE chat_id=? AND program_key=? AND cooldown_until>?
                ORDER BY started_at DESC LIMIT 1""",
                (int(chat_id), key, now),
            )
            locked_cooldown = await cursor.fetchone()
            if locked_cooldown is not None:
                raise ValueError(
                    f"Программа уже запущена другим чиновником. Перезарядка: {gov._remaining(int(locked_cooldown['cooldown_until']))}."
                )
            await debit_fund_locked(core, chat_id, str(spec["fund_key"]), cost)
            if key in {"festival", "social_help", "education_grants", "emergency_social"}:
                count = 5 if key != "social_help" else max(3, min(5, gov._as_int(data.get("recipient_count"), 5)))
                mode = "career" if key == "education_grants" else "points"
                people = await _recipients(core, chat_id, mode, count, key in {"social_help", "emergency_social"})
                if len(people) < 1:
                    raise ValueError("Не найдены участники для выплаты.")
                pool = cost * 80 // 100 if key == "festival" else cost
                each, remainder = divmod(pool, len(people))
                recipient_ids = []
                for index, person in enumerate(people):
                    amount = each + (1 if index < remainder else 0)
                    await conn.execute("UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?", (amount, now, int(chat_id), int(person["user_id"])))
                    await conn.execute("INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)", (int(chat_id), int(person["user_id"]), amount, f"government_program_{key}_v177", now))
                    recipient_ids.append(int(person["user_id"]))
                    public_details.append(f"• {html.escape(str(person['full_name'] or person['user_id']))}: <b>{fmt(amount)}</b>")
                payload["recipients"] = recipient_ids
            elif key in {"market_intervention", "economy_support"}:
                symbols = [str(data.get("symbol") or "EGO").upper()] if key == "market_intervention" else list(market_core.STOCKS.keys())
                changed = {}
                for symbol in symbols:
                    if symbol not in market_core.STOCKS:
                        continue
                    cursor2 = await conn.execute("SELECT price FROM finance_market_v127 WHERE chat_id=? AND symbol=?", (int(chat_id), symbol))
                    row = await cursor2.fetchone()
                    if row is None:
                        continue
                    old = int(row["price"])
                    bp = min(250, max(40, cost // 5_000)) if key == "market_intervention" else min(120, max(25, cost // 25_000))
                    new = max(old + 1, round(old * (1 + bp / 10_000)))
                    new = min(new, round(old * 1.025))
                    await conn.execute("UPDATE finance_market_v127 SET previous_price=price,price=?,high_price=MAX(high_price,?),last_event=?,last_event_at=? WHERE chat_id=? AND symbol=?", (new, new, spec["title"], now, int(chat_id), symbol))
                    changed[symbol] = {"before": old, "after": new}
                payload["stocks"] = changed
            elif key == "housing_subsidy":
                target_id = gov._as_int(data.get("target_user_id"))
                cursor2 = await conn.execute("SELECT property_id,debt FROM government_property_v176 WHERE chat_id=? AND owner_id=? AND debt>0 ORDER BY debt DESC", (int(chat_id), target_id))
                debts = list(await cursor2.fetchall())
                remaining = cost
                paid = 0
                for debt_row in debts:
                    value = min(remaining, int(debt_row["debt"]))
                    if value <= 0:
                        break
                    new_debt = int(debt_row["debt"]) - value
                    new_status = "owned" if new_debt <= 0 else "seized_debt"
                    await conn.execute("UPDATE government_property_v176 SET debt=?,status=?,updated_at=? WHERE property_id=?", (new_debt, new_status, now, str(debt_row["property_id"])))
                    if new_debt <= 0:
                        await conn.execute("DELETE FROM government_property_debts_v176 WHERE property_id=?", (str(debt_row["property_id"]),))
                    paid += value
                    remaining -= value
                if paid <= 0:
                    raise ValueError("У выбранного участника нет задолженности по имуществу.")
                await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (paid, now, int(chat_id)))
                if remaining > 0:
                    await conn.execute("UPDATE government_structure_funds_v164 SET balance=balance+?,updated_at=? WHERE chat_id=? AND structure_key=?", (remaining, now, int(chat_id), str(spec["fund_key"])))
                    cost = paid
                payload.update({"target_user_id": target_id, "paid": paid})
            elif key == "election_campaign":
                cursor2 = await conn.execute("SELECT election_id FROM government_elections_v127 WHERE chat_id=? AND phase IN ('nomination','voting') ORDER BY created_at DESC", (int(chat_id),))
                elections = [str(row["election_id"]) for row in await cursor2.fetchall()]
                if not elections:
                    raise ValueError("Сейчас нет активных выборов для государственной кампании.")
                payload = {"election_ids": elections, "participation_pool": cost // 2, "settled": False}
            elif key == "anti_corruption_audit":
                cursor2 = await conn.execute("SELECT operation_id,amount,reason,actor_id FROM government_treasury_operations_v164 WHERE chat_id=? ORDER BY amount DESC,created_at DESC LIMIT 1", (int(chat_id),))
                suspicious = await cursor2.fetchone()
                if suspicious:
                    case_id = secrets.token_urlsafe(10)
                    await conn.execute("""INSERT INTO government_cases_v128(case_id,chat_id,institution,case_type,title,description,target_user_id,status,payload_json,created_by,created_at,updated_at,resolved_at)
                    VALUES(?,?,'oversight_deputy','inspection','Антикоррупционный аудит',?,?,'open',?,?,?, ?,0)""", (case_id, int(chat_id), f"Проверка крупной операции: {suspicious['reason']}", int(suspicious['actor_id']), json.dumps({"operation_id": str(suspicious['operation_id'])}, ensure_ascii=False), int(actor_id), now, now))
                    payload["case_id"] = case_id
            elif key == "information_campaign":
                await adjust_rating(core, chat_id, actor_id, 3, "Государственная информационная кампания", "program", actor_id)
            elif key == "emergency_mode":
                payload["emergency_transfer_available"] = True
            await conn.execute("""INSERT INTO government_programs_v176(run_id,chat_id,program_key,fund_key,cost,actor_id,status,payload_json,started_at,ends_at,cooldown_until,resolved_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", (run_id, int(chat_id), key, str(spec["fund_key"]), int(cost), int(actor_id), status, json.dumps(payload, ensure_ascii=False), now, ends_at, now + int(spec["cooldown"]), now if status == "completed" else 0))
            if duration:
                table = "government_program_effects_v176" if key in OLD_EFFECTS else "government_program_effects_v177"
                effect_value = 40 if key == "anti_crisis" else 1 if key == "oversight_operation" else int(cost)
                await conn.execute(f"""INSERT INTO {table}(effect_id,chat_id,effect_key,source_run_id,value,payload_json,starts_at,ends_at,active)
                VALUES(?,?,?,?,?,?,?,?,1)""", (secrets.token_urlsafe(12), int(chat_id), key, run_id, effect_value, json.dumps(payload, ensure_ascii=False), now, ends_at))
            await operation(core, chat_id, actor_id, "program_start", f"{spec['title']}: расход фонда", amount=cost, run_id=run_id, payload={"program_key": key, "fund_key": spec["fund_key"]})
            await adjust_rating(core, chat_id, actor_id, 2, f"Успешный запуск программы «{spec['title']}»", "program", actor_id)
            actor = await gov._player_dict(core, chat_id, actor_id)
            message = (
                f"🏛 <b>ГОСУДАРСТВЕННАЯ ПРОГРАММА ЗАПУЩЕНА</b>\n\n"
                f"{spec['emoji']} <b>{html.escape(str(spec['title']).upper())}</b>\n\n"
                f"Инициатор: <b>{html.escape(str((actor or {}).get('name') or actor_id))}</b> · {html.escape(role_label(offices))}\n"
                f"Финансирование: <b>{html.escape(str(treasury.STRUCTURES.get(str(spec['fund_key']), {'title': spec['fund_key']})['title']))}</b>\n"
                f"Расход: <b>{fmt(cost)}</b> влияния\n"
                f"Срок действия: <b>{gov._remaining(ends_at) if duration else 'эффект применён сразу'}</b>\n"
                f"Повторный запуск: <b>{gov._date_text(now + int(spec['cooldown']))}</b>\n\n"
                f"{html.escape(str(spec['effect']))}"
            )
            if public_details:
                message += "\n\n" + "\n".join(public_details)
            await conn.execute(
                """INSERT INTO government_program_publications_v177(
                run_id,chat_id,text,status,attempts,last_error,updated_at)
                VALUES(?,?,?,'pending',0,'',?)""",
                (run_id, int(chat_id), message, now),
            )
            result = f"Программа «{spec['title']}» запущена. Из фонда списано {fmt(cost)}."
            await conn.execute("INSERT INTO government_program_requests_v177(request_id,chat_id,actor_id,program_key,run_id,result_text,created_at) VALUES(?,?,?,?,?,?,?)", (request_id, int(chat_id), int(actor_id), key, run_id, result, now))
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    await _publish_once(core, bot, run_id)
    return result


async def emergency_transfer(core: Any, bot: Any, chat_id: int, actor_id: int) -> str:
    effect = await _effect(core, chat_id, "emergency_mode")
    if effect is None:
        raise ValueError("Режим чрезвычайной ситуации сейчас не действует.")
    offices = await gov._user_offices(core, chat_id, actor_id)
    if not set(offices).intersection({"president", "security"}) and actor_id != int(core.DEVELOPER_ID):
        raise PermissionError("Экстренное действие доступно президенту и Совбезу.")
    payload = json_value(effect["payload_json"], {})
    if payload.get("transfer_used"):
        raise ValueError("Экстренное пополнение по этому режиму уже использовано.")
    conn = core.db._require_connection()
    async with core.db.lock:
        cursor = await conn.execute("SELECT balance FROM government_structure_funds_v164 WHERE chat_id=? AND structure_key='reserve'", (int(chat_id),))
        row = await cursor.fetchone()
        amount = max(0, int(row["balance"] if row else 0) // 10)
        if amount <= 0:
            raise ValueError("Резервный фонд пуст.")
        await debit_fund_locked(core, chat_id, "reserve", amount)
        await conn.execute("UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?", (amount, gov._now(), int(chat_id)))
        payload["transfer_used"] = True
        await conn.execute("UPDATE government_program_effects_v177 SET payload_json=? WHERE effect_id=?", (json.dumps(payload, ensure_ascii=False), str(effect["effect_id"])))
        await conn.commit()
    await gov._publish(bot, chat_id, f"🚑 <b>ЭКСТРЕННАЯ СТАБИЛИЗАЦИЯ</b>\n\nИз Резервного фонда в свободную казну переведено <b>{fmt(amount)}</b> влияния.")
    return f"Свободная казна экстренно пополнена на {fmt(amount)}."


async def process_v177_effects(core: Any, bot: Any) -> None:
    await ensure_schema(core)
    conn = core.db._require_connection()
    now = gov._now()
    cursor = await conn.execute("SELECT * FROM government_program_effects_v177 WHERE active=1 AND ends_at<=? LIMIT 100", (now,))
    rows = list(await cursor.fetchall())
    for row in rows:
        message = ""
        async with core.db.lock:
            cursor2 = await conn.execute("SELECT active FROM government_program_effects_v177 WHERE effect_id=?", (str(row["effect_id"]),))
            current = await cursor2.fetchone()
            if current is None or not int(current["active"]):
                continue
            if str(row["effect_key"]) == "science_project":
                bonuses = [("reserve", 25), ("social_fund", 20), ("event_fund", 20), ("finance_ministry", 15)]
                structure_key, percent = random.choice(bonuses)
                reward = max(10_000, int(row["value"]) * percent // 100)
                await conn.execute("""INSERT INTO government_structure_funds_v164(chat_id,structure_key,balance,updated_at) VALUES(?,?,?,?)
                ON CONFLICT(chat_id,structure_key) DO UPDATE SET balance=balance+excluded.balance,updated_at=excluded.updated_at""", (int(row["chat_id"]), structure_key, reward, now))
                message = f"🧪 <b>НАУЧНЫЙ ПРОЕКТ ЗАВЕРШЁН</b>\n\nГосударственный бонус: <b>{fmt(reward)}</b> перечислено в фонд «{structure_key}»."
            await conn.execute("UPDATE government_program_effects_v177 SET active=0 WHERE effect_id=?", (str(row["effect_id"]),))
            await conn.execute("UPDATE government_programs_v176 SET status='completed',resolved_at=? WHERE run_id=?", (now, str(row["source_run_id"])))
            await conn.commit()
        if message:
            await gov._publish(bot, int(row["chat_id"]), message)
    cursor = await conn.execute("SELECT run_id FROM government_program_publications_v177 WHERE status='pending' AND attempts<10 ORDER BY updated_at LIMIT 30")
    for item in await cursor.fetchall():
        await _publish_once(core, bot, str(item["run_id"]))


async def active_effect(core: Any, chat_id: int, key: str) -> Any | None:
    return await _effect(core, chat_id, key)
