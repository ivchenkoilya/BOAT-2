from __future__ import annotations

import secrets
from typing import Any

import government_reality_v177_funds as fund_bridge
import government_treasury_contributions_v150 as contributions
import government_v127 as gov

from government_reality_v179_common import MAX_SQLITE_INTEGER, SOURCE_TITLES, ensure_schema


def install_treasury_v179(core: Any) -> None:
    if getattr(core, "_government_reality_v179_treasury_installed", False):
        return
    core._government_reality_v179_treasury_installed = True

    contributions.FUND_SPECS["general"] = {
        "emoji": "💰",
        "title": "Министерство финансов",
        "hint": "Профильный бюджет Министерства финансов",
    }
    contributions.FUND_SPECS["state_treasury"] = {
        "emoji": "🏛",
        "title": "Общая казна",
        "hint": "Свободные средства государства для общих расходов",
    }
    contributions.MAX_CONTRIBUTION = MAX_SQLITE_INTEGER

    previous_serialize = contributions._serialize_contributions

    async def serialize_v179(core_arg: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        payload = await previous_serialize(core_arg, int(chat_id), int(user_id))
        await gov._ensure_state(core_arg, int(chat_id))
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT treasury FROM government_state_v127 WHERE chat_id=?",
            (int(chat_id),),
        )
        row = await cursor.fetchone()
        treasury_amount = int(row["treasury"] if row else 0)
        funds = [item for item in payload.get("funds", []) if str(item.get("key")) != "state_treasury"]
        for item in funds:
            if str(item.get("key")) == "general":
                item.update(contributions.FUND_SPECS["general"])
        funds.insert(
            0,
            {
                "key": "state_treasury",
                **contributions.FUND_SPECS["state_treasury"],
                "amount": treasury_amount,
            },
        )
        payload["funds"] = funds
        payload["max_amount"] = int(payload.get("available_balance") or 0)
        payload["fixed_max_removed"] = True
        return payload

    contributions._serialize_contributions = serialize_v179


async def contribute_v179(core: Any, chat_id: int, user_id: int, data: dict[str, Any]) -> tuple[int, str]:
    await contributions._ensure_schema(core)
    await fund_bridge.treasury._ensure_schema(core)
    await fund_bridge.ensure_schema(core)
    await ensure_schema(core)
    await gov._ensure_state(core, int(chat_id))
    await fund_bridge.migrate_funds(core)

    request_id = str(data.get("request_id") or "").strip() or secrets.token_urlsafe(16)
    amount = gov._as_int(data.get("amount"))
    fund_key = str(data.get("fund_key") or "state_treasury")
    note = str(data.get("note") or "").strip()
    if amount < int(contributions.MIN_CONTRIBUTION):
        raise ValueError(f"Минимальный вклад — {gov._fmt(contributions.MIN_CONTRIBUTION)} влияния.")
    if amount > MAX_SQLITE_INTEGER:
        raise ValueError("Сумма слишком большая для хранения в базе данных.")
    if fund_key not in contributions.FUND_SPECS:
        raise ValueError("Выбран неизвестный государственный фонд.")
    if len(note) > 200:
        raise ValueError("Комментарий к вкладу не может быть длиннее 200 символов.")

    mapping = {
        "general": "finance_ministry",
        "reserve": "reserve",
        "social": "social_fund",
        "security": "oversight",
        "elections": "election_commission",
        "development": "event_fund",
    }
    if fund_key != "state_treasury" and fund_key not in mapping:
        raise ValueError("Для выбранного фонда не настроен государственный баланс.")

    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT amount,fund_key,result_text FROM government_contribution_requests_v179 WHERE request_id=?",
        (request_id,),
    )
    prior = await cursor.fetchone()
    if prior is not None:
        return int(prior["amount"]), str(contributions.FUND_SPECS.get(str(prior["fund_key"]), {"title": prior["fund_key"]})["title"])
    now = gov._now()
    contribution_id = secrets.token_urlsafe(12)
    title = str(contributions.FUND_SPECS[fund_key]["title"])
    async with core.db.lock:
        try:
            cursor = await conn.execute(
                "SELECT amount,fund_key,result_text FROM government_contribution_requests_v179 WHERE request_id=?",
                (request_id,),
            )
            prior = await cursor.fetchone()
            if prior is not None:
                return int(prior["amount"]), str(contributions.FUND_SPECS.get(str(prior["fund_key"]), {"title": prior["fund_key"]})["title"])
            cursor = await conn.execute(
                """UPDATE players SET points=points-?,updated_at=?
                WHERE chat_id=? AND user_id=? AND points>=?""",
                (amount, now, int(chat_id), int(user_id), amount),
            )
            if int(cursor.rowcount or 0) <= 0:
                cursor = await conn.execute(
                    "SELECT points FROM players WHERE chat_id=? AND user_id=?",
                    (int(chat_id), int(user_id)),
                )
                row = await cursor.fetchone()
                raise ValueError(
                    f"Недостаточно влияния. Твой баланс: {gov._fmt(int(row['points'] if row else 0))}."
                )

            if fund_key == "state_treasury":
                await conn.execute(
                    "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
                    (amount, now, int(chat_id)),
                )
                await gov._treasury_log(
                    core,
                    int(chat_id),
                    amount,
                    "Добровольный вклад в общую казну" + (f" — {note}" if note else ""),
                    "voluntary_state_treasury_v179",
                    contribution_id,
                    int(user_id),
                )
            else:
                await fund_bridge.credit_fund_locked(
                    core, int(chat_id), mapping[fund_key], amount
                )

            await conn.execute(
                """INSERT INTO government_contributions_v150(
                contribution_id,chat_id,user_id,amount,fund_key,note,created_at)
                VALUES(?,?,?,?,?,?,?)""",
                (contribution_id, int(chat_id), int(user_id), amount, fund_key, note, now),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (int(chat_id), int(user_id), -amount, f"government_contribution_{fund_key}_v179", now),
            )
            result_text = f"Вклад {gov._fmt(amount)} влияния зачислен в «{title}»."
            await conn.execute(
                """INSERT INTO government_contribution_requests_v179(
                request_id,chat_id,user_id,amount,fund_key,result_text,created_at)
                VALUES(?,?,?,?,?,?,?)""",
                (request_id, int(chat_id), int(user_id), amount, fund_key, result_text, now),
            )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return amount, title


def source_title(key: str) -> str:
    return SOURCE_TITLES.get(str(key), str(key))
