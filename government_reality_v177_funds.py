from __future__ import annotations

from typing import Any

import government_treasury_contributions_v150 as contributions
import government_treasury_management_v164 as treasury
import government_v127 as gov

from government_reality_v177_common import LEGACY_TO_STRUCTURE, ensure_schema

_ORIGINAL_STRUCTURE_ROWS = treasury._structure_rows


async def migrate_funds(core: Any) -> None:
    """Move every remaining Reality 150 earmark once into the canonical Reality 164 balance."""
    await ensure_schema(core)
    await contributions._ensure_schema(core)
    await treasury._ensure_schema(core)
    conn = core.db._require_connection()
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT chat_id,fund_key,amount FROM government_fund_balances_v150 WHERE amount>0"
        )
        rows = list(await cursor.fetchall())
        for row in rows:
            chat_id = int(row["chat_id"])
            legacy_key = str(row["fund_key"])
            structure_key = LEGACY_TO_STRUCTURE.get(legacy_key)
            if not structure_key:
                continue
            cursor2 = await conn.execute(
                "SELECT 1 FROM government_fund_migrations_v177 WHERE chat_id=? AND legacy_key=?",
                (chat_id, legacy_key),
            )
            if await cursor2.fetchone() is not None:
                await conn.execute(
                    "UPDATE government_fund_balances_v150 SET amount=0,updated_at=? WHERE chat_id=? AND fund_key=?",
                    (gov._now(), chat_id, legacy_key),
                )
                continue
            amount = max(0, int(row["amount"] or 0))
            if amount <= 0:
                continue
            now = gov._now()
            await gov._ensure_state(core, chat_id)
            cursor3 = await conn.execute("SELECT treasury FROM government_state_v127 WHERE chat_id=?", (chat_id,))
            treasury_row = await cursor3.fetchone()
            if treasury_row is None or int(treasury_row["treasury"] or 0) < amount:
                raise RuntimeError(f"Фонд {legacy_key} содержит неподтверждённый остаток {amount}: в казне недостаточно средств для безопасной миграции.")
            await conn.execute("UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?", (amount, now, chat_id))
            await conn.execute(
                """INSERT INTO government_structure_funds_v164(chat_id,structure_key,balance,updated_at)
                VALUES(?,?,?,?) ON CONFLICT(chat_id,structure_key) DO UPDATE SET
                balance=government_structure_funds_v164.balance+excluded.balance,updated_at=excluded.updated_at""",
                (chat_id, structure_key, amount, now),
            )
            await conn.execute(
                "UPDATE government_fund_balances_v150 SET amount=0,updated_at=? WHERE chat_id=? AND fund_key=?",
                (now, chat_id, legacy_key),
            )
            await conn.execute(
                "INSERT INTO government_fund_migrations_v177(chat_id,legacy_key,structure_key,amount,migrated_at) VALUES(?,?,?,?,?)",
                (chat_id, legacy_key, structure_key, amount, now),
            )
        await conn.commit()


async def fund_balance(core: Any, chat_id: int, structure_key: str) -> int:
    await migrate_funds(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT balance FROM government_structure_funds_v164 WHERE chat_id=? AND structure_key=?",
        (int(chat_id), str(structure_key)),
    )
    row = await cursor.fetchone()
    return int(row["balance"] if row else 0)


async def debit_fund_locked(core: Any, chat_id: int, structure_key: str, amount: int) -> None:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """UPDATE government_structure_funds_v164 SET balance=balance-?,updated_at=?
        WHERE chat_id=? AND structure_key=? AND balance>=?""",
        (int(amount), gov._now(), int(chat_id), str(structure_key), int(amount)),
    )
    if int(cursor.rowcount or 0) <= 0:
        raise ValueError("Баланс фонда изменился: средств уже недостаточно.")


async def credit_fund_locked(core: Any, chat_id: int, structure_key: str, amount: int) -> None:
    conn = core.db._require_connection()
    await conn.execute(
        """INSERT INTO government_structure_funds_v164(chat_id,structure_key,balance,updated_at)
        VALUES(?,?,?,?) ON CONFLICT(chat_id,structure_key) DO UPDATE SET
        balance=government_structure_funds_v164.balance+excluded.balance,updated_at=excluded.updated_at""",
        (int(chat_id), str(structure_key), int(amount), gov._now()),
    )


async def structures_state(core: Any, chat_id: int) -> list[dict[str, Any]]:
    await migrate_funds(core)
    rows = await _ORIGINAL_STRUCTURE_ROWS(core, int(chat_id))
    conn = core.db._require_connection()
    result: list[dict[str, Any]] = []
    for item in rows:
        key = str(item["key"])
        cursor = await conn.execute(
            """SELECT amount,reason,created_at FROM government_treasury_operations_v164
            WHERE chat_id=? AND target_type='structure' AND target_key=?
            ORDER BY created_at DESC LIMIT 1""",
            (int(chat_id), key),
        )
        income = await cursor.fetchone()
        cursor = await conn.execute(
            """SELECT amount,detail,created_at FROM government_property_operations_v176
            WHERE chat_id=? AND operation_type='program_start' AND json_extract(payload_json,'$.fund_key')=?
            ORDER BY created_at DESC LIMIT 1""",
            (int(chat_id), key),
        )
        expense = await cursor.fetchone()
        result.append({
            **item,
            "source": "Единый государственный баланс Reality 177",
            "last_income": ({"amount": int(income["amount"]), "detail": str(income["reason"]), "created_at": int(income["created_at"])} if income else None),
            "last_expense": ({"amount": int(expense["amount"]), "detail": str(expense["detail"]), "created_at": int(expense["created_at"])} if expense else None),
            "empty_hint": "Финансирование не выделено. Президент или министр финансов может перевести средства из общего бюджета.",
        })
    return result


def install_fund_bridge(core: Any) -> None:
    if getattr(core, "_government_reality_v177_funds_installed", False):
        return
    core._government_reality_v177_funds_installed = True

    original_connect = core.Database.connect
    async def connect_v177(self: Any) -> None:
        await original_connect(self)
        await migrate_funds(core)
    core.Database.connect = connect_v177

    original_contribute = contributions._contribute
    async def contribute_v177(core_arg: Any, chat_id: int, user_id: int, amount: int, fund_key: str, note: str):
        value, title = await original_contribute(core_arg, chat_id, user_id, amount, fund_key, note)
        structure_key = LEGACY_TO_STRUCTURE.get(str(fund_key))
        if structure_key:
            conn = core_arg.db._require_connection()
            async with core_arg.db.lock:
                cursor = await conn.execute(
                    "SELECT amount FROM government_fund_balances_v150 WHERE chat_id=? AND fund_key=?",
                    (int(chat_id), str(fund_key)),
                )
                row = await cursor.fetchone()
                move = min(int(value), int(row["amount"] if row else 0))
                if move > 0:
                    cursor2 = await conn.execute("SELECT treasury FROM government_state_v127 WHERE chat_id=?", (int(chat_id),))
                    state = await cursor2.fetchone()
                    if state is None or int(state["treasury"] or 0) < move:
                        raise RuntimeError("Вклад записан в старый фонд, но не подтверждён свободной казной.")
                    await conn.execute(
                        "UPDATE government_fund_balances_v150 SET amount=amount-?,updated_at=? WHERE chat_id=? AND fund_key=?",
                        (move, gov._now(), int(chat_id), str(fund_key)),
                    )
                    await conn.execute("UPDATE government_state_v127 SET treasury=treasury-?,updated_at=? WHERE chat_id=?", (move, gov._now(), int(chat_id)))
                    await credit_fund_locked(core_arg, int(chat_id), structure_key, move)
                    await conn.commit()
        return value, title
    contributions._contribute = contribute_v177

    original_serialize = contributions._serialize_contributions
    async def serialize_v177(core_arg: Any, chat_id: int, user_id: int):
        await migrate_funds(core_arg)
        payload = await original_serialize(core_arg, chat_id, user_id)
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT structure_key,balance FROM government_structure_funds_v164 WHERE chat_id=?",
            (int(chat_id),),
        )
        balances = {str(row["structure_key"]): int(row["balance"] or 0) for row in await cursor.fetchall()}
        for fund in payload.get("funds", []):
            structure_key = LEGACY_TO_STRUCTURE.get(str(fund.get("key")))
            if structure_key:
                fund["amount"] = balances.get(structure_key, 0)
        return payload
    contributions._serialize_contributions = serialize_v177
